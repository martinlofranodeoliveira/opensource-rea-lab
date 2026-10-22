"""Offline publishConfig declaration enumerator for reproducible audits.

Declaration enumeration only, not execution, installation, resolution,
fetching, existence check, provenance verification, safety, security,
compatibility or legal review; values are reported as declared.
"""

_DEFAULT_MAX_ENTRIES = 32
_DEFAULT_MAX_LENGTH = 512
_ERROR_MESSAGE = "Invalid publishConfig scan payload or budget"
_KNOWN_KEYS = ("publishConfig", "max_entries", "max_length")


def _is_positive_int(value):
    if type(value) is not int:
        return False
    if value <= 0:
        return False
    return True


def _is_valid_text(value, limit):
    if not isinstance(value, str):
        return False
    if len(value) < 1:
        return False
    if len(value) > limit:
        return False
    return True


def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_ERROR_MESSAGE)
    if "publishConfig" not in payload:
        raise ValueError(_ERROR_MESSAGE)
    for key in payload:
        if key not in _KNOWN_KEYS:
            raise ValueError(_ERROR_MESSAGE)
    max_entries = _DEFAULT_MAX_ENTRIES
    max_length = _DEFAULT_MAX_LENGTH
    if "max_entries" in payload:
        candidate_entries = payload["max_entries"]
        if not _is_positive_int(candidate_entries):
            raise ValueError(_ERROR_MESSAGE)
        max_entries = candidate_entries
    if "max_length" in payload:
        candidate_length = payload["max_length"]
        if not _is_positive_int(candidate_length):
            raise ValueError(_ERROR_MESSAGE)
        max_length = candidate_length
    declared_value = payload["publishConfig"]
    if declared_value is None:
        return {"entries": None, "declared": False}
    if not isinstance(declared_value, dict):
        raise ValueError(_ERROR_MESSAGE)
    if len(declared_value) > max_entries:
        raise ValueError(_ERROR_MESSAGE)
    for map_key in declared_value:
        map_value = declared_value[map_key]
        if not _is_valid_text(map_key, max_length):
            raise ValueError(_ERROR_MESSAGE)
        if not _is_valid_text(map_value, max_length):
            raise ValueError(_ERROR_MESSAGE)
    try:
        ordered_keys = sorted(declared_value)
    except Exception:
        raise ValueError(_ERROR_MESSAGE)
    entries = []
    for ordered_key in ordered_keys:
        ordered_value = declared_value[ordered_key]
        item = {"key": ordered_key, "value": ordered_value}
        entries.append(item)
    return {"entries": entries, "declared": True}
