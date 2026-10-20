_ERROR = "Invalid browser scan payload or budget"
_DEFAULT_MAX_ENTRIES = 200
_DEFAULT_MAX_LENGTH = 4096
_KIND_ABSENT = "absent"
_KIND_REPLACEMENT = "replacement"
_KIND_REMAP = "remap"

def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_ERROR)
    if "browser" not in payload:
        raise ValueError(_ERROR)
    for k in payload:
        if k != "browser" and k != "max_entries" and k != "max_length":
            raise ValueError(_ERROR)
    max_entries = _DEFAULT_MAX_ENTRIES
    max_length = _DEFAULT_MAX_LENGTH
    if "max_entries" in payload:
        v = payload["max_entries"]
        if isinstance(v, bool):
            raise ValueError(_ERROR)
        if not isinstance(v, int):
            raise ValueError(_ERROR)
        if v <= 0:
            raise ValueError(_ERROR)
        max_entries = v
    if "max_length" in payload:
        v = payload["max_length"]
        if isinstance(v, bool):
            raise ValueError(_ERROR)
        if not isinstance(v, int):
            raise ValueError(_ERROR)
        if v <= 0:
            raise ValueError(_ERROR)
        max_length = v
    browser = payload["browser"]
    if browser is None:
        return {"kind": _KIND_ABSENT, "replacement": None, "ignored": [], "remapped": [], "entry_count": 0}
    if isinstance(browser, str):
        if len(browser) > max_length:
            raise ValueError(_ERROR)
        return {"kind": _KIND_REPLACEMENT, "replacement": browser, "ignored": [], "remapped": [], "entry_count": 1}
    if isinstance(browser, dict):
        if len(browser) > max_entries:
            raise ValueError(_ERROR)
        ignored = []
        pairs = []
        for fk in browser:
            fv = browser[fk]
            if not isinstance(fk, str):
                raise ValueError(_ERROR)
            if len(fk) > max_length:
                raise ValueError(_ERROR)
            if fv is False:
                ignored.append(fk)
            elif isinstance(fv, str):
                if len(fv) > max_length:
                    raise ValueError(_ERROR)
                pairs.append((fk, fv))
            else:
                raise ValueError(_ERROR)
        ignored = sorted(ignored)
        pairs = sorted(pairs)
        remapped = []
        for f, t in pairs:
            remapped.append({"from": f, "to": t})
        count = len(browser)
        return {"kind": _KIND_REMAP, "replacement": None, "ignored": ignored, "remapped": remapped, "entry_count": count}
    raise ValueError(_ERROR)
