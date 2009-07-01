"""
Scraper for Florida residential real estate approvals.
http://www.myflorida.com/dbpr/sto/file_download/lsc_download.shtml
"""

from ebdata.retrieval.scrapers.list_detail import SkipRecord
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
from ebpub.utils.text import clean_address
from everyblock.states.florida.myflorida import MyFloridaScraper

class BaseScraper(MyFloridaScraper):
    has_detail = False
    date_format = '%m/%d/%Y'

    def __init__(self, county_names):
        super(BaseScraper, self).__init__()
        self.county_names = set(county_names)

    def clean_list_record(self, record):
        if record['county'].upper() not in self.county_names:
            raise SkipRecord('Skipping county %s' % record['county'])
        record['approval_date'] = parse_date(record['approval_date'], self.date_format)
        if record['approval_date'] is None:
            raise SkipRecord('Record has no date.')
        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            qs = qs.by_attribute(self.schema_fields['project_number'], record['project_number'])
            qs = qs.by_attribute(self.schema_fields['file_number'], record['file_number'])
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        values = {
            'title': self.get_title(list_record),
            'item_date': list_record['approval_date'],
            'location_name': clean_address('%s, %s' % (list_record['street'].strip(), list_record['city'])),
        }
        attributes = self.get_attributes(list_record)
        if old_record is None:
            self.create_newsitem(attributes, **values)
        else:
            self.update_existing(old_record, values, attributes)

class ConvertedCondominiumsScraper(BaseScraper):
    schema_slugs = ('condo-conversions',)
    name_var = 'coop_name'
    florida_ftp_filename = 'condo_conv.exe'
    florida_csv_fieldnames = ('project_number', 'file_number', 'coop_name', 'county',
        'street', 'city', 'state', 'zip', 'units', 'approval_date',
        'primary_status', 'secondary_status', 'manager_number', 'manager_name',
        'manager_route', 'manager_street', 'manager_city', 'manager_state',
        'manager_zip')

    def list_pages(self):
        f = open('/home/jkocherhans/miami-condos/condo_conv.exe', 'rb')
        yield f
        f.close()

    def get_title(self, record):
        return "%s" % record['coop_name']

    def clean_list_record(self, record):
        if record['primary_status'] == 'Acknowledged':
            raise SkipRecord('Status is "Acknowledged"')
        return super(ConvertedCondominiumsScraper, self).clean_list_record(record)

    def get_attributes(self, record):
        primary_status = self.get_or_create_lookup('primary_status', record['primary_status'],  record['primary_status'], make_text_slug=False)
        secondary_status = self.get_or_create_lookup('secondary_status', record['secondary_status'],  record['secondary_status'], make_text_slug=False)
        return {
            'name': record['coop_name'],
            'project_number': record['project_number'],
            'file_number': record['file_number'],
            'units': record['units'],
            'primary_status': primary_status.id,
            'secondary_status': secondary_status.id,
        }

class IntendedConversionsScraper(BaseScraper):
    schema_slugs = ('condo-conversion-notices',)
    name_var = 'noic_name'
    date_format = '%m/%d/%y'
    florida_ftp_filename = 'noic.exe'
    florida_csv_fieldnames = ('file_number', 'noic_name', 'county', 'street',
        'city', 'state', 'zip', 'approval_date', 'status', 'developer_name',
        'developer_route', 'developer_street', 'developer_city',
        'developer_state', 'developer_zip')

    def list_pages(self):
        f = open('/home/jkocherhans/miami-condos/noic.exe', 'rb')
        yield f
        f.close()

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            qs = qs.by_attribute(self.schema_fields['file_number'], record['file_number'])
            return qs[0]
        except IndexError:
            return None

    def get_title(self, record):
        return "%s" % record['noic_name']

    def get_attributes(self, record):
        status = self.get_or_create_lookup('status', record['status'],  record['status'], make_text_slug=False)
        return {
            'name': record['noic_name'],
            'file_number': record['file_number'],
            'status': status.id,
        }

if __name__ == '__main__':
    from ebdata.retrieval import log_debug
    ConvertedCondominiumsScraper(('DADE',)).update()
    IntendedConversionsScraper(('DADE',)).update()
