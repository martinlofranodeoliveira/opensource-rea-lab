import math
import re
import json
import unicodedata
_DEFAULT_MAX_ENTRIES = 8
_DEFAULT_MAX_KEY_LENGTH = 16
_DEFAULT_MAX_VALUE_LENGTH = 64
_ALLOWED_TOOLS = ("node", "npm", "pnpm", "yarn")
_ALLOWED_BUDGET_KEYS = ("volta", "max_entries", "max_key_length", "max_value_length")
_DIGIT_CHARS = "0123456789"
_ERROR_PAYLOAD = "Invalid volta payload or budget"
_ERROR_DECLARATION = "Invalid volta declaration"
_KIND_ABSENT = "absent"
_KIND_EMPTY = "empty"
_KIND_PINNED = "pinned"
_REASON_KEY_NAME = "key_name"
_REASON_VALUE_LENGTH = "value_length"
_REASON_VALUE_SYNTAX = "value_syntax"
def _is_valid_pin(target):
    parts = target.split(".")
    if len(parts) < 1:
        return False
    if len(parts) > 4:
        return False
    for part in parts:
        if len(part) < 1:
            return False
        if len(part) > 8:
            return False
        for ch in part:
            if ch not in _DIGIT_CHARS:
                return False
    return True
def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_ERROR_PAYLOAD)
    if "volta" not in payload:
        raise ValueError(_ERROR_PAYLOAD)
    for k in payload:
        if k not in _ALLOWED_BUDGET_KEYS:
            raise ValueError(_ERROR_PAYLOAD)
    if "max_entries" in payload:
        tmp = payload["max_entries"]
        if type(tmp) is not int:
            raise ValueError(_ERROR_PAYLOAD)
        if tmp < 1:
            raise ValueError(_ERROR_PAYLOAD)
        if tmp > 16:
            raise ValueError(_ERROR_PAYLOAD)
        max_entries = tmp
    else:
        max_entries = _DEFAULT_MAX_ENTRIES
    if "max_key_length" in payload:
        tmp2 = payload["max_key_length"]
        if type(tmp2) is not int:
            raise ValueError(_ERROR_PAYLOAD)
        if tmp2 < 1:
            raise ValueError(_ERROR_PAYLOAD)
        if tmp2 > 32:
            raise ValueError(_ERROR_PAYLOAD)
        max_key_length = tmp2
    else:
        max_key_length = _DEFAULT_MAX_KEY_LENGTH
    if "max_value_length" in payload:
        tmp3 = payload["max_value_length"]
        if type(tmp3) is not int:
            raise ValueError(_ERROR_PAYLOAD)
        if tmp3 < 1:
            raise ValueError(_ERROR_PAYLOAD)
        if tmp3 > 128:
            raise ValueError(_ERROR_PAYLOAD)
        max_value_length = tmp3
    else:
        max_value_length = _DEFAULT_MAX_VALUE_LENGTH
    volta = payload["volta"]
    if volta is None:
        result = {}
        result["present"] = False
        result["kind"] = str(_KIND_ABSENT)
        result["total"] = 0
        result["valid_count"] = 0
        result["invalid_count"] = 0
        result["entries"] = []
        return result
    if not isinstance(volta, dict):
        raise ValueError(_ERROR_DECLARATION)
    if len(volta) > max_entries:
        raise ValueError(_ERROR_DECLARATION)
    for ek in volta:
        ev = volta[ek]
        if not isinstance(ek, str):
            raise ValueError(_ERROR_DECLARATION)
        if not isinstance(ev, str):
            raise ValueError(_ERROR_DECLARATION)
    if len(volta) == 0:
        result2 = {}
        result2["present"] = True
        result2["kind"] = str(_KIND_EMPTY)
        result2["total"] = 0
        result2["valid_count"] = 0
        result2["invalid_count"] = 0
        result2["entries"] = []
        return result2
    sorted_keys = sorted(volta)
    entries = []
    valid_count = 0
    for raw_key in sorted_keys:
        raw_target = volta[raw_key]
        plain_key = str(raw_key)
        plain_target = str(raw_target)
        reasons = []
        key_ok = True
        if len(plain_key) < 1:
            key_ok = False
        if len(plain_key) > max_key_length:
            key_ok = False
        if plain_key not in _ALLOWED_TOOLS:
            key_ok = False
        if not key_ok:
            reasons.append(str(_REASON_KEY_NAME))
        tlen = len(plain_target)
        if tlen < 1:
            reasons.append(str(_REASON_VALUE_LENGTH))
        else:
            if tlen > max_value_length:
                reasons.append(str(_REASON_VALUE_LENGTH))
            else:
                if not _is_valid_pin(plain_target):
                    reasons.append(str(_REASON_VALUE_SYNTAX))
        is_valid = len(reasons) == 0
        if is_valid:
            valid_count = valid_count + 1
        entry = {}
        entry["key"] = plain_key
        entry["target"] = plain_target
        entry["valid"] = is_valid
        entry["reasons"] = reasons
        entries.append(entry)
    total = len(entries)
    invalid_count = total - valid_count
    final = {}
    final["present"] = True
    final["kind"] = str(_KIND_PINNED)
    final["total"] = total
    final["valid_count"] = valid_count
    final["invalid_count"] = invalid_count
    final["entries"] = entries
    return final
