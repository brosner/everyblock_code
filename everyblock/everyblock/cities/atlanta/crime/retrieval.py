"""
Screen scraper for Atlanta crime.
http://www.atlantapd.org/index.asp?nav=CrimeMapping
"""

from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
from django.contrib.gis.geos import Point
from cStringIO import StringIO
import datetime
import zipfile
import sys
import csv
import os

COLUMN_NAMES = [
    'address',
    'incident_number',
    'ucr_number',
    'offense_description',
    'zon',
    'beat',
    'location',
    'report_date',
    'date_from',
    'day_from',
    'time_from',
    'date_to',
    'day_to',
    'time_to',
    'shift',
    'st_number',
    'street_name',
    'type',
    'quad',
    'apt',
    'intersection',
    'weapon',
    'disp',
    'number_vics',
    'x',
    'y',
    'neighborhood',
    'npu',
    'mi_sql_rec_num',
    'mi_sql_x',
    'mi_sql_y',
]

class CrimeScraper(NewsItemListDetailScraper):
    schema_slugs = ('crime',)
    has_detail = False

    def __init__(self, filename=None):
        super(CrimeScraper, self).__init__()
        self.filename = filename

    def list_pages(self):
        year = (datetime.date.today() - datetime.timedelta(days=1)).year
        uri = 'http://www.atlantapd.org/files/CrimeData/PI-%s.zip' % year
        if self.filename is None:
            filename = self.retriever.get_to_file(uri)
            text_filname = 'PI-%s.txt' % year
        else:
            filename = self.filename
            text_filname = self.filename.split('/')[-1][:-4] + '.txt'
        fh = open(filename, 'r')
        zf = zipfile.ZipFile(fh, 'r')
        reader = csv.DictReader(StringIO(zf.read(text_filname)), fieldnames=COLUMN_NAMES)
        yield reader
        fh.close()
        if self.filename is None:
            os.unlink(filename) # Clean up the temporary file.

    def parse_list(self, reader):
        for row in reader:
            yield row

    def clean_list_record(self, record):
        record['address'] = record['address'].strip().replace('&&', 'and')
        record['incident_number'] = record['incident_number'].strip()
        record['offense'] = record['offense_description'].strip()
        record['beat'] = record['beat'].strip()
        record['report_date'] = parse_date(record['report_date'], '%Y-%m-%d %H:%M:%S.000')
        record['x'] = record['x'].strip()
        record['y'] = record['y'].strip()
        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            qs = qs.by_attribute(self.schema_fields['incident_number'], record['incident_number'])
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        if list_record['x'] and list_record['y']:
            crime_location = Point(float(list_record['x']), float(list_record['y']))
            crime_location = self.safe_location(list_record['address'], crime_location, 375)
        else:
            crime_location = None

        offense = self.get_or_create_lookup('offense', list_record['offense'], list_record['offense'])
        beat = self.get_or_create_lookup('beat', list_record['beat'], list_record['beat'])

        kwargs = {
            'title': offense.name,
            'item_date': list_record['report_date'],
            'location_name': list_record['address'],
            'location': crime_location
        }
        attributes = {
            'incident_number': list_record['incident_number'],
            'offense': offense.id,
            'beat': beat.id,
            'xy': '%s;%s' % (list_record['x'], list_record['y'])
        }
        if old_record is None:
            self.create_newsitem(attributes, **kwargs)
        else:
            self.update_existing(old_record, kwargs, attributes)

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    try:
        filename = sys.argv[1]
        CrimeScraper(filename=filename).update()
    except IndexError:
        CrimeScraper().update()
