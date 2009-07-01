"""
Screen scraper for NYC Dept. of Buildings sign permits.

The data comes in weekly Excel reports from the "Sign Monthly Statistical
Reports" section of this page:
http://www.nyc.gov/html/dob/html/guides/weekly.shtml
"""

from ebdata.parsing.excel import ExcelDictReader
from ebdata.retrieval.scrapers.list_detail import SkipRecord
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

JOB_STATUS_NAMES = {
    'A': 'Pre-filed',
    'B': 'Processed without payment',
    'C': 'Processed with payment only',
    'D': 'Processed',
    'E': 'Processed without a request for an exam by the Department of Buildings, and the applicant will professionally certify the plans',
    'F': 'Assigned for exam by the DOB',
    'G': 'Changed after the DOB approved plans and requires a change fee',
    'H': 'Initiated for exam',
    'J': 'Disapproved after a DOB exam',
    'K': 'Partially approved',
    'L': 'Waiting for change fee assessment after change of plans',
    'M': 'Approved for change of plans after change fee accepted',
    'P': 'Approved by DOB exam',
    'Q': 'Approved for a partial permit',
    'R': 'Approved',
    'U': 'Completed',
    'X': 'Signed off',
}

class SignScraper(NewsItemListDetailScraper):
    schema_slugs = ('sign-permits',)
    has_detail = False

    def __init__(self, week_end_dates=None):
        """
        week_end_dates is a list of datetime objects representing the week to
        download. If it's not provided, this will use the last three weeks.
        """
        super(SignScraper, self).__init__(use_cache=False)
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
                url = 'http://www.nyc.gov/html/dob/downloads/download/foil/sg%s.xls' % week_end_date.strftime('%m%d%y')
            else:
                url = 'http://www.nyc.gov/html/dob/downloads/excel/sg%s.xls' % week_end_date.strftime('%m%d%y')

            workbook_path = self.retriever.get_to_file(url)
            yield ExcelDictReader(workbook_path, sheet_index=0, header_row_num=2, start_row_num=3,
                use_last_header_if_duplicate=False)
            os.unlink(workbook_path) # Clean up the temporary file.

    def parse_list(self, reader):
        for row in reader:
            yield row

    def clean_list_record(self, record):
        record['address'] = '%s %s, %s' % (record['House #'], smart_title(record['Street Name']), smart_title(record['Borough']))
        record['is_landmark'] = record['Landmark'] == 'Y'
        record['is_adult_establishment'] = record['Adult Estab'] == 'Y'
        record['is_city_owned'] = record['City Owned'] == 'Y'
        record['illumination_type'] = record.get('Sign Illumination Type', 'Not available') or 'Not illuminated'
        if not isinstance(record['Latest Action Date'], datetime.datetime):
            self.logger.info('Skipping job #%s, with latest action date %s', record.get('Job #'), record['Latest Action Date'])
            raise SkipRecord()

        try:
            record['sign_text'] = record['Text on Sign'].strip()
            if len(record['sign_text']) > 255:
                # Some records are malformed and have a bad and long value
                # for sign text.
                self.logger.info('Skipping job #%s, with Text on Sign %s', record.get('Job #'), record['Text on Sign'])
                raise SkipRecord()
        except AttributeError:
            try:
                record['sign_text'] = str(int(record['Text on Sign']))
            except TypeError:
                self.logger.info('Skipping job #%s, with Text on Sign %s', record.get('Job #'), record['Text on Sign'])
                raise SkipRecord()

        try:
            record['sign_for'] = record['Sign Advertising']
        except KeyError:
            record['sign_for'] = record['Usage']

        try:
            record['is_near_highway'] = record['Sign Near Highway'] == 'Y'
        except KeyError:
            # Older spreadsheets don't have a 'Sign Near Highway' column,
            # and there's nothing we can do about it. They have a column called
            # 'Adjacent to Arterial Highway', but that's not necessarily the
            # same thing.
            record['is_near_highway'] = None

        try:
            record['is_changeable_copy'] = record['Sign Changeable Copy'] == 'Y'
        except KeyError:
            # Older spreadsheets don't have a 'Sign Changeable Copy' column,
            # but we can deduce the value: if there's text, then it's not
            # changeable. Otherwise, it's NULL.
            if record['sign_text']:
                record['is_changeable_copy'] = False
            else:
                record['is_changeable_copy'] = None

        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            qs = qs.by_attribute(self.schema_fields['job_number'], record['Job #'])
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            return

        job_status = self.get_or_create_lookup('job_status', JOB_STATUS_NAMES[list_record['Job Status']], list_record['Job Status'])
        illumination_type = self.get_or_create_lookup('illumination_type', list_record['illumination_type'], list_record['illumination_type'])
        sign_location = self.get_or_create_lookup('sign_location', smart_title(list_record['Sign Type']), list_record['Sign Type'])
        sign_for = self.get_or_create_lookup('sign_for', smart_title(list_record['sign_for']), list_record['sign_for'])
        title = 'Permit application %s for an %s %s sign' % \
            (JOB_STATUS_HEADLINE_VERBS[list_record['Job Status']],
            (list_record['Sign Illumination'] == 'Y' and 'illuminated' or 'unilluminated'),
            (list_record['sign_for'] == 'BUSINESS' and 'business' or 'advertising'))
        attributes = {
            'bin': list_record['Bin #'],
            'job_number': list_record['Job #'],
            'job_status': job_status.id,
            'is_landmark': list_record['is_landmark'],
            'is_adult_establishment': list_record['is_adult_establishment'],
            'is_city_owned': list_record['is_city_owned'],
            'is_changeable_copy': list_record['is_changeable_copy'],
            'estimated_cost': list_record['Initial Cost'],
            'illumination_type': illumination_type.id,
            'sign_location': sign_location.id,
            'size': list_record['Sign SQ Footage'],
            'sign_for': sign_for.id,
            'sign_text': list_record['sign_text'],
            'job_description': list_record['Job Description 1'],
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
    SignScraper().update()
