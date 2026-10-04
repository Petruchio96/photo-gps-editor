def validate_latitude(value: float | str) -> float:
    lat = float(value)
    if not -90 <= lat <= 90:
        raise ValueError("Latitude must be between -90 and 90")
    return lat


def validate_longitude(value: float | str) -> float:
    lon = float(value)
    if not -180 <= lon <= 180:
        raise ValueError("Longitude must be between -180 and 180")
    return lon


def validate_coordinates(lat: float | str, lon: float | str) -> tuple[float, float]:
    return validate_latitude(lat), validate_longitude(lon)
