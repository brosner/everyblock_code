"""
Scraper for Florida liquor licenses.
http://www.myflorida.com/dbpr/sto/file_download/file-download-ABandT.shtml
"""

from ebdata.retrieval.scrapers.list_detail import SkipRecord
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
from ebpub.utils.text import smart_title, clean_address
from everyblock.states.florida.myflorida import MyFloridaScraper
import datetime

class Scraper(MyFloridaScraper):
    schema_slugs = ('liquor-licenses',)
    has_detail = False

    florida_ftp_filename = 'daily.exe'
    florida_csv_filename = 'daily.txt'
    florida_csv_fieldnames = ('profession', 'county', 'license_number',
        'series_rank', 'class_modifier', 'dba', 'licensee', 'address',
        'address2', 'address3', 'city', 'state', 'zip_code', 'activity_date',
        'activity_code', 'activity_description')

    def __init__(self, *args, **kwargs):
        self.counties = kwargs.pop('counties', [])
        super(Scraper, self).__init__(*args, **kwargs)

    def list_pages(self):
        date = datetime.date(2008, 11, 6)
        while 1:
            if date >= datetime.date.today():
                break
            f = open('/home/jkocherhans/miami-liquor/%s.exe' % date.strftime('%Y-%m-%d'), 'rb')
            date = date + datetime.timedelta(days=1)
            yield f
            f.close()

    def clean_list_record(self, record):
        if record['county'].upper().strip() not in self.counties:
            raise SkipRecord('Record not in %s.' % self.counties)
        record['activity_date'] = parse_date(record['activity_date'], '%m/%d/%Y')
        record['dba'] = smart_title(record['dba'])
        record['address'] = clean_address(record['address'])
        return record

    def existing_record(self, record):
       try:
           qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=record['activity_date'])
           qs = qs.by_attribute(self.schema_fields['activity_code'], record['activity_code'])
           qs = qs.by_attribute(self.schema_fields['license_number'], record['license_number'])
           return qs[0]
       except IndexError:
           return None

    def save(self, old_record, list_record, detail_record):
        normalized_activity = "(%s) %s" % (list_record['activity_code'], list_record['activity_description'].upper().strip())
        activity = self.get_or_create_lookup('activity', normalized_activity, normalized_activity, make_text_slug=False)
        license_type = self.get_or_create_lookup('license_type', list_record['series_rank'], list_record['series_rank'], make_text_slug=False)
        attributes = {
            'license_number': list_record['license_number'],
            'licensee': list_record['licensee'],
            'dba': list_record['dba'],
            'activity': activity.id,
            'activity_code': list_record['activity_code'],
            'license_type': license_type.id,
        }
        values = {
            'title': '%s for %s' % (activity.name, list_record['dba']),
            'item_date': list_record['activity_date'],
            'location_name': list_record['address']
        }
        if old_record is None:
            self.create_newsitem(attributes, **values)
        else:
            self.update_existing(old_record, values, attributes)

class MiamiDadeScraper(Scraper):
    def __init__(self, *args, **kwargs):
        kwargs['counties'] = ('DADE',)
        super(MiamiDadeScraper, self).__init__(*args, **kwargs)

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    s = MiamiDadeScraper()
    s.update()
