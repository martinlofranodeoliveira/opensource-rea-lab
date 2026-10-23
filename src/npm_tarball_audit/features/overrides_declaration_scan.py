# Offline npm overrides declaration enumerator for reproducible audits.
# Declaration enumeration only, not execution, installation, resolution,
# fetching, existence check, provenance verification, safety, security,
# compatibility or legal review; values are reported as declared.
_ERROR = "Invalid overrides scan payload or budget"
_DEFAULT_MAX_ENTRIES = 32
_DEFAULT_MAX_LENGTH = 256
_MIN_BUDGET = 1
_MAX_ENTRIES_LIMIT = 64
_MAX_LENGTH_LIMIT = 1024
_TAB_CODE = 9
_LF_CODE = 10
_CR_CODE = 13
_C0_MAX = 31
_SURR_MIN = 55296
_SURR_MAX = 57343
def _is_valid_text(value, max_length):
    if not isinstance(value, str):
        return False
    count = len(value)
    if count < 1:
        return False
    if count > max_length:
        return False
    pos = 0
    while pos < count:
        code = ord(value[pos])
        if code <= _C0_MAX:
            if code != _TAB_CODE:
                if code != _LF_CODE:
                    if code != _CR_CODE:
                        return False
        if code >= _SURR_MIN:
            if code <= _SURR_MAX:
                return False
        pos = pos + 1
    return True
def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_ERROR)
    if "overrides" not in payload:
        raise ValueError(_ERROR)
    for k in payload:
        if k != "overrides":
            if k != "max_entries":
                if k != "max_length":
                    raise ValueError(_ERROR)
    max_entries = _DEFAULT_MAX_ENTRIES
    max_length = _DEFAULT_MAX_LENGTH
    if "max_entries" in payload:
        raw_entries = payload["max_entries"]
        if isinstance(raw_entries, bool):
            raise ValueError(_ERROR)
        if not isinstance(raw_entries, int):
            raise ValueError(_ERROR)
        if raw_entries < _MIN_BUDGET:
            raise ValueError(_ERROR)
        if raw_entries > _MAX_ENTRIES_LIMIT:
            raise ValueError(_ERROR)
        max_entries = raw_entries
    if "max_length" in payload:
        raw_length = payload["max_length"]
        if isinstance(raw_length, bool):
            raise ValueError(_ERROR)
        if not isinstance(raw_length, int):
            raise ValueError(_ERROR)
        if raw_length < _MIN_BUDGET:
            raise ValueError(_ERROR)
        if raw_length > _MAX_LENGTH_LIMIT:
            raise ValueError(_ERROR)
        max_length = raw_length
    overrides = payload["overrides"]
    if overrides is None:
        return {"declared": False, "entries": None}
    if not isinstance(overrides, dict):
        raise ValueError(_ERROR)
    if len(overrides) > max_entries:
        raise ValueError(_ERROR)
    for top_key in overrides:
        if not _is_valid_text(top_key, max_length):
            raise ValueError(_ERROR)
        top_val = overrides[top_key]
        if isinstance(top_val, str):
            if not _is_valid_text(top_val, max_length):
                raise ValueError(_ERROR)
        else:
            if not isinstance(top_val, dict):
                raise ValueError(_ERROR)
            if len(top_val) < 1:
                raise ValueError(_ERROR)
            if len(top_val) > max_entries:
                raise ValueError(_ERROR)
            for nested_key in top_val:
                if not _is_valid_text(nested_key, max_length):
                    raise ValueError(_ERROR)
                nested_val = top_val[nested_key]
                if not _is_valid_text(nested_val, max_length):
                    raise ValueError(_ERROR)
    top_sorted = sorted(overrides)
    entries = []
    for skey in top_sorted:
        sval = overrides[skey]
        out_key = str(skey)
        if isinstance(sval, str):
            out_val = str(sval)
            entries.append({"key": out_key, "value": out_val})
        else:
            nested_sorted = sorted(sval)
            nested_out = {}
            for nkey in nested_sorted:
                nval = sval[nkey]
                nested_out[str(nkey)] = str(nval)
            entries.append({"key": out_key, "value": nested_out})
    return {"declared": True, "entries": entries}
