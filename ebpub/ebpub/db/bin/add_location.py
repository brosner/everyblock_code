#!/usr/bin/env python

import sys
from optparse import OptionParser
from django.db import connection
from django.contrib.gis.geos import fromstr
from ebpub.db.bin.alphabetize_locations import alphabetize_locations
from ebpub.db.models import Location, LocationType, NewsItem
from ebpub.geocoder.parser.parsing import normalize
from ebpub.utils.text import slugify
from ebpub.metros.allmetros import get_metro

def swallow_out(f, start_msg=None, end_msg=None):
    """
    Swallows the output of the wrapped function normally going to stdout,
    optionally printing a message before and after the function call.
    """
    def wrapped(*args, **kwargs):
        if start_msg:
            sys.stdout.write(start_msg)
            sys.stdout.flush()
        old_stdout = sys.stdout
        sys.stdout = open('/dev/null', 'w')
        f(*args, **kwargs)
        sys.stdout = old_stdout
        if end_msg:
            sys.stdout.write(end_msg)
            sys.stdout.flush()
    return wrapped

def populate_ni_loc(location):
    ni_count = NewsItem.objects.count()
    cursor = connection.cursor()
    i = 0
    while i < ni_count:
        print i
        cursor.execute("""
            INSERT INTO db_newsitemlocation (news_item_id, location_id)
            SELECT ni.id, loc.id FROM db_newsitem ni, db_location loc
            WHERE intersects(loc.location, ni.location)
                AND ni.id >= %s AND ni.id < %s
                AND loc.id = %s """, (i, i+200, location.id))
        connection._commit()
        i += 200

alphabetize_locations = swallow_out(alphabetize_locations, 'Re-alphabetizing locations ...', ' done.\n')
populate_ni_loc = swallow_out(populate_ni_loc, 'Populating newsitemlocations ...', ' done.\n')

def add_location(name, wkt, loc_type, source='UNKNOWN'):
    geom = fromstr(wkt, srid=4326)
    loc, created = Location.objects.get_or_create(
        name=name,
        slug=slugify(name),
        normalized_name=normalize(name),
        location_type=loc_type,
        location=geom,
        centroid=geom.centroid,
        display_order=0,
        city=get_metro()['city_name'].upper(),
        source=source
    )
    print '%s %s %s' % (created and 'Created' or 'Found', loc_type.name, name)
    return loc

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    usage = 'usage: %prog [options] name wkt'
    p = OptionParser(usage=usage)
    p.add_option('-l', '--location_type', dest='loc_type_slug',
                 default='neighborhoods', help='location type slug')
    p.add_option('-s', '--source', dest='source',
                 default='UNKNOWN', help='source of data')

    opts, args = p.parse_args(argv)

    if len(args) != 2:
        p.error('required arguments `name`, `wkt`')

    try:
        loc_type = LocationType.objects.get(slug=opts.loc_type_slug)
    except LocationType.DoesNotExist:
        p.error('unknown location type slug')

    location = add_location(args[0], args[1], loc_type, opts.source)

    alphabetize_locations(opts.loc_type_slug)
    populate_ni_loc(location)

if __name__ == '__main__':
    sys.exit(main())
