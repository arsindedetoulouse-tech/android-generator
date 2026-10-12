from __future__ import annotations

import re
from collections.abc import Sequence

_PACKAGE_SEGMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_APPLICATION_ID_SEGMENT = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_ALPHANUMERIC_SUBTAG = re.compile(r"^[A-Za-z0-9]{1,8}$")
_LANGUAGE_KEYWORDS = {
    "abstract",
    "as",
    "assert",
    "boolean",
    "break",
    "byte",
    "by",
    "case",
    "catch",
    "char",
    "class",
    "continue",
    "default",
    "do",
    "double",
    "else",
    "enum",
    "extends",
    "false",
    "final",
    "finally",
    "float",
    "for",
    "fun",
    "if",
    "implements",
    "import",
    "in",
    "instanceof",
    "int",
    "interface",
    "internal",
    "is",
    "long",
    "native",
    "new",
    "null",
    "object",
    "open",
    "override",
    "package",
    "private",
    "protected",
    "public",
    "return",
    "short",
    "static",
    "strictfp",
    "super",
    "suspend",
    "switch",
    "synchronized",
    "this",
    "throw",
    "throws",
    "transient",
    "true",
    "try",
    "val",
    "var",
    "void",
    "volatile",
    "when",
    "while",
}
_GRANDFATHERED_TAGS = {
    "art-lojban": "art-lojban",
    "cel-gaulish": "cel-gaulish",
    "en-gb-oed": "en-GB-oed",
    "i-ami": "i-ami",
    "i-bnn": "i-bnn",
    "i-default": "i-default",
    "i-enochian": "i-enochian",
    "i-hak": "i-hak",
    "i-klingon": "i-klingon",
    "i-lux": "i-lux",
    "i-mingo": "i-mingo",
    "i-navajo": "i-navajo",
    "i-pwn": "i-pwn",
    "i-tao": "i-tao",
    "i-tay": "i-tay",
    "i-tsu": "i-tsu",
    "no-bok": "no-bok",
    "no-nyn": "no-nyn",
    "sgn-be-fr": "sgn-BE-FR",
    "sgn-be-nl": "sgn-BE-NL",
    "sgn-ch-de": "sgn-CH-DE",
    "zh-guoyu": "zh-guoyu",
    "zh-hakka": "zh-hakka",
    "zh-min": "zh-min",
    "zh-min-nan": "zh-min-nan",
    "zh-xiang": "zh-xiang",
}


class InputValidationError(ValueError):
    """Raised when a user-supplied project identifier is invalid."""


def validate_android_package(value: str, option: str) -> str:
    segments = value.split(".")
    if (
        not value
        or any(
            not _PACKAGE_SEGMENT.fullmatch(segment)
            or segment == "_"
            or segment in _LANGUAGE_KEYWORDS
            for segment in segments
        )
    ):
        raise InputValidationError(
            f"{option} must be a dot-separated Java/Kotlin package name"
        )
    return value


def validate_android_application_id(value: str) -> str:
    segments = value.split(".")
    if (
        len(segments) < 2
        or any(not _APPLICATION_ID_SEGMENT.fullmatch(segment) for segment in segments)
    ):
        raise InputValidationError(
            "--application-id must contain at least two dot-separated segments "
            "starting with a letter"
        )
    return value


def validate_locale_tag(value: str) -> str:
    if not value:
        raise InputValidationError("--locale must be a valid BCP-47 language tag")

    normalized_key = value.lower()
    grandfathered = _GRANDFATHERED_TAGS.get(normalized_key)
    if grandfathered is not None:
        return grandfathered

    parts = value.split("-")
    if any(not part for part in parts):
        raise _invalid_locale(value)

    if parts[0].lower() == "x":
        if len(parts) < 2 or not all(
            _ALPHANUMERIC_SUBTAG.fullmatch(part) for part in parts[1:]
        ):
            raise _invalid_locale(value)
        return "-".join(part.lower() for part in parts)

    language = parts[0]
    if not (
        re.fullmatch(r"[A-Za-z]{2,3}", language)
        or re.fullmatch(r"[A-Za-z]{4}", language)
        or re.fullmatch(r"[A-Za-z]{5,8}", language)
    ):
        raise _invalid_locale(value)

    canonical = [language.lower()]
    index = 1
    if len(language) <= 3:
        extlang_count = 0
        while (
            index < len(parts)
            and extlang_count < 3
            and re.fullmatch(r"[A-Za-z]{3}", parts[index])
        ):
            canonical.append(parts[index].lower())
            index += 1
            extlang_count += 1

    if index < len(parts) and re.fullmatch(r"[A-Za-z]{4}", parts[index]):
        canonical.append(parts[index].title())
        index += 1

    if index < len(parts) and (
        re.fullmatch(r"[A-Za-z]{2}", parts[index])
        or re.fullmatch(r"\d{3}", parts[index])
    ):
        canonical.append(parts[index].upper())
        index += 1

    variants: set[str] = set()
    while index < len(parts) and (
        re.fullmatch(r"[A-Za-z0-9]{5,8}", parts[index])
        or re.fullmatch(r"\d[A-Za-z0-9]{3}", parts[index])
    ):
        variant = parts[index].lower()
        if variant in variants:
            raise _invalid_locale(value)
        variants.add(variant)
        canonical.append(variant)
        index += 1

    extensions: set[str] = set()
    while (
        index < len(parts)
        and re.fullmatch(r"[A-Za-z0-9]", parts[index])
        and parts[index].lower() != "x"
    ):
        singleton = parts[index].lower()
        if singleton in extensions:
            raise _invalid_locale(value)
        extensions.add(singleton)
        canonical.append(singleton)
        index += 1
        first_extension_part = index
        while index < len(parts) and re.fullmatch(
            r"[A-Za-z0-9]{2,8}", parts[index]
        ):
            canonical.append(parts[index].lower())
            index += 1
        if index == first_extension_part:
            raise _invalid_locale(value)

    if index < len(parts) and parts[index].lower() == "x":
        canonical.append("x")
        index += 1
        first_private_part = index
        while index < len(parts) and _ALPHANUMERIC_SUBTAG.fullmatch(parts[index]):
            canonical.append(parts[index].lower())
            index += 1
        if index == first_private_part:
            raise _invalid_locale(value)

    if index != len(parts):
        raise _invalid_locale(value)
    return "-".join(canonical)


def normalize_locale_tags(values: Sequence[str]) -> tuple[str, ...]:
    locales: list[str] = []
    seen: set[str] = set()
    for value in values:
        locale_tag = validate_locale_tag(value)
        key = locale_tag.casefold()
        if key not in seen:
            locales.append(locale_tag)
            seen.add(key)
    return tuple(locales)


def _invalid_locale(value: str) -> InputValidationError:
    return InputValidationError(
        f"--locale must be a valid BCP-47 language tag: {value!r}"
    )
