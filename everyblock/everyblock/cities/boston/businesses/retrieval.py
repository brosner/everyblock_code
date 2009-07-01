"""
Scraper for Boston building permits.

http://www.cityofboston.gov/cityclerk/search_reply.asp
"""

from ebdata.retrieval.scrapers.list_detail import SkipRecord
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
from ebpub.utils.text import smart_title
from urllib import urlencode
import datetime
import re

# An opt-out list of businesses to ignore for privacy reasons.
BUSINESS_NAMES_TO_IGNORE = set([
    ('THINK COOL COSMETICS', '176 WASHINGTON ST'),
])

class Scraper(NewsItemListDetailScraper):
    schema_slugs = ['business-licenses']
    has_detail = False
    parse_list_re = re.compile(r'(?s)<div class="mainColTextBlueBold">(?P<name>.*?)</div><br>\s+?<b>Date:</b>(?P<date>.*?)<br>\s+?<b>Type:</b>(?P<business_type>.*?)<br>\s+?<b>Business Address:</b>(?P<location>.*?)<br>\s+?<b>File #:</b>(?P<file_number>.*?)<br>')
    sleep = 1
    uri = 'http://www.cityofboston.gov/cityclerk/search_reply.asp'

    def __init__(self, *args, **kwargs):
        self.start_date = kwargs.pop('start_date', None)
        super(Scraper, self).__init__(*args, **kwargs)

    def find_next_page_url(self, html, current_page_number):
        pattern = r"<a href='(.*?)'>%s</a>" % (current_page_number + 1)
        print pattern
        m = re.search(pattern, html)
        if m is None:
            return None
        return "http://www.cityofboston.gov%s" % m.group(1)

    def list_pages(self):
        if not self.start_date:
            date = datetime.date.today() - datetime.timedelta(days=7)
        else:
            date = self.start_date
        while date <= datetime.date.today():
            page_number = 1
            while 1:
                params = {
                    'whichpage': str(page_number),
                    'pagesize': '10',
                    'name_fold': '',
                    'name_doc': date.strftime('%Y-%m-%d'),
                    'index1': '',
                    'index2': '',
                    'index3': '',
                    'index4': '',
                    'index6': '',
                    'tempday': date.strftime('%d'),
                    'tempmonth': date.strftime('%m'),
                    'tempyear': date.strftime('%Y'),
                }
                html = self.get_html(self.uri + '?' + urlencode(params))
                try:
                    max_pages = int(re.search(r'Page \d+ of (\d+)', html).group(1))
                except AttributeError:
                    break
                yield html
                page_number += 1
                if page_number > max_pages:
                    break
            date = date + datetime.timedelta(days=1)

    def clean_list_record(self, record):
        record['name'] = record['name'].strip()
        record['business_type'] = record['business_type'].strip()
        record['location'] = smart_title(record['location'].strip())
        record['date'] = parse_date(record['date'].strip(), '%Y-%m-%d')
        if (record['name'].upper(), record['location'].upper()) in BUSINESS_NAMES_TO_IGNORE:
            raise SkipRecord('Skipping %s' % record['name'])
        return record

    def existing_record(self, list_record):
        qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=list_record['date'])
        qs = qs.by_attribute(self.schema_fields['name'], list_record['name'])
        try:
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            return
        if list_record['name'].upper() in ['NONE', '']:
            return
        business_type_lookup = self.get_or_create_lookup('business_type', list_record['business_type'], list_record['business_type'], make_text_slug=False)
        attributes = {
            'name': list_record['name'],
            'file_number': list_record['file_number'],
            'business_type': business_type_lookup.id
        }
        self.create_newsitem(
            attributes,
            title=list_record['name'],
            item_date=list_record['date'],
            location_name=list_record['location']
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    start_date = datetime.date(2003, 1, 2)
    Scraper(start_date=start_date).update()
