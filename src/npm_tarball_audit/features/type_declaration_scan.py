import json
import math
import re
import unicodedata

_ERROR = "Invalid type scan payload or budget"
_COMMONJS = "commonjs"
_MODULE = "module"
_TYPE_KEY = "type"
_BUDGET_KEY = "max_length"
_DEFAULT_BUDGET = 32


def _fresh_text(value):
    fresh = ""
    for ch in value:
        fresh = fresh + ch
    return fresh


def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_ERROR)
    if len(payload) == 1:
        if _TYPE_KEY not in payload:
            raise ValueError(_ERROR)
        budget = _DEFAULT_BUDGET
    elif len(payload) == 2:
        if _TYPE_KEY not in payload:
            raise ValueError(_ERROR)
        if _BUDGET_KEY not in payload:
            raise ValueError(_ERROR)
        budget = payload[_BUDGET_KEY]
        if isinstance(budget, bool):
            raise ValueError(_ERROR)
        if not isinstance(budget, int):
            raise ValueError(_ERROR)
        if budget <= 0:
            raise ValueError(_ERROR)
    else:
        raise ValueError(_ERROR)
    current = payload[_TYPE_KEY]
    if current is None:
        result = {"type": None, "declared": False}
        return result
    if isinstance(current, bool):
        raise ValueError(_ERROR)
    if not isinstance(current, str):
        raise ValueError(_ERROR)
    if len(current) < 1:
        raise ValueError(_ERROR)
    if len(current) > budget:
        raise ValueError(_ERROR)
    if current != _COMMONJS:
        if current != _MODULE:
            raise ValueError(_ERROR)
    fresh = _fresh_text(current)
    result = {"type": fresh, "declared": True}
    return result
