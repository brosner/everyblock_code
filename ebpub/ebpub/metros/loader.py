from django.contrib.gis.gdal import DataSource
from django.contrib.gis.geos import MultiPolygon
from ebpub.metros.allmetros import METRO_DICT
from ebpub.metros.models import Metro

class Usage(Exception):
    pass

def load_metro(short_name, shpfile, layer_id=0):
    """
    Creates a new Metro object, populating geometry from shapefile and
    the rest of its fields from the old settings module.
    """
    ds = DataSource(shpfile)
    lyr = ds[layer_id]
    model_fields = set([f.name for f in Metro._meta.fields])
    metro_from_settings = METRO_DICT[short_name]
    settings_fields = set(metro_from_settings.keys())
    metro = Metro()
    for f in (model_fields & settings_fields):
        setattr(metro, f, metro_from_settings[f])
    metro.name = metro_from_settings['city_name']
    metro_geom = None
    for feature in lyr:
        if metro_geom is None:
            geom = feature.geom.geos
            geom_type = geom.geom_type
            if geom_type == 'Polygon':
                # Normalize to MultiPolygon
                metro_geom = MultiPolygon([geom])
            elif geom_type == 'MultiPolygon':
                metro_geom = geom
            else:
                raise ValueError('expected Polygon or MultiPolygon, got %s' % geom_type)
    metro.location = metro_geom
    metro.save()
    return metro

def main():
    import getopt
    import sys

    (opts, args) = getopt.getopt(sys.argv[1:], 'h', ['help'])
    try:
        for opt, value in opts:
            if opt in ('-h', '--help'):
                raise Usage()
        if len(args) != 2:
            raise Usage()
        try:
            metro = load_metro(args[0], args[1])
        except ValueError, e:
            print >> sys.stderr, e
            return 1
        else:
            print 'Created %s' % metro
            return 0
    except Usage:
        print >> sys.stderr, '%s: <short_name> /path/to/shapefile' % sys.argv[0]
        return 1

if __name__ == '__main__':
    import sys
    sys.exit(main())
