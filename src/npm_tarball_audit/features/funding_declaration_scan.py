DEFAULT_MAX_ENTRIES = 16
DEFAULT_MAX_LENGTH = 512
ERROR_MESSAGE = "Invalid funding scan payload or budget"


def _copy_text(value):
    return value[0:len(value)]


def _entry_from_str(value, max_length):
    if not isinstance(value, str):
        raise ValueError(ERROR_MESSAGE)
    if len(value) < 1:
        raise ValueError(ERROR_MESSAGE)
    if len(value) > max_length:
        raise ValueError(ERROR_MESSAGE)
    copied = _copy_text(value)
    entry = {"type": None, "url": copied}
    return entry


def _entry_from_dict(source, max_length):
    seen_type = False
    seen_url = False
    total = 0
    for key in source:
        total = total + 1
        if key == "type":
            if seen_type:
                raise ValueError(ERROR_MESSAGE)
            seen_type = True
        elif key == "url":
            if seen_url:
                raise ValueError(ERROR_MESSAGE)
            seen_url = True
        else:
            raise ValueError(ERROR_MESSAGE)
    if total < 1:
        raise ValueError(ERROR_MESSAGE)
    if total > 2:
        raise ValueError(ERROR_MESSAGE)
    if not seen_type and not seen_url:
        raise ValueError(ERROR_MESSAGE)
    out_type = None
    out_url = None
    if seen_type:
        raw_type = source["type"]
        if not isinstance(raw_type, str):
            raise ValueError(ERROR_MESSAGE)
        if len(raw_type) < 1:
            raise ValueError(ERROR_MESSAGE)
        if len(raw_type) > max_length:
            raise ValueError(ERROR_MESSAGE)
        out_type = _copy_text(raw_type)
    if seen_url:
        raw_url = source["url"]
        if not isinstance(raw_url, str):
            raise ValueError(ERROR_MESSAGE)
        if len(raw_url) < 1:
            raise ValueError(ERROR_MESSAGE)
        if len(raw_url) > max_length:
            raise ValueError(ERROR_MESSAGE)
        out_url = _copy_text(raw_url)
    entry = {"type": out_type, "url": out_url}
    return entry


def run_feature(payload):
    if type(payload) is not dict:
        raise ValueError(ERROR_MESSAGE)
    has_funding = False
    has_max_entries = False
    has_max_length = False
    for key in payload:
        if key == "funding":
            if has_funding:
                raise ValueError(ERROR_MESSAGE)
            has_funding = True
        elif key == "max_entries":
            if has_max_entries:
                raise ValueError(ERROR_MESSAGE)
            has_max_entries = True
        elif key == "max_length":
            if has_max_length:
                raise ValueError(ERROR_MESSAGE)
            has_max_length = True
        else:
            raise ValueError(ERROR_MESSAGE)
    if not has_funding:
        raise ValueError(ERROR_MESSAGE)
    funding = payload["funding"]
    max_entries = DEFAULT_MAX_ENTRIES
    max_length = DEFAULT_MAX_LENGTH
    if has_max_entries:
        raw_entries = payload["max_entries"]
        if type(raw_entries) is not int:
            raise ValueError(ERROR_MESSAGE)
        if raw_entries <= 0:
            raise ValueError(ERROR_MESSAGE)
        max_entries = raw_entries
    if has_max_length:
        raw_length = payload["max_length"]
        if type(raw_length) is not int:
            raise ValueError(ERROR_MESSAGE)
        if raw_length <= 0:
            raise ValueError(ERROR_MESSAGE)
        max_length = raw_length
    if funding is None:
        entries = []
        result = {"entries": entries, "count": 0}
        return result
    if isinstance(funding, str):
        single = _entry_from_str(funding, max_length)
        entries = []
        entries = entries + [single]
        result = {"entries": entries, "count": 1}
        return result
    if isinstance(funding, dict):
        single = _entry_from_dict(funding, max_length)
        entries = []
        entries = entries + [single]
        result = {"entries": entries, "count": 1}
        return result
    if isinstance(funding, list):
        total = len(funding)
        if total == 0:
            entries = []
            result = {"entries": entries, "count": 0}
            return result
        if total > max_entries:
            raise ValueError(ERROR_MESSAGE)
        entries = []
        for item in funding:
            if isinstance(item, str):
                one = _entry_from_str(item, max_length)
                entries = entries + [one]
            elif isinstance(item, dict):
                one = _entry_from_dict(item, max_length)
                entries = entries + [one]
            else:
                raise ValueError(ERROR_MESSAGE)
        count = len(entries)
        result = {"entries": entries, "count": count}
        return result
    raise ValueError(ERROR_MESSAGE)
