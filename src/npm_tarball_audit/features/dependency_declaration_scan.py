DEFAULT_MAX_ENTRIES = 128
DEFAULT_MAX_LENGTH = 1024
ERROR_MESSAGE = "Invalid dependency scan payload or budget"


def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(ERROR_MESSAGE)
    if "dependencies" not in payload:
        raise ValueError(ERROR_MESSAGE)
    for key in payload:
        if key != "dependencies" and key != "max_entries" and key != "max_length":
            raise ValueError(ERROR_MESSAGE)
    max_entries = DEFAULT_MAX_ENTRIES
    max_length = DEFAULT_MAX_LENGTH
    if "max_entries" in payload:
        candidate_entries = payload["max_entries"]
        if isinstance(candidate_entries, bool):
            raise ValueError(ERROR_MESSAGE)
        if not isinstance(candidate_entries, int):
            raise ValueError(ERROR_MESSAGE)
        if candidate_entries <= 0:
            raise ValueError(ERROR_MESSAGE)
        max_entries = candidate_entries
    if "max_length" in payload:
        candidate_length = payload["max_length"]
        if isinstance(candidate_length, bool):
            raise ValueError(ERROR_MESSAGE)
        if not isinstance(candidate_length, int):
            raise ValueError(ERROR_MESSAGE)
        if candidate_length <= 0:
            raise ValueError(ERROR_MESSAGE)
        max_length = candidate_length
    dependencies = payload["dependencies"]
    if dependencies is None:
        return {"dependencies": [], "count": 0}
    if not isinstance(dependencies, dict):
        raise ValueError(ERROR_MESSAGE)
    if len(dependencies) > max_entries:
        raise ValueError(ERROR_MESSAGE)
    for name in dependencies:
        spec = dependencies[name]
        if not isinstance(name, str):
            raise ValueError(ERROR_MESSAGE)
        if not isinstance(spec, str):
            raise ValueError(ERROR_MESSAGE)
        if len(name) < 1:
            raise ValueError(ERROR_MESSAGE)
        if len(name) > max_length:
            raise ValueError(ERROR_MESSAGE)
        if len(spec) < 1:
            raise ValueError(ERROR_MESSAGE)
        if len(spec) > max_length:
            raise ValueError(ERROR_MESSAGE)
    ordered = sorted(dependencies)
    items = []
    for name in ordered:
        spec = dependencies[name]
        record = {"name": name, "spec": spec}
        items = items + [record]
    result = {"dependencies": items, "count": len(items)}
    return result
