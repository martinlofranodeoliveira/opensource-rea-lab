"""Main entry declaration scan."""
import math
import re
import json
import unicodedata

_PAYLOAD_ERROR = "Invalid main payload or budget"
_DECL_ERROR = "Invalid main declaration"
_KIND_ABSENT = "absent"
_KIND_DECLARED = "declared"
_REASON_LENGTH = "value_length"
_REASON_SYNTAX = "value_syntax"
_KEY_MAIN = "main"
_KEY_BUDGET = "max_length"
_DEFAULT_BUDGET = 256
_MIN_BUDGET = 1
_MAX_BUDGET = 512

def _copy_text(value):
    result = ""
    for ch in value:
        result = result + ch
    return result

def _has_value_syntax(target):
    if "\\" in target:
        return True
    if ":" in target:
        return True
    for ch in target:
        code = ord(ch)
        if code < 32:
            return True
        if code == 127:
            return True
    if target[0:1] == "/":
        return True
    if target == ".":
        return True
    if target == "./":
        return True
    n = len(target)
    if n > 0:
        if target[n - 1:] == "/":
            return True
    rest = target
    if target[0:2] == "./":
        rest = target[2:n]
    seg = ""
    m = len(rest)
    i = 0
    while i < m:
        ch = rest[i:i + 1]
        if ch == "/":
            if seg == "":
                return True
            if seg == ".":
                return True
            if seg == "..":
                return True
            seg = ""
        else:
            seg = seg + ch
        i = i + 1
    if seg == "":
        return True
    if seg == ".":
        return True
    if seg == "..":
        return True
    return False

def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_PAYLOAD_ERROR)
    if _KEY_MAIN not in payload:
        raise ValueError(_PAYLOAD_ERROR)
    for key in payload:
        if key != _KEY_MAIN:
            if key != _KEY_BUDGET:
                raise ValueError(_PAYLOAD_ERROR)
    if _KEY_BUDGET in payload:
        budget = payload[_KEY_BUDGET]
    else:
        budget = _DEFAULT_BUDGET
    if type(budget) is not int:
        raise ValueError(_PAYLOAD_ERROR)
    if budget < _MIN_BUDGET:
        raise ValueError(_PAYLOAD_ERROR)
    if budget > _MAX_BUDGET:
        raise ValueError(_PAYLOAD_ERROR)
    main_value = payload[_KEY_MAIN]
    if main_value is None:
        kind_copy = _copy_text(_KIND_ABSENT)
        empty_reasons = []
        return {"present": False, "kind": kind_copy, "valid": True, "target": None, "reasons": empty_reasons}
    if not isinstance(main_value, str):
        raise ValueError(_DECL_ERROR)
    target = _copy_text(main_value)
    reasons = []
    tlen = len(target)
    if tlen < 1:
        reasons = reasons + [_copy_text(_REASON_LENGTH)]
    else:
        if tlen > budget:
            reasons = reasons + [_copy_text(_REASON_LENGTH)]
    if _has_value_syntax(target):
        reasons = reasons + [_copy_text(_REASON_SYNTAX)]
    if len(reasons) == 0:
        valid = True
    else:
        valid = False
    kind_copy = _copy_text(_KIND_DECLARED)
    return {"present": True, "kind": kind_copy, "valid": valid, "target": target, "reasons": reasons}
