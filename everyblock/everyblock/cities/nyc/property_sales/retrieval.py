"""
Screen scraper for NYC property sales.

The data comes in monthly Excel reports from the "Rolling Sales" section of
this page:
http://www.nyc.gov/html/dof/html/property/property_val_sales.shtml
"""

from django.utils.text import capfirst
from ebdata.parsing.excel import ExcelDictReader
from ebdata.retrieval.scrapers.base import ScraperBroken
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.text import intcomma, smart_title
import os
import re
import urlparse

class SalesScraper(NewsItemListDetailScraper):
    schema_slugs = ('property-sales',)
    has_detail = False

    def list_pages(self):
        # Get the HTML page, which includes links to Excel files (one for each
        # borough). We do this instead of hard-coding the Excel file names in
        # the scraper because the Excel file names tend to change each month.
        url = 'http://www.nyc.gov/html/dof/html/property/property_val_sales.shtml'
        html = self.get_html(url)
        excel_links = re.findall(r'href="([^"]+\.xls)"', html)
        if len(excel_links) != 12:
            raise ScraperBroken('Got a strange number of Excel links: %s' % len(excel_links))

        # The first five links are the "New York City Sales Data" links,
        # which is what we want.
        for excel_link in excel_links[:5]:
            excel_url = urlparse.urljoin(url, excel_link)
            workbook_path = self.retriever.get_to_file(excel_url)
            reader = ExcelDictReader(workbook_path, sheet_index=0, header_row_num=4, start_row_num=5)
            yield reader
            os.unlink(workbook_path) # Clean up the temporary file.

    def parse_list(self, reader):
        for row in reader:
            yield row

    def clean_list_record(self, record):
        # Strip extra internal whitespace.
        record['BUILDING CLASS CATEGORY'] = re.sub(r'\s+', ' ', record['BUILDING CLASS CATEGORY'])
        record['category_name'] = capfirst(record['BUILDING CLASS CATEGORY'][3:].lower())
        try:
            record['sale_price'] = str(int(record['SALE PRICE']))
        except ValueError:
            record['sale_price'] = 'N/A'

        try:
            year_built = str(int(record['YEAR BUILT']))
        except ValueError:
            year_built = 'N/A'
        if year_built == '0':
            year_built = 'N/A'
        record['year_built'] = year_built

        try:
            address, unit = record['ADDRESS'].split(', ')
        except ValueError:
            address, unit = record['ADDRESS'], ''
        address = smart_title(address)
        record['clean_address'] = address
        record['clean_address_with_unit'] = '%s%s' % (address, (unit and ', ' + unit or ''))

        record['borough'] = {
            1: 'Manhattan',
            2: 'Bronx',
            3: 'Brooklyn',
            4: 'Queens',
            5: 'Staten Island'
        }[record['BOROUGH']]

        return record

    def existing_record(self, list_record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=list_record['SALE DATE'])
            qs = qs.by_attribute(self.schema_fields['raw_address'], list_record['ADDRESS'])
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            # Records never change, so we don't have to
            # worry about changing ones that already exist.
            self.logger.debug('Permit record already exists: %s' % old_record)
            return

        category = self.get_or_create_lookup('category', list_record['category_name'], list_record['BUILDING CLASS CATEGORY'])
        year_built = self.get_or_create_lookup('year_built', list_record['year_built'], list_record['year_built'])
        building_class = self.get_or_create_lookup('building_class', list_record['BUILDING CLASS AT TIME OF SALE'], list_record['BUILDING CLASS AT TIME OF SALE'])

        if list_record['sale_price'] == '0':
            title = '%s transferred ownership with no cash consideration' % list_record['clean_address_with_unit']
        else:
            title = '%s sold for $%s' % (list_record['clean_address_with_unit'], intcomma(list_record['sale_price']))

        attributes = {
            'clean_address': list_record['clean_address_with_unit'],
            'raw_address': list_record['ADDRESS'], # Save this for use in future scrapes.
            'sale_price': list_record['sale_price'],
            'category': category.id,
            'year_built': year_built.id,
            'building_class': building_class.id,
            'gross_square_feet': list_record['GROSS SQUARE FEET'],
            'total_units': list_record['TOTAL UNITS'],
        }
        self.create_newsitem(
            attributes,
            title=title,
            pub_date=list_record['SALE DATE'],
            item_date=list_record['SALE DATE'],
            location_name='%s, %s' % (list_record['clean_address'], list_record['borough']),
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    SalesScraper().update()
