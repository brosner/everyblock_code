"""
Scraper for Seattle restaurant inspections

http://www.decadeonline.com/main.phtml?agency=skc
"""

from django.core.serializers.json import DjangoJSONEncoder
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
from ebpub.utils.text import smart_title
import re

class Scraper(NewsItemListDetailScraper):
    schema_slugs = ['restaurant-inspections']
    parse_list_re = re.compile(r'(?s)<tr>\s*<td[^>]*?>\s*?<a[^>]*?facid=(?P<facid>.*?)\"><font[^>]*?>\s*(?P<name>.*?)\s*</font>\s*</a>\s*?</td>\s*?<td[^>]*?>\s*<font[^>]*?>\s*(?P<location>.*?)\s*</font>\s*</td>')
    sleep = 1
    list_uri = 'http://www.decadeonline.com/results.phtml?agency=skc&offset=%s&city=seattle&sort=FACILITY_NAME'
    detail_uri = 'http://www.decadeonline.com/fac.phtml?agency=skc&facid=%s'

    # Finds the table that holds all of the inspections and violations.
    table_re = re.compile(r'(?s)(?P<content><table cellspacing="0" border="0" width="560">.*?</table>)')
    # Finds all table rows so we can process them one at a time.
    tr_re = re.compile(r'(?s)<tr[^>]*>(.*?)</tr>')
    # Finds an inspection in a table row.
    inpection_re = re.compile(r'(?s)<font[^>]*>(?P<inspection_type>.+?)</font>.*<font[^>]*>(?P<inspection_date>\d{2}/\d{2}/\d{4})</font>.*<font[^>]*>(?P<points>.+?)</font>')
    # Finds a violation in a table row.
    violation_re = re.compile(r'(?s)<font.+?color=\s*"#(?P<color>[\w\d]{6})"[^>]*>-(?P<violation>.*?)</font>')

    def list_pages(self):
        offset = 0
        html = self.get_html(self.list_uri % offset)
        self.total_records = int(re.search(r'(?s)Results\s+\d+\s+-\s+\d+\s+of\s+(\d+)', html).group(1))
        yield html

        while 1:
            offset += 50
            if offset >= self.total_records:
                break
            yield self.get_html(self.list_uri % offset)

    def clean_list_record(self, record):
        record['location'] = re.sub(r'\s+', ' ', record['location'])
        record['location'] = re.sub(r'(?i),\s*SEATTLE', '', record['location']).strip()
        return record

    def existing_record(self, list_record):
        # Since parse_detail will emit more than one record, check for existing
        # records in the save method.
        return None

    def detail_required(self, list_record, old_record):
        return True

    def get_detail(self, list_record):
        html = self.get_html(self.detail_uri % list_record['facid'])
        return html

    def parse_detail(self, page, list_record):
        inspections = []
        table_match = self.table_re.search(page)
        if table_match is None:
            return []
        for m in self.tr_re.finditer(table_match.group(1)):
            html = m.group(1)
            inspection_match = self.inpection_re.search(html)
            # First try to find an inspection and if that fails, look for a violation
            # and add it to the current inspection.
            if inspection_match is not None:
                inspection = inspection_match.groupdict()
                inspection['violations'] = []
                inspections.append(inspection)
            else:
                violation_match = self.violation_re.search(html)
                if violation_match is None:
                    continue
                inspection['violations'].append(violation_match.groupdict())
        return inspections

    def clean_detail_record(self, records):
        for record in records:
            record['inspection_date'] = parse_date(record['inspection_date'], '%m/%d/%Y')
            for v in record['violations']:
                if v['color'] == 'ff0000':
                    v['severity'] = 'critical'
                else:
                    v['severity'] = 'normal'
                v['violation'] = v['violation'].decode('latin-1')
        return records

    def save(self, old_record, list_record, detail_records):
        for record in detail_records:
            # Since parse_detail emits more than one record, we check for existing
            # records here rather than in self.existing_record()
            try:
                qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=record['inspection_date'])
                obj = qs.by_attribute(self.schema_fields['facility_id'], list_record['facid'])[0]
            except IndexError:
                pass
            else:
                return None
            if record['inspection_type'] == 'Consultation/Education - Field':
                continue
            inspection_type_lookup = self.get_or_create_lookup('inspection_type', record['inspection_type'], record['inspection_type'], make_text_slug=False)
            violations_lookups = []
            for v in record['violations']:
                vl = self.get_or_create_lookup('violations', v['violation'], v['violation'], make_text_slug=False)
                violations_lookups.append(vl)
            attributes = {
                'name': list_record['name'],
                'inspection_type': inspection_type_lookup.id,
                'points': record['points'],
                'violations': ','.join([str(l.id) for l in violations_lookups]),
                'violations_json': DjangoJSONEncoder().encode(record['violations']),
                'facility_id': list_record['facid'],
            }
            self.create_newsitem(
                attributes,
                title=list_record['name'],
                url='http://www.decadeonline.com/fac.phtml?agency=skc&forceresults=1&facid=%s' % list_record['facid'],
                item_date=record['inspection_date'],
                location_name=smart_title(list_record['location'])
            )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    Scraper().update()
