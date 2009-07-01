"""
Scraper for San Jose permit data

https://www.sjpermits.org/permits/permits/general/reportdata.asp
"""

from ebdata.retrieval.scrapers.list_detail import SkipRecord
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
from cStringIO import StringIO
import csv

class Scraper(NewsItemListDetailScraper):
    schema_slugs = ['building-permit-actions']
    has_detail = False
    sleep = 1
    uri = 'https://www.sjpermits.com/sanjoseftp/permitdataMonths/PDIssue_latest.TXT'

    def list_pages(self):
        yield self.get_html(self.uri)

    def parse_list(self, page):
        fh = StringIO(page)
        reader = csv.DictReader(fh, delimiter='\t')
        for record in reader:
            yield record

    def clean_permit_type(self, pa):
        permit_types_mapping = {
            'B-4. Complete': 'B-Complete',
            'E-4. Complete': 'E-Complete',
            'P-4. Complete': 'P-Complete',
            'M-4. Complete': 'M-Complete',
            'M-1. *n/a':     'M-Complete',
            'P-1. *n/a':     'P-Complete',
            'E-1. *n/a':     'E-Complete',
        }
        pa = pa.strip()
        if permit_types_mapping.has_key(pa):
            return permit_types_mapping[pa]
        return pa

    def clean_list_record(self, record):
        if record['WORKDESC'] == '4635':
            raise SkipRecord('WORKDESC is 4635')
        if record['JOBLOCATION'] is None:
            raise SkipRecord('Record has no location')
        if record['PERMITAPPROVALS'] is None:
            record['permit_types'] = []
        else:
            record['permit_types'] = [self.clean_permit_type(pa) for pa in record['PERMITAPPROVALS'].split(',')]

        # Addresses and extra data generally seem to be separated by 2 or more spaces
        record['location'] = record['JOBLOCATION'].split('  ')[0]
        for format in ['%d-%b-%y', '%m/%d/%Y']:
            try:
                issue_date = parse_date(record['ISSUEDATE'], format)
                break
            except ValueError:
                continue
        record['issue_date'] = issue_date
        record['WORKDESC'] = record['WORKDESC'].strip()
        record['SUBDESC'] = record['SUBDESC'].strip()
        return record

    def existing_record(self, list_record):
        record = None
        qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=list_record['issue_date'])
        qs = qs.by_attribute(self.schema_fields['apn'], list_record['APN'])
        qs = qs.by_attribute(self.schema_fields['work_type'], list_record['WORKDESC'].upper(), is_lookup=True)
        try:
            return qs[0]
        except IndexError:
            return None

    def detail_required(self, list_record, old_record):
        return True

    def get_detail(self, list_record):
        page = ''
        return page

    def parse_detail(self, page, list_record):
        detail_record = {}
        return detail_record

    def clean_detail_record(self, record):
        return record

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            return
        work_type_lookup = self.get_or_create_lookup('work_type', list_record['WORKDESC'], list_record['WORKDESC'].upper(), make_text_slug=False)
        sub_type_lookup = self.get_or_create_lookup('sub_type', list_record['SUBDESC'], list_record['SUBDESC'].upper(), make_text_slug=False)

        permit_type_lookups = []
        for permit_type in list_record['permit_types']:
            permit_type_lookup = self.get_or_create_lookup('permit_types', permit_type, permit_type, make_text_slug=False)
            permit_type_lookups.append(permit_type_lookup)

        attributes = {
            'apn': list_record['APN'],
            'work_type': work_type_lookup.id,
            'sub_type': sub_type_lookup.id,
            'permit_types': ','.join([str(l.id) for l in permit_type_lookups])
        }
        self.create_newsitem(
            attributes,
            title=work_type_lookup.name,
            item_date=list_record['issue_date'],
            location_name=list_record['location']
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    Scraper().update()
