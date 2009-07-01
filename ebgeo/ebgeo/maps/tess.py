from __future__ import division
import math
import os.path
from django.conf import settings
from django.contrib.gis.geos import Point
from django.contrib.gis.gdal import DataSource
from ebgeo.maps.extent import transform_extent
from ebgeo.utils.geodjango import reduce_layer_geom
from ebpub.metros.allmetros import get_metro

def tessellate(extent, radius):
    """
    Computes a tessellation of a given extent, with each tile covering
    a area inscribed by a circle with radius given. Returns an
    iterator which yields the center (x, y) coordinate.

    The algorithm covers the extent with squares with edges of size
    `radius`, then horizontally shifts every other row. The squares
    then have their top and bottom edges resized and shifted so the
    polygon becomes a regular hexagon.
    """
    # Hexagon math characteristics -- note that we use a vertically
    # oriented hexagon (standing on a vertex instead of an edge).
    height = 2 * radius
    width = math.sqrt(3) * radius
    h = math.sin(math.radians(30)) * radius # `h` is the sin(30) height
    r = width / 2 # `r` is the cos(30) width
    y_offset = -h

    extent_h = abs(extent[3] - extent[1])
    extent_w = abs(extent[2] - extent[0])

    # figure out number of rows
    n_rows = int(math.ceil(extent_h / height))

    # add rows to cover the gap created by the offset
    while (n_rows * (h + radius)) + y_offset < extent_h:
        n_rows += 1

    for row in xrange(n_rows):
        n_cols = int(math.ceil(extent_w / width))
        # if odd, offset x
        if row % 2 != 0:
            x_offset = -(width / 2)
            # add a col to cover the gap created by the offset
            if (n_cols * width) + x_offset < extent_w:
                n_cols += 1
        else:
            x_offset = 0
        for col in xrange(n_cols):
            # figure the centroid (x, y) of the hexagon
            x = ((col + 0.5) * width) + x_offset + extent[0]
            y = (row * (h + radius)) + (height / 2) + y_offset + extent[1]
            yield (x, y)

def cover_region(extent, radius):
    """
    Returns an iterator that covers a given region with circle buffer of given
    radius. `extent` should be given in terms of lat/lng, and `radius` should be
    in kilometers.

    The iterator yields (lng, lat) tuples -- the centroid of the buffer.
    """
    target_srs = 900913 # Spherical Mercator

    # Convert radius from km to meters
    radius_m = radius * 1000

    # Convert extent from lat/lng to a projected extent
    proj_ext = transform_extent(extent, target_srs)

    for (x, y) in tessellate(proj_ext, radius_m):
        pt = Point(x, y, srid=target_srs)
        pt.transform(4326)
        yield (pt.x, pt.y)

def cover_city(city_slug, radius):
    """
    An iterator that yields a centroid (lng, lat) for a circle buffer with
    radius given. The total buffers completely cover the city and no buffers
    that do not intersect with the city boundary are included.

    Radius is in kilometers.
    """
    def shapefile_path(city):
        return os.path.normpath(os.path.join(settings.SHAPEFILE_ROOT, city, 'city_4326'))

    ds = DataSource(shapefile_path(city_slug) + '.shp')
    city_geom = reduce_layer_geom(ds[0], 'union')
    city_geom.srid = 4326
    city_geom.transform(900913)

    for (x, y) in cover_region(get_metro(city_slug)['extent'], radius):
        pt = Point(x, y, srid=4326)
        pt.transform(900913)
        buf = pt.buffer(radius)
        if buf.intersects(city_geom.geos):
            yield (x, y)

def test_draw():
    import pylab
    from matplotlib.patches import RegularPolygon, Rectangle

    extent = (0, 0, 10, 10)
    radius = 1
    
    fig = pylab.figure()
    ax = fig.add_subplot(111)
    ax.add_artist(Rectangle((extent[0], extent[1]), extent[2] - extent[0],
                            extent[3] - extent[1]))

    for (x, y) in tessellate(extent, radius):
        ax.add_artist(RegularPolygon((x, y), 6, radius=radius,
                                     orientation=math.pi/2, alpha=0.5, facecolor='r'))

    pylab.show()

def test():
    print len(list(cover_region(get_metro('la')['extent'], 1.609)))

def test_cover_city():
    print len(list(cover_city('la', 1.609)))

if __name__ == '__main__':
    #test()
    test_cover_city()
