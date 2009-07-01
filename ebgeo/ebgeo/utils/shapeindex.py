"""
Functions for taking advantage of the quad-tree shapefile index produced by
Mapnik's bundled shapeindex utility, allowing for efficient selection of
features based on a given bounding box / extent.
"""

import os.path
import struct
from django.contrib.gis.gdal import Envelope, OGRGeometry

def read_shapeindex(f, extent):
    """
    Reads the binary index as written out by quadtree.hpp in
    mapnik/utils/shapeindex
    """
    # Read the header -- 16 bytes -- just a sanity check
    (name, zeropad) = struct.unpack('6s10s', f.read(16))
    assert name == 'mapnik' and zeropad == '\x00' * 10

    ids = []
    filter_env = OGRGeometry(Envelope(*extent).wkt)
    read_node(f, filter_env, ids)
    ids.sort()
    return ids

def read_node(f, filter_env, ids):
    """
    Follows query_node() in plugins/input/shape/shp_index.hpp
    """
    (offset,) = struct.unpack('i', f.read(4))
    envelope = OGRGeometry(Envelope(*struct.unpack('4d', f.read(32))).wkt)
    (shape_count,) = struct.unpack('i', f.read(4))
    if not envelope.intersects(filter_env):
        f.seek(offset + shape_count * 4 + 4, 1)
        return
    ids.extend(struct.unpack('%di' % shape_count, f.read(4 * shape_count)))
    (num_children,) = struct.unpack('i', f.read(4))
    for i in xrange(num_children):
        read_node(f, filter_env, ids)

def indexed_shapefile(ds, extent):
    shapefile = ds.name
    root, _ = os.path.splitext(shapefile)
    filename = root + '.index'
    ids = read_shapeindex(open(filename), extent)
    f = open(shapefile)
    layer = ds[0]
    for id in ids:
        f.seek(id)
        (record_number,) = struct.unpack('>i', f.read(4))
        yield layer[record_number - 1]
