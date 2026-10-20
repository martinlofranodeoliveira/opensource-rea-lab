"""Pure declarative comparison of main/bin/exports declarations.

API:
    compare_entrypoints(before, after) -> dict

Compares only explicitly supplied package metadata. Reads no files,
archives, network, or audit reports and never executes, resolves,
normalizes, or infers targets. Not a safety or compatibility verdict.

Example:
    from npm_tarball_audit.entrypoints import compare_entrypoints

    before = {"main": "index.js", "exports": {".": "./index.js"}}
    after = {"main": "index.js", "exports": {".": "./esm.js"}}
    result = compare_entrypoints(before, after)
"""

from __future__ import annotations

import math

__all__ = ["compare_entrypoints"]

_INVALID_MESSAGE = "Invalid entrypoint metadata"
_MAX_TOP_FIELDS = 128
_MAX_TOP_KEY_LEN = 1024
_MAX_STR_LEN = 1024
_MAX_NODES = 4096
_MAX_DEPTH = 16
_MAX_TOTAL_STR = 16384
_INT_MIN = -(2**53 - 1)
_INT_MAX = 2**53 - 1
_FIELDS = ("main", "bin", "exports")
_NoneType = type(None)


def _invalid() -> ValueError:
    return ValueError(_INVALID_MESSAGE)


def _has_surrogate(text: str) -> bool:
    for ch in text:
        code = ord(ch)
        if 0xD800 <= code <= 0xDFFF:
            return True
    return False


def _validate_top(value: object) -> None:
    if type(value) is not dict:
        raise _invalid()
    if len(value) > _MAX_TOP_FIELDS:
        raise _invalid()
    for key in value.keys():
        if type(key) is not str:
            raise _invalid()
        if len(key) > _MAX_TOP_KEY_LEN:
            raise _invalid()
        if _has_surrogate(key):
            raise _invalid()


def _validate_side(values: list[object]) -> None:
    total_nodes = 0
    total_str_len = 0
    ancestors: set[int] = set()

    def check(node: object, cdepth: int) -> None:
        nonlocal total_nodes, total_str_len
        t = type(node)
        if t is dict:
            if cdepth > _MAX_DEPTH:
                raise _invalid()
            nid = id(node)
            if nid in ancestors:
                raise _invalid()
            total_nodes += 1
            if total_nodes > _MAX_NODES:
                raise _invalid()
            ancestors.add(nid)
            try:
                for k, v in node.items():
                    if type(k) is not str:
                        raise _invalid()
                    if len(k) > _MAX_STR_LEN:
                        raise _invalid()
                    if _has_surrogate(k):
                        raise _invalid()
                    total_str_len += len(k)
                    if total_str_len > _MAX_TOTAL_STR:
                        raise _invalid()
                    check(v, cdepth + 1)
            finally:
                ancestors.remove(nid)
        elif t is list:
            if cdepth > _MAX_DEPTH:
                raise _invalid()
            nid = id(node)
            if nid in ancestors:
                raise _invalid()
            total_nodes += 1
            if total_nodes > _MAX_NODES:
                raise _invalid()
            ancestors.add(nid)
            try:
                for item in node:
                    check(item, cdepth + 1)
            finally:
                ancestors.remove(nid)
        elif t is str:
            if len(node) > _MAX_STR_LEN:  # type: ignore[arg-type]
                raise _invalid()
            if _has_surrogate(node):  # type: ignore[arg-type]
                raise _invalid()
            total_nodes += 1
            if total_nodes > _MAX_NODES:
                raise _invalid()
            total_str_len += len(node)  # type: ignore[arg-type]
            if total_str_len > _MAX_TOTAL_STR:
                raise _invalid()
        elif t is int:
            if node < _INT_MIN or node > _INT_MAX:  # type: ignore[operator]
                raise _invalid()
            total_nodes += 1
            if total_nodes > _MAX_NODES:
                raise _invalid()
        elif t is float:
            if not math.isfinite(node):  # type: ignore[arg-type]
                raise _invalid()
            total_nodes += 1
            if total_nodes > _MAX_NODES:
                raise _invalid()
        elif t is bool or t is _NoneType:
            total_nodes += 1
            if total_nodes > _MAX_NODES:
                raise _invalid()
        else:
            raise _invalid()

    for root in values:
        rt = type(root)
        if rt is dict or rt is list:
            check(root, 1)
        else:
            check(root, 0)


