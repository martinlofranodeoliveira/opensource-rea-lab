"""Inspect a gzip-compressed npm tar archive using only the Python standard library."""

from __future__ import annotations

import base64
import gzip
import hashlib
import hmac
import io
import json
import re
import tarfile
import zlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO


@dataclass(frozen=True)
class Limits:
    """Independent budgets, enforced before reading arbitrary member payloads."""

    archive_bytes: int = 64 * 1024 * 1024
    stream_bytes: int = 256 * 1024 * 1024
    member_bytes: int = 32 * 1024 * 1024
    total_file_bytes: int = 128 * 1024 * 1024
    manifest_bytes: int = 1024 * 1024
    members: int = 20_000

    def __post_init__(self) -> None:
        if any(not isinstance(v, int) or v <= 0 for v in vars(self).values()):
            raise ValueError("All limits must be positive integers")


class BudgetExceeded(ValueError):
    pass


class _LimitedReader(io.RawIOBase):
    """Also bounds tar headers, padding, GNU longnames and PAX metadata."""

    def __init__(self, source: BinaryIO, maximum: int):
        self.source, self.maximum, self.count = source, maximum, 0

    def readable(self) -> bool:
        return True

    def read(self, size: int = -1) -> bytes:
        remaining = self.maximum - self.count
        wanted = remaining + 1 if size < 0 else min(size, remaining + 1)
        data = self.source.read(wanted)
        self.count += len(data)
        if self.count > self.maximum:
            raise BudgetExceeded("Decompressed stream exceeds its byte budget")
        return data


def _path_problem(name: str) -> str | None:
    if not name or "\x00" in name or "\\" in name:
        return "empty, NUL or backslash-containing path"
    parts = name.rstrip("/").split("/")
    if name.startswith("/") or re.match(r"^[A-Za-z]:", name):
        return "absolute path"
    if any(":" in part for part in parts):
        return "colon-containing path may name a Windows drive or alternate data stream"
    if ".." in parts or "." in parts or "" in parts:
        return "non-canonical or traversing path"
    if parts[0] != "package":
        return "member is outside the npm package/ root"
    if any(ord(c) < 32 or ord(c) == 127 for c in name):
        return "control character in path"
    return None


def _object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _invalid_constant(value: str) -> object:
    raise ValueError(f"Non-JSON numeric constant: {value}")


def _targets(manifest: dict) -> list[tuple[str, str, bool]]:
    """Yield declared local entrypoints; wildcard patterns are reported separately."""
    out: list[tuple[str, str, bool]] = []
    for field in ("main", "module", "types", "typings"):
        value = manifest.get(field)
        if isinstance(value, str):
            out.append((field, value, False))
    bins = manifest.get("bin", {})
    if isinstance(bins, str):
        out.append(("bin", bins, True))
    elif isinstance(bins, dict):
        out.extend((f"bin.{k}", v, True) for k, v in bins.items() if isinstance(v, str))
    browser = manifest.get("browser")
    if isinstance(browser, str):
        out.append(("browser", browser, False))
    elif isinstance(browser, dict):
        out.extend((f"browser.{k}", v, False) for k, v in browser.items()
                   if isinstance(v, str) and v.startswith("."))

    def walk(value: object, field: str) -> None:
        if isinstance(value, str):
            out.append((field, value, True))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                walk(item, f"{field}[{i}]")
        elif isinstance(value, dict):
            for key, item in value.items():
                walk(item, f"{field}.{key}")
    if "exports" in manifest:
        walk(manifest["exports"], "exports")
    return out


