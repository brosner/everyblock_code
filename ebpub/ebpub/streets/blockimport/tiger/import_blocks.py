#!/usr/bin/env python
import sys
import optparse
from django.contrib.gis.gdal import DataSource
from ebdata.parsing import dbf
from ebpub.streets.blockimport import BlockImporter

STATE_FIPS = {
    '02': ('AK', 'ALASKA'),
    '01': ('AL', 'ALABAMA'),
    '05': ('AR', 'ARKANSAS'),
    '60': ('AS', 'AMERICAN SAMOA'),
    '04': ('AZ', 'ARIZONA'),
    '06': ('CA', 'CALIFORNIA'),
    '08': ('CO', 'COLORADO'),
    '09': ('CT', 'CONNECTICUT'),
    '11': ('DC', 'DISTRICT OF COLUMBIA'),
    '10': ('DE', 'DELAWARE'),
    '12': ('FL', 'FLORIDA'),
    '13': ('GA', 'GEORGIA'),
    '66': ('GU', 'GUAM'),
    '15': ('HI', 'HAWAII'),
    '19': ('IA', 'IOWA'),
    '16': ('ID', 'IDAHO'),
    '17': ('IL', 'ILLINOIS'),
    '18': ('IN', 'INDIANA'),
    '20': ('KS', 'KANSAS'),
    '21': ('KY', 'KENTUCKY'),
    '22': ('LA', 'LOUISIANA'),
    '25': ('MA', 'MASSACHUSETTS'),
    '24': ('MD', 'MARYLAND'),
    '23': ('ME', 'MAINE'),
    '26': ('MI', 'MICHIGAN'),
    '27': ('MN', 'MINNESOTA'),
    '29': ('MO', 'MISSOURI'),
    '28': ('MS', 'MISSISSIPPI'),
    '30': ('MT', 'MONTANA'),
    '37': ('NC', 'NORTH CAROLINA'),
    '38': ('ND', 'NORTH DAKOTA'),
    '31': ('NE', 'NEBRASKA'),
    '33': ('NH', 'NEW HAMPSHIRE'),
    '34': ('NJ', 'NEW JERSEY'),
    '35': ('NM', 'NEW MEXICO'),
    '32': ('NV', 'NEVADA'),
    '36': ('NY', 'NEW YORK'),
    '39': ('OH', 'OHIO'),
    '40': ('OK', 'OKLAHOMA'),
    '41': ('OR', 'OREGON'),
    '42': ('PA', 'PENNSYLVANIA'),
    '72': ('PR', 'PUERTO RICO'),
    '44': ('RI', 'RHODE ISLAND'),
    '45': ('SC', 'SOUTH CAROLINA'),
    '46': ('SD', 'SOUTH DAKOTA'),
    '47': ('TN', 'TENNESSEE'),
    '48': ('TX', 'TEXAS'),
    '49': ('UT', 'UTAH'),
    '51': ('VA', 'VIRGINIA'),
    '78': ('VI', 'VIRGIN ISLANDS'),
    '50': ('VT', 'VERMONT'),
    '53': ('WA', 'WASHINGTON'),
    '55': ('WI', 'WISCONSIN'),
    '54': ('WV', 'WEST VIRGINIA'),
    '56': ('WY', 'WYOMING'),
}

# Only import features with these MTFCC codes - primary road,
# secondary road, and city street
VALID_MTFCC = set(['S1100', 'S1200', 'S1400'])

class TigerImporter(BlockImporter):
    """
    Imports blocks using TIGER/Line data from the US Census.

    Note this importer requires a lot of memory, because it loads the
    necessary .DBF files into memory for various lookups.

    Please refer to Census TIGER/Line shapefile documentation
    regarding the relationships between shapefiles and support DBF
    databases:

    http://www.census.gov/geo/www/tiger/tgrshp2008/rel_file_desc_2008.txt
    """
    def __init__(self, edges_shp, featnames_dbf, faces_dbf, place_shp, filter_city=None):
        self.layer = DataSource(edges_shp)[0]
        self.featnames_db = featnames_db = {}
        for row in self._load_rel_db(featnames_dbf, 'LINEARID').itervalues():
            if row['MTFCC'] not in VALID_MTFCC:
                continue
            tlid = row['TLID']
            featnames_db.setdefault(tlid, [])
            featnames_db[tlid].append(row)
        self.faces_db = self._load_rel_db(faces_dbf, 'TFID')
        # Load places keyed by FIPS code
        places_layer = DataSource(place_shp)[0]
        fields = places_layer.fields
        self.places = places = {}
        for feature in DataSource(place_shp)[0]:
            fips = feature.get('PLACEFP')
            values = dict(zip(fields, map(feature.get, fields)))
            places[fips] = values
        self.filter_city = filter_city and filter_city.upper() or None

    def _load_rel_db(self, dbf_file, rel_key):
        f = open(dbf_file, 'rb')
        db = {}
        try:
            for row in dbf.dict_reader(f, strip_values=True):
                db[row[rel_key]] = row
        finally:
            f.close()
        return db

    def _get_city(self, feature, side):
        fid = feature.get('TFID' + side)
        city = ''
        if fid in self.faces_db:
            face = self.faces_db[fid]
            pid = face['PLACEFP']
            if pid in self.places:
                place = self.places[pid]
                city = place['NAME']
        return city

    def _get_state(self, feature, side):
        fid = feature.get('TFID' + side)
        if fid in self.faces_db:
            face = self.faces_db[fid]
            return STATE_FIPS[face['STATEFP']][0]
        else:
            return ''

    def skip_feature(self, feature):
        if self.filter_city:
            in_city = False
            for side in ('R', 'L'):
                if self._get_city(feature, side).upper() == self.filter_city:
                    in_city = True
            if not in_city:
                return True
        return not feature.get('MTFCC') in VALID_MTFCC or not \
               ((feature.get('RFROMADD') and feature.get('RTOADD')) or \
                (feature.get('LFROMADD') and feature.get('LTOADD')))

    def gen_blocks(self, feature):
        block_fields = {}
        tlid = feature.get('TLID')
        for side in ('right', 'left'):
            for end in ('from', 'to'):
                field_key = '%s_%s_num' % (side, end)
                sl = side[0].upper() # side letter
                try:
                    block_fields[field_key] = int(feature.get('%s%sADD' % (sl, end.upper())))
                except ValueError:
                    block_fields[field_key] = None
        block_fields['right_zip'] = feature.get('ZIPR')
        block_fields['left_zip'] = feature.get('ZIPL')
        for side in ('right', 'left'):
            block_fields[side + '_city'] = self._get_city(feature, side[0].upper()).upper()
            block_fields[side + '_state'] = self._get_state(feature, side[0].upper()).upper()
        if tlid in self.featnames_db:
            for featname in self.featnames_db[tlid]:
                name_fields = {}
                name_fields['street'] = featname['NAME'].upper()
                name_fields['predir'] = featname['PREDIRABRV'].upper()
                name_fields['suffix'] = featname['SUFTYPABRV'].upper()
                name_fields['postdir'] = featname['SUFDIRABRV'].upper()
                block_fields.update(name_fields)
                yield block_fields

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = optparse.OptionParser(usage='%prog edges.shp featnames.dbf faces.dbf place.shp')
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', default=False)
    parser.add_option('-c', '--city', dest='city', help='A city name to filter against')
    (options, args) = parser.parse_args(argv)
    if len(args) != 4:
        return parser.error('must provide 4 arguments, see usage')
    tiger = TigerImporter(*args, filter_city=options.city)
    tiger.save(options.verbose)

if __name__ == '__main__':
    sys.exit(main())
