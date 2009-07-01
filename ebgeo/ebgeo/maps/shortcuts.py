from django.conf import settings
from TileCache.Service import Service
from TileCache.Layer import Tile
from ebgeo.maps.extent import transform_extent, buffer_extent
from ebgeo.maps.tile import get_tile_coords
from ebgeo.maps.mapserver import get_mapserver
from ebgeo.maps.utils import extent_scale
from ebpub.metros.allmetros import get_metro, METRO_DICT
from django.contrib.gis.gdal import SpatialReference

def get_eb_layer(name):
    svc = Service.load(settings.TILECACHE_CONFIG)
    return svc.layers[name]

def render_tile(name, z, x, y, source_srs=None, dest_srs=None, bbox=None,
                scales=None, units=None, extension='png'):
    """
    A shortcut for rendering a map tile using the EveryBlock settings.

    Useful for views and for rendering scripts. Main config options can be
    overriden.
    """
    layer = get_eb_layer(name)
    if source_srs is not None:
        layer.source_srs = source_srs
    if dest_srs is not None:
        layer.dest_srs = dest_srs
    if bbox is not None:
        layer.set_bbox(bbox)
    if scales is not None:
        layer.set_resolutions(scales, units)
    layer.extension = extension
    tile = Tile(layer, x, y, z)
    return layer.renderTile(tile)

def get_citywide_mapserver(maptype, size=(75,75), extension=None):
    map_srs = SpatialReference(settings.SPATIAL_REF_SYS)
    mapserver = get_mapserver(maptype)(map_srs.proj4, width=size[0], height=size[1])
    return mapserver

def render_locator_map(city_slug, size=(75,75), extension='png'):
    map_srs = SpatialReference(settings.SPATIAL_REF_SYS)
    bbox = city_extent_in_map_srs(city_slug)
    mapserver = get_mapserver('locator')(map_srs.proj4, width=size[0], height=size[1])
    mapserver.zoom_to_bbox(*bbox)
    return mapserver(extension)

def get_locator_scale(city_slug, size=(75,75)):
    bbox = transform_extent(get_metro(city_slug)['extent'], settings.SPATIAL_REF_SYS)
    return extent_scale(bbox, size, settings.MAP_UNITS)

def get_all_tile_coords(layer, cities=None, levels=(0, 5)):
    """
    A shortcut for getting all the tile coordinates for a layer.

    Can be optionally constrained by city or a list of cities (slugs).
    """
    if isinstance(layer, basestring):
        layer = get_eb_layer(layer)

    if cities is None:
        cities = METRO_DICT.keys()
    elif isinstance(cities, basestring):
        cities = [cities]

    for slug in cities:
        bboxes = []
        city_ext = transform_extent(get_metro(slug)['extent'], layer.dest_srs)
        for level in xrange(*levels):
            bboxes.append(buffer_extent(city_ext, level, units=settings.MAP_UNITS))
        for tile_coords in get_tile_coords(layer, levels=levels, bboxes=bboxes):
            yield tile_coords

def extent_in_map_srs(extent):
    """
    Returns an extent assumed to be in lng/lat in the target map SRS
    """
    return transform_extent(extent, settings.SPATIAL_REF_SYS)

def city_extent_in_map_srs(city_slug):
    return extent_in_map_srs(get_metro(city_slug)['extent'])

