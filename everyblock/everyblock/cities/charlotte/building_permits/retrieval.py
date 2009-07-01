"""
Screen scraper for Charlotte building permits.
http://dwexternal.co.mecklenburg.nc.us/ids/RptGrid01.aspx?rpt=Daily_Building_Permits_Issued
"""

from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
from ebpub.utils.text import smart_title
from everyblock.cities.charlotte.utils import MecklenburgScraper
import datetime

class BuildingPermitScraper(MecklenburgScraper):
    schema_slugs = ('building-permits',)
    has_detail = False
    root_uri = 'http://dwexternal.co.mecklenburg.nc.us/ids/RptGrid01.aspx?rpt=Daily_Building_Permits_Issued'

    def search_arguments(self, start, end, viewstate):
        return {
            '__EVENTARGUMENT': '',
            '__EVENTTARGET': '',
            '__VIEWSTATE': viewstate,
            '_ctl0:QUERY': '',
            #'_ctl3:btn_Search': 'Search',
            '_ctl3:btn_Download': 'File Download',
            '_ctl4:date_IssueDate_from': start,
            '_ctl4:date_IssueDate_to': end,
            '_ctl4:txt_ContractorName_s': '',
            '_ctl4:txt_ExternalFileNum': '',
            '_ctl4:txt_PermitType': '',
            '_ctl4:txt_ProjectAddress': '',
            '_ctl4:txt_ProjectName': '',
            '_ctl4:txt_TaxJurisdiction': 'CHARLOTTE',
            '_ctl4:txt_USDCCodeNumber': '',
            'fmt': 'standard',
        }

    def clean_list_record(self, record):
        formats = ['%Y-%m-%dT00:00:00', '%m/%d/%Y']
        for format in formats:
            try:
                record['Issue_Date'] = parse_date(record['Issue_Date'], format)
                break
            except ValueError:
                continue
        # collapse some occupancy types
        mapping = {
            'A3C     * ASSEMBLY - CHURCH': 'A3     * ASSEMBLY - CHURCH',
            'F1     * FACTORY - MODERATE': 'F1     * FACTORY/INDUSTRIAL - MODERATE HAZARD',
            'F2     * FACTORY - LOW': 'F2     * FACTORY/INDUSTRIAL - LOW HAZARD',
            'R3     * RESIDENTIAL - SINGLE FAM': 'R3     * RESIDENTIAL - SINGLE FAMILY'
        }
        record['occupancy_type'] = mapping.get(record['Occupancy'], record['Occupancy'])
        return record

    def existing_record(self, record):
        if not isinstance(record['Issue_Date'], datetime.date):
            return None
        qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=record['Issue_Date'])
        qs = qs.by_attribute(self.schema_fields['permit_number'], record['ExternalFileNum'])
        try:
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        if not isinstance(list_record['Issue_Date'], datetime.date):
            self.logger.debug("Did not save %s. Invalid date %s." % (list_record['ExternalFileNum'], list_record['Issue_Date']))
            return
        if old_record is not None:
            self.logger.debug('Record already exists')
            return
        permit_type = self.get_or_create_lookup('permit_type', list_record['PermitType'], list_record['PermitType'], make_text_slug=False)
        project_type = self.get_or_create_lookup('project_type', list_record['USDCCodeNumber'], list_record['USDCCodeNumber'], make_text_slug=False)
        occupancy_type = self.get_or_create_lookup('occupancy_type', list_record['occupancy_type'], list_record['occupancy_type'], make_text_slug=False)
        construction_type = self.get_or_create_lookup('construction_type', list_record['ConstructionType'], list_record['ConstructionType'], make_text_slug=False)

        title = 'Permit issued for %s' % project_type.name
        attributes = {
            'permit_number': list_record['ExternalFileNum'],
            'cost': list_record['Construction_Cost'],
            'permit_type': permit_type.id,
            'project_type': project_type.id,
            'project_number': list_record['ProjectNumber'],
            'owner': list_record['OwnerTenant'],
            'occupancy_type': occupancy_type.id,
            'occupancy_type_raw': list_record['Occupancy'],
            'number_of_stories': list_record['NumberOfStories'],
            'construction_type': construction_type.id,
            'total_fee': list_record['TotalFee'],
        }
        self.create_newsitem(
            attributes,
            title=title,
            item_date=list_record['Issue_Date'],
            location_name=smart_title(list_record['Address']),
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    import sys
    if len(sys.argv) > 1:
        start_date = parse_date(sys.argv[1], '%Y-%m-%d')
    else:
        start_date = None
    BuildingPermitScraper(start_date=start_date).update()
