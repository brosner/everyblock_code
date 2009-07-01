"""
Screen scraper for Charlotte certificates of occupancy.
http://dwexternal.co.mecklenburg.nc.us/ids/RptGrid01.aspx?rpt=Certificate%20of%20Occupancy%20Report
"""

from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
from ebpub.utils.text import smart_title
from everyblock.cities.charlotte.utils import MecklenburgScraper

class OccupancyScraper(MecklenburgScraper):
    schema_slugs = ('occupancy',)
    has_detail = False
    root_uri = 'http://dwexternal.co.mecklenburg.nc.us/ids/RptGrid01.aspx?rpt=Certificate%20of%20Occupancy%20Report'

    def list_pages(self):
        self.login()
        return super(OccupancyScraper, self).list_pages()

    def search_arguments(self, start, end, viewstate):
        return {
            '__EVENTARGUMENT': '',
            '__EVENTTARGET': '',
            '__VIEWSTATE': viewstate,
            '_ctl0:QUERY': '',
            #'_ctl3:btn_Search': 'Search',
            '_ctl3:btn_Download': 'File Download',
            '_ctl4:Municipality:0': 'on',
            '_ctl4:date_COIssueDate_from': start,
            '_ctl4:date_COIssueDate_to': end,
            '_ctl4:date_ContractCost_From': '',
            '_ctl4:date_ContractCost_To': '',
            '_ctl4:date_IssueDate_from': '',
            '_ctl4:date_IssueDate_to':  '',
            '_ctl4:txt_BuildingAddress': '',
            '_ctl4:txt_CAMA_Parcel_From': '',
            '_ctl4:txt_CAMA_Parcel_To': '',
            '_ctl4:txt_JobStatus': '',
            '_ctl4:txt_JobTypeName': 'j_BuildingPermit',
            '_ctl4:txt_PermitID_From': '',
            '_ctl4:txt_PermitID_To': '',
            '_ctl4:txt_PermitType': '',
            '_ctl4:txt_StreetName': '',
            '_ctl4:txt_USDCCode_From': '',
            '_ctl4:txt_USDCCode_To': '',
            'fmt': 'standard'
        }

    def clean_list_record(self, record):
        record['CO_Date'] = parse_date(record['CO_Date'], '%m/%d/%Y')
        mapping = {
          '328 - Other Not-CO\'able Non-Residential Buildings(well h': '328 - Other CO\'able Non-Res Bldgs(jails,post office)',
          '437 - All Other CO\'able Buildings / Structures': '437 - All Other Buildings / Structures(additions, remode'
        }
        record['project_type'] = mapping.get(record['USDC_Code'], record['USDC_Code'])
        return record

    def existing_record(self, record):
        qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=record['CO_Date'])
        qs = qs.by_attribute(self.schema_fields['permit_number'], record['Permit_Number'])
        try:
            return qs[0]
        except IndexError:
            return None
        return None

    def save(self, old_record, list_record, detail_record):
        print list_record
        if old_record is not None:
            self.logger.debug('Record already exists')
            return
        project_type = self.get_or_create_lookup('project_type', list_record['project_type'], list_record['project_type'], make_text_slug=False)
        title = 'Certificate issued for %s' % project_type.name
        attributes = {
            'parcel_id': list_record['PID__Parcel_ID_'],
            'permit_number': list_record['Permit_Number'],
            'cost': list_record['Cost'],
            'project_type': project_type.id,
            'project_type_raw': list_record['USDC_Code'],
            'num_units': list_record['NumberOfUnits'],
            'heated_sqft': list_record['Heated_Square_Feet']
        }
        self.create_newsitem(
            attributes,
            title=title,
            item_date=list_record['CO_Date'],
            location_name=smart_title(list_record['Project_Address']),
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    import sys
    if len(sys.argv) > 1:
        start_date = parse_date(sys.argv[1], '%Y-%m-%d')
    else:
        start_date = None
    OccupancyScraper(start_date=start_date).update()
