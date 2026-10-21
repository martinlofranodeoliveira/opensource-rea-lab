import json
import math
import re
import unicodedata

_DEFAULT_MAX_ENTRIES = 64
_DEFAULT_MAX_LENGTH = 256
_ERROR_MESSAGE = "Invalid keywords scan payload or budget"
_KEY_KEYWORDS = "keywords"
_KEY_MAX_ENTRIES = "max_entries"
_KEY_MAX_LENGTH = "max_length"


def _is_positive_int(value):
    if isinstance(value, bool):
        return False
    if not isinstance(value, int):
        return False
    if value <= 0:
        return False
    return True


def _is_valid_string(value, max_length):
    if not isinstance(value, str):
        return False
    if len(value) < 1:
        return False
    if len(value) > max_length:
        return False
    return True


def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_ERROR_MESSAGE)
    if _KEY_KEYWORDS not in payload:
        raise ValueError(_ERROR_MESSAGE)
    for key in payload:
        if key != _KEY_KEYWORDS:
            if key != _KEY_MAX_ENTRIES:
                if key != _KEY_MAX_LENGTH:
                    raise ValueError(_ERROR_MESSAGE)
    max_entries = _DEFAULT_MAX_ENTRIES
    max_length = _DEFAULT_MAX_LENGTH
    if _KEY_MAX_ENTRIES in payload:
        candidate_entries = payload[_KEY_MAX_ENTRIES]
        if not _is_positive_int(candidate_entries):
            raise ValueError(_ERROR_MESSAGE)
        max_entries = candidate_entries
    if _KEY_MAX_LENGTH in payload:
        candidate_length = payload[_KEY_MAX_LENGTH]
        if not _is_positive_int(candidate_length):
            raise ValueError(_ERROR_MESSAGE)
        max_length = candidate_length
    keywords_value = payload[_KEY_KEYWORDS]
    if keywords_value is None:
        empty_list = []
        result_absent = {}
        result_absent["keywords"] = empty_list
        result_absent["count"] = 0
        result_absent["declared"] = False
        return result_absent
    if not isinstance(keywords_value, list):
        raise ValueError(_ERROR_MESSAGE)
    if len(keywords_value) > max_entries:
        raise ValueError(_ERROR_MESSAGE)
    fresh_keywords = []
    for entry in keywords_value:
        if not _is_valid_string(entry, max_length):
            raise ValueError(_ERROR_MESSAGE)
        fresh_keywords.append(entry)
    count = len(fresh_keywords)
    declared = False
    if count > 0:
        declared = True
    result = {}
    result["keywords"] = fresh_keywords
    result["count"] = count
    result["declared"] = declared
    return result
