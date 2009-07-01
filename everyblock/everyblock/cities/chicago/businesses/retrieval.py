"""
Screen scraper for City of Chicago Business License Holders data.
http://webapps.cityofchicago.org/lic/iris.jsp
"""

from ebdata.retrieval.scrapers.list_detail import SkipRecord
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
from ebpub.utils.text import clean_address
import re

strip_tags = lambda x: re.sub(r'(?s)</?[^>]*>', '', x).replace('&nbsp;', ' ').strip()

# List of DBAs to skip, due to privacy reasons or whatever else.
SKIPPED_DBAS = set([
    'SHALVA', # Domestic abuse center; sensitive address
])

class BusinessLicense(NewsItemListDetailScraper):
    schema_slugs = ('business-licenses',)
    parse_list_re = re.compile(r'(?si)<tr>\s*<td width="115"[^>]*>(?P<address>.*?)</td>\s*<td[^>]*>(?P<dba>.*?)</td>\s*<td[^>]*>(?P<structure>.*?)</td>\s*<td[^>]*>(?P<ward>.*?)</td>\s*<td[^>]*>(?P<precinct>.*?)</td>\s*<td[^>]*>.*?</td>\s*<td[^>]*>.*?callLic\((?P<city_id>\d+),(?P<site_id>\d+)')

    def __init__(self, wards=None):
        super(BusinessLicense, self).__init__()
        self.wards = wards or xrange(1, 51)

    def list_pages(self):
        next_offset = re.compile(r'(?si)<a href="irisresult\.jsp\?firstRow=(\d+)&newSearch=f">Next\s+Page').search
        for ward in self.wards:
            # For the first page, submit a search.
            data = {'str_nbr': '', 'str_nbr2': '', 'str_direction': '', 'str_nm': '', 'str_type_cde': '',
                    'dba_txt': '', 'ward_cde': str(ward), 'precinct_cde': ''}
            html = self.get_html('http://webapps.cityofchicago.org/lic/irisresult.jsp?newSearch=t', data)

            # For subsequent pages, just submit the row offset. The rest of
            # the search is saved in a cookie. Get the row offset by parsing
            # each result page.
            while 1:
                yield html
                m = next_offset(html)
                if not m:
                    break # No more "Next page" link.
                offset = m.group(1)
                html = self.get_html('http://webapps.cityofchicago.org/lic/irisresult.jsp?firstRow=%s&newSearch=f' % offset)

    def clean_list_record(self, record):
        for k, v in record.items():
            v = strip_tags(v)
            record[k] = re.sub(r'(?s)\s\s+', ' ', v).strip()

        # Remove the "Suite/Apt" or "Floor" clause from the address, if it exists.
        record['address'] = record['address'].replace(' ,', ',')
        m = re.search(r'^(.*?), (?:Suite/Apt|Floor):.*$', record['address'])
        if m:
            record['address'] = m.group(1)
        record['address'] = clean_address(record['address'])

        if record['dba'] in SKIPPED_DBAS:
            raise SkipRecord('Skipping %r' % record['dba'])

        # For privacy reasons, skip individuals.
        if record['structure'].upper().strip() == 'INDIVIDUAL':
            raise SkipRecord('Skipping structure=individual')

        record['city_id'] = int(record['city_id'])
        record['site_id'] = int(record['site_id'])
        return record

    def existing_record(self, record):
        qs = NewsItem.objects.filter(schema__id=self.schema.id)
        qs = qs.by_attribute(self.schema_fields['city_id'], record['city_id'])
        qs = qs.by_attribute(self.schema_fields['site_id'], record['site_id'])
        records = {}
        for ni in qs:
            # We need the license type and both dates to uniquely identify a
            # particular license for a business.
            key = (ni.attributes['license'], ni.item_date, ni.attributes['expiration_date'])
            records[key] = ni
        return records

    def detail_required(self, list_record, old_record):
        return True # Detail is always required, unfortunately.

    def get_detail(self, record):
        return self.get_html('http://webapps.cityofchicago.org/lic/irislic.jsp?acct_nbr=%s&site_nbr=%s' % \
            (record['city_id'], record['site_id']))

    def parse_detail(self, page, list_record):
        licenses = []
        for record in re.finditer(r'(?si)<tr>\s*<td[^>]*>(?P<license>.*?)</td>\s*<td[^>]*>(?P<issue_date>.*?)</td>\s*<td[^>]*>(?P<expiration_date>.*?)</td>', page):
            data = record.groupdict()

            # For privacy reasons, skip street performers and peddlers.
            normalized_license = data['license'].upper().strip()
            if (normalized_license == 'STREET PERFORMER') or ('PEDDLER' in normalized_license):
                continue

            for k, v in data.items():
                data[k] = strip_tags(v)
            licenses.append(data)
        return {'licenses': licenses[1:]} # Skip first row (the header)

    def clean_detail_record(self, record):
        for i, license in enumerate(record['licenses']):
            license['issue_date'] = license['issue_date'] != 'null' and parse_date(license['issue_date'], '%m/%d/%Y') or None
            license['expiration_date'] = license['expiration_date'] != 'null' and parse_date(license['expiration_date'], '%m/%d/%Y') or None
            if license['issue_date'] is None:
                del record['licenses'][i] # If the issue date is empty, just drop it.
        return record

    def save(self, old_record, list_record, detail_record):
        structure = self.get_or_create_lookup('structure', list_record['structure'], list_record['structure'])
        title = list_record['dba']

        for license in detail_record['licenses']:
            license_type = self.get_or_create_lookup('license', license['license'], license['license'])
            if license_type.name.upper().strip() == 'HOME OCCUPATION':
                continue # Skip "Home Occupation"
            new_attributes = {
                'license': license_type.id,
                'expiration_date': license['expiration_date'],
                'structure': structure.id,
                'dba': list_record['dba'],
                'city_id': list_record['city_id'],
                'site_id': list_record['site_id'],
            }

            key = (license_type.id, license['issue_date'], license['expiration_date'])
            if not old_record.has_key(key) \
                    or old_record[key].item_date != license['issue_date'] \
                    or old_record[key].attributes['expiration_date'] != license['expiration_date']:
                self.create_newsitem(
                    new_attributes,
                    title=title,
                    description=u'The business was issued a license of type "%s".' % license_type.name,
                    url='http://webapps.cityofchicago.org/lic/iris.jsp',
                    item_date=license['issue_date'],
                    location_name=list_record['address'],
                )
            else:
                # This business already exists in our database, but check
                # whether any of the values have changed.
                new_values = {'title': title, 'location_name': list_record['address']}
                self.update_existing(old_record[key], new_values, new_attributes)

if __name__ == "__main__":
    s = BusinessLicense()
    s.update()
