import math
import re
import json
import unicodedata

_ERROR_MESSAGE = "Invalid types scan payload or budget"
_DEFAULT_BUDGET = 512
_KEY_TYPES = "types"
_KEY_TYPINGS = "typings"
_KEY_BUDGET = "max_length"
_KEY_DECLARED = "declared"


def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_ERROR_MESSAGE)
    if _KEY_TYPES not in payload:
        raise ValueError(_ERROR_MESSAGE)
    if _KEY_TYPINGS not in payload:
        raise ValueError(_ERROR_MESSAGE)
    for key in payload:
        if key == _KEY_TYPES:
            continue
        if key == _KEY_TYPINGS:
            continue
        if key == _KEY_BUDGET:
            continue
        raise ValueError(_ERROR_MESSAGE)
    if _KEY_BUDGET in payload:
        budget = payload[_KEY_BUDGET]
    else:
        budget = _DEFAULT_BUDGET
    if isinstance(budget, bool):
        raise ValueError(_ERROR_MESSAGE)
    if not isinstance(budget, int):
        raise ValueError(_ERROR_MESSAGE)
    if budget <= 0:
        raise ValueError(_ERROR_MESSAGE)
    types_value = payload[_KEY_TYPES]
    typings_value = payload[_KEY_TYPINGS]
    if types_value is None:
        pass
    elif isinstance(types_value, str):
        if not 1 <= len(types_value) <= budget:
            raise ValueError(_ERROR_MESSAGE)
    else:
        raise ValueError(_ERROR_MESSAGE)
    if typings_value is None:
        pass
    elif isinstance(typings_value, str):
        if not 1 <= len(typings_value) <= budget:
            raise ValueError(_ERROR_MESSAGE)
    else:
        raise ValueError(_ERROR_MESSAGE)
    if types_value is None:
        if typings_value is None:
            declared = False
        else:
            declared = True
    else:
        declared = True
    result = {}
    result[_KEY_TYPES] = types_value
    result[_KEY_TYPINGS] = typings_value
    result[_KEY_DECLARED] = declared
    return result
