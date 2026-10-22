"""Directories declaration enumeration. Declaration only, values reported as declared."""
_DEFAULT_MAX_ENTRIES = 8
_DEFAULT_MAX_LENGTH = 512
_ALLOWED_DIRECTORY_KEYS = ("lib", "bin", "man", "doc", "example", "test")
_ALLOWED_PAYLOAD_KEYS = ("directories", "max_entries", "max_length")
_ERROR_MESSAGE = "Invalid directories scan payload or budget"


def run_feature(payload):
    max_entries = _DEFAULT_MAX_ENTRIES
    max_length = _DEFAULT_MAX_LENGTH
    if not isinstance(payload, dict):
        raise ValueError(_ERROR_MESSAGE)
    if "directories" not in payload:
        raise ValueError(_ERROR_MESSAGE)
    for k in payload:
        if k not in _ALLOWED_PAYLOAD_KEYS:
            raise ValueError(_ERROR_MESSAGE)
    if "max_entries" in payload:
        tmp = payload["max_entries"]
        if isinstance(tmp, bool):
            raise ValueError(_ERROR_MESSAGE)
        if not isinstance(tmp, int):
            raise ValueError(_ERROR_MESSAGE)
        if tmp <= 0:
            raise ValueError(_ERROR_MESSAGE)
        max_entries = tmp
    if "max_length" in payload:
        tmp2 = payload["max_length"]
        if isinstance(tmp2, bool):
            raise ValueError(_ERROR_MESSAGE)
        if not isinstance(tmp2, int):
            raise ValueError(_ERROR_MESSAGE)
        if tmp2 <= 0:
            raise ValueError(_ERROR_MESSAGE)
        max_length = tmp2
    directories = payload["directories"]
    if directories is None:
        result_none = {"entries": None, "declared": False}
        return result_none
    if not isinstance(directories, dict):
        raise ValueError(_ERROR_MESSAGE)
    if len(directories) > max_entries:
        raise ValueError(_ERROR_MESSAGE)
    for dk in directories:
        dv = directories[dk]
        if not isinstance(dk, str):
            raise ValueError(_ERROR_MESSAGE)
        if dk not in _ALLOWED_DIRECTORY_KEYS:
            raise ValueError(_ERROR_MESSAGE)
        if not isinstance(dv, str):
            raise ValueError(_ERROR_MESSAGE)
        if len(dv) < 1:
            raise ValueError(_ERROR_MESSAGE)
        if len(dv) > max_length:
            raise ValueError(_ERROR_MESSAGE)
    ordered = sorted(directories)
    entries = []
    for sk in ordered:
        sv = directories[sk]
        item = {"key": sk, "value": sv}
        entries = entries + [item]
    result = {"entries": entries, "declared": True}
    return result
