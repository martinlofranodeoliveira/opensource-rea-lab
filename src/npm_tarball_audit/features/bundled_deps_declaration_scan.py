import json
import math
import re
import unicodedata

_ERROR_MESSAGE = 'Invalid bundled dependencies scan payload or budget'
_DEFAULT_MAX_ENTRIES = 64
_DEFAULT_MAX_LENGTH = 214
_MIN_BUDGET = 1
_MAX_ENTRIES_UPPER = 128
_MAX_LENGTH_UPPER = 214
_BUNDLED_KEY = 'bundled'
_MAX_ENTRIES_KEY = 'max_entries'
_MAX_LENGTH_KEY = 'max_length'
_TAB_CODE = 9
_LF_CODE = 10
_CR_CODE = 13
_C0_UPPER = 32
_HIGH_LOW = 55296
_HIGH_HIGH = 56319
_LOW_LOW = 56320
_LOW_HIGH = 57343

def _read_budget(payload, key, low, high, default):
    if key not in payload:
        return default
    value = payload[key]
    if isinstance(value, bool):
        raise ValueError(_ERROR_MESSAGE)
    if not isinstance(value, int):
        raise ValueError(_ERROR_MESSAGE)
    if value < low:
        raise ValueError(_ERROR_MESSAGE)
    if value > high:
        raise ValueError(_ERROR_MESSAGE)
    return value

def _check_entry(text, max_length):
    if not isinstance(text, str):
        raise ValueError(_ERROR_MESSAGE)
    size = len(text)
    if size < 1:
        raise ValueError(_ERROR_MESSAGE)
    if size > max_length:
        raise ValueError(_ERROR_MESSAGE)
    index = 0
    while index < size:
        code = ord(text[index])
        if code < _C0_UPPER:
            if code != _TAB_CODE:
                if code != _LF_CODE:
                    if code != _CR_CODE:
                        raise ValueError(_ERROR_MESSAGE)
        index = index + 1
    pos = 0
    while pos < size:
        code = ord(text[pos])
        if code >= _HIGH_LOW:
            if code <= _HIGH_HIGH:
                nxt = pos + 1
                if nxt >= size:
                    raise ValueError(_ERROR_MESSAGE)
                nxt_code = ord(text[nxt])
                if nxt_code < _LOW_LOW:
                    raise ValueError(_ERROR_MESSAGE)
                if nxt_code > _LOW_HIGH:
                    raise ValueError(_ERROR_MESSAGE)
            else:
                if code <= _LOW_HIGH:
                    if pos == 0:
                        raise ValueError(_ERROR_MESSAGE)
                    prev_code = ord(text[pos - 1])
                    if prev_code < _HIGH_LOW:
                        raise ValueError(_ERROR_MESSAGE)
                    if prev_code > _HIGH_HIGH:
                        raise ValueError(_ERROR_MESSAGE)
        pos = pos + 1
    return text

def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_ERROR_MESSAGE)
    if _BUNDLED_KEY not in payload:
        raise ValueError(_ERROR_MESSAGE)
    for key in payload:
        if key == _BUNDLED_KEY:
            continue
        if key == _MAX_ENTRIES_KEY:
            continue
        if key == _MAX_LENGTH_KEY:
            continue
        raise ValueError(_ERROR_MESSAGE)
    max_entries = _read_budget(payload, _MAX_ENTRIES_KEY, _MIN_BUDGET, _MAX_ENTRIES_UPPER, _DEFAULT_MAX_ENTRIES)
    max_length = _read_budget(payload, _MAX_LENGTH_KEY, _MIN_BUDGET, _MAX_LENGTH_UPPER, _DEFAULT_MAX_LENGTH)
    bundled = payload[_BUNDLED_KEY]
    if bundled is None:
        return {'declared': False, 'entries': None}
    if not isinstance(bundled, list):
        raise ValueError(_ERROR_MESSAGE)
    if len(bundled) > max_entries:
        raise ValueError(_ERROR_MESSAGE)
    cleaned = []
    for item in bundled:
        _check_entry(item, max_length)
        cleaned = cleaned + [item]
    i = 0
    n = len(cleaned)
    while i < n:
        j = i + 1
        while j < n:
            if cleaned[i] == cleaned[j]:
                raise ValueError(_ERROR_MESSAGE)
            j = j + 1
        i = i + 1
    ordered = sorted(cleaned)
    return {'declared': True, 'entries': ordered}
