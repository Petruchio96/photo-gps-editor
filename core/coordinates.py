def validate_latitude(value: str) -> float:
    lat = float(value)
    if not -90 <= lat <= 90:
        raise ValueError("Latitude must be between -90 and 90")
    return lat


def validate_longitude(value: str) -> float:
    lon = float(value)
    if not -180 <= lon <= 180:
        raise ValueError("Longitude must be between -180 and 180")
    return lon


def validate_coordinates(lat: str, lon: str) -> tuple[float, float]:
    return validate_latitude(lat), validate_longitude(lon)