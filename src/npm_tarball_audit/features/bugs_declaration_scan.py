_ERROR_MESSAGE = "Invalid bugs scan payload or budget"
_DEFAULT_BUDGET = 512
_KEY_BUGS = "bugs"
_KEY_MAX_LENGTH = "max_length"
_KEY_URL = "url"
_KEY_EMAIL = "email"
_KEY_DECLARED = "declared"

def _copy_text(value):
    result = ""
    for ch in value:
        result = result + ch
    return result

def _is_text_ok(value, limit):
    if not isinstance(value, str):
        return False
    count = len(value)
    if count < 1:
        return False
    if count > limit:
        return False
    return True

def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_ERROR_MESSAGE)
    found_bugs = False
    found_budget = False
    for k in payload:
        if k == _KEY_BUGS:
            found_bugs = True
        elif k == _KEY_MAX_LENGTH:
            found_budget = True
        else:
            raise ValueError(_ERROR_MESSAGE)
    if not found_bugs:
        raise ValueError(_ERROR_MESSAGE)
    total = len(payload)
    if total < 1:
        raise ValueError(_ERROR_MESSAGE)
    if total > 2:
        raise ValueError(_ERROR_MESSAGE)
    if found_budget:
        if total != 2:
            raise ValueError(_ERROR_MESSAGE)
    if not found_budget:
        if total != 1:
            raise ValueError(_ERROR_MESSAGE)
    limit = _DEFAULT_BUDGET
    if found_budget:
        raw_limit = payload[_KEY_MAX_LENGTH]
        if type(raw_limit) is not int:
            raise ValueError(_ERROR_MESSAGE)
        if raw_limit <= 0:
            raise ValueError(_ERROR_MESSAGE)
        limit = raw_limit
    bugs = payload[_KEY_BUGS]
    if bugs is None:
        out = {}
        out[_KEY_URL] = None
        out[_KEY_EMAIL] = None
        out[_KEY_DECLARED] = False
        return out
    if isinstance(bugs, str):
        if not _is_text_ok(bugs, limit):
            raise ValueError(_ERROR_MESSAGE)
        url_copy = _copy_text(bugs)
        out = {}
        out[_KEY_URL] = url_copy
        out[_KEY_EMAIL] = None
        out[_KEY_DECLARED] = True
        return out
    if isinstance(bugs, dict):
        n = len(bugs)
        if n < 1:
            raise ValueError(_ERROR_MESSAGE)
        if n > 2:
            raise ValueError(_ERROR_MESSAGE)
        has_url = False
        has_email = False
        for k in bugs:
            if k == _KEY_URL:
                has_url = True
            elif k == _KEY_EMAIL:
                has_email = True
            else:
                raise ValueError(_ERROR_MESSAGE)
        if not has_url:
            if not has_email:
                raise ValueError(_ERROR_MESSAGE)
        url_out = None
        email_out = None
        if has_url:
            raw_url = bugs[_KEY_URL]
            if not _is_text_ok(raw_url, limit):
                raise ValueError(_ERROR_MESSAGE)
            url_out = _copy_text(raw_url)
        if has_email:
            raw_email = bugs[_KEY_EMAIL]
            if not _is_text_ok(raw_email, limit):
                raise ValueError(_ERROR_MESSAGE)
            email_out = _copy_text(raw_email)
        out = {}
        out[_KEY_URL] = url_out
        out[_KEY_EMAIL] = email_out
        out[_KEY_DECLARED] = True
        return out
    raise ValueError(_ERROR_MESSAGE)
