"""Pure, validated comparison of audit inventory records.

This module compares only explicitly supplied inventory lists produced by the
existing auditor. It does not read reports, files, archives, entrypoint
declarations, or any external state. It is not a malware verdict and does not
implement the full future CLI roadmap.

API:
    compare_inventories(before: list[dict], after: list[dict], *, max_entries: int = 20000) -> dict

Each inventory entry must be a dict with exactly these fields:
    path: canonical POSIX path rooted at package/
    bytes: nonnegative int, never bool
    sha256: exactly 64 hexadecimal ASCII characters, normalized to lowercase

Canonical path rules:
    - must be a string
    - must begin with package/
    - must have nonempty components
    - must not contain ., .., empty components, trailing slash, backslash,
      colon/drive forms, absolute paths, or C0/C1 control characters

max_entries is a positive int, excluding bool, and is applied independently to
each inventory. Exactly max_entries entries per side are allowed; more are
rejected. Inputs are not mutated, and output dictionaries do not alias inputs.

Example:
    from npm_tarball_audit.compare import compare_inventories

    before = [
        {"path": "package/index.js", "bytes": 10, "sha256": "0" * 64}
    ]
    after = [
        {"path": "package/index.js", "bytes": 10, "sha256": "1" * 64}
    ]
    result = compare_inventories(before, after)

Returns a dict with exactly these keys:
    added, removed, changed, unchanged_count

added contains after-only canonical entries.
removed contains before-only canonical entries.
changed contains dicts with exactly path, before, and after.
unchanged_count counts paths present in both inventories with equal bytes and
normalized sha256.
"""

from __future__ import annotations

import re
from typing import Any

_HEX_RE = re.compile(r"\A[0-9a-fA-F]{64}\Z")


def _validate_max_entries(max_entries: Any) -> int:
    if isinstance(max_entries, bool) or not isinstance(max_entries, int) or max_entries <= 0:
        raise ValueError("max_entries must be a positive integer")
    return max_entries


def _validate_path(path: Any) -> str:
    if not isinstance(path, str):
        raise ValueError("path must be a string")

    if not path:
        raise ValueError("path must be nonempty")

    if path.startswith("/"):
        raise ValueError("path must be relative")

    if "\\" in path:
        raise ValueError("path must not contain backslash")

    if ":" in path:
        raise ValueError("path must not contain colon")

    if any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in path):
        raise ValueError("path must not contain control characters")

    if path.endswith("/"):
        raise ValueError("path must not end with slash")

    if not path.startswith("package/"):
        raise ValueError("path must begin with package/")

    parts = path.split("/")
    if len(parts) < 2:
        raise ValueError("path must contain at least one component after package/")

    if any(part == "" for part in parts):
        raise ValueError("path must not contain empty components")

    if any(part == "." or part == ".." for part in parts):
        raise ValueError("path must not contain . or .. components")

    if parts[0] != "package":
        raise ValueError("path must be rooted at package/")

    return path


def _canonical_entry(entry: Any) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise ValueError("entry must be a dict")

    if set(entry.keys()) != {"path", "bytes", "sha256"}:
        raise ValueError("entry must contain exactly path, bytes and sha256 fields")

    path = _validate_path(entry["path"])

    size = entry["bytes"]
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise ValueError("bytes must be a nonnegative integer")

    digest = entry["sha256"]
    if not isinstance(digest, str) or not _HEX_RE.match(digest):
        raise ValueError("sha256 must be exactly 64 hexadecimal ASCII characters")

    return {
        "path": path,
        "bytes": size,
        "sha256": digest.lower(),
    }


def _build_index(inventory: list[dict], name: str, max_entries: int) -> dict[str, dict[str, Any]]:
    if not isinstance(inventory, list):
        raise ValueError("inventories must be lists")

    if len(inventory) > max_entries:
        raise ValueError(f"{name} inventory exceeds max_entries")

    index: dict[str, dict[str, Any]] = {}
    for entry in inventory:
        canonical = _canonical_entry(entry)
        path = canonical["path"]
        if path in index:
            raise ValueError(f"duplicate path in {name} inventory")
        index[path] = canonical

    return index


def compare_inventories(
    before: list[dict],
    after: list[dict],
    *,
    max_entries: int = 20000,
) -> dict[str, Any]:
    """Compare two explicitly supplied inventory lists.

    Returns a dict with exactly added, removed, changed, and unchanged_count.
    Output is deterministic and sorted by path. Inputs are not mutated.
    """
    max_entries = _validate_max_entries(max_entries)

    if not isinstance(before, list):
        raise ValueError("inventories must be lists")
    if not isinstance(after, list):
        raise ValueError("inventories must be lists")

    if len(before) > max_entries:
        raise ValueError("before inventory exceeds max_entries")
    if len(after) > max_entries:
        raise ValueError("after inventory exceeds max_entries")

    before_index = _build_index(before, "before", max_entries)
    after_index = _build_index(after, "after", max_entries)

    added = [
        after_index[path]
        for path in sorted(after_index)
        if path not in before_index
    ]

    removed = [
        before_index[path]
        for path in sorted(before_index)
        if path not in after_index
    ]

    changed: list[dict[str, Any]] = []
    unchanged_count = 0

    for path in sorted(set(before_index) & set(after_index)):
        before_entry = before_index[path]
        after_entry = after_index[path]

        if before_entry["bytes"] == after_entry["bytes"] and before_entry["sha256"] == after_entry["sha256"]:
            unchanged_count += 1
            continue

        changed.append(
            {
                "path": path,
                "before": dict(before_entry),
                "after": dict(after_entry),
            }
        )

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged_count": unchanged_count,
    }
