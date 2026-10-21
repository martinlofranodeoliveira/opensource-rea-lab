import json
import math
import re
import unicodedata

_ERROR_MESSAGE = "Invalid engines scan payload or budget"
_DEFAULT_MAX_ENTRIES = 16
_DEFAULT_MAX_LENGTH = 256
_KEY_ENGINES = "engines"
_KEY_MAX_ENTRIES = "max_entries"
_KEY_MAX_LENGTH = "max_length"

def _is_positive_int(value):
    if type(value) is int:
        if value > 0:
            return True
    return False

def _is_valid_text(value, limit):
    if isinstance(value, str):
        if len(value) >= 1:
            if len(value) <= limit:
                return True
    return False

def run_feature(payload):
    if isinstance(payload, dict):
        pass
    else:
        raise ValueError(_ERROR_MESSAGE)
    found = False
    for key in payload:
        if key == _KEY_ENGINES:
            found = True
        else:
            if key == _KEY_MAX_ENTRIES:
                pass
            else:
                if key == _KEY_MAX_LENGTH:
                    pass
                else:
                    raise ValueError(_ERROR_MESSAGE)
    if found:
        pass
    else:
        raise ValueError(_ERROR_MESSAGE)
    if _KEY_MAX_ENTRIES in payload:
        max_entries = payload[_KEY_MAX_ENTRIES]
    else:
        max_entries = _DEFAULT_MAX_ENTRIES
    if _KEY_MAX_LENGTH in payload:
        max_length = payload[_KEY_MAX_LENGTH]
    else:
        max_length = _DEFAULT_MAX_LENGTH
    if _is_positive_int(max_entries):
        pass
    else:
        raise ValueError(_ERROR_MESSAGE)
    if _is_positive_int(max_length):
        pass
    else:
        raise ValueError(_ERROR_MESSAGE)
    engines_value = payload[_KEY_ENGINES]
    if engines_value is None:
        return {"engines": [], "count": 0}
    if isinstance(engines_value, dict):
        pass
    else:
        raise ValueError(_ERROR_MESSAGE)
    if len(engines_value) > max_entries:
        raise ValueError(_ERROR_MESSAGE)
    pairs = []
    for name in engines_value:
        item_range = engines_value[name]
        if _is_valid_text(name, max_length):
            pass
        else:
            raise ValueError(_ERROR_MESSAGE)
        if _is_valid_text(item_range, max_length):
            pass
        else:
            raise ValueError(_ERROR_MESSAGE)
        pairs.append((name, item_range))
    ordered = sorted(pairs)
    entries = []
    for pair in ordered:
        entry_name = pair[0]
        entry_range = pair[1]
        entry = {"name": entry_name, "range": entry_range}
        entries.append(entry)
    result = {"engines": entries, "count": len(entries)}
    return result
