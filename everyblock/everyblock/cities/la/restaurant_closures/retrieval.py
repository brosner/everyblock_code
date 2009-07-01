"""
Scraper for restaurant closures in Los Angeles

http://www.lapublichealth.org/phcommon/public/eh/closure/restall1.cfm
"""

from ebdata.retrieval.scrapers.new_newsitem_list_detail import NewsItemListDetailScraper
from ebdata.retrieval.models import ScrapedPage
from ebpub.db.models import NewsItem
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
    schema_slugs = ['food-closures']
    parse_list_re = re.compile(r'(?s)<tr>\s*<td[^>]*><br>\s*<hr[^>]*>\s*<b>(?P<name>.*?)</b>,\s*(?P<location>.*?), (?P<city>.*?), (?P<also_city>.*?), CA, \d+ <br></td>\s*</tr>\s*<tr>\s*<td[^>]*>\s*<ul[^>]*>\s*(?P<html>.*?)\s*</td>')
    date_closed_re = re.compile(r'<li><b><span[^>]*> Date Closed:</span></b>\s*(\w+ \d{2}, \d{4})')
    date_reopened_re = re.compile(r'<li><b>Date Reopened:</b>\s*(\w+ \d{2}, \d{4})')
    reasons_html_re = re.compile(r'(?s)<li><b>Reason for Closure:</b><br>\s*(.*?)(?:<li>|$)')
    reasons_re = re.compile(r'&nbsp;([^;]*?)<br>')
    sleep = 1
    list_uri = 'http://www.lapublichealth.org/phcommon/public/eh/closure/restall1.cfm'

    def list_pages(self):
        for facility_type in FACILITY_TYPES:
            params = {
                'TYPE': facility_type,
                'addrcity': '',
                'address': '',
                'addrzip': '',
                'dba': '',
                'selsort': 'cl_date',
            }
            yield self.get_page(self.list_uri, params)

    def clean_list_record(self, record):
        return record

    def existing_record(self, list_record):
        # We check for exisitng records in the save method because the list
        # record doesn't contain a date.
        return None

    def detail_required(self, list_record, old_record):
        return old_record is None

    def get_detail(self, list_record):
        return ScrapedPage(html=list_record['html'], when_crawled=datetime.datetime.now())

    def parse_detail(self, page, list_record):
        date_reopened_match = self.date_reopened_re.search(page)
        reasons_html = self.reasons_html_re.search(page).group(1)
        reasons = [m.group(1) for m in self.reasons_re.finditer(reasons_html)]

        detail_record = {
            'date_closed': self.date_closed_re.search(page).group(1),
            'date_reopened': date_reopened_match and date_reopened_match.group(1) or None,
            'reasons': reasons
        }
        return detail_record

    def clean_detail_record(self, record):
        record['date_closed'] = parse_date(record['date_closed'], '%B %d, %Y')
        if record['date_reopened'] is not None:
            record['date_reopened'] = parse_date(record['date_reopened'], '%B %d, %Y')
        return record

    def save(self, old_record, list_record, detail_record, list_page, detail_page):
        qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=detail_record['date_closed'])
        qs = qs.by_attribute(self.schema_fields['name'], list_record['name'])
        try:
            old_record = qs[0]
        except IndexError:
            old_record = None

        city_lookup = self.get_or_create_lookup('city', list_record['city'], list_record['city'], make_text_slug=False)
        reason_lookups = []
        for r in detail_record['reasons']:
            lookup = self.get_or_create_lookup('reasons', r, r, make_text_slug=False)
            reason_lookups.append(lookup)
        attributes = {
            'name': list_record['name'],
            'date_reopened': detail_record['date_reopened'],
            'reasons': ','.join([str(l.id) for l in reason_lookups]),
            'city': city_lookup.id
        }
        values = {
            'title': list_record['name'],
            'item_date': detail_record['date_closed'],
            'location_name': '%s, %s' % (list_record['location'], city_lookup.name)
        }
        if old_record is None:
            self.create_newsitem(attributes, list_page=list_page, **values)
        else:
            self.update_existing(old_record, values, attributes, list_page=list_page)

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    Scraper().update()
