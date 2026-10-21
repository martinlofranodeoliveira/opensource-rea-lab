_DEFAULT_MAX_ENTRIES = 128
_DEFAULT_MAX_LENGTH = 1024


def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError("Invalid files scan payload or budget")
    if "files" not in payload:
        raise ValueError("Invalid files scan payload or budget")
    for key in payload:
        if key != "files" and key != "max_entries" and key != "max_length":
            raise ValueError("Invalid files scan payload or budget")
    if "max_entries" in payload:
        max_entries = payload["max_entries"]
    else:
        max_entries = _DEFAULT_MAX_ENTRIES
    if "max_length" in payload:
        max_length = payload["max_length"]
    else:
        max_length = _DEFAULT_MAX_LENGTH
    if isinstance(max_entries, bool):
        raise ValueError("Invalid files scan payload or budget")
    if not isinstance(max_entries, int):
        raise ValueError("Invalid files scan payload or budget")
    if max_entries <= 0:
        raise ValueError("Invalid files scan payload or budget")
    if isinstance(max_length, bool):
        raise ValueError("Invalid files scan payload or budget")
    if not isinstance(max_length, int):
        raise ValueError("Invalid files scan payload or budget")
    if max_length <= 0:
        raise ValueError("Invalid files scan payload or budget")
    files_value = payload["files"]
    if files_value is None:
        return {"files": [], "count": 0}
    if not isinstance(files_value, list):
        raise ValueError("Invalid files scan payload or budget")
    if len(files_value) > max_entries:
        raise ValueError("Invalid files scan payload or budget")
    for entry in files_value:
        if not isinstance(entry, str):
            raise ValueError("Invalid files scan payload or budget")
        if len(entry) < 1:
            raise ValueError("Invalid files scan payload or budget")
        if len(entry) > max_length:
            raise ValueError("Invalid files scan payload or budget")
    sorted_files = sorted(files_value)
    return {"files": sorted_files, "count": len(sorted_files)}
