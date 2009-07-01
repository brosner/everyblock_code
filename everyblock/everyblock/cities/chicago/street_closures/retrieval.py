"""
Screen scraper for City of Chicago street closures.
http://www.cityofchicago.org/Transportation/TravelAdvisories/streetclosures.html
"""

from django.utils.dateformat import format
from django.utils.text import capfirst
from ebdata.retrieval.scrapers.base import ScraperBroken
from ebdata.retrieval.scrapers.list_detail import SkipRecord
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
import re

SOURCE_URL = 'http://www.cityofchicago.org/Transportation/TravelAdvisories/streetclosures.html'

strip_unneeded_tags = lambda x: re.sub(r'(?si)</?(?:b|font)\b[^>]*>', '', x).replace('&nbsp;', ' ').strip()

class StreetClosure(NewsItemListDetailScraper):
    schema_slugs = ('street-closures',)
    has_detail = False

    def list_pages(self):
        yield self.get_html(SOURCE_URL)

    def parse_list(self, page):
        # First, get the date and time that the page was updated.
        update_re = re.compile(r'(?si)<td height="42" bgcolor="white"><b><font size="3" face="Arial">(?P<update_date>.*?)</font></b></td>\s*</tr>\s*</table>\s*</td>\s*<td width="73" rowspan="2" valign="top">\s*<table border="0" width="71">\s*<tr>\s*<td height="42" bgcolor="white"><b><font size="3" face="Arial">(?P<update_time>.*?)</font></b></td>')
        m = update_re.search(page)
        if not m:
            raise ScraperBroken('Update date not found')
        updated = m.groupdict()

        # Next, get the table that contains the rows we want.
        m = re.search(r'(?si)<table [^>]* width="868">(.*?)</table>', page)
        if not m:
            raise ScraperBroken('Data table not found')
        table = m.group(1)

        # Return each data row in that table *after* the first row (the headers).
        parse_list_re = re.compile(r'(?si)<tr>\s*<td[^>]*>(?P<street_name>.*?)</td>\s*<td[^>]*>(?P<street_dir>.*?)</td>\s*<td[^>]*>(?P<block_from>.*?)</td>\s*<td[^>]*>(?P<block_to>.*?)</td>\s*<td[^>]*>(?P<street_suffix>.*?)</td>\s*<td[^>]*>(?P<start_date>.*?)</td>\s*<td[^>]*>(?P<end_date>.*?)</td>\s*<td[^>]*>(?P<closure_type>.*?)</td>\s*<td[^>]*>(?P<details>.*?)</td>\s*</tr>')
        for match in parse_list_re.finditer(table):
            record = match.groupdict()
            if 'street name' in record['street_name'].lower():
                continue # Skip the header row.
            yield dict(record, **updated)

    def clean_list_record(self, record):
        for k, v in record.items(): record[k] = strip_unneeded_tags(v)
        if not record['street_name']:
            raise SkipRecord('Street name not found')
        record['start_date'] = parse_date(record['start_date'], '%m/%d/%y')
        record['end_date'] = parse_date(record['end_date'], '%m/%d/%y')
        record['date_posted'] = parse_date('%s_%s' % (record.pop('update_date'), record.pop('update_time')), '%m/%d/%Y_%I:%M %p', return_datetime=True)
        record['address'] = '%s-%s %s %s %s' % (record['block_from'], record['block_to'], record['street_dir'], record['street_name'], record['street_suffix'])
        record['details'] = re.sub(r'(?i)<br>', '\n', record['details']).replace('&nbsp;', ' ').strip()
        return record

    def existing_record(self, record):
        try:
            obj = NewsItem.objects.filter(schema__id=self.schema.id,
                item_date=record['start_date']).by_attribute(self.schema_fields['address'], record['address']).by_attribute(self.schema_fields['end_date'], record['end_date'])[0]
        except IndexError:
            return None
        # If the details have changed, treat this as a new record.
        if obj.attributes['details'] != record['details']:
            return None
        return obj

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            # Street closures never change, so we don't have to
            # worry about changing applications that already exist.
            self.logger.debug('Closure already exists')
            return

        closure_type = self.get_or_create_lookup('closure_type', capfirst(list_record['closure_type'].lower()), list_record['closure_type'].upper())

        # Calculate a "friendly" date range to avoid lameness like "from Oct. 3 to Oct. 3".
        if list_record['start_date'] == list_record['end_date']:
            friendly_date_range = 'on %s' % format(list_record['start_date'], 'F j')
        else:
            friendly_date_range = 'from %s to %s' % (format(list_record['start_date'], 'F j'), format(list_record['end_date'], 'F j'))

        attributes = {
            'block_from': list_record['block_from'],
            'block_to': list_record['block_to'],
            'address': list_record['address'],
            'street_dir': list_record['street_dir'],
            'street_name': list_record['street_name'],
            'street_suffix': list_record['street_suffix'],
            'closure_type': closure_type.id,
            'end_date': list_record['end_date'],
            'details': list_record['details'],
            'date_posted': list_record['date_posted'],
        }
        self.create_newsitem(
            attributes,
            title=u'%s %s' % (closure_type.name, friendly_date_range),
            url=SOURCE_URL,
            pub_date=list_record['date_posted'],
            item_date=list_record['start_date'],
            location_name=list_record['address'],
        )

if __name__ == "__main__":
    s = StreetClosure()
    s.update()
