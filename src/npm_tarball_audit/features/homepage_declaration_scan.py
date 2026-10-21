"""Offline homepage declaration checker."""
import json
import math
import re
import unicodedata

_ERROR_MESSAGE = "Invalid homepage scan payload or budget"
_DEFAULT_MAX_LENGTH = 512
_HOMEPAGE_KEY = "homepage"
_MAX_LENGTH_KEY = "max_length"

def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_ERROR_MESSAGE)
    if _HOMEPAGE_KEY not in payload:
        raise ValueError(_ERROR_MESSAGE)
    for key in list(payload):
        if key != _HOMEPAGE_KEY and key != _MAX_LENGTH_KEY:
            raise ValueError(_ERROR_MESSAGE)
    if _MAX_LENGTH_KEY in payload:
        budget = payload[_MAX_LENGTH_KEY]
        if isinstance(budget, bool):
            raise ValueError(_ERROR_MESSAGE)
        if not isinstance(budget, int):
            raise ValueError(_ERROR_MESSAGE)
        if budget <= 0:
            raise ValueError(_ERROR_MESSAGE)
        limit = budget
    else:
        limit = _DEFAULT_MAX_LENGTH
    value = payload[_HOMEPAGE_KEY]
    if value is None:
        result = {"homepage": None, "declared": False}
        return result
    if not isinstance(value, str):
        raise ValueError(_ERROR_MESSAGE)
    size = len(value)
    if size < 1:
        raise ValueError(_ERROR_MESSAGE)
    if size > limit:
        raise ValueError(_ERROR_MESSAGE)
    parts = list(value)
    fresh = "".join(parts)
    result = {"homepage": fresh, "declared": True}
    return result
