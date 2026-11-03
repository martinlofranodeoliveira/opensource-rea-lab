import json
import math
import re
import unicodedata

_DEFAULT_MAX_ENTRIES = 16
_DEFAULT_MAX_KEY_LENGTH = 64
_DEFAULT_MAX_VALUE_LENGTH = 256
_PAYLOAD_ERROR = "Invalid bin payload or budget"
_DECLARATION_ERROR = "Invalid bin declaration"
_REASON_KEY = "key_syntax"
_REASON_LENGTH = "value_length"
_REASON_SYNTAX = "value_syntax"
_KIND_ABSENT = "absent"
_KIND_EMPTY = "empty"
_KIND_STRING = "string"
_KIND_MAP = "map"

def _is_valid_key_text(text, limit):
    if len(text) < 1:
        return False
    if len(text) > limit:
        return False
    first = text[0]
    if first >= "a" and first <= "z":
        pass
    elif first >= "0" and first <= "9":
        pass
    else:
        return False
    for ch in text:
        if ch >= "a" and ch <= "z":
            continue
        if ch >= "0" and ch <= "9":
            continue
        if ch == ".":
            continue
        if ch == "_":
            continue
        if ch == "-":
            continue
        return False
    return True

def _has_value_syntax_issue(text):
    if chr(92) in text:
        return True
    if len(text) > 0 and text[0] == "/":
        return True
    if "*" in text:
        return True
    if ":" in text:
        return True
    for ch in text:
        code = ord(ch)
        if code < 32:
            return True
        if code == 127:
            return True
    if text == ".":
        return True
    if text == "./":
        return True
    if len(text) >= 2 and text[0] == "." and text[1] == "/":
        stripped = text[2:]
    else:
        stripped = text
    parts = stripped.split("/")
    for part in parts:
        if part == "":
            return True
        if part == ".":
            return True
        if part == "..":
            return True
    return False

def _make_value_reasons(target, limit):
    reasons = []
    if len(target) < 1:
        reasons.append(_REASON_LENGTH)
        return reasons
    if len(target) > limit:
        reasons.append(_REASON_LENGTH)
        return reasons
    if _has_value_syntax_issue(target):
        reasons.append(_REASON_SYNTAX)
    return reasons

def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_PAYLOAD_ERROR)
    if "bin" not in payload:
        raise ValueError(_PAYLOAD_ERROR)
    for k in payload:
        if k == "bin":
            continue
        if k == "max_entries":
            continue
        if k == "max_key_length":
            continue
        if k == "max_value_length":
            continue
        raise ValueError(_PAYLOAD_ERROR)
    if "max_entries" in payload:
        raw_max_entries = payload["max_entries"]
        if type(raw_max_entries) is not int:
            raise ValueError(_PAYLOAD_ERROR)
        if raw_max_entries < 1:
            raise ValueError(_PAYLOAD_ERROR)
        if raw_max_entries > 64:
            raise ValueError(_PAYLOAD_ERROR)
        max_entries = raw_max_entries
    else:
        max_entries = _DEFAULT_MAX_ENTRIES
    if "max_key_length" in payload:
        raw_max_key_length = payload["max_key_length"]
        if type(raw_max_key_length) is not int:
            raise ValueError(_PAYLOAD_ERROR)
        if raw_max_key_length < 1:
            raise ValueError(_PAYLOAD_ERROR)
        if raw_max_key_length > 128:
            raise ValueError(_PAYLOAD_ERROR)
        max_key_length = raw_max_key_length
    else:
        max_key_length = _DEFAULT_MAX_KEY_LENGTH
    if "max_value_length" in payload:
        raw_max_value_length = payload["max_value_length"]
        if type(raw_max_value_length) is not int:
            raise ValueError(_PAYLOAD_ERROR)
        if raw_max_value_length < 1:
            raise ValueError(_PAYLOAD_ERROR)
        if raw_max_value_length > 512:
            raise ValueError(_PAYLOAD_ERROR)
        max_value_length = raw_max_value_length
    else:
        max_value_length = _DEFAULT_MAX_VALUE_LENGTH
    raw_bin = payload["bin"]
    if raw_bin is None:
        return {"present": False, "kind": _KIND_ABSENT, "total": 0, "valid_count": 0, "invalid_count": 0, "entries": []}
    if isinstance(raw_bin, str):
        target = str(raw_bin)
        reasons = _make_value_reasons(target, max_value_length)
        if len(reasons) == 0:
            is_valid = True
        else:
            is_valid = False
        fresh_reasons = []
        for r in reasons:
            fresh_reasons.append(str(r))
        entry = {"key": None, "target": target, "valid": is_valid, "reasons": fresh_reasons}
        entries = []
        entries.append(entry)
        if is_valid:
            valid_count = 1
            invalid_count = 0
        else:
            valid_count = 0
            invalid_count = 1
        return {"present": True, "kind": _KIND_STRING, "total": 1, "valid_count": valid_count, "invalid_count": invalid_count, "entries": entries}
    if isinstance(raw_bin, dict):
        if len(raw_bin) > max_entries:
            raise ValueError(_DECLARATION_ERROR)
        for k in raw_bin:
            if not isinstance(k, str):
                raise ValueError(_DECLARATION_ERROR)
        for k in raw_bin:
            v = raw_bin[k]
            if not isinstance(v, str):
                raise ValueError(_DECLARATION_ERROR)
        if len(raw_bin) == 0:
            return {"present": True, "kind": _KIND_EMPTY, "total": 0, "valid_count": 0, "invalid_count": 0, "entries": []}
        keys_list = list(raw_bin.keys())
        sorted_keys = sorted(keys_list)
        entries = []
        valid_count = 0
        for k in sorted_keys:
            v = raw_bin[k]
            plain_key = str(k)
            plain_target = str(v)
            entry_reasons = []
            if not _is_valid_key_text(plain_key, max_key_length):
                entry_reasons.append(_REASON_KEY)
            value_reasons = _make_value_reasons(plain_target, max_value_length)
            for r in value_reasons:
                entry_reasons.append(str(r))
            if len(entry_reasons) == 0:
                is_valid = True
            else:
                is_valid = False
            if is_valid:
                valid_count = valid_count + 1
            fresh_reasons = []
            for r in entry_reasons:
                fresh_reasons.append(str(r))
            entry = {"key": plain_key, "target": plain_target, "valid": is_valid, "reasons": fresh_reasons}
            entries.append(entry)
        total = len(entries)
        invalid_count = total - valid_count
        return {"present": True, "kind": _KIND_MAP, "total": total, "valid_count": valid_count, "invalid_count": invalid_count, "entries": entries}
    raise ValueError(_DECLARATION_ERROR)
