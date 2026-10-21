_ERROR = "Invalid platform scan payload or budget"
_DEFAULT_MAX_ENTRIES = 32
_DEFAULT_MAX_LENGTH = 64
_KEY_OS = "os"
_KEY_CPU = "cpu"
_KEY_MAX_ENTRIES = "max_entries"
_KEY_MAX_LENGTH = "max_length"
_KEY_COUNT = "count"

def _sorted_copy(entries, max_entries, max_length):
    if entries is None:
        return []
    if not isinstance(entries, list):
        raise ValueError(_ERROR)
    if len(entries) > max_entries:
        raise ValueError(_ERROR)
    for item in entries:
        if not isinstance(item, str):
            raise ValueError(_ERROR)
        if len(item) < 1:
            raise ValueError(_ERROR)
        if len(item) > max_length:
            raise ValueError(_ERROR)
    result = sorted(entries)
    return list(result)

def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_ERROR)
    if _KEY_OS not in payload:
        raise ValueError(_ERROR)
    if _KEY_CPU not in payload:
        raise ValueError(_ERROR)
    for key in payload:
        if key != _KEY_OS and key != _KEY_CPU and key != _KEY_MAX_ENTRIES and key != _KEY_MAX_LENGTH:
            raise ValueError(_ERROR)
    if _KEY_MAX_ENTRIES in payload:
        max_entries = payload[_KEY_MAX_ENTRIES]
    else:
        max_entries = _DEFAULT_MAX_ENTRIES
    if _KEY_MAX_LENGTH in payload:
        max_length = payload[_KEY_MAX_LENGTH]
    else:
        max_length = _DEFAULT_MAX_LENGTH
    if type(max_entries) is not int:
        raise ValueError(_ERROR)
    if type(max_length) is not int:
        raise ValueError(_ERROR)
    if max_entries <= 0:
        raise ValueError(_ERROR)
    if max_length <= 0:
        raise ValueError(_ERROR)
    os_value = payload[_KEY_OS]
    cpu_value = payload[_KEY_CPU]
    os_list = _sorted_copy(os_value, max_entries, max_length)
    cpu_list = _sorted_copy(cpu_value, max_entries, max_length)
    total = len(os_list) + len(cpu_list)
    return {_KEY_OS: os_list, _KEY_CPU: cpu_list, _KEY_COUNT: total}
