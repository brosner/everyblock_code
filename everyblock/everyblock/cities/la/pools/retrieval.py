"""
Scraper for Los Angeles pool inspections

http://publichealth.lacounty.gov/phcommon/public/eh/pool/
"""

from ebdata.retrieval.scrapers.new_newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.streets.models import Suburb
from ebpub.utils.dates import parse_date
import re

FACILITY_TYPES = (
    'APARTMENT HOUSE',
    'CONDOMINIUM/TOWNHOUSE',
    'COUNTRY CLUB',
    'FRESH WATER SWIM AREA, PUBLIC',
    'HEALTH CLUB',
    'HOTEL',
    'INSPECTION OF INACTIVE POOL',
    'MEDICAL FACILITY',
    'MOBILE HOME PARK',
    'MOTEL/TRAVEL COURT',
    'MUNICIPAL POOL',
    'ORGANIZATION',
    'OTHER',
    'POOL AT FOUR UNIT DWELLING',
    'PRIVATE HOMES COMMUNITY',
    'PRIVATE SCHOOL',
    'PUBLIC SCHOOL',
    'RESORT/CAMP',
    'SWIM SCHOOL',
    'WATER THEME PARK'
)

class Scraper(NewsItemListDetailScraper):
    schema_slugs = ['pool-inspections']

    parse_list_re = re.compile(r'(?s)<tr>\s*<td[^>]*>(?P<name>[\w\s\']*?)<br></td>\s*<td[^>]*>\s*(?P<location>.*?)<br>\s*</td>\s*<td[^>]*>(?P<city>.*?)<br></td>\s*<td[^>]*>(?P<zip>\d*?)<br></td>\s*<td[^>]*>(?P<date>\d{2}/\d{2}/\d{4})<br></td>\s*<td[^>]*>(?P<facility_type>.*?)<br></td>\s*<td[^>]*>(?P<pool_type>.*?)</td>\s*<td[^>]*>\s*<form[^>]*>\s*<input[^>]*>\s*<input type="hidden" name="dsiteid" value="(?P<dsiteid>\d+)">')
    parse_detail_re = re.compile(r'(?s)<tr>\s*<td[^>]*>\s*Inspection Date:</td>\s*<td[^>]*>\s*(?P<date>\d{2}/\d{2}/\d{4})</td>\s*(?P<html>.*?)<tr>\s*<td colspan="3"><hr class="contLine"></td>\s*</tr>')
    parse_violations_re = re.compile(r'<tr>\s*<td[^>]*>\s*(?:Violations:|\s*)</td>\s*<td[^>]*>\s*(?P<code>\d+)\s*</td>\s*<td[^>]*>\s*<a[^>]*>\s*(?P<violation>.*?)</a>')

    sleep = 0
    list_uri = 'http://publichealth.lacounty.gov/phcommon/public/eh/pool/poolsearchaction.cfm'
    detail_uri = 'http://publichealth.lacounty.gov/phcommon/public/eh/pool/pooldetail.cfm'

    def __init__(self, *args, **kwargs):
        self.get_archive = kwargs.pop('get_archive', False)
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
                    'sort': 'inspdt',
                    'type': facility_type,
                    'zipcode': '',
                    'start': row + 1,
                    'row': row
                }
                page = self.get_page(self.list_uri, params)
                total = re.search(r'<span[^>]*>(\d+) record\(s\) match your search criteria.</span>', page.html).group(1)
                yield page
                row += 100
                if row > int(total) or (not self.get_archive):
                    break

    def clean_list_record(self, record):
        record['date'] = parse_date(record['date'], '%m/%d/%Y')
        return record

    def existing_record(self, list_record):
        # Each list record can result in multiple detail records. The save
        # method should handle existing records instead.
        return None

    def detail_required(self, list_record, old_record):
        return old_record is None

    def get_detail(self, list_record):
        params = {
            'address': '',
            'alphalist': '',
            'checkbox': 'no',
            'city': '',
            'dba': '',
            'dsiteid': list_record['dsiteid'],
            'pooltypdsc': '',
            'sort': 'inspdt',
            'start': '1',
            'type': '',
            'zipcode': '',
        }
        return self.get_page(self.detail_uri, params)

    def parse_detail(self, page, list_record):
        detail_record = {'inspections': []}
        for m in self.parse_detail_re.finditer(page):
            inspection = {
                'date': m.groupdict()['date'],
                'violations': []
            }
            for vm in self.parse_violations_re.finditer(m.groupdict()['html']):
                inspection['violations'].append(vm.groupdict())
            detail_record['inspections'].append(inspection)
        return detail_record

    def clean_detail_record(self, record):
        for inspection in record['inspections']:
            inspection['date'] = parse_date(inspection['date'], '%m/%d/%Y')
        return record

    def save(self, old_record, list_record, detail_record, list_page, detail_page):
        facility_type_lookup = self.get_or_create_lookup('facility_type', list_record['facility_type'], list_record['facility_type'], make_text_slug=False)
        pool_type_lookup = self.get_or_create_lookup('pool_type', list_record['pool_type'], list_record['pool_type'], make_text_slug=False)
        city_lookup = self.get_or_create_lookup('city', list_record['city'], list_record['city'], make_text_slug=False)

        # Store the existing inspection dates in a set so we can quickly
        # determine whether or not we need to save the current one.
        qs = NewsItem.objects.filter(schema__id=self.schema.id)
        qs = qs.by_attribute(self.schema_fields['dsiteid'], list_record['dsiteid'])
        existing_inspection_dates = set([d['item_date'] for d in qs.values('item_date')])

        for inspection in detail_record['inspections']:
            if inspection['date'] in existing_inspection_dates:
                continue

            violation_lookups = []
            for v in inspection['violations']:
                lookup = self.get_or_create_lookup('violations', v['violation'], v['code'], make_text_slug=False)
                violation_lookups.append(lookup)

            violation_count = len(violation_lookups)
            name = list_record['name'] or list_record['location']
            if violation_count == 0:
                violation_string = 'No violations'
            elif violation_count == 1:
                violation_string = '1 violation'
            elif violation_count > 1:
                violation_string = '%s violations' % violation_count
            title = "Pool at %s inspected: %s" % (name, violation_string)
            attributes = {
                'name': name,
                'facility_type': facility_type_lookup.id,
                'pool_type': pool_type_lookup.id,
                'violations': ','.join([str(l.id) for l in violation_lookups]),
                'dsiteid': list_record['dsiteid'],
                'city': city_lookup.id
            }
            values = {
                'list_page': list_page,
                'detail_page': detail_page,
                'title': title,
                'item_date': inspection['date'],
                'location_name': '%s, %s' % (list_record['location'], city_lookup.name),
            }
            # Don't try to geocode items in the suburbs table
            if city_lookup.name.upper() in self.suburbs:
                values['location'] = None
            self.create_newsitem(attributes, **values)

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    Scraper(get_archive=True).update()
