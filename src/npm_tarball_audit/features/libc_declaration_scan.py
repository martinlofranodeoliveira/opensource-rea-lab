_PAYLOAD_ERROR = "Invalid libc payload or budget"
_DECLARATION_ERROR = "Invalid libc declaration"
_KIND_ABSENT = "absent"
_KIND_EMPTY = "empty"
_KIND_LISTED = "listed"
_REASON_LENGTH = "value_length"
_REASON_SYNTAX = "value_syntax"
_DEFAULT_MAX_ENTRIES = 8
_DEFAULT_MAX_VALUE_LENGTH = 32
_MIN_BUDGET = 1
_MAX_ENTRIES_LIMIT = 16
_MAX_VALUE_LENGTH_LIMIT = 64


def _is_exact_int(value):
    return type(value) is int


def _copy_str(value):
    result = ""
    idx = 0
    total = len(value)
    while idx < total:
        code = ord(value[idx])
        result = result + chr(code)
        idx = idx + 1
    return result


def _has_syntax_error(value):
    n = len(value)
    if n == 0:
        return False
    first = ord(value[0])
    first_ok = False
    if 97 <= first and first <= 122:
        first_ok = True
    if 48 <= first and first <= 57:
        first_ok = True
    if first_ok is False:
        return True
    idx = 1
    while idx < n:
        c = ord(value[idx])
        ok = False
        if 97 <= c and c <= 122:
            ok = True
        if 48 <= c and c <= 57:
            ok = True
        if c == 45:
            ok = True
        if c == 95:
            ok = True
        if ok is False:
            return True
        idx = idx + 1
    return False


def run_feature(payload):
    if isinstance(payload, dict) is False:
        raise ValueError(_PAYLOAD_ERROR)
    if "libc" not in payload:
        raise ValueError(_PAYLOAD_ERROR)
    for key in payload:
        if key != "libc" and key != "max_entries" and key != "max_value_length":
            raise ValueError(_PAYLOAD_ERROR)
    max_entries = _DEFAULT_MAX_ENTRIES
    max_value_length = _DEFAULT_MAX_VALUE_LENGTH
    if "max_entries" in payload:
        candidate = payload["max_entries"]
        if _is_exact_int(candidate) is False:
            raise ValueError(_PAYLOAD_ERROR)
        if candidate < _MIN_BUDGET or candidate > _MAX_ENTRIES_LIMIT:
            raise ValueError(_PAYLOAD_ERROR)
        max_entries = candidate
    if "max_value_length" in payload:
        candidate2 = payload["max_value_length"]
        if _is_exact_int(candidate2) is False:
            raise ValueError(_PAYLOAD_ERROR)
        if candidate2 < _MIN_BUDGET or candidate2 > _MAX_VALUE_LENGTH_LIMIT:
            raise ValueError(_PAYLOAD_ERROR)
        max_value_length = candidate2
    libc = payload["libc"]
    if libc is None:
        kind = _copy_str(_KIND_ABSENT)
        result_entries = []
        result = {}
        result["present"] = False
        result["kind"] = kind
        result["total"] = 0
        result["valid_count"] = 0
        result["invalid_count"] = 0
        result["entries"] = result_entries
        return result
    if isinstance(libc, list) is False:
        raise ValueError(_DECLARATION_ERROR)
    if len(libc) > max_entries:
        raise ValueError(_DECLARATION_ERROR)
    plain = []
    for item in libc:
        if isinstance(item, str) is False:
            raise ValueError(_DECLARATION_ERROR)
        copied = _copy_str(item)
        plain = plain + [copied]
    ordered = sorted(plain)
    entries = []
    valid_count = 0
    invalid_count = 0
    for val in ordered:
        reasons = []
        if len(val) < 1 or len(val) > max_value_length:
            reasons = reasons + [_copy_str(_REASON_LENGTH)]
        if _has_syntax_error(val) is True:
            reasons = reasons + [_copy_str(_REASON_SYNTAX)]
        is_valid = len(reasons) == 0
        if is_valid is True:
            valid_count = valid_count + 1
        else:
            invalid_count = invalid_count + 1
        value_copy = _copy_str(val)
        fresh_reasons = []
        for r in reasons:
            fresh_reasons = fresh_reasons + [_copy_str(r)]
        entry = {}
        entry["value"] = value_copy
        entry["valid"] = is_valid
        entry["reasons"] = fresh_reasons
        entries = entries + [entry]
    total = len(ordered)
    if total == 0:
        kind2 = _copy_str(_KIND_EMPTY)
    else:
        kind2 = _copy_str(_KIND_LISTED)
    final = {}
    final["present"] = True
    final["kind"] = kind2
    final["total"] = total
    final["valid_count"] = valid_count
    final["invalid_count"] = invalid_count
    final["entries"] = entries
    return final
