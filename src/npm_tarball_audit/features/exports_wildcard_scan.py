import json
import math
import re
import unicodedata

_PAYLOAD_ERROR = "Invalid exports payload or budget"
_DECLARATION_ERROR = "Invalid exports declaration"
_DEFAULT_MAX_ENTRIES = 64
_DEFAULT_MAX_LENGTH = 256
_DEFAULT_MAX_DEPTH = 8
_ASTERISK = "*"

def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_PAYLOAD_ERROR)
    for _k in payload:
        if _k != "exports" and _k != "max_entries" and _k != "max_length" and _k != "max_depth":
            raise ValueError(_PAYLOAD_ERROR)
    if "exports" not in payload:
        raise ValueError(_PAYLOAD_ERROR)
    if "max_entries" in payload:
        _b1 = payload["max_entries"]
        if type(_b1) is not int:
            raise ValueError(_PAYLOAD_ERROR)
        if _b1 < 1 or _b1 > 256:
            raise ValueError(_PAYLOAD_ERROR)
        _max_entries = _b1
    else:
        _max_entries = _DEFAULT_MAX_ENTRIES
    if "max_length" in payload:
        _b2 = payload["max_length"]
        if type(_b2) is not int:
            raise ValueError(_PAYLOAD_ERROR)
        if _b2 < 1 or _b2 > 1024:
            raise ValueError(_PAYLOAD_ERROR)
        _max_length = _b2
    else:
        _max_length = _DEFAULT_MAX_LENGTH
    if "max_depth" in payload:
        _b3 = payload["max_depth"]
        if type(_b3) is not int:
            raise ValueError(_PAYLOAD_ERROR)
        if _b3 < 1 or _b3 > 16:
            raise ValueError(_PAYLOAD_ERROR)
        _max_depth = _b3
    else:
        _max_depth = _DEFAULT_MAX_DEPTH
    _exports = payload["exports"]
    if _exports is None:
        return {"declared": False, "total_keys": 0, "total_targets": 0, "wildcard_key_occurrences": 0, "wildcard_target_occurrences": 0, "wildcard_keys": [], "wildcard_targets": []}
    if isinstance(_exports, str):
        _plain = str(_exports)
        if len(_plain) < 1 or len(_plain) > _max_length:
            raise ValueError(_DECLARATION_ERROR)
        if 1 > _max_entries:
            raise ValueError(_PAYLOAD_ERROR)
        _wto = 0
        _wt = []
        if _ASTERISK in _plain:
            _wto = 1
            _wt = [str(_plain)]
        return {"declared": True, "total_keys": 0, "total_targets": 1, "wildcard_key_occurrences": 0, "wildcard_target_occurrences": _wto, "wildcard_keys": [], "wildcard_targets": _wt}
    if not isinstance(_exports, list) and not isinstance(_exports, dict):
        raise ValueError(_DECLARATION_ERROR)
    _total_keys = 0
    _total_targets = 0
    _blocked = 0
    _wkey_occ = 0
    _wtarget_occ = 0
    _wkey_unique = []
    _wtarget_unique = []
    _stack = [(_exports, 1)]
    while len(_stack) > 0:
        _pair = _stack[len(_stack) - 1]
        _stack = _stack[0:len(_stack) - 1]
        _cur = _pair[0]
        _depth = _pair[1]
        if isinstance(_cur, dict):
            for _kk in _cur:
                if not isinstance(_kk, str):
                    raise ValueError(_DECLARATION_ERROR)
                _pk = str(_kk)
                if len(_pk) < 1 or len(_pk) > _max_length:
                    raise ValueError(_DECLARATION_ERROR)
                _total_keys = _total_keys + 1
                if _total_keys + _total_targets + _blocked > _max_entries:
                    raise ValueError(_PAYLOAD_ERROR)
                if _ASTERISK in _pk:
                    _wkey_occ = _wkey_occ + 1
                    if str(_pk) not in _wkey_unique:
                        _wkey_unique = _wkey_unique + [str(_pk)]
                _vv = _cur[_kk]
                if _vv is None:
                    _blocked = _blocked + 1
                    if _total_keys + _total_targets + _blocked > _max_entries:
                        raise ValueError(_PAYLOAD_ERROR)
                elif isinstance(_vv, str):
                    _pv = str(_vv)
                    if len(_pv) < 1 or len(_pv) > _max_length:
                        raise ValueError(_DECLARATION_ERROR)
                    _total_targets = _total_targets + 1
                    if _total_keys + _total_targets + _blocked > _max_entries:
                        raise ValueError(_PAYLOAD_ERROR)
                    if _ASTERISK in _pv:
                        _wtarget_occ = _wtarget_occ + 1
                        if str(_pv) not in _wtarget_unique:
                            _wtarget_unique = _wtarget_unique + [str(_pv)]
                elif isinstance(_vv, list):
                    _nd = _depth + 1
                    if _nd > _max_depth:
                        raise ValueError(_DECLARATION_ERROR)
                    _stack = _stack + [(_vv, _nd)]
                elif isinstance(_vv, dict):
                    _nd2 = _depth + 1
                    if _nd2 > _max_depth:
                        raise ValueError(_DECLARATION_ERROR)
                    _stack = _stack + [(_vv, _nd2)]
                else:
                    raise ValueError(_DECLARATION_ERROR)
        elif isinstance(_cur, list):
            for _el in _cur:
                if _el is None:
                    _blocked = _blocked + 1
                    if _total_keys + _total_targets + _blocked > _max_entries:
                        raise ValueError(_PAYLOAD_ERROR)
                elif isinstance(_el, str):
                    _pe = str(_el)
                    if len(_pe) < 1 or len(_pe) > _max_length:
                        raise ValueError(_DECLARATION_ERROR)
                    _total_targets = _total_targets + 1
                    if _total_keys + _total_targets + _blocked > _max_entries:
                        raise ValueError(_PAYLOAD_ERROR)
                    if _ASTERISK in _pe:
                        _wtarget_occ = _wtarget_occ + 1
                        if str(_pe) not in _wtarget_unique:
                            _wtarget_unique = _wtarget_unique + [str(_pe)]
                elif isinstance(_el, list):
                    _nd3 = _depth + 1
                    if _nd3 > _max_depth:
                        raise ValueError(_DECLARATION_ERROR)
                    _stack = _stack + [(_el, _nd3)]
                elif isinstance(_el, dict):
                    _nd4 = _depth + 1
                    if _nd4 > _max_depth:
                        raise ValueError(_DECLARATION_ERROR)
                    _stack = _stack + [(_el, _nd4)]
                else:
                    raise ValueError(_DECLARATION_ERROR)
        else:
            raise ValueError(_DECLARATION_ERROR)
    _sorted_keys = sorted(_wkey_unique)
    _sorted_targets = sorted(_wtarget_unique)
    _out_keys = []
    for _s in _sorted_keys:
        _out_keys = _out_keys + [str(_s)]
    _out_targets = []
    for _t in _sorted_targets:
        _out_targets = _out_targets + [str(_t)]
    return {"declared": True, "total_keys": _total_keys, "total_targets": _total_targets, "wildcard_key_occurrences": _wkey_occ, "wildcard_target_occurrences": _wtarget_occ, "wildcard_keys": _out_keys, "wildcard_targets": _out_targets}
