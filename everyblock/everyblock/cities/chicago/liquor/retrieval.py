"""
Screen scraper for City of Chicago liquor-license application data.
https://webapps.cityofchicago.org/liqppa/liqppa.jsp?liqppa=liq
"""

from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebdata.retrieval.utils import norm_dict_space
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
import re

SOURCE_URL = 'https://webapps.cityofchicago.org/liqppa/liqppa.jsp?liqppa=liq'

class LiquorLicenseApplication(NewsItemListDetailScraper):
    schema_slugs = ('liquor-license-applications',)
    has_detail = False
    parse_list_re = re.compile(r'<tr.*?<font size="2" face="Arial, Helvetica, sans-serif">(?P<legal_name>.*?)</font>.*?<font size="2" face="Arial, Helvetica, sans-serif">(?P<dba>.*?)</font>.*?<font size="2" face="Arial, Helvetica, sans-serif">(?P<address_raw>.*?)</font>.*?<font size="2" face="Arial, Helvetica, sans-serif">(?P<license>.*?)</font>.*?<font size="2" face="Arial, Helvetica, sans-serif">(?P<start_date>.*?)</font>.*?<font size="2" face="Arial, Helvetica, sans-serif">(?P<application_date>.*?)</font>.*?<a href="Javascript:callOwner\((?P<city_business_id>\d+),', re.IGNORECASE | re.MULTILINE | re.DOTALL)

    def list_pages(self):
        yield self.get_html(SOURCE_URL)

    def clean_list_record(self, record):
        norm_dict_space(record, 'legal_name', 'address_raw', 'license', 'dba', 'start_date', 'application_date')
        record['dba'], record['business_type'] = record['dba'].rsplit(' - ', 1)
        record['start_date'] = parse_date(record['start_date'], '%m/%d/%Y')
        record['application_date'] = parse_date(record['application_date'], '%m/%d/%Y')

        # Remove the "Suite/Apt" or "Floor" clause from the address, if it exists.
        record['address_raw'] = record['address_raw'].replace(' ,', ',')
        m = re.search(r'^(.*?), (?:Suite/Apt|Floor):.*$', record['address_raw'])
        if m:
            record['address_raw'] = m.group(1)

        return record

    def existing_record(self, record):
        try:
            return NewsItem.objects.filter(schema__id=self.schema.id, item_date=record['application_date']).by_attribute(self.schema_fields['legal_name'], record['legal_name'])[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            # Liquor license applications never change, so we don't have to
            # worry about changing applications that already exist.
            self.logger.debug('Application already exists')
            return

        license = self.get_or_create_lookup('license', list_record['license'], list_record['license'])
        business_type = self.get_or_create_lookup('business_type', list_record['business_type'], list_record['business_type'])

        attributes = {
            'city_business_id': list_record['city_business_id'],
            'legal_name': list_record['legal_name'],
            'dba': list_record['dba'],
            'business_type': business_type.id,
            'license': license.id,
            'start_date': list_record['start_date'],
        }
        self.create_newsitem(
            attributes,
            title=list_record['legal_name'],
            description=u'%s applied for a license of type "%s."' % (list_record['legal_name'], license.name),
            url=SOURCE_URL,
            pub_date=list_record['application_date'],
            item_date=list_record['application_date'],
            location_name=list_record['address_raw'],
        )

if __name__ == "__main__":
    LiquorLicenseApplication().update()
