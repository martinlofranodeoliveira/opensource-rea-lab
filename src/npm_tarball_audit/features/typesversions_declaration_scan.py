import math
import re
import json
import unicodedata

_ERROR_MESSAGE = "Invalid typesVersions scan payload or budget"
_DEFAULT_MAX_ENTRIES = 32
_DEFAULT_MAX_LENGTH = 256
_MIN_BUDGET = 1
_MAX_ENTRIES_LIMIT = 64
_MAX_LENGTH_LIMIT = 512
_KEY_TYPESVERSIONS = "typesVersions"
_KEY_MAX_ENTRIES = "max_entries"
_KEY_MAX_LENGTH = "max_length"
_KEY_DECLARED = "declared"
_KEY_ENTRIES = "entries"
_KEY_SELECTOR = "selector"
_KEY_MAPPINGS = "mappings"
_KEY_PATTERN = "pattern"
_KEY_TARGETS = "targets"

def _is_valid_budget(value, low, high):
    if isinstance(value, bool):
        return False
    if not isinstance(value, int):
        return False
    if value < low:
        return False
    if value > high:
        return False
    return True

def _is_valid_text(value, limit):
    if isinstance(value, bool):
        return False
    if not isinstance(value, str):
        return False
    n = len(value)
    if n < 1:
        return False
    if n > limit:
        return False
    i = 0
    while i < n:
        c = value[i]
        o = ord(c)
        if o < 32:
            if o != 9 and o != 10 and o != 13:
                return False
        if o >= 55296 and o <= 57343:
            return False
        i = i + 1
    return True

def _copy_text(value):
    chars = list(value)
    joined = "".join(chars)
    plain = str(joined)
    return plain

def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_ERROR_MESSAGE)
    if _KEY_TYPESVERSIONS not in payload:
        raise ValueError(_ERROR_MESSAGE)
    for k in payload:
        if k != _KEY_TYPESVERSIONS and k != _KEY_MAX_ENTRIES and k != _KEY_MAX_LENGTH:
            raise ValueError(_ERROR_MESSAGE)
    max_entries = _DEFAULT_MAX_ENTRIES
    max_length = _DEFAULT_MAX_LENGTH
    if _KEY_MAX_ENTRIES in payload:
        v = payload[_KEY_MAX_ENTRIES]
        if not _is_valid_budget(v, _MIN_BUDGET, _MAX_ENTRIES_LIMIT):
            raise ValueError(_ERROR_MESSAGE)
        max_entries = v
    if _KEY_MAX_LENGTH in payload:
        v2 = payload[_KEY_MAX_LENGTH]
        if not _is_valid_budget(v2, _MIN_BUDGET, _MAX_LENGTH_LIMIT):
            raise ValueError(_ERROR_MESSAGE)
        max_length = v2
    tv = payload[_KEY_TYPESVERSIONS]
    if tv is None:
        out_none = {}
        out_none[_KEY_DECLARED] = False
        out_none[_KEY_ENTRIES] = None
        return out_none
    if isinstance(tv, bool):
        raise ValueError(_ERROR_MESSAGE)
    if not isinstance(tv, dict):
        raise ValueError(_ERROR_MESSAGE)
    if len(tv) > max_entries:
        raise ValueError(_ERROR_MESSAGE)
    for sk in tv:
        if not _is_valid_text(sk, max_length):
            raise ValueError(_ERROR_MESSAGE)
        sv = tv[sk]
        if isinstance(sv, bool):
            raise ValueError(_ERROR_MESSAGE)
        if not isinstance(sv, dict):
            raise ValueError(_ERROR_MESSAGE)
        if len(sv) < 1:
            raise ValueError(_ERROR_MESSAGE)
        if len(sv) > max_entries:
            raise ValueError(_ERROR_MESSAGE)
        for pk in sv:
            if not _is_valid_text(pk, max_length):
                raise ValueError(_ERROR_MESSAGE)
            pv = sv[pk]
            if isinstance(pv, bool):
                raise ValueError(_ERROR_MESSAGE)
            if not isinstance(pv, list):
                raise ValueError(_ERROR_MESSAGE)
            if len(pv) < 1:
                raise ValueError(_ERROR_MESSAGE)
            if len(pv) > max_entries:
                raise ValueError(_ERROR_MESSAGE)
            for item in pv:
                if not _is_valid_text(item, max_length):
                    raise ValueError(_ERROR_MESSAGE)
    selector_keys = list(tv.keys())
    sorted_selectors = sorted(selector_keys)
    entries = []
    for sk in sorted_selectors:
        sv = tv[sk]
        pattern_keys = list(sv.keys())
        sorted_patterns = sorted(pattern_keys)
        mappings = []
        for pk in sorted_patterns:
            pv = sv[pk]
            targets = []
            for t in pv:
                targets.append(_copy_text(t))
            mapping = {}
            mapping[_KEY_PATTERN] = _copy_text(pk)
            mapping[_KEY_TARGETS] = targets
            mappings.append(mapping)
        entry = {}
        entry[_KEY_SELECTOR] = _copy_text(sk)
        entry[_KEY_MAPPINGS] = mappings
        entries.append(entry)
    out = {}
    out[_KEY_DECLARED] = True
    out[_KEY_ENTRIES] = entries
    return out
