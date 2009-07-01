from TileCache.Layer import MetaLayer
from ebgeo.maps.mapserver import get_mapserver
from ebgeo.maps.utils import get_resolution
from ebgeo.maps.extent import transform_extent, city_from_extent

class EBLayer(MetaLayer):
    config_properties = [
        {'name': 'scales', 'description': 'Comma-delimited list of scales'},
        {'name': 'source_srs', 'description': 'Source spatial ref system ID (SRID)'},
        {'name': 'dest_srs', 'description': 'Destination, i.e., map\'s, spatial ref system ID (SRID)'},
    ] + MetaLayer.config_properties

    def __init__(self, name, source_srs, dest_srs, scales, **kwargs):
        MetaLayer.__init__(self, name, **kwargs)

        # Type-cast scales (if coming from tilecache config file)
        if isinstance(scales, basestring):
            scales = [float(s) for s in scales.split(',')]

        self.set_resolutions(scales)
        self.source_srs = source_srs
        self.dest_srs = dest_srs
        self.set_bbox(self.bbox)

    def set_resolutions(self, scales, units=None):
        if units is None:
            units = self.units
        self.resolutions = [get_resolution(s, units) for s in scales]

    def set_bbox(self, bbox):
        self.bbox = transform_extent(bbox, self.dest_srs)

    def renderTile(self, tile):
        """
        Overrides MetaLayer's renderTile method

        Returns the raw bytes of the rendered tile.
        """
        # The bbox will be in map projection units, not (necessarily) lat/lng
        tile_bbox = tile.bounds()

        width, height = tile.size()
        mapserver = get_mapserver(self.name)(self.dest_srs, width=width, height=height)
        mapserver.zoom_to_bbox(*tile_bbox)
        mimetype = 'image/%s' % self.extension
        # Calling the mapserver instance gives the raw bytestream
        # of the tile image
        tile.data = mapserver(mimetype)
        return tile.data

def get_tile_coords(layer, levels=(0, 5), bboxes=None):
    """
    A generator that yields tuples of tile grid coordinates.

    Yields a 3-tuple (x, y, z).

    Arguments:

        layer
            A TileCache.Layer (or subclass) instance

        levels
            A 2-tuple of the start and stop zoom levels

        bboxes
            A bounding box or list of bounding boxes to contrain tiles to.

            This should be in units of the target map projection
            (i.e., probably /not/ lat/lng)

            If a list is given, its length must match the number of levels being
            queried (determined by subtracting the stop (2nd element of the
            ``levels`` tuple) from the start (1st element))
    """
    if bboxes is None:
        bboxes = layer.bbox

    if isinstance(bboxes, list):
        if len(bboxes) != (levels[1] - levels[0]) or \
           False in [isinstance(x, tuple) for x in bboxes]:
            raise RuntimeError('list of bboxeses must match number of levels')
    else:
        # To match the semantics below, copy the bboxes for each level
        bboxes = [bboxes for _ in xrange(*levels)]

    for i, z in enumerate(xrange(*levels)):
        bbox = bboxes[i]
        bottomleft = layer.getClosestCell(z, bbox[0:2])
        topright = layer.getClosestCell(z, bbox[2:4])
        metaSize = layer.getMetaSize(z)
        for y in xrange(bottomleft[1], topright[1], metaSize[1]):
            for x in xrange(bottomleft[0], topright[0], metaSize[0]):
                yield (x, y, z)
