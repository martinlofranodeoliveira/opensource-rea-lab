"""Pure, sanitized SARIF 2.1.0 interchange for offline audit findings.

The original report's messages and metadata are deliberately not exported: an
archive error may include a host path. Findings retain their order, rule codes
and severity, with fixed neutral text and a bounded, escaped member label. No
locations are emitted because archive members are not checked-out source files.

This serializer validates required fields, not report provenance or agreement
between status and findings. Callers own the size of the input already in memory;
``max_findings`` limits output records. It does not execute or extract packages,
read files or use the network. Review the original audit report offline; neither
the audit nor this export is a malware verdict.
"""

import json
import re


_SCHEMA_URI = (
    "https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/schemas/"
    "sarif-schema-2.1.0.json"
)
_CODE = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*", flags=re.ASCII)
_INVALID = "Invalid or unbounded offline audit report"
_OVERSIZE_MEMBER = "member omitted: display exceeds 240 characters"
_UNSAFE_MEMBER = "unsafe member omitted"
_SYNTAX = "<>&{}[]()"


def _member_display(member: str) -> str:
    # Check raw length before splitting or encoding an arbitrarily large value.
    if len(member) > 238:
        return _OVERSIZE_MEMBER
    path = member[:-1] if member.endswith("/") else member
    parts = path.split("/")
    if (not path or parts[0] != "package"
            or any(part in ("", ".", "..") for part in parts)
            or "\\" in member or ":" in member
            or any(ord(char) < 32 or ord(char) == 127 for char in member)):
        return _UNSAFE_MEMBER
    display = json.dumps(member, ensure_ascii=True)
    # SARIF text can interpret links, placeholders and HTML. JSON quoting alone
    # does not neutralize those syntaxes; keep their characters as literal escapes.
    display = "".join(f"\\u{ord(char):04x}" if char in _SYNTAX else char
                      for char in display)
    return display if len(display) <= 240 else _OVERSIZE_MEMBER


def to_sarif(report: dict, *, max_findings: int = 20000) -> dict:
    """Return a fresh SARIF document, or a generic ValueError for invalid input.

    Unknown valid snake_case codes are supported. Extra fields are ignored, never
    copied or traversed. Member display is at most 240 ASCII characters including
    quotes; unsafe names and over-budget labels use fixed omission text instead.
    """
    if (isinstance(max_findings, bool) or not isinstance(max_findings, int)
            or max_findings <= 0 or not isinstance(report, dict)
            or report.get("schema") != "npm-tarball-audit/v1"
            or report.get("status") not in ("pass", "warning", "fail")
            or report.get("package_executed") is not False
            or report.get("files_extracted") is not False):
        raise ValueError(_INVALID)
    findings = report.get("findings")
    if not isinstance(findings, list) or len(findings) > max_findings:
        raise ValueError(_INVALID)

    # Validate the entire collection before building a result document.
    codes: set[str] = set()
    for finding in findings:
        if not isinstance(finding, dict):
            raise ValueError(_INVALID)
        code, message = finding.get("code"), finding.get("message")
        if (finding.get("level") not in ("error", "warning")
                or not isinstance(code, str) or not 1 <= len(code) <= 64
                or _CODE.fullmatch(code) is None
                or not isinstance(message, str) or not message.strip()
                or ("member" in finding and not isinstance(finding["member"], str))):
            raise ValueError(_INVALID)
        codes.add(code)

    ordered_codes = sorted(codes)
    rule_indexes = {code: index for index, code in enumerate(ordered_codes)}
    rules = [{"id": "NTA/" + code,
              "shortDescription": {"text": "Audit check " + code}}
             for code in ordered_codes]
    results = []
    for finding in findings:
        code = finding["code"]
        text = "Audit check " + code + "."
        if "member" in finding:
            text += " Member: " + _member_display(finding["member"]) + "."
        results.append({"ruleId": "NTA/" + code,
                        "ruleIndex": rule_indexes[code],
                        "level": finding["level"],
                        "message": {"text": text}})
    return {
        "$schema": _SCHEMA_URI,
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {"name": "npm-tarball-audit", "rules": rules}},
            "results": results,
            "properties": {
                "originalReportRequired": True,
                "scope": "Review the original audit report offline. "
                         "This export is not a malware verdict.",
            },
        }],
    }
