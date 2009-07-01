"""
Scraper for Florida restaurant inspections.
http://www.myfloridalicense.com/dbpr/sto/file_download/hr_food_service_inspection.shtml
"""

from django.core.serializers.json import DjangoJSONEncoder
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
from ebpub.utils.text import clean_address
from everyblock.states.florida.myflorida import MyFloridaScraper

class Scraper(MyFloridaScraper):
    schema_slugs = ('restaurant-inspections',)
    has_detail = False

    florida_csv_fieldnames = ('district', 'county_number', 'county_name',
        'license_type_code', 'license_number', 'business_name', 'address',
        'city', 'zip', 'inspection_number', 'visit_number', 'inspection_class',
        'inspection_type', 'disposition', 'inspection_date',
        'critical_violations', 'noncritical_violations', 'total_violations',
        'pda_status', 'vio1', 'vio2', 'vio3', 'vio4', 'vio5', 'vio6', 'vio7',
        'vio8', 'vio9', 'vio10', 'vio11', 'vio12', 'vio13', 'vio14', 'vio15',
        'vio16', 'vio17', 'vio18', 'vio19', 'vio20', 'vio21', 'vio22', 'vio23',
        'vio24', 'vio25', 'vio26', 'vio27', 'vio28', 'vio29', 'vio30', 'vio31',
        'vio32', 'vio33', 'vio34', 'vio35', 'vio36', 'vio37', 'vio38', 'vio39',
        'vio40', 'vio41', 'vio42', 'vio43', 'vio44', 'vio45', 'vio46', 'vio47',
        'vio48', 'vio49', 'vio50', 'vio51', 'vio52', 'vio53', 'vio54', 'vio55',
        'vio56', 'vio57', 'vio58', 'license_id', 'inspection_visit_id')

    def __init__(self, city_names, district):
        # city_names should be a list of uppercase strings like 'MIAMI'.
        # district should be an integers
        super(Scraper, self).__init__()
        self.city_names = set(city_names)
        self.florida_ftp_filename = '%sfdinspi.exe' % district

    def clean_list_record(self, record):
        # Collapse the violations into a single value, rather than 58 values,
        # most of which are zero.
        num_violations = []
        for i in range(1, 59):
            val = int(record.pop('vio%s' % i))
            if val:
                num_violations.append((str(i), val))
        record['violations'] = num_violations

        record['inspection_date'] = parse_date(record['inspection_date'], '%m/%d/%Y')
        record['address'] = clean_address(record['address'])

        if record['city'] not in self.city_names:
            raise SkipRecord('Skipping city %s' % record['city'])

        record['city'] = record['city'].title()
        record['visit_number'] = int(record['visit_number'])
        record['critical_violations'] = int(record['critical_violations'])
        record['noncritical_violations'] = int(record['noncritical_violations'])
        record['total_violations'] = int(record['total_violations'])
        record['inspection_number'] = int(record['inspection_number'])

        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            qs = qs.by_attribute(self.schema_fields['inspection_visit_id'], record['inspection_visit_id'])
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        license_type = self.get_or_create_lookup('license_type', list_record['license_type_code'], list_record['license_type_code'], make_text_slug=False)
        disposition = self.get_or_create_lookup('disposition', list_record['disposition'], list_record['disposition'], make_text_slug=False)
        violation_lookups = [self.get_or_create_lookup('violation', v[0], v[0], make_text_slug=False) for v in list_record['violations']]
        violation_lookup_text = ','.join([str(v.id) for v in violation_lookups])

        v_lookup_dict = dict([(v.code, v.id) for v in violation_lookups])
        v_list = [{'lookup_id': v_lookup_dict[code], 'number': number} for code, number in list_record['violations']]
        details_json = DjangoJSONEncoder().encode(v_list)

        title = u'%s inspected: %s violation%s' % (list_record['business_name'], list_record['total_violations'], list_record['total_violations'] != 1 and 's' or '')

        values = {
            'title': title,
            'item_date': list_record['inspection_date'],
            'location_name': '%s, %s' % (list_record['address'], list_record['city']),
        }
        attributes = {
            'inspection_visit_id': list_record['inspection_visit_id'],
            'license_id': list_record['license_id'],
            'license_number': list_record['license_number'],
            'business_name': list_record['business_name'],
            'inspection_number': list_record['inspection_number'],
            'license_type': license_type.id,
            'critical_violations': list_record['critical_violations'],
            'noncritical_violations': list_record['noncritical_violations'],
            'total_violations': list_record['total_violations'],
            'visit_number': list_record['visit_number'],
            'disposition': disposition.id,
            'violation': violation_lookup_text,
            'violation_details': details_json,
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
        super(MiamiScraper, self).__init__(city_names, 1)

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    s = MiamiScraper()
    s.update()
