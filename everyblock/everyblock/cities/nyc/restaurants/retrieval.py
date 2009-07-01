"""
Screen scraper for NYC restaurant inspections.

Introductory page:
http://www.nyc.gov/html/doh/html/rii/index.shtml

Direct link to search page:
http://167.153.150.32/RI/web/index.do;?method=alphaSearch
"""

from ebdata.retrieval.scrapers.base import ScraperBroken
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebdata.retrieval import UnicodeRetriever
from ebdata.retrieval.utils import convert_entities
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
import md5
import re
from urllib import urlencode

violation_list_re = re.compile(r'<tr><td[^>]*>.*?</td><td[^>]*>(.*?)</td></tr>')
strip_tags = lambda x: re.sub(r'<[^>]*>', ' ', x)
detail_url = lambda restaurant_id, inspection_date: 'http://167.153.150.32/RI/web/detail.do?method=detail&restaurantId=%s&inspectionDate=%s' % (restaurant_id, inspection_date.strftime('%Y%m%d'))

DEFAULT_LETTERS = ['0-9'] + list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')

class RestaurantScraper(NewsItemListDetailScraper):
    schema_slugs = ('restaurant-inspections',)
    parse_list_re = re.compile(r'class="restaurantinfo"><b><a href="detail\.do\?method=detail&restaurantId=(?P<restaurant_id>\d+)&inspectionDate=(?P<inspection_date>\d+)"')
    parse_detail_re = re.compile(r'<tr><td valign="top" width="99%"><b>(?P<restaurant_name>[^>]+)</b><br />(?P<address>[^>]+)<br />(?P<phone>[^>]*)<br /><br /><span style="letter-spacing:-1px;">Violation points: <b>\s*(?P<violation_points>.+?)</b></span></td><td valign="top" width="1%" align="right">.*?</td></tr><tr><td colspan="2"><br />Inspection Date: <b>(?P<inspection_date>[^>]*)</b><br /><br /><b>[^\n]*\n\s*<table border="0" cellspacing="0" cellpadding="3" width="90%" align="left">\s*(?P<violations>.*?)\s*</table>', re.DOTALL)
    sleep = 1

    def __init__(self, letters=None, *args, **kwargs):
        super(RestaurantScraper, self).__init__(*args, **kwargs)
        self.letters = letters or DEFAULT_LETTERS
        self.retriever = UnicodeRetriever()

    def list_pages(self):
        url = 'http://167.153.150.32/RI/web/index.do?'
        params = {
            'method': 'alphaSearch',
            'selection': '',
            'searchValue': '',
            'requestedSortOrder': '1', # 1=alphabetically, 2=by violation points
            'boroughSelect': '',
            'state': 'prompt',
        }
        for letter in self.letters:
            for page in xrange(1, 3000): # We'll never reach 3000, so use it as an upper bound.
                html = self.get_html(url + urlencode(dict(params, alphaValue=letter, pageNum=page)))
                if 'class="restaurantinfo"' not in html:
                    break
                yield html

    def clean_list_record(self, record):
        record['inspection_date'] = parse_date(record['inspection_date'], '%Y%m%d')
        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=record['inspection_date'])
            qs = qs.by_attribute(self.schema_fields['restaurant_id'], record['restaurant_id'])
            return qs[0]
        except IndexError:
            return None

    def detail_required(self, list_record, old_record):
        return True

    def get_detail(self, record):
        url = detail_url(record['restaurant_id'], record['inspection_date'])
        return self.get_html(url)

    def clean_detail_record(self, record):
        if record == {}:
            # Parsing the detail page failed.
            return None
        if record['violation_points'].startswith('Not Available'):
            record['violation_points'] = 'N/A'
            record['followup_inspection'] = False
        else:
            if not record['violation_points'].isdigit():
                raise ScraperBroken('Got odd violation points value %r' % record['violation_points'])
            record['followup_inspection'] = int(record['violation_points']) > 27

        # Parse the violations from the HTML chunk. When we're done,
        # record['violation_list'] will be a (possibly empty) list of strings.
        vio_chunk = record.pop('violations')
        if vio_chunk == '':
            record['violation_list'] = []
        else:
            vios = violation_list_re.findall(vio_chunk)
            if not vios:
                raise ScraperBroken("Violation data not found for restaurant %s", record['restaurant_name'])
            record['violation_list'] = [strip_tags(convert_entities(v.strip())) for v in vios]

        # Remove the ZIP code from the address, as it complicates geocoding.
        record['address'] = re.sub(r'\s*\d{5}\s*$', '', record['address'])
        # Strip extra internal whitespace.
        record['address'] = re.sub(r'\s+', ' ', record['address'])

        return record

    def save(self, old_record, list_record, detail_record):
        # Parsing the detail page failed.
        if detail_record is None:
            return

        # Violation text can be long -- so long that it breaks our 255-character
        # limit on Lookup.code. Thus, use an MD5 hash of the violation as its
        # code.
        md5hash = lambda x: md5.new(x).hexdigest()
        violations = [self.get_or_create_lookup('violation', v, md5hash(v.encode('utf8')), make_text_slug=False) for v in detail_record['violation_list']]
        violations_text = ','.join([str(v.id) for v in violations])
        violation_points = self.get_or_create_lookup('violation_points', detail_record['violation_points'], detail_record['violation_points'])

        title = '%s inspected' % detail_record['restaurant_name']
        if detail_record['violation_points'] == '0':
            title += ': No violation points'
        elif detail_record['violation_points'] != 'N/A':
            title += ': %s violation point%s' % \
                (detail_record['violation_points'], detail_record['violation_points'] != '1' and 's' or '')

        num_violations = len(detail_record['violation_list'])
        values = {
            'title': title,
            'description': '%s violation%s cited.' % (num_violations, num_violations != '1' and 's' or ''),
            'url': detail_url(list_record['restaurant_id'], list_record['inspection_date']),
            'item_date': list_record['inspection_date'],
            'location_name': detail_record['address'],
        }
        attributes = {
            'restaurant_id': list_record['restaurant_id'],
            'restaurant_name': detail_record['restaurant_name'],
            'phone': detail_record['phone'],
            'violation_points': violation_points.id,
            'violation': violations_text,
            'followup_inspection': detail_record['followup_inspection'],
        }
        if old_record is None:
            self.create_newsitem(attributes, **values)
        else:
            self.update_existing(old_record, values, attributes)

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    s = RestaurantScraper()
    s.update()
