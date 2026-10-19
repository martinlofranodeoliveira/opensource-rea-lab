"""Load a bounded JSON audit inventory without reading files or executing code.

``parse_inventory_report(text, *, max_bytes=16777216, max_depth=64,
max_entries=20000)`` accepts explicit UTF-8-encodable text. Positive integer
budgets exclude bools. UTF-8 bytes and JSON container depth are checked before
parsing; the root object counts as depth 1. Duplicate keys and nonfinite numbers
are rejected throughout the JSON document, including ignored metadata.

The root must declare schema ``npm-tarball-audit/v1``, status ``pass`` or
``warning``, both ``package_executed`` and ``files_extracted`` exactly false,
and an explicit ``inventory`` list. Empty inventories are valid. Inventory
records follow ``compare_inventories`` validation and are returned as fresh,
normalized dictionaries sorted by path. Other report metadata is not returned;
this boundary does not validate the complete report schema or prove provenance.

Example::

    from npm_tarball_audit.report import parse_inventory_report

    inventory = parse_inventory_report(report_json_text, max_entries=5000)

Failed reports are rejected because their inventories may be partial. An
explicit manual comparison can still use ``compare_inventories`` directly.
Assess status and findings separately: unchanged inventory does not prove
complete package equivalence, and parsing or comparison is not a malware or
safety verdict. This pure loader performs no file/archive access or extraction;
the caller owns bounded file reading. Entrypoint comparison is outside this API.
"""

import json
import math

from .compare import compare_inventories


def _check_depth(text: str, maximum: int) -> None:
    depth = 0
    in_string = False
    escaped = False
    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
        elif character == '"':
            in_string = True
        elif character in "{[":
            depth += 1
            if depth > maximum:
                raise ValueError("Report exceeds the JSON depth budget")
        elif character in "}]":
            depth -= 1
            if depth < 0:
                raise ValueError("Invalid audit report JSON")


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate report JSON key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError("Nonfinite report JSON number")


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Nonfinite report JSON number")
    return number


def parse_inventory_report(
    text: str,
    *,
    max_bytes: int = 16 * 1024 * 1024,
    max_depth: int = 64,
    max_entries: int = 20000,
) -> list[dict]:
    """Return validated inventory records; reject invalid input with ValueError."""
    for limit in (max_bytes, max_depth, max_entries):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("Report budgets must be positive integers")
    if not isinstance(text, str):
        raise ValueError("Report text must be a string")
    # UTF-8 has at least one byte per code point; avoid a large extra allocation.
    if len(text) > max_bytes:
        raise ValueError("Report exceeds the UTF-8 byte budget")
    try:
        size = len(text.encode("utf-8", errors="strict"))
    except UnicodeEncodeError:
        raise ValueError("Report text must be valid UTF-8") from None
    if size > max_bytes:
        raise ValueError("Report exceeds the UTF-8 byte budget")
    _check_depth(text, max_depth)
    try:
        report = json.loads(text, object_pairs_hook=_unique_object,
                            parse_constant=_reject_constant, parse_float=_finite_float)
    except (ValueError, RecursionError):
        raise ValueError("Invalid audit report JSON") from None
    if not isinstance(report, dict) or report.get("schema") != "npm-tarball-audit/v1":
        raise ValueError("Unsupported audit report schema")
    if report.get("status") not in ("pass", "warning"):
        raise ValueError("Report must have pass or warning status")
    if report.get("package_executed") is not False or report.get("files_extracted") is not False:
        raise ValueError("Report must declare offline inspection without extraction")
    if "inventory" not in report:
        raise ValueError("Report must include an explicit inventory")
    try:
        return compare_inventories([], report["inventory"], max_entries=max_entries)["added"]
    except ValueError:
        raise ValueError("Invalid report inventory") from None
