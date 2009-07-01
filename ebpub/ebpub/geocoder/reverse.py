import unittest
from psycopg2 import Binary
from django.contrib.gis.geos import Point
from django.db import connection
from ebpub.streets.models import Block

class ReverseGeocodeError(Exception):
    pass

def reverse_geocode(point):
    """
    Looks up the nearest block to the point.
    """
    # In degrees for now because transforming to a projected space is
    # too slow for this purpose. TODO: store projected versions of the
    # locations alongside the canonical lng/lat versions.
    min_distance = 0.007
    # We use min_distance to cut down on the searchable space, because
    # the distance query we do next that actually compares distances
    # between geometries does not use the spatial index. TODO: convert
    # this to GeoDjango syntax. Should be possible but there are some
    # subtleties / performance issues with the DB API.
    cursor = connection.cursor()
    cursor.execute("""
        SELECT %(field_list)s, ST_Distance(ST_GeomFromWKB(E%(pt_wkb)s, 4326), %(geom_fieldname)s) AS "dist"
        FROM %(tablename)s
        WHERE id IN
            (SELECT id
             FROM %(tablename)s
             WHERE ST_DWithin(%(geom_fieldname)s, ST_GeomFromWKB(E%(pt_wkb)s, 4326), %(min_distance)s))
        ORDER BY "dist"
        LIMIT 1;
    """ % {'field_list': ', '.join([f.column for f in Block._meta.fields]),
           'pt_wkb': Binary(point.wkb),
           'geom_fieldname': 'location',
           'tablename': Block._meta.db_table,
           'min_distance': min_distance})
    num_fields = len(Block._meta.fields)
    try:
        block, distance = [(Block(*row[:num_fields]), row[-1]) for row in cursor.fetchall()][0]
    except IndexError:
        raise ReverseGeocodeError()
    return block, distance
