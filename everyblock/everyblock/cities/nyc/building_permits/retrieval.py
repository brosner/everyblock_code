"""
Screen scraper for NYC Dept. of Buildings building permits.

The data comes in monthly Excel reports from the "Job Weekly Statistical Reports"
section of this page:
http://www.nyc.gov/html/dob/html/guides/weekly.shtml
"""

from ebdata.parsing.excel import ExcelDictReader
from ebdata.retrieval.scrapers.list_detail import SkipRecord
from ebdata.retrieval.retrievers import PageNotFoundError
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.text import smart_title
import datetime
import os

JOB_STATUS_HEADLINE_VERBS = {
    'A': 'pre-filed',
    'B': 'processed',
    'C': 'processed',
    'D': 'processed',
    'E': 'processed',
    'F': 'assigned for DOB exam',
    'G': 'changed plans',
    'H': 'initiated for exam',
    'J': 'disapproved by DOB',
    'K': 'partially approved',
    'L': 'waiting for change fee assessment',
    'M': 'approved for changed plans',
    'P': 'approved by DOB exam',
    'Q': 'approved for a partial permit',
    'R': 'approved',
    'U': 'completed',
    'X': 'signed off',
}

JOB_TYPE_HEADLINE_NOUNS = {
    'A1': 'alteration to property',
    'A2': 'alteration to property',
    'A3': 'alteration to property',
    'NB': 'creation of a new building',
    'PA': 'place of assembly',
    'DM': 'demolition',
    'SC': 'subdivision of property into condo units',
    'SI': 'subdivision of property into new/different lot sizes',
}

class PermitScraper(NewsItemListDetailScraper):
    schema_slugs = ('building-permits',)
    has_detail = False

    def __init__(self, week_end_dates=None):
        """
        week_end_dates is a list of datetime objects representing the week to
        download. If it's not provided, this will use the last three weeks.
        """
        super(PermitScraper, self).__init__(use_cache=False)
        if week_end_dates is None:
            # Use the last three Saturdays.
            end_date = datetime.date.today()
            while 1:
                end_date -= datetime.timedelta(days=1)
                if end_date.weekday() == 5:
                    break
            week_end_dates = [end_date - datetime.timedelta(days=7), end_date]
        self.week_end_dates = week_end_dates

    def list_pages(self):
        for week_end_date in self.week_end_dates:
            # They've used a different URL scheme over time.
            if week_end_date <= datetime.date(2005, 5, 13):
                url = 'http://www.nyc.gov/html/dob/downloads/download/foil/job%s.xls' % week_end_date.strftime('%m%d%y')
            else:
                url = 'http://www.nyc.gov/html/dob/downloads/excel/job%s.xls' % week_end_date.strftime('%m%d%y')

            try:
                workbook_path = self.retriever.get_to_file(url)
                yield ExcelDictReader(workbook_path, sheet_index=0, header_row_num=2, start_row_num=3)
                os.unlink(workbook_path) # Clean up the temporary file.
            except PageNotFoundError:
                self.logger.warn("Could not find %s" % url)

    def parse_list(self, reader):
        for row in reader:
            yield row

    def clean_list_record(self, record):
        record['address'] = '%s %s, %s' % (record['House #'], smart_title(record['Street Name']), smart_title(record['Borough']))
        record['is_landmark'] = record['Landmarked'] == 'Y'
        record['is_adult_establishment'] = record['Adult Estab'] == 'Y'
        record['is_city_owned'] = record['City Owned'] == 'Y'
        if not isinstance(record['Latest Action Date'], (datetime.date, datetime.datetime)):
            raise SkipRecord('Got last action date %s' % record['Latest Action Date'])
        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            qs = qs.by_attribute(self.schema_fields['job_number'], record['Job #'])
            qs = qs.by_attribute(self.schema_fields['doc_number'], record['Doc #'])
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            return

        try:
            title = 'Permit application %s for %s' % \
                (JOB_STATUS_HEADLINE_VERBS[list_record['Job Status']],
                JOB_TYPE_HEADLINE_NOUNS[list_record['Job Type']])
        except KeyError:
            self.logger.warning('Got unknown values Job Status=%s, Job Type=%s', list_record['Job Status'], list_record['Job Type'])
            return

        job_type = self.get_or_create_lookup('job_type', list_record['Job Type'], list_record['Job Type'], make_text_slug=False)
        job_status = self.get_or_create_lookup('job_status', list_record['Job Status'], list_record['Job Status'], make_text_slug=False)
        building_type = self.get_or_create_lookup('building_type', list_record['Building Type'], list_record['Building Type'], make_text_slug=False)
        existing_occupancy = self.get_or_create_lookup('existing_occupancy', list_record['Existing Occupancy'], list_record['Existing Occupancy'], make_text_slug=False)
        proposed_occupancy = self.get_or_create_lookup('proposed_occupancy', list_record['Proposed Occupancy'], list_record['Proposed Occupancy'], make_text_slug=False)

        attributes = {
            'job_number': list_record['Job #'],
            'doc_number': list_record['Doc #'],
            'bin_number': list_record['Bin #'],
            'job_type': job_type.id,
            'job_status': job_status.id,
            'building_type': building_type.id,
            'is_landmark': list_record['is_landmark'],
            'is_adult_establishment': list_record['is_adult_establishment'],
            'is_city_owned': list_record['is_city_owned'],
            'estimated_cost': list_record['Initial Cost'] or None,
            'existing_occupancy': existing_occupancy.id,
            'proposed_occupancy': proposed_occupancy.id,
            'job_description': list_record['Job Description'],
        }
        self.create_newsitem(
            attributes,
            title=title,
            pub_date=list_record['Latest Action Date'],
            item_date=list_record['Latest Action Date'],
            location_name=list_record['address'],
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    PermitScraper().update()
