import math
from django.conf import settings

PAIR_SEP = "|"
KEY_VALUE_SEP = ":"

def encode_theme_data(data):
    """
    Encodes a dictionary suitable for passing theme data in a URI to the
    map server.

    Assumes URI encoding will be handled upstream.

    >>> d = {"logan-square": 54, "edgewater": 31, "the-loop": 44}
    >>> s = encode_theme_data(d)
    >>> s == 'the-loop:44|logan-square:54|edgewater:31'
    True
    """
    return PAIR_SEP.join(["%s%s%s" % (k, KEY_VALUE_SEP, v) for k, v in data.items()])

def decode_theme_data(s):
    """
    Decodes a string that's been encoding by encode_theme_data() and
    returns a dictionary.

    Assumes already URI-decoded.

    >>> d = decode_theme_data("the-loop:44|logan-square:54|edgewater:31")
    >>> d == {"logan-square": 54, "edgewater": 31, "the-loop": 44}
    True
    """
    pairs = [s.split(KEY_VALUE_SEP) for s in s.split(PAIR_SEP)]
    return dict([(k, float(v)) for k, v in pairs])

INCHES_PER_UNIT = {
    "inches": 1.0,
    "ft": 12.0,
    "mi": 63360.0,
    "m": 39.3701,
    "km": 39370.1,
    "dd": 4374754
}
INCHES_PER_UNIT["in"] = INCHES_PER_UNIT["inches"]
INCHES_PER_UNIT["degrees"] = INCHES_PER_UNIT["dd"]

DOTS_PER_INCH = 72

def normalize_scale(scale):
    """
    Ensures scale is in the 1/n representation.
    """
    return scale >= 1.0 and (1.0 / scale) or scale

def get_resolution(scale, units="degrees"):
    """
    Returns resolution from given scale and units.
    """
    return 1 / (normalize_scale(scale) * INCHES_PER_UNIT[units] * DOTS_PER_INCH)

def get_scale(resolution, units="degrees"):
    """
    Returns scale from given resolution and units.
    """
    return resolution * INCHES_PER_UNIT[units] * DOTS_PER_INCH

def px_from_lnglat(lnglat, resolution, extent=(-180, -90, 180, 90)):
    return (round(1/resolution * (lnglat[0] - extent[0])),
            round(1/resolution * (extent[3] - lnglat[1])))

def lnglat_from_px(px, resolution, extent=(-180, -90, 180, 90)):
    w = round(1/resolution * extent[2]) - round(1/resolution * extent[0])
    h = round(1/resolution * extent[3]) - round(1/resolution * extent[1])
    return ((px[0] - w / 2) * resolution,
            -(px[1] - h / 2) * resolution)

def km_per_lng_at_lat(lat):
    return 111.321 * math.cos(math.radians(lat))

def km_per_lat():
    return 111.0

def lng_per_km_at_lat(lat):
    return 1 / km_per_lng_at_lat(lat)

def lat_per_km():
    return 1 / km_per_lat()

def extent_resolution(extent, size, units='degrees'):
    width = extent[2] - extent[0]
    height = extent[3] - extent[1]
    return max(width / size[0], height / size[1])

def extent_scale(extent, size, units='degrees'):
    """
    Given an extent, return the scale at which it will fill the given
    size, a 2-tuple: (width, height)
    """
    resolution = extent_resolution(extent, size, units)
    return get_scale(resolution, units)

def get_scale_for_resolution(resolution, units='degrees'):
    resolutions = [get_resolution(s, units) for s in settings.MAP_SCALES]
    for i, res in enumerate(resolutions):
        if res < resolution:
            break
    i = max(0, i-1)
    return settings.MAP_SCALES[i]

def calculate_bounds(center, resolution, size):
    w_units = size[0] * resolution
    h_units = size[1] * resolution
    return (center[0] - w_units / 2,
            center[1] - h_units / 2,
            center[0] + w_units / 2,
            center[1] + h_units / 2)

def center(extent):
    return ((extent[2] - extent[0]) / 2 + extent[0],
            (extent[3] - extent[1]) / 2 + extent[1])

if __name__ == "__main__":
    import doctest
    doctest.testmod()
