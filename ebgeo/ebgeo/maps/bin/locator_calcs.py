#!/usr/bin/env python
import sys
from django.conf import settings
from ebgeo.maps.shortcuts import city_extent_in_map_srs
from ebgeo.maps.utils import extent_scale, center, extent_resolution, calculate_bounds
from ebgeo.maps.extent import transform_extent

LOCATOR_SIZE = (75, 75)

def get_citywide_bounds_for_size(city_slug, size=LOCATOR_SIZE):
    """
    Returns a 4-tuple extent in degrees decimal longitude and latitude
    the extent of a rectangle in (size[0], size[1]) pixels that is
    filled by the city.

    This is useful in generating locator map bounds because the extent
    of the city doesn't typically match the aspect ratio of the image.
    """
    extent = city_extent_in_map_srs(city_slug)
    resolution = extent_resolution(extent, size, settings.MAP_UNITS)
    new_extent = calculate_bounds(center(extent), resolution, size)
    # Convert back to lng/lat
    return transform_extent(new_extent, 4326, src_srs=900913)

def get_bounds_for_openlayers(city_slug, size=LOCATOR_SIZE):
    extent = get_citywide_bounds_for_size(city_slug, size)
    return 'new OpenLayers.Bounds(%.5f, %.5f, %.5f, %.5f)' % extent

def calc_locator_scale(city_slug):
    return extent_scale(city_extent_in_map_srs(city_slug),
                        size=LOCATOR_SIZE,
                        units=settings.MAP_UNITS)

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    if len(argv) < 2:
        print >> sys.stderr, 'Usage: %s {bounds|scale} city_slug [city_slug ...]' % sys.argv[0]
        return 1

    actions = {
        'bounds': get_bounds_for_openlayers,
        'scale': calc_locator_scale
    }

    for slug in argv[1:]:
        print slug, actions[argv[0]](slug)

if __name__ == '__main__':
    sys.exit(main())
