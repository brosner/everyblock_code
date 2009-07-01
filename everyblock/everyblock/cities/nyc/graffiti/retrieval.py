"""
Screen scraper for NYC graffiti location data
https://a002-oom01.nyc.gov/graffiti/

More information is here:
http://www.nyc.gov/html/cau/html/anti_graffiti/main.shtml
"""

from ebdata.retrieval.scrapers.base import ScraperBroken
from ebdata.retrieval.scrapers.list_detail import SkipRecord
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
import re

class GraffitiScraperBase(NewsItemListDetailScraper):
    has_detail = False

    def list_pages(self):
        html = self.get_html(self.source_url)

        m = re.search(r'<input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE" value="([^"]*)"', html)
        if not m:
            raise ScraperBroken('VIEWSTATE not found on %s' % self.source_url)
        viewstate = m.group(1)

        m = re.search(r'<input type="hidden" name="__EVENTVALIDATION" id="__EVENTVALIDATION" value="([^"]*)"', html)
        if not m:
            raise ScraperBroken('EVENTVALIDATION not found on %s' % self.source_url)
        eventvalidation = m.group(1)

        yield self.get_html(self.source_url, {'__VIEWSTATE': viewstate, '__EVENTVALIDATION': eventvalidation, 'cmdFind': 'Find'})

    def parse_list(self, page):
        page = page.replace('&nbsp;', ' ')
        for record in self.parse_list_re.finditer(page):
            yield record.groupdict()

    def clean_list_record(self, record):
        record['waiver_date'] = parse_date(record['waiver_date'], '%m/%d/%y')
        record['address'] = ('%s %s %s' % (record.pop('street_number', '').strip(), record.pop('street_name', '').strip(), record.pop('street_suffix', '').strip())).strip()
        try:
            record['borough'] = {
                'BK': 'Brooklyn',
                'BX': 'The Bronx',
                'MN': 'Manhattan',
                'QS': 'Queens',
                'SI': 'Staten Island',
            }[record['borough']]
        except KeyError:
            raise SkipRecord('Invalid borough')
        return record

class PendingGraffitiScraper(GraffitiScraperBase):
    schema_slugs = ('graffiti-pending-cleanup',)
    parse_list_re = re.compile(r'(?si)<tr[^>]*>\s*<td[^>]*>(?P<street_number>[^<]*)</td><td[^>]*>(?P<street_name>[^<]*)</td><td[^>]*>(?P<street_suffix>[^<]*)</td><td[^>]*>(?P<borough>[^<]*)</td><td[^>]*>(?P<zipcode>[^<]*)</td><td[^>]*>[^<]*</td><td[^>]*>[^<]*</td><td[^>]*>[^<]*</td><td[^>]*>(?P<waiver_date>[^<]*)</td><td[^>]*>Waiver Received</td>\s*</tr>')
    source_url = 'https://a002-oom03.nyc.gov/graffiti/Pending.aspx'

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=record['waiver_date'])
            qs = qs.by_attribute(self.schema_fields['address'], record['address'])
            qs = qs.by_attribute(self.schema_fields['borough'], record['borough'])
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            # Graffiti data never changes, so we don't have to
            # worry about changing data that already exists.
            self.logger.debug('Data already exists')
            return

        attributes = {
            'address': list_record['address'],
            'borough': list_record['borough'],
        }
        self.create_newsitem(
            attributes,
            title='Graffiti reported at %s, %s' % (list_record['address'], list_record['borough']),
            url=self.source_url,
            item_date=list_record['waiver_date'],
            location_name='%s, %s' % (list_record['address'], list_record['borough']),
        )

class CompletedGraffitiScraper(GraffitiScraperBase):
    schema_slugs = ('graffiti-cleaned',)
    parse_list_re = re.compile(r'(?si)<tr[^>]*>\s*<td[^>]*>(?P<street_number>[^<]*)</td><td[^>]*>(?P<street_name>[^<]*)</td><td[^>]*>(?P<street_suffix>[^<]*)</td><td[^>]*>(?P<borough>[^<]*)</td><td[^>]*>(?P<zipcode>[^<]*)</td><td[^>]*>[^<]*</td><td[^>]*>[^<]*</td><td[^>]*>[^<]*</td><td[^>]*>(?P<waiver_date>\d\d/\d\d/\d\d)</td><td[^>]*>(?P<completed_on>\d\d/\d\d/\d\d)</td><td[^>]*>(?P<status>[^<]*)</td>\s*</tr>')
    source_url = 'https://a002-oom03.nyc.gov/graffiti/Completed.aspx'

    def clean_list_record(self, record):
        record = GraffitiScraperBase.clean_list_record(self, record)
        record['completed_on'] = parse_date(record['completed_on'], '%m/%d/%y')
        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=record['completed_on'])
            qs = qs.by_attribute(self.schema_fields['address'], record['address'])
            qs = qs.by_attribute(self.schema_fields['borough'], record['borough'])
            qs = qs.by_attribute(self.schema_fields['waiver_date'], record['waiver_date'])
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        status = self.get_or_create_lookup('status', list_record['status'], list_record['status'], make_text_slug=False)
        attributes = {
            'address': list_record['address'],
            'borough': list_record['borough'],
            'waiver_date': list_record['waiver_date'],
            'status': status.id,
        }
        values = {
            'title': 'Graffiti cleaned up at %s, %s' % (list_record['address'], list_record['borough']),
            'url': self.source_url,
            'item_date': list_record['completed_on'],
            'location_name': '%s, %s' % (list_record['address'], list_record['borough']),
        }

        if old_record is None:
            self.create_newsitem(attributes, **values)
        else:
            self.update_existing(old_record, values, attributes)

def update_newest():
    s = PendingGraffitiScraper()
    s.update()
    s = CompletedGraffitiScraper()
    s.update()

if __name__ == "__main__":
    update_newest()
