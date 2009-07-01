"""
Scraper for Philly historical images.

http://www.phillyhistory.org/PhotoArchive/
"""

from django.contrib.gis.geos import Point
from django.utils import simplejson
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from urllib import urlencode, unquote, urlopen
from Cookie import SimpleCookie
import datetime
import re

philly_proj = "+proj=lcc +lat_1=39.93333333333333 +lat_2=40.96666666666667 +lat_0=39.33333333333334 +lon_0=-77.75 +x_0=600000.0000000001 +y_0=0 +ellps=GRS80 +datum=NAD83 +to_meter=0.3048006096012192 +no_defs"

# httplib2, urllib2, and httplib won't work because of a bug in httplib. Or
# rather, because of a bug in IIS that httplib doesn't handle.
# http://bugs.python.org/issue2645

def repair_json(json):
    # For some reason some colons, semicolons, periods, and ampersands are
    # escped with a backslash. Fix that.
    json = json.replace(r'\:', r':')
    json = json.replace(r'\;', r';')
    json = json.replace(r'\.', r'.')
    json = json.replace(r'\&', r'&amp;')
    return json

class HistoricalImagesScraper(NewsItemListDetailScraper):
    list_uri = 'http://www.phillyhistory.org/PhotoArchive/Thumbnails.ashx'
    detail_uri = 'http://www.phillyhistory.org/PhotoArchive/Details.ashx'
    sleep = 1
    schema_slugs = ('historical-images',)

    def __init__(self, *args, **kwargs):
        self.limit = kwargs.pop('limit', 2000)
        super(HistoricalImagesScraper, self).__init__(*args, **kwargs)

    def get_json(self, uri, data):
        if not hasattr(self, 'cookies'):
            self.cookies = SimpleCookie()
        json = urlopen(uri, urlencode(data)).read()
        json = repair_json(json)
        if json == '':
            return None
        return simplejson.loads(json)

    def list_pages(self):
        batch_size = 10
        if self.limit:
            image_limit = self.limit
        else:
            # Start out with something huge. This will be set to the actual
            # number during the first iteration of the loop.
            image_limit = 10000000
        start = 0
        while start + batch_size < image_limit:
            data = self.get_json(self.list_uri, {
                'start': start,
                'limit': batch_size,
                'urlqs': 'type=area&updateDays=30&sortOrder=UpdatedDateDesc&minx=2648000&miny=187000&maxx=2762000&maxy=320000',
                'request': 'Images',
            })
            if data is None:
                continue
            if self.limit is None:
                image_limit = data['totalImages']
            print "Retrieved %s - %s of %s" % (start, start + batch_size, image_limit)
            start += batch_size
            yield data

    def parse_list(self, page):
        return page['images']

    def detail_required(self, list_record, old_record):
        return True

    def get_detail(self, list_record):
        return self.get_json(self.detail_uri, {'assetId': list_record['assetId']})

    def parse_detail(self, page, list_record):
        return page['assets'][0]

    def clean_list_record(self, record):
        # MediaStream.ashx?mediaId=
        record['mediaId'] = str(record['url'][25:])
        record['assetId'] = str(record['assetId'])
        return record

    def clean_detail_record(self, record):
        record['assetId'] = str(record['assetId'])
        record['address'] = unquote(record['address'])
        m = re.search('(\d{4})', record.get('date', ''))
        if m is not None:
            # Turn 1926 into 1920s
            record['decade'] = m.group(1)[:3] + "0s"
        else:
            record['decade'] = 'Unknown'
        return record

    def existing_record(self, record):
        qs = NewsItem.objects.filter(schema__id=self.schema.id)
        qs = qs.by_attribute(self.schema_fields['asset_id'], record['assetId'])
        try:
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        # Skip images that we already have in the database.
        if old_record is not None:
            return
        decade = self.get_or_create_lookup('decade', detail_record['decade'], detail_record['decade'])
        attrs = {
            'media_id': list_record['mediaId'],
            'asset_id': detail_record['assetId'],
            'decade': decade.id,
        }
        x, y = list_record['loc'].split('?')

        self.create_newsitem(
            attrs,
            title=detail_record['title'].strip(),
            item_date=datetime.date.today(),
            location=Point(float(x), float(y), srid=philly_proj),
            location_name=detail_record['address'],
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    HistoricalImagesScraper().update()
