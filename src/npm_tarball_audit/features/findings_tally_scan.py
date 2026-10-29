import re

_PAYLOAD_ERROR = "Invalid findings payload or budget"
_RECORD_ERROR = "Invalid finding record"
_DEFAULT_BUDGET = 256
_MIN_BUDGET = 1
_MAX_BUDGET = 500
_CODE_PATTERN = "[A-Za-z0-9_/-]+"
_ERROR_LABEL = "error"
_WARNING_LABEL = "warning"
_FINDINGS_KEY = "findings"
_BUDGET_KEY = "max_entries"
_CODE_KEY = "code"
_SEVERITY_KEY = "severity"
_TOTAL_KEY = "total"
_ERRORS_KEY = "errors"
_WARNINGS_KEY = "warnings"
_BY_CODE_KEY = "by_code"
_COUNT_KEY = "count"
_SLASH = "/"
_DOUBLE_SLASH = "//"

def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_PAYLOAD_ERROR)
    if _FINDINGS_KEY not in payload:
        raise ValueError(_PAYLOAD_ERROR)
    if len(payload) == 1:
        budget = _DEFAULT_BUDGET
    else:
        if len(payload) != 2:
            raise ValueError(_PAYLOAD_ERROR)
        if _BUDGET_KEY not in payload:
            raise ValueError(_PAYLOAD_ERROR)
        budget = payload[_BUDGET_KEY]
        if type(budget) is not int:
            raise ValueError(_PAYLOAD_ERROR)
        if budget < _MIN_BUDGET:
            raise ValueError(_PAYLOAD_ERROR)
        if budget > _MAX_BUDGET:
            raise ValueError(_PAYLOAD_ERROR)
    findings = payload[_FINDINGS_KEY]
    if not isinstance(findings, list):
        raise ValueError(_PAYLOAD_ERROR)
    if len(findings) > budget:
        raise ValueError(_PAYLOAD_ERROR)
    total = len(findings)
    err_total = 0
    warn_total = 0
    groups = {}
    groups_err = {}
    groups_warn = {}
    idx = 0
    while idx < total:
        rec = findings[idx]
        if not isinstance(rec, dict):
            raise ValueError(_RECORD_ERROR)
        if len(rec) != 2:
            raise ValueError(_RECORD_ERROR)
        if _CODE_KEY not in rec:
            raise ValueError(_RECORD_ERROR)
        if _SEVERITY_KEY not in rec:
            raise ValueError(_RECORD_ERROR)
        code = rec[_CODE_KEY]
        sev = rec[_SEVERITY_KEY]
        if not isinstance(code, str):
            raise ValueError(_RECORD_ERROR)
        if len(code) < 1:
            raise ValueError(_RECORD_ERROR)
        if len(code) > 64:
            raise ValueError(_RECORD_ERROR)
        if code[0] == _SLASH:
            raise ValueError(_RECORD_ERROR)
        if code[len(code) - 1] == _SLASH:
            raise ValueError(_RECORD_ERROR)
        if _DOUBLE_SLASH in code:
            raise ValueError(_RECORD_ERROR)
        if re.fullmatch(_CODE_PATTERN, code) is None:
            raise ValueError(_RECORD_ERROR)
        if type(sev) is not str:
            raise ValueError(_RECORD_ERROR)
        if sev != _ERROR_LABEL:
            if sev != _WARNING_LABEL:
                raise ValueError(_RECORD_ERROR)
        plain = code[0:0] + code[0:len(code)]
        if plain in groups:
            groups[plain] = groups[plain] + 1
        else:
            groups[plain] = 1
            groups_err[plain] = 0
            groups_warn[plain] = 0
        if sev == _ERROR_LABEL:
            err_total = err_total + 1
            groups_err[plain] = groups_err[plain] + 1
        else:
            warn_total = warn_total + 1
            groups_warn[plain] = groups_warn[plain] + 1
        idx = idx + 1
    sorted_keys = sorted(groups)
    by_code = []
    j = 0
    while j < len(sorted_keys):
        k = sorted_keys[j]
        out_code = k[0:0] + k[0:len(k)]
        entry = {}
        entry[_CODE_KEY] = out_code
        entry[_COUNT_KEY] = groups[k]
        entry[_ERRORS_KEY] = groups_err[k]
        entry[_WARNINGS_KEY] = groups_warn[k]
        by_code.append(entry)
        j = j + 1
    result = {}
    result[_TOTAL_KEY] = total
    result[_ERRORS_KEY] = err_total
    result[_WARNINGS_KEY] = warn_total
    result[_BY_CODE_KEY] = by_code
    return result
