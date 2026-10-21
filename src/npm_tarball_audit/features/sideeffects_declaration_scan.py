_DEFAULT_MAX_ENTRIES = 32
_DEFAULT_MAX_LENGTH = 512
_ERROR = "Invalid sideEffects scan payload or budget"
def run_feature(payload):
    if isinstance(payload, dict) is False:
        raise ValueError(_ERROR)
    if "sideEffects" not in payload:
        raise ValueError(_ERROR)
    for k in payload:
        if k != "sideEffects":
            if k != "max_entries":
                if k != "max_length":
                    raise ValueError(_ERROR)
    if "max_entries" in payload:
        _me = payload["max_entries"]
        if type(_me) is not int:
            raise ValueError(_ERROR)
        if _me <= 0:
            raise ValueError(_ERROR)
        _max_entries = _me
    else:
        _max_entries = _DEFAULT_MAX_ENTRIES
    if "max_length" in payload:
        _ml = payload["max_length"]
        if type(_ml) is not int:
            raise ValueError(_ERROR)
        if _ml <= 0:
            raise ValueError(_ERROR)
        _max_length = _ml
    else:
        _max_length = _DEFAULT_MAX_LENGTH
    _v = payload["sideEffects"]
    if _v is None:
        return {"flag": None, "entries": None, "declared": False}
    if type(_v) is bool:
        return {"flag": _v, "entries": None, "declared": True}
    if isinstance(_v, str):
        if len(_v) < 1:
            raise ValueError(_ERROR)
        if len(_v) > _max_length:
            raise ValueError(_ERROR)
        _s = str(_v)
        _single = [_s]
        return {"flag": None, "entries": _single, "declared": True}
    if type(_v) is list:
        if len(_v) > _max_entries:
            raise ValueError(_ERROR)
        _out = []
        for _i in range(len(_v)):
            _item = _v[_i]
            if isinstance(_item, str) is False:
                raise ValueError(_ERROR)
            if len(_item) < 1:
                raise ValueError(_ERROR)
            if len(_item) > _max_length:
                raise ValueError(_ERROR)
            _fresh = str(_item)
            _out = _out + [_fresh]
        return {"flag": None, "entries": _out, "declared": True}
    raise ValueError(_ERROR)
