"""Offline repository declaration enumerator for reproducible audits.

Declaration enumeration only. Reports declared entries verbatim.
"""
import json
import math
import re
import unicodedata
_ERROR_MESSAGE = "Invalid repository scan payload or budget"
_DEFAULT_MAX_LENGTH = 512
_KEY_REPOSITORY = "repository"
_KEY_MAX_LENGTH = "max_length"
_KEY_TYPE = "type"
_KEY_URL = "url"
_KEY_DIRECTORY = "directory"
_KEY_COUNT = "count"
def run_feature(payload):
    if not isinstance(payload, dict):
        raise ValueError(_ERROR_MESSAGE)
    if len(payload) == 1:
        if _KEY_REPOSITORY not in payload:
            raise ValueError(_ERROR_MESSAGE)
        budget = _DEFAULT_MAX_LENGTH
    elif len(payload) == 2:
        if _KEY_REPOSITORY not in payload:
            raise ValueError(_ERROR_MESSAGE)
        if _KEY_MAX_LENGTH not in payload:
            raise ValueError(_ERROR_MESSAGE)
        budget = payload[_KEY_MAX_LENGTH]
        if isinstance(budget, bool):
            raise ValueError(_ERROR_MESSAGE)
        if not isinstance(budget, int):
            raise ValueError(_ERROR_MESSAGE)
        if budget <= 0:
            raise ValueError(_ERROR_MESSAGE)
    else:
        raise ValueError(_ERROR_MESSAGE)
    repository = payload[_KEY_REPOSITORY]
    if repository is None:
        result = {_KEY_REPOSITORY: None, _KEY_COUNT: 0}
        return result
    if isinstance(repository, str):
        if len(repository) < 1:
            raise ValueError(_ERROR_MESSAGE)
        if len(repository) > budget:
            raise ValueError(_ERROR_MESSAGE)
        entry = {_KEY_TYPE: None, _KEY_URL: repository, _KEY_DIRECTORY: None}
        result = {_KEY_REPOSITORY: entry, _KEY_COUNT: 1}
        return result
    if isinstance(repository, dict):
        if _KEY_URL not in repository:
            raise ValueError(_ERROR_MESSAGE)
        if len(repository) < 1:
            raise ValueError(_ERROR_MESSAGE)
        if len(repository) > 3:
            raise ValueError(_ERROR_MESSAGE)
        for key in repository:
            if key != _KEY_TYPE and key != _KEY_URL and key != _KEY_DIRECTORY:
                raise ValueError(_ERROR_MESSAGE)
        url_value = repository[_KEY_URL]
        if not isinstance(url_value, str):
            raise ValueError(_ERROR_MESSAGE)
        if len(url_value) < 1:
            raise ValueError(_ERROR_MESSAGE)
        if len(url_value) > budget:
            raise ValueError(_ERROR_MESSAGE)
        if _KEY_TYPE in repository:
            type_value = repository[_KEY_TYPE]
            if not isinstance(type_value, str):
                raise ValueError(_ERROR_MESSAGE)
            if len(type_value) < 1:
                raise ValueError(_ERROR_MESSAGE)
            if len(type_value) > budget:
                raise ValueError(_ERROR_MESSAGE)
        else:
            type_value = None
        if _KEY_DIRECTORY in repository:
            directory_value = repository[_KEY_DIRECTORY]
            if not isinstance(directory_value, str):
                raise ValueError(_ERROR_MESSAGE)
            if len(directory_value) < 1:
                raise ValueError(_ERROR_MESSAGE)
            if len(directory_value) > budget:
                raise ValueError(_ERROR_MESSAGE)
        else:
            directory_value = None
        entry = {_KEY_TYPE: type_value, _KEY_URL: url_value, _KEY_DIRECTORY: directory_value}
        result = {_KEY_REPOSITORY: entry, _KEY_COUNT: 1}
        return result
    raise ValueError(_ERROR_MESSAGE)
