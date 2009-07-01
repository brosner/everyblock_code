"""
Screen scraper for Houston crime.
http://www.houstontx.gov/police/cs/stats2.htm
"""

from ebdata.parsing.excel import ExcelDictReader
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from dateutil.relativedelta import relativedelta
import datetime
import time
import sys
import os

class CrimeScraper(NewsItemListDetailScraper):
    schema_slugs = ('crime',)
    has_detail = False

    def __init__(self, excel_url=None):
        super(CrimeScraper, self).__init__()
        if excel_url is None:
            last_month = datetime.date.today() - relativedelta(months=1)
            filename = last_month.strftime('%b%y').lower()
            excel_url = 'http://www.houstontx.gov/police/cs/xls/%s.xls' % filename
        self.excel_url = excel_url

    def list_pages(self):
        file_path = self.retriever.get_to_file(self.excel_url)
        reader = ExcelDictReader(file_path, sheet_index=0, header_row_num=0, start_row_num=1)
        yield reader
        os.unlink(file_path) # Clean up the temporary file.

    def parse_list(self, reader):
        for row in reader:
            yield row

    def clean_list_record(self, record):
        if record['Street Name'] == 'OUTSIDE':
            record['address'] = 'Outside'
        else:
            record['address'] = "%s %s block of %s %s" % (int(record['Block']), record['Suffix'], record['Street Name'], record['Type'])
        record['offense_time'] = datetime.datetime(*time.strptime(record['Offense Time'], '%H%M')[:5]).time()
        return record

    def existing_record(self, record):
        offense = self.get_or_create_lookup('offense', record['Offense'], record['Offense'])
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=record['Offense Date'])
            qs = qs.by_attribute(self.schema_fields['offense_time'], record['offense_time'])
            qs = qs.by_attribute(self.schema_fields['offense'], offense.id)
            return qs[0]
        except IndexError:
            return None
        return None

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            self.logger.debug('Record already exists')
            return

        offense = self.get_or_create_lookup('offense', list_record['Offense'], list_record['Offense'])
        beat = self.get_or_create_lookup('beat', list_record['Beat'], list_record['Beat'])
        premise_type = self.get_or_create_lookup('premise_type', list_record['Premise'], list_record['Premise'])

        attributes = {
            'offense': offense.id,
            'offense_time': list_record['offense_time'],
            'beat': beat.id,
            'premise_type': premise_type.id,
        }
        self.create_newsitem(
            attributes,
            title=offense.name,
            item_date=list_record['Offense Date'],
            location_name=list_record['address'],
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    try:
        excel_url = sys.argv[1]
        CrimeScraper(excel_url=excel_url).update()
    except IndexError:
        CrimeScraper().update()
