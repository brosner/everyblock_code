"""
Scraper for Los Angeles restaurant inspections

http://www.lapublichealth.org/rating/
"""

from ebdata.retrieval.scrapers.new_newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.streets.models import Suburb
from ebpub.utils.dates import parse_date
import datetime
import re

FACILITY_TYPES = (
    'Caterer',
    'Food Warehouse',
    'Restaurant',
    'Retail Food Market',
    'Retail Food Processor',
    'Wholesale Food Market',
)

class Scraper(NewsItemListDetailScraper):
    schema_slugs = ['food-inspections']
    parse_list_re = re.compile(r'(?s)<tr>\s*<td[^>]*>(?P<name>[\w\s\']*?)<br></td>\s*<td[^>]*>\s*(?P<location>.*?)<br>\s*</td>\s*<td[^>]*>(?P<city>.*?)<br></td>\s*<td[^>]*>(?P<zip>\d*?)<br></td>\s*<td[^>]*>(?P<date>\d{2}/\d{2}/\d{4})<br></td>\s*<td[^>]*>(?P<score>.*?)<br></td>\s*<td[^>]*>(?P<facility_type>.*?)<br></td>\s*<td[^>]*>\s*<form[^>]*>.*?<input type="hidden" name="dsiteid" value="(?P<dsiteid>.*?)">.*?</td>')
    parse_detail_re = re.compile(r'<tr>\s*<td[^>]*>\s*(?:Violations:|\s*)</td>\s*<td[^>]*>\s*<span[^>]*>\s*(?P<code>\d+)</span>\s*</td>\s*<td[^>]*>\s*<a[^>]*>\s*<span[^>]*>\s*(?P<violation>.*?)</span></a>')
    sleep = 1
    list_uri = 'http://www.lapublichealth.org/phcommon/public/eh/rating/ratesearchaction.cfm'
    detail_uri = 'http://www.lapublichealth.org/phcommon/public/eh/rating/ratedetail.cfm'

    def __init__(self, *args, **kwargs):
        self.get_archive = kwargs.pop('get_archive', False)
        self.perform_updates = kwargs.pop('perform_updates', False) # should we update existing records?
        self.suburbs = set([d['normalized_name'].upper() for d in Suburb.objects.values('normalized_name')])
        super(Scraper, self).__init__(*args, **kwargs)

    def list_pages(self):
        for facility_type in FACILITY_TYPES:
            row = 0
            while 1:
                params = {
                    'B1': 'Submit',
                    'address': '',
                    'city': '',
                    'dba': '',
                    'score': '',
                    'sort': 'inspdt',
                    'type': facility_type,
                    'zipcode': '',
                    'start': row + 1,
                    'row': row
                }
                page = self.get_page(self.list_uri, params)
                total = re.search(r'<b>(\d+) record\(s\) match your search criteria.<br></b>', page.html).group(1)
                yield page
                row += 100
                if row > int(total) or (not self.get_archive):
                    break

    def clean_list_record(self, record):
        record['date'] = parse_date(record['date'], '%m/%d/%Y')
        if record['score'] == 'NA':
            record['score'] = 'N/A'
        return record

    def existing_record(self, list_record):
        qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=list_record['date'])
        qs = qs.by_attribute(self.schema_fields['name'], list_record['name'])
        try:
            return qs[0]
        except IndexError:
            return None

    def detail_required(self, list_record, old_record):
        return self.perform_updates or old_record is None

    def get_detail(self, list_record):
        params = {
            'address': '',
            'alphalist': '',
            'checkbox': 'no',
            'city': list_record['city'],
            'dba': '',
            'dsiteid': list_record['dsiteid'],
            'score': '',
            'sort': 'inspdt',
            'start': '1',
            'type': '',
            'zipcode': '',
        }
        return self.get_page(self.detail_uri, params)

    def parse_detail(self, page, list_record):
        detail_record = {'violations': []}
        for m in self.parse_detail_re.finditer(page):
            detail_record['violations'].append(m.groupdict())
        return detail_record

    def clean_detail_record(self, record):
        return record

    def save(self, old_record, list_record, detail_record, list_page, detail_page):
        if list_record['date'] < datetime.date(2007, 7, 1):
            return
        if detail_record is None:
	    return
        facility_type_lookup = self.get_or_create_lookup('facility_type', list_record['facility_type'], list_record['facility_type'], make_text_slug=False)
        city_lookup = self.get_or_create_lookup('city', list_record['city'], list_record['city'], make_text_slug=False)

        violation_lookups = []
        for v in detail_record['violations']:
            lookup = self.get_or_create_lookup('violations', v['violation'], v['code'], make_text_slug=False)
            violation_lookups.append(lookup)
        attributes = {
            'name': list_record['name'],
            'facility_type': facility_type_lookup.id,
            'score': list_record['score'],
            'violations': ','.join([str(l.id) for l in violation_lookups]),
            'dsiteid': list_record['dsiteid'],
            'city': city_lookup.id
        }
        location_name = u'%s, %s' % (list_record['location'].decode('latin-1'), city_lookup.name)
        values = {
            'title': list_record['name'],
            'item_date': list_record['date'],
            'location_name': location_name,
        }
        # Don't try to geocode items in the suburbs table
        if city_lookup.name.upper() in self.suburbs:
            values['location'] = None
        if old_record is None:
            self.create_newsitem(attributes, list_page=list_page, detail_page=detail_page, **values)
        elif self.perform_updates:
            self.update_existing(old_record, values, attributes, list_page=list_page, detail_page=detail_page)

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    Scraper(get_archive=True, perform_updates=True).update()
