"""Scripts declaration scan. Pure deterministic enumeration."""

ERROR_MESSAGE = "Invalid scripts scan payload or budget"
DEFAULT_MAX_ENTRIES = 32
DEFAULT_MAX_LENGTH = 1024
KEY_SCRIPTS = "scripts"
KEY_MAX_ENTRIES = "max_entries"
KEY_MAX_LENGTH = "max_length"

def _is_positive_budget(value):
    return type(value) is int and value > 0

def _is_valid_text(value, limit):
    if not isinstance(value, str):
        return False
    if len(value) < 1:
        return False
    if len(value) > limit:
        return False
    return True

def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(ERROR_MESSAGE)
    if KEY_SCRIPTS not in payload:
        raise ValueError(ERROR_MESSAGE)
    for key in payload:
        if key != KEY_SCRIPTS and key != KEY_MAX_ENTRIES and key != KEY_MAX_LENGTH:
            raise ValueError(ERROR_MESSAGE)
    max_entries = DEFAULT_MAX_ENTRIES
    max_length = DEFAULT_MAX_LENGTH
    if KEY_MAX_ENTRIES in payload:
        candidate_entries = payload[KEY_MAX_ENTRIES]
        if not _is_positive_budget(candidate_entries):
            raise ValueError(ERROR_MESSAGE)
        max_entries = candidate_entries
    if KEY_MAX_LENGTH in payload:
        candidate_length = payload[KEY_MAX_LENGTH]
        if not _is_positive_budget(candidate_length):
            raise ValueError(ERROR_MESSAGE)
        max_length = candidate_length
    scripts_obj = payload[KEY_SCRIPTS]
    if scripts_obj is None:
        return {"scripts": [], "count": 0}
    if not isinstance(scripts_obj, dict):
        raise ValueError(ERROR_MESSAGE)
    if len(scripts_obj) > max_entries:
        raise ValueError(ERROR_MESSAGE)
    for name in scripts_obj:
        command = scripts_obj[name]
        if not _is_valid_text(name, max_length):
            raise ValueError(ERROR_MESSAGE)
        if not _is_valid_text(command, max_length):
            raise ValueError(ERROR_MESSAGE)
    ordered = sorted(scripts_obj)
    entries = []
    for name in ordered:
        command = scripts_obj[name]
        entries.append({"name": name, "command": command})
    result = {"scripts": entries, "count": len(entries)}
    return result
