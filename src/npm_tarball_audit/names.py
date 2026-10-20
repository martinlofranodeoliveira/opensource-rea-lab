"""Split scoped npm package names with explicit local ASCII policy.

API:
    parse_package_name(value) -> dict

Returns a newly allocated plain dict with exactly ``scope`` and ``name``,
e.g. ``{"scope": "acme", "name": "widget"}``. ``scope`` is ``None``
for unscoped names or a string without ``@``; ``name`` is a string.
Freshness applies to the mutable result container.

Example:
    from npm_tarball_audit.names import parse_package_name

    parse_package_name("@my-scope/my-name")
    # {"scope": "my-scope", "name": "my-name"}
    parse_package_name("example")
    # {"scope": None, "name": "example"}

Local syntax policy: 1-214 ASCII characters total, including ``@`` and
``/`` when present; lowercase letters, digits, ``.``, ``_`` and ``-``
only, plus leading ``@`` and a single ``/`` for scoped form
``@scope/name``. Each of scope and name must be non-empty and start
with a lowercase letter or digit. No coercion, trimming, spaces,
Unicode, or escapes are accepted. Ordinary ``str`` subclasses are
accepted without coercion.

Invalid inputs raise ``ValueError("Invalid package name")`` without
copying the input into the error.

This pure function reads no files, uses no network, and executes no
package code. It checks local syntax only. It does not validate name
availability, the complete npm registry policy, safety, security,
compatibility, or module resolution.
"""

from __future__ import annotations

__all__ = ["parse_package_name"]

_INVALID_MESSAGE = "Invalid package name"
_MAX_LENGTH = 214
_ALLOWED_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789-_.")
_ALLOWED_START = frozenset("abcdefghijklmnopqrstuvwxyz0123456789")


def _invalid() -> ValueError:
    return ValueError(_INVALID_MESSAGE)


def _validate_component(component: str) -> None:
    if not component:
        raise _invalid()
    if component[0] not in _ALLOWED_START:
        raise _invalid()
    for char in component:
        if char not in _ALLOWED_CHARS:
            raise _invalid()


def parse_package_name(value: str) -> dict[str, object]:
    """Split an npm package name into ``{"scope": ..., "name": ...}``.

    Accepts ``str`` instances and subclasses without coercion. Returns a
    newly allocated plain ``dict`` with exactly ``scope`` and ``name``.
    Raises ``ValueError("Invalid package name")`` without echoing input
    for every invalid type, length, or syntax.
    """
    if not isinstance(value, str):
        raise _invalid()
    if len(value) < 1 or len(value) > _MAX_LENGTH:
        raise _invalid()
    if not value.isascii():
        raise _invalid()
    if value.startswith("@"):
        parts = value.split("/")
        if len(parts) != 2:
            raise _invalid()
        scope_with_at, name_part = parts
        if len(scope_with_at) < 2:
            raise _invalid()
        scope_part = scope_with_at[1:]
        if not scope_part or not name_part:
            raise _invalid()
        _validate_component(scope_part)
        _validate_component(name_part)
        return {"scope": scope_part, "name": name_part}
    if "@" in value or "/" in value:
        raise _invalid()
    _validate_component(value)
    return {"scope": None, "name": value}
