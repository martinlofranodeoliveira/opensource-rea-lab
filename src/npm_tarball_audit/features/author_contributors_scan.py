_ERROR = "Invalid author scan payload or budget"
_DEFAULT_MAX_ENTRIES = 32
_DEFAULT_MAX_LENGTH = 512
_SOURCE_AUTHOR = "author"
_SOURCE_CONTRIBUTORS = "contributors"
_PAYLOAD_KEYS = ("author", "contributors", "max_entries", "max_length")
_PERSON_KEYS = ("name", "email", "url")

def _checked_string(value, max_length):
    if not isinstance(value, str):
        raise ValueError(_ERROR)
    if len(value) < 1:
        raise ValueError(_ERROR)
    if len(value) > max_length:
        raise ValueError(_ERROR)
    return value

def _entry_from_dict(item, max_length, source):
    if "name" not in item:
        raise ValueError(_ERROR)
    for k in item:
        if k not in _PERSON_KEYS:
            raise ValueError(_ERROR)
    name_value = item["name"]
    if not isinstance(name_value, str):
        raise ValueError(_ERROR)
    if len(name_value) < 1:
        raise ValueError(_ERROR)
    if len(name_value) > max_length:
        raise ValueError(_ERROR)
    if "email" in item:
        email_value = item["email"]
        if not isinstance(email_value, str):
            raise ValueError(_ERROR)
        if len(email_value) < 1:
            raise ValueError(_ERROR)
        if len(email_value) > max_length:
            raise ValueError(_ERROR)
    else:
        email_value = None
    if "url" in item:
        url_value = item["url"]
        if not isinstance(url_value, str):
            raise ValueError(_ERROR)
        if len(url_value) < 1:
            raise ValueError(_ERROR)
        if len(url_value) > max_length:
            raise ValueError(_ERROR)
    else:
        url_value = None
    entry = {"name": name_value, "email": email_value, "url": url_value, "source": source}
    return entry

def _entry_less(left, right):
    if left["source"] < right["source"]:
        return True
    if left["source"] > right["source"]:
        return False
    if left["name"] < right["name"]:
        return True
    if left["name"] > right["name"]:
        return False
    if left["email"] is None:
        left_email = ""
    else:
        left_email = left["email"]
    if right["email"] is None:
        right_email = ""
    else:
        right_email = right["email"]
    if left_email < right_email:
        return True
    if left_email > right_email:
        return False
    if left["url"] is None:
        left_url = ""
    else:
        left_url = left["url"]
    if right["url"] is None:
        right_url = ""
    else:
        right_url = right["url"]
    if left_url < right_url:
        return True
    if left_url > right_url:
        return False
    return False

def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_ERROR)
    if "author" not in payload:
        raise ValueError(_ERROR)
    if "contributors" not in payload:
        raise ValueError(_ERROR)
    for k in payload:
        if k not in _PAYLOAD_KEYS:
            raise ValueError(_ERROR)
    if "max_entries" in payload:
        max_entries = payload["max_entries"]
        if isinstance(max_entries, bool):
            raise ValueError(_ERROR)
        if not isinstance(max_entries, int):
            raise ValueError(_ERROR)
        if max_entries < 1:
            raise ValueError(_ERROR)
    else:
        max_entries = _DEFAULT_MAX_ENTRIES
    if "max_length" in payload:
        max_length = payload["max_length"]
        if isinstance(max_length, bool):
            raise ValueError(_ERROR)
        if not isinstance(max_length, int):
            raise ValueError(_ERROR)
        if max_length < 1:
            raise ValueError(_ERROR)
    else:
        max_length = _DEFAULT_MAX_LENGTH
    persons = []
    author = payload["author"]
    if author is None:
        pass
    elif isinstance(author, str):
        if len(author) < 1:
            raise ValueError(_ERROR)
        if len(author) > max_length:
            raise ValueError(_ERROR)
        entry = {"name": author, "email": None, "url": None, "source": _SOURCE_AUTHOR}
        persons.append(entry)
    elif isinstance(author, dict):
        entry = _entry_from_dict(author, max_length, _SOURCE_AUTHOR)
        persons.append(entry)
    else:
        raise ValueError(_ERROR)
    contributors = payload["contributors"]
    if contributors is None:
        pass
    elif isinstance(contributors, list):
        if len(contributors) > max_entries:
            raise ValueError(_ERROR)
        for item in contributors:
            if isinstance(item, str):
                if len(item) < 1:
                    raise ValueError(_ERROR)
                if len(item) > max_length:
                    raise ValueError(_ERROR)
                entry = {"name": item, "email": None, "url": None, "source": _SOURCE_CONTRIBUTORS}
                persons.append(entry)
            elif isinstance(item, dict):
                entry = _entry_from_dict(item, max_length, _SOURCE_CONTRIBUTORS)
                persons.append(entry)
            else:
                raise ValueError(_ERROR)
    else:
        raise ValueError(_ERROR)
    n = len(persons)
    i = 0
    while i < n:
        j = i + 1
        while j < n:
            if _entry_less(persons[j], persons[i]):
                tmp = persons[i]
                persons[i] = persons[j]
                persons[j] = tmp
            j = j + 1
        i = i + 1
    result = {"persons": persons, "count": len(persons)}
    return result
