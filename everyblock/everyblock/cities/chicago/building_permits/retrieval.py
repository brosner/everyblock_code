"""
Import script for Chicago building permits.

This data is imported from an Excel file, which is e-mailed to us every month.

Note: As of 2008-04-25, the Excel file is in an older Excel format that isn't
supported by our Excel-parsing library. (XLRDError: "BIFF version 2 is not
supported".) To fix this, open the file in Excel and save it; you'll be
prompted to save it to a newer version.
"""

from ebdata.parsing.excel import ExcelDictReader
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
from ebpub.utils.text import smart_title
import re

class BuildingPermitImporter(NewsItemListDetailScraper):
    schema_slugs = ('building-permits',)
    has_detail = False

    def __init__(self, excel_file_name, *args, **kwargs):
        super(BuildingPermitImporter, self).__init__(*args, **kwargs)
        self.excel_file_name = excel_file_name

    def list_pages(self):
        reader = ExcelDictReader(self.excel_file_name, sheet_index=0, header_row_num=0, start_row_num=1)
        yield reader

    def parse_list(self, reader):
        for row in reader:
            yield row

    def clean_list_record(self, record):
        issue_datetime = parse_date(record['issdttm'], '%m/%d/%Y %H:%M:%S', return_datetime=True)
        record['issue_date'] = issue_datetime.date()
        record['issue_time'] = issue_datetime.time()
        record['clean_address'] = '%s %s. %s %s.' % (record['stno'], record['predir'],
            smart_title(record['stname']), smart_title(record['suffix']))
        record['clean_permit_type'] = smart_title(re.sub(r'^PERMIT - ', '', record['apdesc']))
        try:
            record['description'] = record['compute_0009']
        except KeyError:
            record['description'] = record['permit_description']
        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            qs = qs.by_attribute(self.schema_fields['application_number'], record['apno'])
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            return
        work_type = self.get_or_create_lookup('work_type', list_record['clean_permit_type'], list_record['aptype'])
        title = 'Permit issued for %s' % work_type.name.lower()
        attributes = {
            'application_number': list_record['apno'],
            'work_type': work_type.id,
            'description': list_record['description'],
            'estimated_value': list_record['declvltn'],
            'issue_time': list_record['issue_time'],
        }
        self.create_newsitem(
            attributes,
            title=title,
            item_date=list_record['issue_date'],
            location_name=list_record['clean_address'],
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    import sys
    importer = BuildingPermitImporter(sys.argv[1])
    importer.update()
