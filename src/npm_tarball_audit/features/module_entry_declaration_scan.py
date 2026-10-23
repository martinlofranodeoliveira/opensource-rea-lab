_ERROR = "Invalid module entry scan payload or budget"
_DEFAULT_BUDGET = 512
_MIN_BUDGET = 1
_MAX_BUDGET = 1024

def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_ERROR)
    if len(payload) == 1:
        if "module" not in payload:
            raise ValueError(_ERROR)
        budget = _DEFAULT_BUDGET
    elif len(payload) == 2:
        if "module" not in payload:
            raise ValueError(_ERROR)
        if "max_length" not in payload:
            raise ValueError(_ERROR)
        candidate = payload["max_length"]
        if type(candidate) is not int:
            raise ValueError(_ERROR)
        if candidate < _MIN_BUDGET:
            raise ValueError(_ERROR)
        if candidate > _MAX_BUDGET:
            raise ValueError(_ERROR)
        budget = candidate
    else:
        raise ValueError(_ERROR)
    module_value = payload["module"]
    if module_value is None:
        return {"declared": False, "value": None}
    if isinstance(module_value, str):
        size = len(module_value)
        if size < 1:
            raise ValueError(_ERROR)
        if size > budget:
            raise ValueError(_ERROR)
        copied = module_value[0:size]
        return {"declared": True, "value": copied}
    raise ValueError(_ERROR)
