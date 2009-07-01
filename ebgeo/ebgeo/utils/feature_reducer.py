from ebgeo.utils.geodjango import iterfeatures, getfield, itergeoms, linemerge
from collections import defaultdict
import ogr

DEBUG = True

class Reducer(object):
    """
    Reduces an OGR datasource by combining the geometries of features
    that are identified by common field values (``key_fields``)
    """
    def __init__(self, key_fields):
        """
        ``key_fields`` is a sequence consisting either or both of strings,
        which are names of the source datasource's fields, or 2-tuples,
        which consist of a field name for the destination datasource and a
        callable which takes a feature and a layer and returns the value
        of the field.
        """
        self.key_fields = key_fields
        # Create a list of destination field names; order is imporant
        # and the list comes in handy for creating the destinations'
        # fields.
        self.key_fieldnames = []
        for fieldname in self.key_fields:
            if isinstance(fieldname, tuple):
                fieldname = fieldname[0]
            self.key_fieldnames.append(fieldname)

    def _add_feature(self, layer, geom, fields):
        feature = ogr.Feature(feature_def=layer.GetLayerDefn())
        feature.SetGeometry(geom)
        for i, field in enumerate(fields):
            feature.SetField(i, field)
        layer.CreateFeature(feature)
        feature.Destroy()

    def reduce(self, src_layer, dst_layer):
        "Reduces a layer's features down to the destination layer"
        src_layer_defn = src_layer.GetLayerDefn()

        # This is the data structure which holds our new,
        # combined features
        reduced = defaultdict(list)

        count = 0
        for feature in iterfeatures(src_layer):
            count += 1
            # "Key fields" are a tuple of the values of the
            # fields of the feature which uniquely identify a
            # reduced-down feature. We start with a list to build
            # it initially from ``self.key_fields``.
            key_fields = []
            try:
                for fieldname in self.key_fields:
                    if isinstance(fieldname, basestring):
                        value = getfield(feature, fieldname)
                    elif isinstance(fieldname, tuple):
                        fieldname, func = fieldname
                        if not callable(func):
                            raise ValueError("2nd member of tuple must be a callable")
                        # Callable must take ``feature`` and ``layer``
                        # as positional args and return a string
                        value = func(feature, src_layer)
                    else:
                        raise ValueError("key_fields item must be the name of a field or a tuple")
                    if value is None:
                        value = ""
                    key_fields.append(value)
            except StopIteration:
                continue
            # Tuple-ize the key_fields so it can be a key in our
            # dictionary
            key_fields = tuple(key_fields)
            reduced[key_fields].append(feature.GetGeometryRef().Clone())
            feature.Destroy()
            if DEBUG and count % 100 == 0:
                print "Processed %s features" % count

        # Calculate width for each field
        widths = []
        reduced_keys = reduced.keys()
        for i in range(len(self.key_fieldnames)):
            widths.append(max([len(k[i]) for k in reduced_keys if k is not None]))

        # Create layer's fields
        for i, key_fieldname in enumerate(self.key_fieldnames):
            dst_fd = ogr.FieldDefn(key_fieldname, ogr.OFTString)
            dst_fd.SetWidth(widths[i])
            dst_layer.CreateField(dst_fd)

        # Create the new features
        for key_fields, geom_list in reduced.items():
            # Sew together adjacent LineStrings
            merged_geom = linemerge(geom_list)
            subgeom_count = merged_geom.GetGeometryCount()
            if DEBUG:
                print "Outputting %r with %s separate lines" % (key_fields[0], subgeom_count and subgeom_count or 1)
            if subgeom_count == 0:
                self._add_feature(dst_layer, merged_geom, key_fields)
            else:
                for geom in itergeoms(merged_geom):
                    self._add_feature(dst_layer, geom, key_fields)
