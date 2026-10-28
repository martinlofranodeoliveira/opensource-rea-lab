import math
import re
import json
import unicodedata
_PAYLOAD_ERROR = "Invalid inventory summary payload or budget"
_RECORD_ERROR = "Invalid inventory record"
_DEFAULT_BUDGET = 20000
_MIN_BUDGET = 1
_MAX_BUDGET = 20000
_MIN_BYTES = 0
_MAX_BYTES = 33554432
_PREFIX = "package/"
_SLASH = "/"
_DOT = "."
_DOUBLE_SLASH = "//"
_DOT_SLASH = "./"
_DOTDOT_SLASH = "../"
def _fresh_text(value):
    out = ""
    for ch in value:
        out = out + ch
    return out
def _lower_ascii_text(value):
    out = ""
    for ch in value:
        code = ord(ch)
        if code >= 65:
            if code <= 90:
                out = out + chr(code + 32)
            else:
                out = out + ch
        else:
            out = out + ch
    return out
def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_PAYLOAD_ERROR)
    found_inventory = False
    found_budget = False
    for k in payload:
        if k == "inventory":
            found_inventory = True
        else:
            if k == "max_entries":
                found_budget = True
            else:
                raise ValueError(_PAYLOAD_ERROR)
    if not found_inventory:
        raise ValueError(_PAYLOAD_ERROR)
    if found_budget:
        budget = payload["max_entries"]
    else:
        budget = _DEFAULT_BUDGET
    if type(budget) is not int:
        raise ValueError(_PAYLOAD_ERROR)
    if budget < _MIN_BUDGET:
        raise ValueError(_PAYLOAD_ERROR)
    if budget > _MAX_BUDGET:
        raise ValueError(_PAYLOAD_ERROR)
    inventory = payload["inventory"]
    if not isinstance(inventory, list):
        raise ValueError(_PAYLOAD_ERROR)
    if len(inventory) > budget:
        raise ValueError(_PAYLOAD_ERROR)
    seen = {}
    clean_paths = []
    clean_sizes = []
    for record in inventory:
        if not isinstance(record, dict):
            raise ValueError(_RECORD_ERROR)
        if len(record) != 3:
            raise ValueError(_RECORD_ERROR)
        if "path" not in record:
            raise ValueError(_RECORD_ERROR)
        if "bytes" not in record:
            raise ValueError(_RECORD_ERROR)
        if "sha256" not in record:
            raise ValueError(_RECORD_ERROR)
        path_val = record["path"]
        bytes_val = record["bytes"]
        sha_val = record["sha256"]
        if not isinstance(path_val, str):
            raise ValueError(_RECORD_ERROR)
        path_text = _fresh_text(path_val)
        if len(path_text) < 9:
            raise ValueError(_RECORD_ERROR)
        if len(path_text) > 256:
            raise ValueError(_RECORD_ERROR)
        if path_text[0:8] != _PREFIX:
            raise ValueError(_RECORD_ERROR)
        for ch in path_text:
            code = ord(ch)
            if code < 32:
                raise ValueError(_RECORD_ERROR)
            if code > 126:
                raise ValueError(_RECORD_ERROR)
            if code == 92:
                raise ValueError(_RECORD_ERROR)
        if path_text[len(path_text) - 1] == _SLASH:
            raise ValueError(_RECORD_ERROR)
        if _DOUBLE_SLASH in path_text:
            raise ValueError(_RECORD_ERROR)
        if _DOT_SLASH in path_text:
            raise ValueError(_RECORD_ERROR)
        if _DOTDOT_SLASH in path_text:
            raise ValueError(_RECORD_ERROR)
        cur = ""
        for ch in path_text:
            if ch == _SLASH:
                if cur == "":
                    raise ValueError(_RECORD_ERROR)
                if cur == _DOT:
                    raise ValueError(_RECORD_ERROR)
                if cur == "..":
                    raise ValueError(_RECORD_ERROR)
                cur = ""
            else:
                cur = cur + ch
        if cur == "":
            raise ValueError(_RECORD_ERROR)
        if cur == _DOT:
            raise ValueError(_RECORD_ERROR)
        if cur == "..":
            raise ValueError(_RECORD_ERROR)
        if path_text in seen:
            raise ValueError(_RECORD_ERROR)
        seen[path_text] = True
        if type(bytes_val) is not int:
            raise ValueError(_RECORD_ERROR)
        if bytes_val < _MIN_BYTES:
            raise ValueError(_RECORD_ERROR)
        if bytes_val > _MAX_BYTES:
            raise ValueError(_RECORD_ERROR)
        if not isinstance(sha_val, str):
            raise ValueError(_RECORD_ERROR)
        sha_text = _fresh_text(sha_val)
        if len(sha_text) != 64:
            raise ValueError(_RECORD_ERROR)
        for ch in sha_text:
            code = ord(ch)
            is_digit = False
            is_low = False
            is_up = False
            if code >= 48:
                if code <= 57:
                    is_digit = True
            if code >= 97:
                if code <= 102:
                    is_low = True
            if code >= 65:
                if code <= 70:
                    is_up = True
            if not is_digit:
                if not is_low:
                    if not is_up:
                        raise ValueError(_RECORD_ERROR)
        clean_paths = clean_paths + [path_text]
        clean_sizes = clean_sizes + [bytes_val]
    total_files_v = len(inventory)
    total_bytes_v = 0
    for b in clean_sizes:
        total_bytes_v = total_bytes_v + b
    groups = {}
    for idx in range(len(clean_paths)):
        p = clean_paths[idx]
        b = clean_sizes[idx]
        slash_pos = -1
        pos = 0
        for ch in p:
            if ch == _SLASH:
                slash_pos = pos
            pos = pos + 1
        base_text = ""
        pos2 = 0
        for ch in p:
            if pos2 > slash_pos:
                base_text = base_text + ch
            pos2 = pos2 + 1
        dot_pos = -1
        pos3 = 0
        for ch in base_text:
            if ch == _DOT:
                dot_pos = pos3
            pos3 = pos3 + 1
        if dot_pos == -1:
            ext_text = ""
        else:
            if dot_pos == 0:
                ext_text = ""
            else:
                suffix_text = ""
                pos4 = 0
                for ch in base_text:
                    if pos4 > dot_pos:
                        suffix_text = suffix_text + ch
                    pos4 = pos4 + 1
                ext_text = _lower_ascii_text(suffix_text)
        if ext_text in groups:
            entry = groups[ext_text]
            entry[0] = entry[0] + 1
            entry[1] = entry[1] + b
        else:
            groups[ext_text] = [1, b]
    sorted_keys = sorted(groups)
    by_list = []
    for k in sorted_keys:
        vals = groups[k]
        cnt = vals[0]
        bsum = vals[1]
        fresh_ext = _fresh_text(k)
        item = {}
        item["extension"] = fresh_ext
        item["count"] = cnt
        item["bytes"] = bsum
        by_list = by_list + [item]
    result = {}
    result["total_files"] = total_files_v
    result["total_bytes"] = total_bytes_v
    result["by_extension"] = by_list
    return result
