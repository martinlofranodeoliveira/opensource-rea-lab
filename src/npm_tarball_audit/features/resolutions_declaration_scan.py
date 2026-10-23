import math
import re
import json
import unicodedata

_ERROR_MESSAGE = "Invalid resolutions scan payload or budget"
_DEFAULT_MAX_ENTRIES = 64
_DEFAULT_MAX_LENGTH = 256
_MIN_BUDGET = 1
_MAX_ENTRIES_UPPER = 128
_MAX_LENGTH_UPPER = 512
_KEY_RESOLUTIONS = "resolutions"
_KEY_MAX_ENTRIES = "max_entries"
_KEY_MAX_LENGTH = "max_length"
_CODE_TAB = 9
_CODE_LF = 10
_CODE_CR = 13
_CODE_C0_END = 32
_CODE_SURR_LO = 55296
_CODE_SURR_HI = 57343

def _check_budget(value, low, high):
    if isinstance(value, bool):
        raise ValueError(_ERROR_MESSAGE)
    if not isinstance(value, int):
        raise ValueError(_ERROR_MESSAGE)
    if value < low:
        raise ValueError(_ERROR_MESSAGE)
    if value > high:
        raise ValueError(_ERROR_MESSAGE)
    return value

def _check_text(value, limit):
    if not isinstance(value, str):
        raise ValueError(_ERROR_MESSAGE)
    size = len(value)
    if size < 1:
        raise ValueError(_ERROR_MESSAGE)
    if size > limit:
        raise ValueError(_ERROR_MESSAGE)
    for ch in value:
        code = ord(ch)
        if code >= _CODE_SURR_LO:
            if code <= _CODE_SURR_HI:
                raise ValueError(_ERROR_MESSAGE)
        if code < _CODE_C0_END:
            if code != _CODE_TAB:
                if code != _CODE_LF:
                    if code != _CODE_CR:
                        raise ValueError(_ERROR_MESSAGE)
    return value

def _copy_text(value):
    parts = []
    for ch in value:
        parts.append(ch)
    return "".join(parts)

def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_ERROR_MESSAGE)
    if _KEY_RESOLUTIONS not in payload:
        raise ValueError(_ERROR_MESSAGE)
    for key in payload:
        if key != _KEY_RESOLUTIONS:
            if key != _KEY_MAX_ENTRIES:
                if key != _KEY_MAX_LENGTH:
                    raise ValueError(_ERROR_MESSAGE)
    max_entries = _DEFAULT_MAX_ENTRIES
    max_length = _DEFAULT_MAX_LENGTH
    if _KEY_MAX_ENTRIES in payload:
        found = payload[_KEY_MAX_ENTRIES]
        _check_budget(found, _MIN_BUDGET, _MAX_ENTRIES_UPPER)
        max_entries = found
    if _KEY_MAX_LENGTH in payload:
        found2 = payload[_KEY_MAX_LENGTH]
        _check_budget(found2, _MIN_BUDGET, _MAX_LENGTH_UPPER)
        max_length = found2
    resolutions = payload[_KEY_RESOLUTIONS]
    if resolutions is None:
        return {"declared": False, "entries": None}
    if not isinstance(resolutions, dict):
        raise ValueError(_ERROR_MESSAGE)
    if len(resolutions) > max_entries:
        raise ValueError(_ERROR_MESSAGE)
    for selector in resolutions:
        pin = resolutions[selector]
        _check_text(selector, max_length)
        _check_text(pin, max_length)
    ordered = sorted(resolutions)
    entries = []
    for selector in ordered:
        pin = resolutions[selector]
        selector_copy = _copy_text(selector)
        pin_copy = _copy_text(pin)
        entry = {"selector": selector_copy, "pin": pin_copy}
        entries.append(entry)
    return {"declared": True, "entries": entries}
