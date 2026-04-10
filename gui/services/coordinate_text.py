"""
Helpers for parsing coordinate text entered or pasted into the GUI.
"""

from __future__ import annotations

import re

from core.coordinates import validate_latitude, validate_longitude

_PAIR_SEPARATOR_PATTERN = re.compile(r"\s*,\s*|\s+(?=[NSEW])", re.IGNORECASE)
_SINGLE_COORDINATE_PATTERN = re.compile(
    r"""
    ^\s*
    (?P<prefix>[NSEW])?
    \s*
    (?P<degrees>[+-]?\d+(?:\.\d+)?)
    (?:\s*[°\s]\s*
        (?P<minutes>\d+(?:\.\d+)?)
        \s*(?:['’′])?
        (?:\s*
            (?P<seconds>\d+(?:\.\d+)?)
            \s*(?:["”″])?
        )?
    )?
    \s*(?P<suffix>[NSEW])?
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _direction_sign(direction: str | None) -> int:
    if direction is None:
        return 1
    return -1 if direction.upper() in {"S", "W"} else 1


def _parse_coordinate_value(text: str, *, is_latitude: bool) -> float:
    """
    Parse one coordinate in decimal, DMS, or decimal-minutes form.
    """
    text = text.strip()
    if not text:
        raise ValueError("Coordinate is empty")

    match = _SINGLE_COORDINATE_PATTERN.match(text)
    if match is None:
        raise ValueError("Unsupported coordinate format")

    prefix = match.group("prefix")
    suffix = match.group("suffix")
    if prefix and suffix and prefix.upper() != suffix.upper():
        raise ValueError("Conflicting coordinate directions")

    direction = suffix or prefix
    sign = _direction_sign(direction)

    degrees = float(match.group("degrees"))
    minutes_text = match.group("minutes")
    seconds_text = match.group("seconds")

    if direction and degrees < 0:
        raise ValueError("Do not combine sign and compass direction")

    absolute_degrees = abs(degrees)
    value = absolute_degrees

    if minutes_text is not None:
        minutes = float(minutes_text)
        if not 0 <= minutes < 60:
            raise ValueError("Minutes must be between 0 and 60")
        value += minutes / 60

        if seconds_text is not None:
            seconds = float(seconds_text)
            if not 0 <= seconds < 60:
                raise ValueError("Seconds must be between 0 and 60")
            value += seconds / 3600

    if direction is None and degrees < 0:
        value *= -1
    else:
        value *= sign

    if is_latitude:
        return validate_latitude(str(value))
    return validate_longitude(str(value))


def parse_latitude_text(text: str) -> float:
    """
    Parse a latitude field into decimal degrees.
    """
    return _parse_coordinate_value(text, is_latitude=True)


def parse_longitude_text(text: str) -> float:
    """
    Parse a longitude field into decimal degrees.
    """
    return _parse_coordinate_value(text, is_latitude=False)


def parse_coordinate_text(text: str) -> tuple[str, str] | None:
    """
    Parse a combined coordinate string into separate latitude and longitude
    strings for the two input fields.
    """
    text = text.strip()
    if not text:
        return None

    parts = [part.strip() for part in _PAIR_SEPARATOR_PATTERN.split(text) if part.strip()]
    if len(parts) == 2:
        try:
            parse_latitude_text(parts[0])
            parse_longitude_text(parts[1])
        except ValueError:
            return None
        return parts[0], parts[1]

    for match in re.finditer(r"\s+", text):
        left = text[: match.start()].strip()
        right = text[match.end() :].strip()

        if not left or not right:
            continue

        try:
            parse_latitude_text(left)
            parse_longitude_text(right)
        except ValueError:
            continue

        return left, right

    parts = re.findall(r"[+-]?\d+(?:\.\d+)?", text)
    if len(parts) != 2:
        return None

    try:
        parse_latitude_text(parts[0])
        parse_longitude_text(parts[1])
    except ValueError:
        return None

    return parts[0], parts[1]


def parse_manual_coordinates(
    latitude_text: str,
    longitude_text: str,
) -> tuple[float, float] | None:
    """
    Parse and validate manual latitude and longitude field values.
    """
    latitude_text = latitude_text.strip()
    longitude_text = longitude_text.strip()

    if not latitude_text or not longitude_text:
        return None

    try:
        latitude = parse_latitude_text(latitude_text)
        longitude = parse_longitude_text(longitude_text)
    except ValueError:
        return None

    return latitude, longitude
