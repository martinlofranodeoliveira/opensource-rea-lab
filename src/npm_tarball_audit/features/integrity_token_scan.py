_ERROR_MESSAGE = "Invalid integrity scan payload or budget"
_DEFAULT_BUDGET = 128
_PREFIX = "sha512-"
_SUFFIX = "=="
_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"

def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_ERROR_MESSAGE)
    if "integrity" not in payload:
        raise ValueError(_ERROR_MESSAGE)
    if "max_length" in payload:
        if len(payload) != 2:
            raise ValueError(_ERROR_MESSAGE)
    else:
        if len(payload) != 1:
            raise ValueError(_ERROR_MESSAGE)
    if "max_length" in payload:
        budget = payload["max_length"]
    else:
        budget = _DEFAULT_BUDGET
    if isinstance(budget, bool):
        raise ValueError(_ERROR_MESSAGE)
    if not isinstance(budget, int):
        raise ValueError(_ERROR_MESSAGE)
    if budget <= 0:
        raise ValueError(_ERROR_MESSAGE)
    integrity = payload["integrity"]
    if integrity is None:
        return {"valid": False, "kind": "absent", "token": None}
    if not isinstance(integrity, str):
        raise ValueError(_ERROR_MESSAGE)
    size = len(integrity)
    if size < 1:
        return {"valid": False, "kind": "string", "token": None}
    if size > budget:
        return {"valid": False, "kind": "string", "token": None}
    if size != 95:
        return {"valid": False, "kind": "string", "token": None}
    if integrity[0:7] != _PREFIX:
        return {"valid": False, "kind": "string", "token": None}
    if integrity[93:95] != _SUFFIX:
        return {"valid": False, "kind": "string", "token": None}
    body = integrity[7:93]
    for ch in body:
        if ch not in _ALPHABET:
            return {"valid": False, "kind": "string", "token": None}
    return {"valid": True, "kind": "string", "token": integrity}
