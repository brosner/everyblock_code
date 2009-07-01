class InvalidGeometry(Exception):
    pass

def correcting_layer(layer):
    """
    Generator for correcting invalid geometries of the layer's
    features. Yields 2-tuples (feature, geometry), where geometry is
    the corrected geometry. The original feature.geom is left
    preserved.

    Usage is simply to wrap an existing gdal.layer.Layer with this
    function and iterate over features.
    """
    for feature in layer:
        geom = feature.geom
        if not geom.geos.valid:
            # Note that the correction method is to buffer the
            # geometry with distance 0 -- this may not always work, so
            # check the resulting geometry before reassigning the
            # feature's geometry
            new_geom = geom.geos.buffer(0.0)
            if new_geom.valid:
                geom = new_geom.ogr
            else:
                raise InvalidGeometry()
        yield (feature, geom)