def audit(path: str | Path, *, limits: Limits | None = None,
          expected_name: str | None = None, expected_version: str | None = None,
          integrity: str | None = None, include_inventory: bool = False) -> dict:
    """Return a deterministic, JSON-serializable report without extracting files.

    A passing report means the implemented checks passed. It is not a malware,
    dependency-vulnerability, publisher-identity or runtime-behavior verdict.
    """
    limits = limits or Limits()
    findings: list[dict] = []
    report: dict = {
        "schema": "npm-tarball-audit/v1", "status": "pass", "sha256": None,
        "archive_bytes": 0, "decompressed_bytes_read": 0,
        "member_count": 0, "regular_file_bytes": 0, "package": None,
        "findings": findings,
        "scope": "offline archive metadata, paths, local entrypoints and integrity only",
        "package_executed": False, "files_extracted": False,
    }
    inventory: list[dict] = []

    def add(level: str, code: str, message: str, member: str | None = None) -> None:
        finding = {"level": level, "code": code, "message": message}
        if member is not None:
            finding["member"] = member
        findings.append(finding)

    manifest_data: bytes | None = None
    files: set[str] = set()
    seen: set[str] = set()
    try:
        # Read at most the configured compressed budget, even if the file grows.
        with open(path, "rb") as source:
            compressed = source.read(limits.archive_bytes + 1)
        report["archive_bytes"] = len(compressed)
        if len(compressed) > limits.archive_bytes:
            raise BudgetExceeded("Compressed archive exceeds its byte budget")
        report["sha256"] = hashlib.sha256(compressed).hexdigest()
        if integrity is not None:
            if not integrity.startswith("sha512-"):
                raise ValueError("Integrity must be one sha512- base64 SRI token")
            expected = base64.b64decode(integrity[7:], validate=True)
            if len(expected) != 64:
                raise ValueError("SHA-512 integrity has the wrong length")
            if not hmac.compare_digest(expected, hashlib.sha512(compressed).digest()):
                add("error", "integrity_mismatch", "Archive does not match the supplied SHA-512 integrity")
        with gzip.GzipFile(fileobj=io.BytesIO(compressed), mode="rb") as gz:
            bounded = _LimitedReader(gz, limits.stream_bytes)
            with tarfile.open(fileobj=bounded, mode="r|") as archive:
                for member in archive:
                    report["member_count"] += 1
                    if report["member_count"] > limits.members:
                        raise BudgetExceeded("Archive exceeds its member-count budget")
                    name = member.name.rstrip("/")
                    problem = _path_problem(member.name)
                    if problem:
                        add("error", "unsafe_path", problem, member.name)
                    if name in seen:
                        add("error", "duplicate_member", "Duplicate member path; extraction order would affect its contents", member.name)
                    seen.add(name)
                    if member.issym() or member.islnk():
                        add("error", "link_member", "Symbolic and hard links are not accepted", member.name)
                        continue
                    if not member.isfile() and not member.isdir():
                        add("error", "special_member", "Only regular files and directories are accepted", member.name)
                        continue
                    if member.sparse is not None:
                        add("error", "sparse_member", "Sparse file metadata is not accepted", member.name)
                        continue
                    if member.mode & 0o6000:
                        add("error", "privileged_mode", "setuid/setgid mode bits are not accepted", member.name)
                    if not member.isfile():
                        continue
                    if member.size < 0 or member.size > limits.member_bytes:
                        raise BudgetExceeded("A regular file exceeds its byte budget")
                    report["regular_file_bytes"] += member.size
                    if report["regular_file_bytes"] > limits.total_file_bytes:
                        raise BudgetExceeded("Regular files exceed their total byte budget")
                    if name == "package/package.json" and member.size > limits.manifest_bytes:
                        raise BudgetExceeded("package.json exceeds its byte budget")
                    files.add(name)
                    stream = archive.extractfile(member)
                    assert stream is not None
                    digest = hashlib.sha256()
                    data = bytearray()
                    count = 0
                    while chunk := stream.read(64 * 1024):
                        count += len(chunk)
                        digest.update(chunk)
                        if name == "package/package.json":
                            data.extend(chunk)
                    if count != member.size:
                        raise ValueError("Member payload length disagrees with its header")
                    if name == "package/package.json":
                        manifest_data = bytes(data)
                    if include_inventory:
                        inventory.append({"path": name, "bytes": count, "sha256": digest.hexdigest()})
            # Consume the remainder too: gzip CRC/truncation and decompression budget
            # must be checked even after tar's first end-of-archive marker.
            while bounded.read(64 * 1024):
                pass
            report["decompressed_bytes_read"] = bounded.count
        if manifest_data is None:
            add("error", "manifest_missing", "package/package.json is missing")
        else:
            manifest = json.loads(manifest_data.decode("utf-8"), object_pairs_hook=_object,
                                  parse_constant=_invalid_constant)
            if not isinstance(manifest, dict):
                raise ValueError("package.json must be a JSON object")
            report["package"] = {k: manifest[k] for k in ("name", "version", "license") if k in manifest}
            for field in ("name", "version"):
                if not isinstance(manifest.get(field), str) or not manifest[field].strip():
                    add("error", "manifest_identity", f"package.json requires a nonempty {field}")
            for field, expected in (("name", expected_name), ("version", expected_version)):
                if expected is not None and manifest.get(field) != expected:
                    add("error", "identity_mismatch", f"Package {field} does not match the expected value")
            if not manifest.get("license"):
                add("warning", "license_metadata_missing", "No license metadata is declared; verify reuse rights separately")
            if not any(PurePosixPath(f).name.lower().startswith(("license", "licence", "copying")) for f in files):
                add("warning", "license_file_missing", "No license/copying file was found; metadata alone is not a legal review")
            scripts = manifest.get("scripts", {})
            if isinstance(scripts, dict):
                for name in ("preinstall", "install", "postinstall", "prepare"):
                    if name in scripts:
                        add("warning", "lifecycle_script", f"Lifecycle script {name!r} is declared; it was not executed")
            for field, target, exact in _targets(manifest):
                relative = target[2:] if target.startswith("./") else target
                if _path_problem("package/" + relative):
                    add("error", "unsafe_entrypoint", f"{field} points outside a canonical package path")
                    continue
                if "*" in relative:
                    add("warning", "entrypoint_pattern", f"{field} uses a wildcard; per-export resolution is outside this check")
                    continue
                candidate = "package/" + relative
                candidates = [candidate]
                if not exact:
                    candidates += [candidate + suffix for suffix in (".js", ".json", ".node", "/index.js", "/index.json", "/index.node")]
                if not any(c in files for c in candidates):
                    add("error", "entrypoint_missing", f"Declared {field} target is absent: {target!r}")
    except BudgetExceeded as exc:
        add("error", "budget_exceeded", str(exc))
    except (OSError, EOFError, tarfile.TarError, ValueError, RecursionError, zlib.error) as exc:
        add("error", "invalid_archive", f"{type(exc).__name__}: {exc}")
    if include_inventory:
        report["inventory"] = inventory
    if any(f["level"] == "error" for f in findings):
        report["status"] = "fail"
    elif findings:
        report["status"] = "warning"
    return report
