_DEFAULT_MAX_ENTRIES = 32
_DEFAULT_MAX_LENGTH = 512
_ERROR_MESSAGE = "Invalid man scan payload or budget"

def run_feature(payload):
    max_entries = _DEFAULT_MAX_ENTRIES
    max_length = _DEFAULT_MAX_LENGTH
    if not isinstance(payload, dict):
        raise ValueError(_ERROR_MESSAGE)
    if "man" not in payload:
        raise ValueError(_ERROR_MESSAGE)
    for key in payload:
        if key != "man" and key != "max_entries" and key != "max_length":
            raise ValueError(_ERROR_MESSAGE)
    if "max_entries" in payload:
        candidate_entries = payload["max_entries"]
        if isinstance(candidate_entries, bool):
            raise ValueError(_ERROR_MESSAGE)
        if not isinstance(candidate_entries, int):
            raise ValueError(_ERROR_MESSAGE)
        if candidate_entries <= 0:
            raise ValueError(_ERROR_MESSAGE)
        max_entries = candidate_entries
    if "max_length" in payload:
        candidate_length = payload["max_length"]
        if isinstance(candidate_length, bool):
            raise ValueError(_ERROR_MESSAGE)
        if not isinstance(candidate_length, int):
            raise ValueError(_ERROR_MESSAGE)
        if candidate_length <= 0:
            raise ValueError(_ERROR_MESSAGE)
        max_length = candidate_length
    man_value = payload["man"]
    if man_value is None:
        return {"entries": None, "declared": False}
    if isinstance(man_value, str):
        if len(man_value) < 1:
            raise ValueError(_ERROR_MESSAGE)
        if len(man_value) > max_length:
            raise ValueError(_ERROR_MESSAGE)
        single = [man_value]
        return {"entries": single, "declared": True}
    if isinstance(man_value, list):
        if len(man_value) > max_entries:
            raise ValueError(_ERROR_MESSAGE)
        checked = []
        for item in man_value:
            if not isinstance(item, str):
                raise ValueError(_ERROR_MESSAGE)
            if len(item) < 1:
                raise ValueError(_ERROR_MESSAGE)
            if len(item) > max_length:
                raise ValueError(_ERROR_MESSAGE)
            checked = checked + [item]
        count = len(checked)
        for i in range(count):
            for j in range(i + 1, count):
                if checked[i] == checked[j]:
                    raise ValueError(_ERROR_MESSAGE)
        ordered = sorted(checked)
        return {"entries": ordered, "declared": True}
    raise ValueError(_ERROR_MESSAGE)
