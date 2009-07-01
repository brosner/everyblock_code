from django.conf import settings
from django.contrib.gis.geos import Point
from django.contrib.gis.gdal import OGRGeometry, Envelope
from ebgeo.maps.utils import get_resolution, px_from_lnglat, lnglat_from_px
from ebpub.metros.allmetros import METRO_LIST

def transform_extent(extent, dest_srs, src_srs=4326):
    """
    Transforms an extent -- given as 4-tuple (min x, min y, max x,
    max x) -- to a target SRS.

    The `dest_srs' can be a SRID, WKT, or Proj.4 string. It is passed
    directly to the GEOS `transform()' method.
    """
    # lower-left (min x, min y)
    ll = Point(extent[0], extent[1], srid=src_srs)
    # upper-right (max x, max y)
    ur = Point(extent[2], extent[3], srid=src_srs)

    ll.transform(dest_srs)
    ur.transform(dest_srs)

    return (ll.x, ll.y, ur.x, ur.y)

def city_from_extent(extent):
    city_extents = dict([(m['short_name'], m['extent']) for m in METRO_LIST])

    env = OGRGeometry(Envelope(*extent).wkt)

    matches = []
    for slug, city_ext in city_extents.iteritems():
        city_env = OGRGeometry(Envelope(*city_ext).wkt)
        if city_env.intersects(env):
            matches.append((slug, city_env))

    if len(matches) == 1:
        return matches[0][0]
    elif len(matches) > 1:
        # Crudely select the intersecting city with the most overlap
        # TODO: get rid of this
        current_best_slug, current_max_area = None, float('-inf')
        for slug, city_env in matches:
            intersection = city_env.intersection(env)
            area = intersection.area
            if area > current_max_area:
                current_max_area = area
                current_best_slug = slug
        return current_best_slug

    # If we didn't find a match with a city extent, start expanding the buffer
    # around the city extents until we match one
    for i in xrange(6):
        for slug, city_ext in city_extents.iteritems():
            extent = buffer_extent(city_ext, 1, num_tiles=i+1)
            city_env = OGRGeometry(Envelope(*extent).wkt)
            if env.intersects(city_env):
                return slug

def buffer_extent(extent, zoom_level, num_tiles=6, tile_size=256, units='degrees'):
    """
    Buffers an extent by the size of num_tiles at a particular zoom level.
    """
    scale = settings.MAP_SCALES[zoom_level]
    resolution = get_resolution(scale, units)
    ll_px = px_from_lnglat((extent[0], extent[1]), resolution)
    ur_px = px_from_lnglat((extent[2], extent[3]), resolution)
    pixel_buf = num_tiles * tile_size
    # Note that the (0, 0) point for the lnglat_from_px function is upper-left,
    # so /addition/ of the buffer to the y component moves it in the negative
    # direction, and vice versa
    ll_px = (ll_px[0] - pixel_buf, ll_px[1] + pixel_buf)
    ur_px = (ur_px[0] + pixel_buf, ur_px[1] - pixel_buf)
    return lnglat_from_px(ll_px, resolution) + lnglat_from_px(ur_px, resolution)
