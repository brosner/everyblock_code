"""
Scraper for San Jose crime.

http://public.coronasolutions.com/?page=agency_home&agency=25
"""

from ebdata.retrieval.retrievers import PageNotFoundError
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
import datetime
import re

class PoliceCallsScraper(NewsItemListDetailScraper):
    schema_slugs = ['police-calls']
    has_detail = True
    parse_list_re = re.compile(r'(?s)<h2>(?P<crime_type>.*?)</h2>\s*<table[^>]*>(?P<content>.*?)</table>')
    parse_detail_re = re.compile(r'(?s)<td>(?P<event_number>.*?)</td>\s*<td>(?P<entry_date>.*?)</td>\s*<td>(?P<location>.*?)</td>\s*<td>(?P<disposition>.*?)</td>')
    sleep = 1
    max_bbb_number = 421
    url_template = 'http://public.coronasolutions.com/25/reports/zones/%s/Zone_EventListing.html'

    def list_pages(self):
        missing_pages = 0
        for bbb in range(1, self.max_bbb_number):
            try:
                yield self.get_html(self.url_template % bbb)
            except PageNotFoundError:
                missing_pages += 1
                print "Missing BBB: %s" % bbb
                continue

    def existing_record(self, list_record):
        # We don't know the event_number until we parse the detail record, so
        # we'll check for existing records in the save method.
        return None

    def detail_required(self, list_record, old_record):
        return True

    def get_detail(self, list_record):
        return list_record['content']

    def clean_detail_record(self, record):
        record['location'] = re.sub(r'\s+', ' ', record['location'])
        entry_datetime = parse_date(record['entry_date'], '%Y-%m-%d %H:%M:%S', return_datetime=True)
        record['entry_time'] = entry_datetime.time()
        record['entry_date'] = entry_datetime.date()
        return record

    def save(self, old_record, list_record, detail_record):
        # Check for existing records here since we didn't have enough
        # information to check for them in self.existing_record()
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            old_record = qs.by_attribute(self.schema_fields['event_number'], detail_record['event_number'])[0]
            return
        except IndexError:
            old_record = None
        # Don't import records older than Oct. 21st, 2008. The system *says* that
        # it keeps 90 days worth of data, but the older stuff seems too sparse
        # for that to be true.
        if detail_record['entry_date'] < datetime.date(2008, 10, 21):
            return
        crime_type = self.get_or_create_lookup('crime_type', list_record['crime_type'], list_record['crime_type'], make_text_slug=False)
        disposition = self.get_or_create_lookup('disposition', detail_record['disposition'], detail_record['disposition'], make_text_slug=False)

        attributes = {
            'crime_type': crime_type.id,
            'disposition': disposition.id,
            'event_number': detail_record['event_number'],
            'event_time': detail_record['entry_time'],
        }
        self.create_newsitem(
            attributes,
            title=crime_type.name,
            item_date=detail_record['entry_date'],
            location_name=detail_record['location']
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    PoliceCallsScraper().update()
