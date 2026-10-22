_DEFAULT_MAX_ENTRIES = 32
_DEFAULT_MAX_LENGTH = 256
_MIN_BUDGET_ENTRIES = 1
_MAX_BUDGET_ENTRIES = 256
_MIN_BUDGET_LENGTH = 1
_MAX_BUDGET_LENGTH = 1024
_ERROR_MESSAGE = "Invalid workspaces scan payload or budget"


def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_ERROR_MESSAGE)
    seen_workspaces = False
    seen_max_entries = False
    seen_max_length = False
    for key in payload:
        if key == "workspaces":
            if seen_workspaces:
                raise ValueError(_ERROR_MESSAGE)
            seen_workspaces = True
        elif key == "max_entries":
            if seen_max_entries:
                raise ValueError(_ERROR_MESSAGE)
            seen_max_entries = True
        elif key == "max_length":
            if seen_max_length:
                raise ValueError(_ERROR_MESSAGE)
            seen_max_length = True
        else:
            raise ValueError(_ERROR_MESSAGE)
    if not seen_workspaces:
        raise ValueError(_ERROR_MESSAGE)
    max_entries = _DEFAULT_MAX_ENTRIES
    max_length = _DEFAULT_MAX_LENGTH
    if seen_max_entries:
        candidate_entries = payload["max_entries"]
        if type(candidate_entries) is not int:
            raise ValueError(_ERROR_MESSAGE)
        if candidate_entries < _MIN_BUDGET_ENTRIES:
            raise ValueError(_ERROR_MESSAGE)
        if candidate_entries > _MAX_BUDGET_ENTRIES:
            raise ValueError(_ERROR_MESSAGE)
        max_entries = candidate_entries
    if seen_max_length:
        candidate_length = payload["max_length"]
        if type(candidate_length) is not int:
            raise ValueError(_ERROR_MESSAGE)
        if candidate_length < _MIN_BUDGET_LENGTH:
            raise ValueError(_ERROR_MESSAGE)
        if candidate_length > _MAX_BUDGET_LENGTH:
            raise ValueError(_ERROR_MESSAGE)
        max_length = candidate_length
    workspaces = payload["workspaces"]
    if workspaces is None:
        return {"entries": None, "declared": False}
    if not isinstance(workspaces, list):
        raise ValueError(_ERROR_MESSAGE)
    if len(workspaces) > max_entries:
        raise ValueError(_ERROR_MESSAGE)
    for item in workspaces:
        if not isinstance(item, str):
            raise ValueError(_ERROR_MESSAGE)
        item_length = len(item)
        if item_length < 1:
            raise ValueError(_ERROR_MESSAGE)
        if item_length > max_length:
            raise ValueError(_ERROR_MESSAGE)
        for ch in item:
            code = ord(ch)
            if code >= 55296:
                if code <= 57343:
                    raise ValueError(_ERROR_MESSAGE)
            if code < 32:
                if code != 9:
                    if code != 10:
                        if code != 13:
                            raise ValueError(_ERROR_MESSAGE)
    ordered = sorted(workspaces)
    return {"entries": ordered, "declared": True}
