"""
Import script for Chicago property transfers.

This data is imported from an Excel file, which is e-mailed to us every two
weeks.
"""

from ebdata.parsing.excel import ExcelDictReader
from ebdata.retrieval.scrapers.list_detail import SkipRecord
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
from ebpub.utils.text import intcomma, clean_address

class PropertyTransferImporter(NewsItemListDetailScraper):
    schema_slugs = ('property-transfers',)
    has_detail = False

    def __init__(self, excel_file_name, *args, **kwargs):
        super(PropertyTransferImporter, self).__init__(*args, **kwargs)
        self.excel_file_name = excel_file_name

    def list_pages(self):
        reader = ExcelDictReader(self.excel_file_name, sheet_index=0, header_row_num=0, start_row_num=1)
        yield reader

    def parse_list(self, reader):
        for row in reader:
            yield row

    def clean_list_record(self, record):
        if record['City'].strip().upper() != 'CHICAGO':
            raise SkipRecord
        if record['Amount'].strip().upper() == 'UNKNOWN':
            record['Amount'] = None
        else:
            record['Amount'] = record['Amount'].replace('.00', '').replace('$', '').replace(',', '')

        record['Executed'] = parse_date(record['Executed'], '%m/%d/%Y')
        record['Recorded'] = parse_date(record['Recorded'], '%m/%d/%Y')

        record['clean_address'] = clean_address(record['Address'])
        unit = record['Unit #'] not in ('', 'MANY') and record['Unit #'] or None
        record['clean_address_with_unit'] = '%s%s' % (record['clean_address'], (unit and ', unit ' + unit or ''))

        try:
            record['doc_number'] = record['Doc Number']
        except KeyError:
            record['doc_number'] = record['Doc #']

        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            qs = qs.by_attribute(self.schema_fields['doc_number'], record['doc_number'])
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            return
        if list_record['Amount'] is None:
            title = '%s transferred ownership' % list_record['clean_address_with_unit']
        else:
            title = '%s sold for $%s' % (list_record['clean_address_with_unit'], intcomma(list_record['Amount']))
        attributes = {
            'doc_number': list_record['doc_number'],
            'sale_price': list_record['Amount'],
            'seller': list_record['Seller'],
            'buyer': list_record['Buyer'],
            'pin': list_record['PIN'],
            'date_executed': list_record['Executed'],
        }
        self.create_newsitem(
            attributes,
            title=title,
            item_date=list_record['Recorded'],
            location_name=list_record['clean_address'],
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    import sys
    importer = PropertyTransferImporter(sys.argv[1])
    importer.update()
