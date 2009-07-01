"""
Scraper for Florida restaurant plan review applications.
http://www.myflorida.com/dbpr/sto/file_download/hr_food_service_files.shtml
"""

from ebdata.retrieval.scrapers.list_detail import SkipRecord
from ebpub.db.models import NewsItem
from ebpub.geocoder.parser.parsing import strip_unit
from ebpub.utils.dates import parse_date
from ebpub.utils.text import clean_address
from everyblock.states.florida.myflorida import MyFloridaScraper

class Scraper(MyFloridaScraper):
    schema_slugs = ('plan-reviews',)
    has_detail = False

    florida_ftp_filename = 'HR_plan_review.exe'
    florida_csv_fieldnames = ('district', 'county', 'business_name',
        'address', 'city', 'zip', 'phone', 'email', 'status',
        'application_date', 'review_date', 'application_type', 'facility_type',
        'file_number', 'application_number', 'license_number', 'transaction',
        'variance', 'mailing_name', 'mailing_address', 'mailing_city',
        'mailing_state', 'mailing_zip', 'mailing_country', 'contact_phone',
        'contact_email', 'alternate_phone', 'alternate_email')

    def __init__(self, city_names):
        # city_names should be a list of uppercase strings like 'MIAMI'.
        super(Scraper, self).__init__()
        self.city_names = set(city_names)

    def clean_list_record(self, record):
        record['application_date'] = parse_date(record['application_date'], '%m/%d/%Y')

        try:
            record['review_date'] = parse_date(record['review_date'], '%m/%d/%Y')
        except ValueError: # sometimes it's 'n/a'
            record['review_date'] = None

        record['address'] = strip_unit(clean_address(record['address']))
        if record['city'] not in self.city_names:
            raise SkipRecord('Skipping city %s' % record['city'])
        record['city'] = record['city'].title()
        return record

    def existing_record(self, record):
        # To determine previous records, we use the application number and
        # review date. There can be multiple records for a single application
        # number.
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            qs = qs.by_attribute(self.schema_fields['application_number'], record['application_number'])
            qs = qs.by_attribute(self.schema_fields['review_date'], record['review_date'])
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        application_type = self.get_or_create_lookup('application_type', list_record['application_type'], list_record['application_type'])
        facility_type = self.get_or_create_lookup('facility_type', list_record['facility_type'], list_record['facility_type'])
        status = self.get_or_create_lookup('status', list_record['status'], list_record['status'])

        title = u'%s applied for plan review' % list_record['business_name']
        values = {
            'title': title,
            'item_date': list_record['application_date'],
            'location_name': '%s, %s' % (list_record['address'], list_record['city']),
        }
        attributes = {
            'file_number': list_record['file_number'],
            'application_number': list_record['application_number'],
            'application_type': application_type.id,
            'business_name': list_record['business_name'],
            'facility_type': facility_type.id,
            'license_number': list_record['license_number'],
            'review_date': list_record['review_date'],
            'status': status.id,
        }
        if old_record is None:
            self.create_newsitem(attributes, **values)
        else:
            self.update_existing(old_record, values, attributes)

class MiamiScraper(Scraper):
    def __init__(self):
        city_names = ['MIAMI', 'AVENTURA', 'BAL HARBOUR', 'BAY HARBOR ISLANDS',
            'BISCAYNE PARK', 'CORAL GABLES', 'CUTLER BAY', 'DORAL', 'EL PORTAL',
            'FLORIDA CITY', 'GOLDEN BEACH', 'HIALEAH', 'HIALEAH GARDENS',
            'HOMESTEAD', 'INDIAN CREEK VILLAGE', 'ISLANDIA', 'KEY BISCAYNE',
            'MEDLEY', 'MIAMI BEACH', 'MIAMI GARDENS', 'MIAMI LAKES',
            'MIAMI SHORES', 'MIAMI SPRINGS', 'NORTH BAY VILLAGE', 'NORTH MIAMI',
            'NORTH MIAMI BEACH', 'OPA-LOCKA', 'PALMETTO BAY', 'PINECREST',
            'SOUTH MIAMI', 'SUNNY ISLES BEACH', 'SURFSIDE', 'SWEETWATER',
            'VIRGINIA GARDENS', 'WEST MIAMI']
        super(MiamiScraper, self).__init__(city_names)

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    MiamiScraper().update()
