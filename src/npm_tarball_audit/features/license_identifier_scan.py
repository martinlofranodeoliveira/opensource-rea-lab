"""Offline license identifier syntax checker for reproducible audits."""
_ERROR = "Invalid license scan payload or budget"
_DEFAULT_MAX_LENGTH = 64


def _is_ascii_alnum(code):
    if 48 <= code <= 57:
        return True
    if 65 <= code <= 90:
        return True
    if 97 <= code <= 122:
        return True
    return False


def _is_allowed_inner(code):
    if 48 <= code <= 57:
        return True
    if 65 <= code <= 90:
        return True
    if 97 <= code <= 122:
        return True
    if code == 46:
        return True
    if code == 45:
        return True
    if code == 43:
        return True
    return False


def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_ERROR)
    if "license" not in payload:
        raise ValueError(_ERROR)
    nkeys = len(payload)
    if nkeys == 1:
        pass
    elif nkeys == 2:
        if "max_length" not in payload:
            raise ValueError(_ERROR)
    else:
        raise ValueError(_ERROR)
    lic = payload["license"]
    if lic is None:
        is_absent = True
    elif isinstance(lic, str):
        is_absent = False
    else:
        raise ValueError(_ERROR)
    if "max_length" in payload:
        budget = payload["max_length"]
    else:
        budget = _DEFAULT_MAX_LENGTH
    if isinstance(budget, bool):
        raise ValueError(_ERROR)
    if not isinstance(budget, int):
        raise ValueError(_ERROR)
    if budget <= 0:
        raise ValueError(_ERROR)
    if is_absent:
        return {"valid": False, "kind": "absent", "identifier": None}
    n = len(lic)
    if n == 0:
        return {"valid": False, "kind": "string", "identifier": None}
    if n > budget:
        return {"valid": False, "kind": "string", "identifier": None}
    first = ord(lic[0])
    if not _is_ascii_alnum(first):
        return {"valid": False, "kind": "string", "identifier": None}
    last = ord(lic[n - 1])
    if not _is_ascii_alnum(last):
        return {"valid": False, "kind": "string", "identifier": None}
    copied = ""
    i = 0
    while i < n:
        c = lic[i]
        o = ord(c)
        if not _is_allowed_inner(o):
            return {"valid": False, "kind": "string", "identifier": None}
        copied = copied + c
        i = i + 1
    return {"valid": True, "kind": "string", "identifier": copied}
