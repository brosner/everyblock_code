"""
Screen scraper for Charlotte certificates of occupancy.
http://dwexternal.co.mecklenburg.nc.us/ids/RptGrid01.aspx?rpt=Certificate%20of%20Occupancy%20Report
"""

from ebdata.retrieval.scrapers.list_detail import SkipRecord
from ebpub.db.models import NewsItem, SchemaField
from ebpub.utils.dates import parse_date
from ebpub.utils.text import smart_title
from everyblock.cities.charlotte.utils import MecklenburgScraper
from dateutil.relativedelta import relativedelta
import datetime

class BuildingInspectionScraper(MecklenburgScraper):
    schema_slugs = ('building-permit-inspections',)
    has_detail = False
    root_uri = 'http://dwexternal.co.mecklenburg.nc.us/ids/RptGrid01.aspx?rpt=CFR%20Inspections'

    def get_location(self, permit_number):
        # cache the schemafield for building permit permit numbers so we don't
        # have to look it up for each record
        if not hasattr(self, '_permit_number_field'):
            self._permit_number_field = SchemaField.objects.get(
                schema__slug='building-permits', name='permit_number')
        # lookup address from the permit number
        qs = NewsItem.objects.filter(schema__slug='building-permits')
        qs = qs.by_attribute(self._permit_number_field, permit_number)
        try:
            permit = qs[0]
            return permit.location_name
        except IndexError:
            return None

    def list_pages(self):
        self.login()
        return super(BuildingInspectionScraper, self).list_pages()

    def date_pairs(self):
        # Alwys start the scraper running 4 months ago. The data is updated
        # quarterly, so this will give us a cushion if they publish it up to a
        # month after the quarter ends.
        d = datetime.date.today() - relativedelta(months=4)
        while d < datetime.date.today():
            start = d.strftime('%m/%d/%Y')
            end = (d + relativedelta(days=6)).strftime('%m/%d/%Y')
            d += relativedelta(days=7)
            yield (start, end)

    def search_arguments(self, start, end, viewstate):
        return {
            '_ctl3:btn_Download': 'File Download',
            '__EVENTARGUMENT': '',
            '__EVENTTARGET': '',
            '__VIEWSTATE': viewstate,
            '_ctl0:QUERY': '',
            #'_ctl3:btn_Search': 'Search',
            '_ctl4:CFR_CONFIRMATIONNUMBER': '',
            '_ctl4:CFR_Contractor': '',
            '_ctl4:CFR_Contractor_stem': '',
            '_ctl4:CFR_INSPECTORINFO': '',
            '_ctl4:CFR_LagTime_Days_from': '',
            '_ctl4:CFR_LagTime_Days_to': '',
            '_ctl4:CFR_PERMITTRADE': '',
            '_ctl4:CFR_PERMITTYPE': '',
            '_ctl4:CFR_REQUESTDATE_from': start,
            '_ctl4:CFR_REQUESTDATE_to': end,
            '_ctl4:CFR_RESULTDATE_from': '',
            '_ctl4:CFR_RESULTDATE_to': '',
            '_ctl4:CFR_Result': '',
            '_ctl4:CFR_USDC_Activity_Type': '',
            '_ctl4:CFR_USDCcode': '',
            'fmt': 'standard'
        }

    def clean_list_record(self, record):
        record['location'] = self.get_location(record['PERMIT_NUMBER'])
        if record['location'] is None:
            raise SkipRecord("No permit found for '%s'" % record['PERMIT_NUMBER'])
        record['InspectionDate'] = parse_date(record['InspectionDate'], '%Y-%m-%dT00:00:00')
        return record

    def existing_record(self, record):
        inspection_type = self.get_or_create_lookup('inspection_type', record['TASKPERFORMED'], record['TASKPERFORMED'], make_text_slug=False)
        # use permit number, task performed, and date
        qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=record['InspectionDate'])
        qs = qs.by_attribute(self.schema_fields['permit_number'], record['PERMIT_NUMBER'])
        qs = qs.by_attribute(self.schema_fields['inspection_type'], inspection_type.id)
        try:
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            self.logger.debug('Record already exists')
            return
        if list_record['location'] is None:
            self.logger.debug('Skipping %s. No address found.' % list_record['PERMIT_NUMBER'])
            return
        project_type = self.get_or_create_lookup('project_type', list_record['USDC_Activity_Type'], list_record['USDC_Activity_Type'], make_text_slug=False)
        inspection_type = self.get_or_create_lookup('inspection_type', list_record['TASKPERFORMED'], list_record['TASKPERFORMED'], make_text_slug=False)
        result = self.get_or_create_lookup('result', list_record['RESULT'], list_record['RESULT'], make_text_slug=False)
        detail_lookups = []
        for i in range(1, 10):
            code = list_record['Defect%s_Code' % i].strip()
            name = list_record['DEFECT%s' % i].strip()
            if name != '' and code != '':
                lookup = self.get_or_create_lookup('details', name, code, make_text_slug=False)
                detail_lookups.append(lookup)
        if list_record['RESULT'] == '01 - Passed':
            title = "Project passed inspection at %s" % list_record['location']
        elif list_record['RESULT'] == '02 - Failed':
            title = "Project failed inspection at %s" % list_record['location']
        elif list_record['RESULT'] == '03 - Inaccessible':
            title = "Project conditionally passed inspection at %s" % list_record['location']
        elif list_record['RESULT'] == 'Not Done':
            title = "Project was not inspected at %s" % list_record['location']
        attributes = {
            'contractor_id': list_record['CONTRACTORID'],
            'contractor': list_record['CONTRACTOR'],
            'project_type': project_type.id,
            'permit_number': list_record['PERMIT_NUMBER'],
            'inspection_type': inspection_type.id,
            'result': result.id,
            'details': ','.join([str(d.id) for d in detail_lookups])
        }
        self.create_newsitem(
            attributes,
            title=title,
            item_date=list_record['InspectionDate'],
            location_name=smart_title(list_record['location']),
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    import sys
    if len(sys.argv) > 1:
        start_date = parse_date(sys.argv[1], '%Y-%m-%d')
    else:
        start_date = None
    BuildingInspectionScraper(start_date=start_date).update()
