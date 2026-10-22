"""Offline packageManager declaration enumerator for reproducible audits."""
import math
import re
import json
import unicodedata

_ERROR_MESSAGE = "Invalid packageManager scan payload or budget"
_DEFAULT_MAX_LENGTH = 256
_MIN_MAX_LENGTH = 1
_MAX_MAX_LENGTH = 4096
_DISALLOWED_PATTERN = "[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f]"
_PACKAGE_KEY = "packageManager"
_BUDGET_KEY = "max_length"
_DECLARED_KEY = "declared"
_VALUE_KEY = "value"


def run_feature(payload):
    """Report declared packageManager verbatim without execution."""
    if not isinstance(payload, dict):
        raise ValueError(_ERROR_MESSAGE)
    if _PACKAGE_KEY not in payload:
        raise ValueError(_ERROR_MESSAGE)
    if _BUDGET_KEY in payload:
        if len(payload) != 2:
            raise ValueError(_ERROR_MESSAGE)
        budget = payload[_BUDGET_KEY]
        if isinstance(budget, bool):
            raise ValueError(_ERROR_MESSAGE)
        if not isinstance(budget, int):
            raise ValueError(_ERROR_MESSAGE)
        if math.floor(budget) != budget:
            raise ValueError(_ERROR_MESSAGE)
        if budget < _MIN_MAX_LENGTH or budget > _MAX_MAX_LENGTH:
            raise ValueError(_ERROR_MESSAGE)
    else:
        if len(payload) != 1:
            raise ValueError(_ERROR_MESSAGE)
        budget = _DEFAULT_MAX_LENGTH
    raw = payload[_PACKAGE_KEY]
    if raw is None:
        result = {_DECLARED_KEY: False, _VALUE_KEY: None}
        return result
    if not isinstance(raw, str):
        raise ValueError(_ERROR_MESSAGE)
    if len(raw) < 1 or len(raw) > budget:
        raise ValueError(_ERROR_MESSAGE)
    if re.search(_DISALLOWED_PATTERN, raw) is not None:
        raise ValueError(_ERROR_MESSAGE)
    index = 0
    total = len(raw)
    while index < total:
        ch = raw[index]
        code = ord(ch)
        label = unicodedata.category(ch)
        if label == "Cs":
            if 55296 <= code <= 56319:
                nxt = index + 1
                if nxt >= total:
                    raise ValueError(_ERROR_MESSAGE)
                code2 = ord(raw[nxt])
                if 56320 <= code2 <= 57343:
                    index = nxt + 1
                    continue
                raise ValueError(_ERROR_MESSAGE)
            raise ValueError(_ERROR_MESSAGE)
        if 55296 <= code <= 57343:
            raise ValueError(_ERROR_MESSAGE)
        index = index + 1
    copied = json.loads(json.dumps(raw))
    result = {_DECLARED_KEY: True, _VALUE_KEY: copied}
    return result
