"""
Utility functions for working with GeoDjango GDAL and GEOS data
"""

from django.contrib.gis import geos
from django.contrib.gis.geos import Point, LineString, Polygon, GeometryCollection, MultiPoint, MultiLineString, MultiPolygon

def reduce_layer_geom(layer, method):
    """
    Iterates over all the geometries in an GDAL layer and successively
    applies given `method' to the geometries.
    """
    def reduction(x, y):
        return getattr(x, method)(y)
    
    return reduce(reduction, [feat.geom for feat in layer])

# TODO: remove this once line_merge is added to django.contrib.gis.geos
from django.contrib.gis.geos.libgeos import lgeos
from django.contrib.gis.geos.prototypes.topology import topology
geos_linemerge = topology(lgeos.GEOSLineMerge)
def line_merge(geom):
    return geom._topology(geos_linemerge(geom.ptr))

def flatten(geos_geom):
    """
    Flattens a GEOS geometry and returns a list of the component geometries.
    """
    def _flatten(geom, acc):
        if isinstance(geom, (Point, LineString, Polygon)):
            acc.append(geom)
            return acc
        elif isinstance(geom, (GeometryCollection, MultiPoint, MultiLineString, MultiPolygon)):
            subgeom_list = list(geom)
            if subgeom_list:
                acc.append(subgeom_list.pop(0))
                for subgeom in subgeom_list:
                    _flatten(subgeom, acc)
            return acc
        else:
            raise TypeError, 'not a recognized GEOSGeometry type'
    flattened = []
    _flatten(geos_geom, flattened)
    return flattened

def make_geomcoll(geom_list):
    """
    From a list of geometries, return a single GeometryCollection (or
    subclass) geometry.

    This flattens multi-point/linestring/polygon geometries in the
    list.
    """
    flattened = []

    for geom in geom_list:
        flattened.extend(flatten(geom))

    return GeometryCollection(flattened)

def make_multi(geom_list, collapse_single=False):
    if len(geom_list) == 1 and collapse_single:
        return geom_list[0]

    geom_types = set(g.geom_type for g in geom_list)

    if len(geom_types) > 1:
        raise ValueError, 'all geometries must be of the same geom_type'

    geom_type = geom_types.pop()

    valid_geom_types = ('Point', 'LineString', 'Polygon')

    if geom_type not in valid_geom_types:
        raise ValueError, 'geometries must be of type %s' % ', '.join(valid_geom_types)

    cls = getattr(geos, 'Multi%s' % geom_type)
    return cls(geom_list)

def smart_transform(geom, srid, clone=True):
    """
    Returns a new geometry transformed to the srid given. Assumes if
    the initial geom is lacking an SRS that it is EPSG 4326. (Hence the
    "smartness" of this function.) This fixes many silent bugs when
    transforming between SRSes when the geometry is missing this info.
    """
    if not geom.srs:
        geom.srid = 4326
    return geom.transform(srid, clone=clone)
