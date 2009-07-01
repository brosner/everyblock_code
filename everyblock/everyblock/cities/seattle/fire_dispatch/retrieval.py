"""
Screen scraper for Seattle real-time fire 911 calls.

http://www2.seattle.gov/fire/realTime911/getRecsForDatePub.asp?action=Today&incDate=&rad1=des
"""

from ebdata.retrieval import UnicodeRetriever
from ebdata.retrieval.scrapers.list_detail import SkipRecord
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from urllib import urlencode
from time import strptime
import datetime
import re

class SeattleFireDispatchScraper(NewsItemListDetailScraper):
    uri_template = 'http://www2.seattle.gov/fire/realTime911/getRecsForDatePub.asp?%s'
    schema_slugs = ['fire-dispatch']
    has_detail = False
    sleep = 1
    parse_list_re = re.compile(r"(?s)<tr id=row_\d+[^>]*>\s*<td[^>]*>(?P<date>.*?)</td>\s*<td[^>]*>(?P<incident_number>.*?)</td>\s*<td[^>]*>(?P<level>.*?)</td>\s*<td[^>]*>(?P<units>.*?)</td>\s*<td[^>]*>(?P<location>.*?)</td>\s*<td[^>]*>(?P<type>.*?)</td>\s*</tr>")

    def __init__(self, *args, **kwargs):
        self.get_archive = kwargs.pop('get_archive', False)
        super(SeattleFireDispatchScraper, self).__init__(*args, **kwargs)
        self.retriever = UnicodeRetriever()

    def list_pages(self):
        if self.get_archive:
            date = datetime.date(2003, 11, 7)
        else:
            date = datetime.date.today() - datetime.timedelta(days=7)
        while 1:
            if date == datetime.date.today():
                break
            params = urlencode({'incDate': date.strftime('%m/%d/%y'), 'rad1': 'des'})
            yield self.get_html(self.uri_template % params)
            date += datetime.timedelta(days=1)

    def clean_list_record(self, record):
        try:
            dt = strptime(record['date'].strip(), '%m/%d/%Y %I:%M:%S %p')
            record['incident_date'] = datetime.date(*dt[:3])
            record['incident_time'] = datetime.time(*dt[3:6])
        except ValueError:
            dt = strptime(record['date'].strip(), '%m/%d/%Y')
            record['incident_date'] = datetime.date(*dt[:3])
            record['incident_time'] = None
        record['units'] = record['units'].split()
        if 'mutual aid' in record['type'].lower():
            raise SkipRecord('Skipping mutual aid: %r' % record['type'])
        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            return qs.by_attribute(self.schema_fields['incident_number'], record['incident_number'])[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            return
        incident_type = self.get_or_create_lookup('incident_type', list_record['type'], list_record['type'], make_text_slug=False)
        unit_lookups = []
        for unit in list_record['units']:
            unit_lookup = self.get_or_create_lookup('units', unit, unit, make_text_slug=False)
            unit_lookups.append(unit_lookup)
            
        attributes = {
            'incident_date': list_record['incident_date'],
            'incident_time': list_record['incident_time'],
            'incident_number': list_record['incident_number'],
            'incident_type': incident_type.id,
            'units': ','.join([str(u.id) for u in unit_lookups])
        }
        self.create_newsitem(
            attributes,
            title=incident_type.name,
            item_date=list_record['incident_date'],
            location_name=list_record['location']
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    SeattleFireDispatchScraper(get_archive=True).update()
