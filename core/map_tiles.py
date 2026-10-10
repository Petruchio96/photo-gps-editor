"""
Slippy-map tile math and the map's tile sources, with no Qt.

Web maps cut the world (in the Web Mercator projection) into 256-pixel square
tiles. At zoom level z the world is 2**z tiles wide and tall. Here positions
are "world" coordinates: x and y from 0 to 1 across the whole map, with (0, 0)
at the top-left (180° W, about 85° N). Multiplying by the world size in pixels
at a zoom level gives pixel positions on that level.

Kept free of Qt so a future web version could reuse the tile sources.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from urllib.parse import quote

TILE_SIZE = 256

# Web Mercator cannot show the poles; maps stop at this latitude.
MAX_LATITUDE = 85.05112878

MIN_ZOOM = 2
MAX_ZOOM = 19


@dataclass(frozen=True)
class TileSource:
    """
    One map style (street map, satellite) and where its tiles come from.

    Attributes:
        key:
            Short name used in settings, for example "street".
        name:
            Shown on the map's layer buttons.
        url_template:
            Tile address with {z}, {x}, and {y} placeholders, and {key}
            for the user's API key if the source needs one.
        max_zoom:
            The most detailed level the server has (in its own numbering).
            Closer zoom levels enlarge tiles from this level.
        attribution_html:
            Credit line the map must show (a licensing requirement).
        coverage_note:
            Shown when the server has no tiles for the area in view, or "".
        needs_key:
            True if the server needs the user's own API key.
    """

    key: str
    name: str
    url_template: str
    max_zoom: int
    attribution_html: str
    coverage_note: str = ""
    needs_key: bool = False

    def tile_url(self, zoom: int, x: int, y: int, api_key: str = "") -> str:
        return self.url_template.format(z=zoom, x=x, y=y, key=quote(api_key, safe=""))


# OpenStreetMap's own tile server. Its usage policy asks for an identifying
# User-Agent, honoring cache headers, no bulk downloads, and this credit.
STREET_MAP = TileSource(
    key="street",
    name="Street",
    url_template="https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    max_zoom=19,
    attribution_html=(
        '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    ),
)

# USGS National Map orthoimagery (mostly 1 m NAIP aerial photos). US
# government data with no use constraints; it covers the United States only
# (404 elsewhere) and is detailed down to zoom 16. Note the {y}/{x} order.
SATELLITE_MAP = TileSource(
    key="satellite",
    name="US Satellite",
    url_template=(
        "https://basemap.nationalmap.gov/arcgis/rest/services/"
        "USGSImageryOnly/MapServer/tile/{z}/{y}/{x}"
    ),
    max_zoom=16,
    attribution_html=(
        'Imagery: <a href="https://www.usgs.gov/programs/national-geospatial-program/national-map">'
        "USGS The National Map</a>"
    ),
    coverage_note="Satellite imagery covers the United States only.",
)

# Esri World Imagery (the image tile service for API keys): worldwide and
# detailed to street level. It needs the user's own API key from a free
# ArcGIS Location Platform account (an open-source app can't keep a key of
# its own secret). The Static Basemap Tiles service has no imagery style,
# and this service accepts the key only in the address (?token=), not in
# a header. 256-pixel tiles, {y}/{x} order; detailed past zoom 19.
ESRI_SATELLITE_MAP = TileSource(
    key="esri",
    # The map's satellite button reads just "Satellite" with a key.
    name="Satellite",
    url_template=(
        "https://ibasemaps-api.arcgis.com/arcgis/rest/services/"
        "World_Imagery/MapServer/tile/{z}/{y}/{x}?token={key}"
    ),
    max_zoom=19,
    attribution_html=(
        'Powered by <a href="https://www.esri.com">Esri</a> | Source: Esri, Vantor, '
        "GeoEye, Earthstar Geographics, CNES/Airbus DS, USDA, USGS, AeroGRID, IGN, "
        "and the GIS User Community"
    ),
    needs_key=True,
)

TILE_SOURCES = {
    source.key: source for source in (STREET_MAP, SATELLITE_MAP, ESRI_SATELLITE_MAP)
}

# Corners of the lower 48 United States (northwest, southeast), shown when
# there are no photos with GPS to show.
CONTIGUOUS_US_CORNERS = [(49.38, -124.85), (24.52, -66.95)]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def lat_lon_to_world(latitude: float, longitude: float) -> tuple[float, float]:
    """
    Convert degrees to world coordinates (0..1 across, 0..1 down).
    """
    latitude = clamp(latitude, -MAX_LATITUDE, MAX_LATITUDE)
    x = (longitude + 180.0) / 360.0
    sin_lat = math.sin(math.radians(latitude))
    y = 0.5 - math.log((1 + sin_lat) / (1 - sin_lat)) / (4 * math.pi)
    return clamp(x, 0.0, 1.0), clamp(y, 0.0, 1.0)


def world_to_lat_lon(x: float, y: float) -> tuple[float, float]:
    """
    Convert world coordinates back to latitude and longitude in degrees.
    """
    x = clamp(x, 0.0, 1.0)
    y = clamp(y, 0.0, 1.0)
    longitude = x * 360.0 - 180.0
    latitude = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y))))
    return latitude, longitude


def world_size(zoom: float) -> float:
    """
    Width (and height) of the whole world in pixels at a zoom level. Zoom
    levels in between (like 4.6) are allowed; tiles are then scaled.
    """
    return TILE_SIZE * (2 ** zoom)


def visible_tiles(
    center_x: float,
    center_y: float,
    zoom: int,
    width: int,
    height: int,
) -> list[tuple[int, int]]:
    """
    The tiles (x, y) at this zoom that cover a view of width x height pixels
    centered on (center_x, center_y), nearest the center first so the middle
    of the map fills in first. Tiles outside the world are left out.
    """
    size = TILE_SIZE * (2 ** zoom)
    left = center_x * size - width / 2
    top = center_y * size - height / 2
    tile_count = 2 ** zoom
    first_x = max(0, int(math.floor(left / TILE_SIZE)))
    last_x = min(tile_count - 1, int(math.floor((left + width - 1) / TILE_SIZE)))
    first_y = max(0, int(math.floor(top / TILE_SIZE)))
    last_y = min(tile_count - 1, int(math.floor((top + height - 1) / TILE_SIZE)))

    center_tile_x = center_x * tile_count - 0.5
    center_tile_y = center_y * tile_count - 0.5
    tiles = [
        (tile_x, tile_y)
        for tile_x in range(first_x, last_x + 1)
        for tile_y in range(first_y, last_y + 1)
    ]
    tiles.sort(key=lambda tile: (tile[0] - center_tile_x) ** 2 + (tile[1] - center_tile_y) ** 2)
    return tiles


def zoom_to_fit(
    points: list[tuple[float, float]],
    width: int,
    height: int,
    *,
    padding: float = 0.1,
    min_margin: int = 40,
    max_zoom: float = 16,
) -> tuple[float, float, float]:
    """
    The center (world x, y) and the closest zoom (possibly in between whole
    levels) that shows every point (each a (latitude, longitude) pair) in a
    view of width x height pixels, leaving a margin on every side of
    padding times the view's size (at least min_margin pixels).
    """
    world_points = [lat_lon_to_world(latitude, longitude) for latitude, longitude in points]
    xs = [point[0] for point in world_points]
    ys = [point[1] for point in world_points]
    center_x = (min(xs) + max(xs)) / 2
    center_y = (min(ys) + max(ys)) / 2
    span_x = max(xs) - min(xs)
    span_y = max(ys) - min(ys)
    usable_width = max(1.0, width - 2 * max(min_margin, width * padding))
    usable_height = max(1.0, height - 2 * max(min_margin, height * padding))

    zoom = float(max_zoom)
    if span_x > 0:
        zoom = min(zoom, math.log2(usable_width / (span_x * TILE_SIZE)))
    if span_y > 0:
        zoom = min(zoom, math.log2(usable_height / (span_y * TILE_SIZE)))
    return center_x, center_y, max(float(MIN_ZOOM), zoom)