def _equal(first: object, second: object, exports_mode: bool) -> bool:
    tf = type(first)
    ts = type(second)
    if tf is not ts:
        return False
    if tf is dict:
        if len(first) != len(second):  # type: ignore[arg-type]
            return False
        if exports_mode:
            first_keys = list(first.keys())  # type: ignore[union-attr]
            second_keys = list(second.keys())  # type: ignore[union-attr]
            if first_keys != second_keys:
                return False
            for k in first_keys:  # type: ignore[union-attr]
                if not _equal(first[k], second[k], True):  # type: ignore[index]
                    return False
            return True
        if set(first.keys()) != set(second.keys()):  # type: ignore[union-attr]
            return False
        for k in first.keys():  # type: ignore[union-attr]
            if not _equal(first[k], second[k], False):  # type: ignore[index]
                return False
        return True
    if tf is list:
        if len(first) != len(second):  # type: ignore[arg-type]
            return False
        for a, b in zip(first, second):  # type: ignore[arg-type]
            if not _equal(a, b, exports_mode):
                return False
        return True
    if tf is str:
        return first == second
    if tf is int:
        return first == second
    if tf is float:
        return first == second  # type: ignore[operator]
    if tf is bool:
        return first == second
    if tf is _NoneType:
        return True
    return False


def _copy_sorted(node: object) -> object:
    t = type(node)
    if t is dict:
        fresh: dict[object, object] = {}
        for k in sorted(node.keys()):  # type: ignore[arg-type]
            fresh[k] = _copy_sorted(node[k])  # type: ignore[index]
        return fresh
    if t is list:
        return [_copy_sorted(item) for item in node]  # type: ignore[union-attr]
    return node


def _copy_preserve(node: object) -> object:
    t = type(node)
    if t is dict:
        fresh2: dict[object, object] = {}
        for k, v in node.items():  # type: ignore[union-attr]
            fresh2[k] = _copy_preserve(v)
        return fresh2
    if t is list:
        return [_copy_preserve(item) for item in node]  # type: ignore[union-attr]
    return node


def compare_entrypoints(before: dict, after: dict) -> dict:
    """Compare declared ``main``/``bin``/``exports`` without execution.

    Each side must be an exact built-in ``dict`` with at most 128 fields
    whose keys are exact ``str`` values of at most 1024 code points with
    no surrogates. Only literal ``main``, ``bin`` and ``exports`` values
    are inspected. Returns a fresh plain ``dict`` with exactly ``added``,
    ``removed``, ``changed`` and ``unchanged_count``. Invalid inputs raise
    ``ValueError("Invalid entrypoint metadata")`` without echoing input.
    """
    try:
        _validate_top(before)
    except Exception:
        raise ValueError(_INVALID_MESSAGE) from None
    try:
        _validate_top(after)
    except Exception:
        raise ValueError(_INVALID_MESSAGE) from None
    before_selected: dict[str, object] = {}
    after_selected: dict[str, object] = {}
    for field in _FIELDS:
        if field in before:
            before_selected[field] = before[field]
        if field in after:
            after_selected[field] = after[field]
    try:
        _validate_side(list(before_selected.values()))
    except Exception:
        raise ValueError(_INVALID_MESSAGE) from None
    try:
        _validate_side(list(after_selected.values()))
    except Exception:
        raise ValueError(_INVALID_MESSAGE) from None
    added: list[dict[str, object]] = []
    removed: list[dict[str, object]] = []
    changed: list[dict[str, object]] = []
    unchanged_count = 0
    for field in _FIELDS:
        has_before = field in before_selected
        has_after = field in after_selected
        if not has_before and not has_after:
            continue
        if has_before and not has_after:
            if field == "exports":
                value = _copy_preserve(before_selected[field])
            else:
                value = _copy_sorted(before_selected[field])
            removed.append({"field": field, "value": value})
        elif not has_before and has_after:
            if field == "exports":
                value2 = _copy_preserve(after_selected[field])
            else:
                value2 = _copy_sorted(after_selected[field])
            added.append({"field": field, "value": value2})
        else:
            first = before_selected[field]
            second = after_selected[field]
            is_exports = field == "exports"
            if _equal(first, second, is_exports):
                unchanged_count += 1
            else:
                if is_exports:
                    b_copy = _copy_preserve(first)
                    a_copy = _copy_preserve(second)
                else:
                    b_copy = _copy_sorted(first)
                    a_copy = _copy_sorted(second)
                changed.append({"field": field, "before": b_copy, "after": a_copy})
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged_count": unchanged_count,
    }
