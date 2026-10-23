import json
import math
import re
import unicodedata

_ERROR = "Invalid peer metadata scan payload or budget"
_KEY_META = "peerDependenciesMeta"
_KEY_MAX_ENTRIES = "max_entries"
_KEY_MAX_LENGTH = "max_length"
_KEY_OPTIONAL = "optional"
_KEY_DECLARED = "declared"
_KEY_ENTRIES = "entries"
_KEY_NAME = "name"
_DEFAULT_MAX_ENTRIES = 32
_MIN_ENTRIES = 1
_MAX_ENTRIES = 64
_DEFAULT_MAX_LEN = 214
_MIN_LEN = 1
_MAX_LEN = 214

def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_ERROR)
    if _KEY_META not in payload:
        raise ValueError(_ERROR)
    for k in payload:
        if k != _KEY_META and k != _KEY_MAX_ENTRIES and k != _KEY_MAX_LENGTH:
            raise ValueError(_ERROR)
    max_entries = _DEFAULT_MAX_ENTRIES
    max_len = _DEFAULT_MAX_LEN
    if _KEY_MAX_ENTRIES in payload:
        b = payload[_KEY_MAX_ENTRIES]
        if type(b) is not int:
            raise ValueError(_ERROR)
        if b < _MIN_ENTRIES or b > _MAX_ENTRIES:
            raise ValueError(_ERROR)
        max_entries = b
    if _KEY_MAX_LENGTH in payload:
        c = payload[_KEY_MAX_LENGTH]
        if type(c) is not int:
            raise ValueError(_ERROR)
        if c < _MIN_LEN or c > _MAX_LEN:
            raise ValueError(_ERROR)
        max_len = c
    meta = payload[_KEY_META]
    if meta is None:
        return {_KEY_DECLARED: False, _KEY_ENTRIES: None}
    if not isinstance(meta, dict):
        raise ValueError(_ERROR)
    if len(meta) > max_entries:
        raise ValueError(_ERROR)
    for name in meta:
        if not isinstance(name, str):
            raise ValueError(_ERROR)
        if len(name) < _MIN_LEN or len(name) > max_len:
            raise ValueError(_ERROR)
        inner = meta[name]
        if not isinstance(inner, dict):
            raise ValueError(_ERROR)
        if len(inner) > 1:
            raise ValueError(_ERROR)
        if len(inner) == 1:
            if _KEY_OPTIONAL not in inner:
                raise ValueError(_ERROR)
            flag = inner[_KEY_OPTIONAL]
            if type(flag) is not bool:
                raise ValueError(_ERROR)
    ordered = sorted(meta)
    out_list = []
    for name in ordered:
        inner = meta[name]
        if len(inner) == 0:
            opt = None
        else:
            opt = inner[_KEY_OPTIONAL]
        item = {_KEY_NAME: name, _KEY_OPTIONAL: opt}
        out_list = out_list + [item]
    return {_KEY_DECLARED: True, _KEY_ENTRIES: out_list}
