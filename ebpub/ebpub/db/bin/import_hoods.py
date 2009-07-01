import os
import sys
import datetime
from optparse import OptionParser
from django.contrib.gis.gdal import DataSource
from django.db import connection
from ebpub.db.models import Location, LocationType, NewsItem
from ebpub.geocoder.parser.parsing import normalize
from ebpub.utils.text import slugify
from ebpub.metros.allmetros import get_metro

def populate_ni_loc(location):
    ni_count = NewsItem.objects.count()
    cursor = connection.cursor()
    i = 0
    while i < ni_count:
        cursor.execute("""
            INSERT INTO db_newsitemlocation (news_item_id, location_id)
            SELECT ni.id, loc.id FROM db_newsitem ni, db_location loc
            WHERE st_intersects(loc.location, ni.location)
                AND ni.id >= %s AND ni.id < %s
                AND loc.id = %s
        """, (i, i+200, location.id))
        connection._commit()
        i += 200

class NeighborhoodImporter(object):
    def __init__(self, layer):
        self.layer = layer
        metro = get_metro()
        self.metro_name = metro['metro_name'].upper()
        self.now = datetime.datetime.now()
        self.location_type, _ = LocationType.objects.get_or_create(
            name = 'neighborhood',
            plural_name = 'neighborhoods',
            scope = self.metro_name,
            slug = 'neighborhoods',
            is_browsable = True,
            is_significant = True,
        )
        unknown, created = Location.objects.get_or_create(
            name = 'Unknown neighborhood',
            normalized_name = 'UNKNOWN',
            slug = 'unknown',
            location_type = self.location_type,
            location = None,
            centroid = None,
            display_order = 0,
            city = self.metro_name,
            source = '',
            area = None,
            is_public = False
        )
        if not created:
            unknown.creation_date = self.now
            unknown.last_mod_date = self.now

    def save(self, name_field='name', source='UNKNOWN', verbose=True):
        hoods = []
        for feature in self.layer:
            name = feature.get(name_field)
            geom = feature.geom.transform(4326, True).geos
            if not geom.valid:
                geom = geom.buffer(0.0)
                if not geom.valid:
                    print >> sys.stderr, 'Warning: invalid geometry: %s' % name
            fields = dict(
                name = name,
                normalized_name = normalize(name),
                slug = slugify(name),
                location_type = self.location_type,
                location = geom,
                centroid = geom.centroid,
                city = self.metro_name,
                source = source,
                area = geom.transform(3395, True).area,
                is_public = True,
                display_order = 0, # This is overwritten in the next loop
            )
            hoods.append(fields)
        num_created = 0
        for i, hood_fields in enumerate(sorted(hoods, key=lambda h: h['name'])):
            kwargs = dict(hood_fields, defaults={'creation_date': self.now, 'last_mod_date': self.now, 'display_order': i})
            hood, created = Location.objects.get_or_create(**kwargs)
            if created:
                num_created += 1
            if verbose:
                print >> sys.stderr, '%s neighborhood %s' % (created and 'Created' or 'Already had', hood)
            if verbose:
                sys.stderr.write('Populating newsitem locations ... ')
            populate_ni_loc(hood)
            if verbose:
                sys.stderr.write('done.\n')
        return num_created

usage = 'usage: %prog [options] /path/to/shapefile'
optparser = OptionParser(usage=usage)

def parse_args(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    optparser.add_option('-n', '--name-field', dest='name_field', default='name', help='field that contains neighborhood\'s name')
    optparser.add_option('-i', '--layer-index', dest='layer_id', default=0, help='index of layer in shapefile')
    optparser.add_option('-s', '--source', dest='source', default='UNKNOWN', help='source metadata of the shapefile')
    optparser.add_option('-v', '--verbose', dest='verbose', action='store_true', default=False, help='be verbose')

    return optparser.parse_args(argv)

def main():
    opts, args = parse_args()
    if len(args) != 1:
        optparser.error('must give path to shapefile')
    shapefile = args[0]
    if not os.path.exists(shapefile):
        optparser.error('file does not exist')
    ds = DataSource(shapefile)
    layer = ds[opts.layer_id]
    importer = NeighborhoodImporter(layer)
    num_created = importer.save(name_field=opts.name_field, source=opts.source, verbose=opts.verbose)
    if opts.verbose:
        print >> sys.stderr, 'Created %s neighborhoods.' % num_created

if __name__ == '__main__':
    sys.exit(main())
