"""Bounded pure SemVer 2.0.0 syntax parsing.

API:
    parse_semver(text, *, max_length=4096) -> dict

Returns a dict with exactly these keys:
    major, minor, patch, prerelease, build

Core components are strings, not integers. prerelease and build are fresh
lists of strings, empty when absent. Spelling, case, and order are preserved.
Every mutable container in the result is fresh, including distinct empty
extension lists.

The default max_length is 4096 and is an inclusive Python code-point resource
budget. It is an API resource budget, not a limit imposed by SemVer itself.

Example:
    from npm_tarball_audit.semver import parse_semver

    result = parse_semver("1.2.3-alpha.1+build.7")
    # result == {
    #     "major": "1",
    #     "minor": "2",
    #     "patch": "3",
    #     "prerelease": ["alpha", "1"],
    #     "build": ["build", "7"],
    # }

This pure core does not validate npm package names, sort versions, assess
compatibility or safety, read manifests, or enforce audit/CLI identity. It is
not the full roadmap item.
"""

from __future__ import annotations

from typing import Any

_INVALID_MESSAGE = "Invalid semantic version or length budget"
_ASCII_DIGITS = frozenset("0123456789")
_ASCII_ALPHANUMERIC_HYPHEN = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-"
)
_ASCII_WHITESPACE = frozenset(" \t\n\r\f\v")


def _invalid() -> ValueError:
    return ValueError(_INVALID_MESSAGE)


def _validate_max_length(max_length: Any) -> int:
    if isinstance(max_length, bool) or not isinstance(max_length, int) or max_length <= 0:
        raise _invalid()
    return max_length


def _is_ascii_digit(value: str) -> bool:
    return value in _ASCII_DIGITS


def _is_ascii_alphanumeric_hyphen(value: str) -> bool:
    return value in _ASCII_ALPHANUMERIC_HYPHEN


def _has_whitespace(text: str) -> bool:
    return any(char in _ASCII_WHITESPACE or char.isspace() for char in text)


def _validate_numeric_identifier(identifier: str, *, allow_leading_zero: bool) -> None:
    if not identifier:
        raise _invalid()

    if not all(_is_ascii_digit(char) for char in identifier):
        raise _invalid()

    if not allow_leading_zero and len(identifier) > 1 and identifier[0] == "0":
        raise _invalid()


def _validate_identifier(identifier: str, *, allow_leading_zero: bool) -> None:
    if not identifier:
        raise _invalid()

    if not all(_is_ascii_alphanumeric_hyphen(char) for char in identifier):
        raise _invalid()

    if not allow_leading_zero:
        if all(_is_ascii_digit(char) for char in identifier):
            if len(identifier) > 1 and identifier[0] == "0":
                raise _invalid()


def _split_extensions(segment: str, *, allow_leading_zero: bool) -> list[str]:
    if not segment:
        raise _invalid()

    identifiers = segment.split(".")
    if any(not identifier for identifier in identifiers):
        raise _invalid()

    for identifier in identifiers:
        _validate_identifier(identifier, allow_leading_zero=allow_leading_zero)

    return list(identifiers)


def parse_semver(text: str, *, max_length: int = 4096) -> dict[str, Any]:
    """Parse full-string SemVer 2.0.0 syntax without package execution.

    Accepts str instances and subclasses without coercion. Raises ValueError
    with the fixed message Invalid semantic version or length budget for every
    invalid text, type, syntax, or length budget. The message does not include
    input text, cause, or exposed context.
    """
    max_length = _validate_max_length(max_length)

    if not isinstance(text, str):
        raise _invalid()

    if len(text) > max_length:
        raise _invalid()

    if not text:
        raise _invalid()

    if not text.isascii():
        raise _invalid()

    if _has_whitespace(text):
        raise _invalid()

    if text.startswith("v") or text.startswith("V"):
        raise _invalid()

    # Split build metadata first: its hyphens are identifier characters,
    # never the delimiter that introduces a prerelease.
    version, build_separator, build_text = text.partition("+")
    core, prerelease_separator, prerelease_text = version.partition("-")
    core_parts = core.split(".")

    if len(core_parts) != 3:
        raise _invalid()

    major, minor, patch = core_parts

    _validate_numeric_identifier(major, allow_leading_zero=False)
    _validate_numeric_identifier(minor, allow_leading_zero=False)
    _validate_numeric_identifier(patch, allow_leading_zero=False)

    prerelease: list[str] = []
    build: list[str] = []

    if prerelease_separator:
        prerelease = _split_extensions(prerelease_text, allow_leading_zero=False)

    if build_separator:
        build = _split_extensions(build_text, allow_leading_zero=True)

    return {
        "major": major,
        "minor": minor,
        "patch": patch,
        "prerelease": prerelease,
        "build": build,
    }
