"""
Scraper for San Jose Restaurant Inspections

http://www.decadeonline.com/results.phtml?agency=scc&offset=0&city=san+jose&sort=FACILITY_NAME
"""

from ebdata.retrieval.scrapers.list_detail import SkipRecord
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
from ebpub.utils.text import smart_title, clean_address
import re

# These inspection types reflect records that aren't actually inspections, so
# we ignore them.
INSPECTION_TYPES_TO_IGNORE = set([
    'BILINGUAL ASSISTANCE',
    'CONSULTATION/MEETING',
    'FOOD SAFETY CLASS',
    'IN-SERVICE TRAINING-TRAINEE',
    'IN-SERVICE TRAINING-TRAINER',
    'PLAN/MAP CHECK',
])

class Scraper(NewsItemListDetailScraper):
    schema_slugs = ['restaurant-inspections']
    parse_list_re = re.compile(r'(?s)<tr class="bodytext"[^>]*?>\s*<td[^>]*?>\s*?<a[^>]*?facid=(?P<facid>.*?)\">(?P<name>.*?)</a>\s*?</td>\s*?<td[^>]*?>(?P<location>.*?)</td>')
    parse_detail_re = re.compile(r'(?s)<td[^>]*>\s*(?P<inspection_date>\d{2}/\d{2}/\d{4})\s*</td>.*?<td[^>]*>\s*<A[^>]*>(?P<inspection_type>.*?)</A><A[^>]*>(?:.*?)</A>\s*</td>\s*</tr>(?P<html>.*?)(?:<tr bgcolor="silver" class="bodytext">|<A[^>]*>Search Again</A>)')
    parse_violations_re = re.compile(r'<strong>(.*?)</strong>')
    sleep = 1
    list_uri = 'http://www.decadeonline.com/results.phtml?agency=scc&offset=%s&city=san+jose&sort=FACILITY_NAME'
    detail_uri = 'http://www.decadeonline.com/fac.phtml?agency=scc&facid=%s'

    def list_pages(self):
        next_page_re = re.compile(r'<a[^>]*>Next Page</a>')
        offset = 0
        while 1:
            html = self.get_html(self.list_uri % offset)
            yield html
            offset += 50
            if next_page_re.search(html) == None:
                break

    def clean_list_record(self, record):
        record['location'] = re.sub(r'\s+', ' ', record['location']).replace(', SAN JOSE ', '').strip()
        return record

    def existing_record(self, list_record):
        # There is no way to determine an existing record from list_record
        return None

    def detail_required(self, list_record, old_record):
        return True

    def get_detail(self, list_record):
        html = self.get_html(self.detail_uri % list_record['facid'])
        return html

    def parse_detail(self, page, list_record):
        detail_record = []
        for m in self.parse_detail_re.finditer(page):
            record = m.groupdict()
            if record['inspection_type'] in INSPECTION_TYPES_TO_IGNORE:
                raise SkipRecord('Got ignorable inspection type %r' % record['inspection_type'])
            html = record.pop('html')
            record['violations'] = []
            for vm in self.parse_violations_re.finditer(html):
                record['violations'].append(vm.group(1))
            detail_record.append(record)
        return detail_record

    def clean_detail_record(self, record):
        for inspection in record:
            inspection['inspection_date'] = parse_date(inspection['inspection_date'], '%m/%d/%Y')
        return record

    def save(self, old_record, list_record, detail_record):
        for record in detail_record:
            # Since parse_detail emits more than one record, we check for existing
            # records here rather than in self.existing_record()
            try:
                qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=record['inspection_date'])
                obj = qs.by_attribute(self.schema_fields['facility_id'], list_record['facid'])[0]
            except IndexError:
                pass
            else:
                return None

            inspection_type_lookup = self.get_or_create_lookup('inspection_type', record['inspection_type'], record['inspection_type'], make_text_slug=False)
            violations_lookups = []
            for violation in record['violations']:
                lookup = self.get_or_create_lookup('violations', violation, violation, make_text_slug=False)
                violations_lookups.append(lookup)
            attributes = {
                'name': list_record['name'],
                'inspection_type': inspection_type_lookup.id,
                'violations': ','.join([str(l.id) for l in violations_lookups]),
                'facility_id': list_record['facid'],
            }
            self.create_newsitem(
                attributes,
                title=smart_title(list_record['name']),
                url=self.detail_uri % list_record['facid'],
                item_date=record['inspection_date'],
                location_name=clean_address(list_record['location'])
            )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    Scraper().update()
