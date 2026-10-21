_DEFAULT_MAX_LENGTH = 512
_ERROR_MESSAGE = "Invalid description scan payload or budget"

def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_ERROR_MESSAGE)
    if len(payload) == 1:
        if "description" not in payload:
            raise ValueError(_ERROR_MESSAGE)
        max_length = _DEFAULT_MAX_LENGTH
    elif len(payload) == 2:
        if "description" not in payload:
            raise ValueError(_ERROR_MESSAGE)
        if "max_length" not in payload:
            raise ValueError(_ERROR_MESSAGE)
        max_length = payload["max_length"]
        if isinstance(max_length, bool):
            raise ValueError(_ERROR_MESSAGE)
        if not isinstance(max_length, int):
            raise ValueError(_ERROR_MESSAGE)
        if max_length <= 0:
            raise ValueError(_ERROR_MESSAGE)
    else:
        raise ValueError(_ERROR_MESSAGE)
    description = payload["description"]
    if description is None:
        result_none = {"description": None, "declared": False}
        return result_none
    if not isinstance(description, str):
        raise ValueError(_ERROR_MESSAGE)
    if len(description) < 1:
        raise ValueError(_ERROR_MESSAGE)
    if len(description) > max_length:
        raise ValueError(_ERROR_MESSAGE)
    fresh = ""
    for ch in description:
        fresh = fresh + ch
    result = {"description": fresh, "declared": True}
    return result
