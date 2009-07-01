"""
Screen scraper for Washington state liquor-license data.
http://www.liq.wa.gov/Media_Releases/MediaReleasesCountyMap.asp

Our scraper works by submitting a form for a particular city, but
note that the entire state's licenses are in one place here:
http://www.liq.wa.gov/Media_Releases/EntireStateWeb.asp
"""

from django.core.serializers.json import DjangoJSONEncoder
from ebdata.retrieval.scrapers.base import ScraperBroken
from ebdata.retrieval.scrapers.list_detail import SkipRecord
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.geocoder.parser.parsing import strip_unit
from ebpub.utils.dates import parse_date
from ebpub.utils.text import clean_address
from lxml.html import document_fromstring
from lxml import etree
import re

def rows(table):
    # Yields lists of strings, with a string representing a <td>/<th> and
    # a list representing a <tr>.
    for tr in etree.XPath('tr')(table):
        yield [col.text_content() for col in etree.XPath('td | th')(tr)]

def clean_washington_address(add, city):
    add = add.replace(u'\xa0', ' ')
    add = re.sub(r',\s+%s,\s+WA.*$' % city, '', add)
    add = clean_address(add)
    return add, strip_unit(add).strip()

class LiquorLicenseScraper(NewsItemListDetailScraper):
    schema_slugs = ('liquor-licenses',)
    has_detail = False

    def __init__(self, county, city):
        super(LiquorLicenseScraper, self).__init__(use_cache=False)
        self.license_county, self.license_city = county, city

    def list_pages(self):
        # Note that we scrape the HTML instead of the Excel file because the
        # Excel file cannot be read properly by our Excel library:
        #    xlrd.biffh.XLRDError: Expected BOF record; found 0x0a0d
        url = 'http://www.liq.wa.gov/Media_Releases/MediaReleasesReport3Excel.asp'
        data = {
            'hiddenCounty': self.license_county,
            'cboCity': self.license_city,
            'radFormat': 'on',
            'txtFormat': 'Web',
        }
        yield self.get_html(url, data)

    def parse_list(self, html):
        xml = document_fromstring(html)

        # The record headers (e.g., "Notification Date", "Application Type")
        # have trailing colons, so this regex removes those. It also removes
        # leading backslash characters, which show up very rarely.
        unwanted_characters = re.compile(r'^\\?\s*|:$')

        for table in etree.XPath('//table')(xml)[1:]:
            full_record = {}
            category = None
            for i, row in enumerate(rows(table)):
                row = [val.strip() for val in row]
                if i == 0: # The first row has the category, e.g. "SEATTLE NEW LIQUOR LICENSE APPLICATIONS".
                    category = row[0]
                    full_record['category'] = category
                elif len(row) < 2 or ''.join(row) == '':
                    # New data block.
                    if len(full_record) > 1:
                        yield full_record
                    full_record = {'category': category}
                else:
                    full_record[unwanted_characters.sub('', row[0])] = row[1]
            if len(full_record) > 1:
                yield full_record

    def clean_list_record(self, record):
        record['category'] = record['category'].replace(u'\xa0', ' ').replace(self.license_city + ' ', '')

        try:
            add = record.pop('Business Location')
        except KeyError:
            add = record.pop('Current Business Location')
        record['address'], record['clean_address'] = clean_washington_address(add, self.license_city)
        if 'New Business Location' in record:
            record['new_address'] = clean_washington_address(record.pop('New Business Location'), self.license_city)[0]
        else:
            record['new_address'] = ''

        if 'Discontinued Date' in record:
            record['item_date'] = parse_date(record.pop('Discontinued Date'), '%m/%d/%Y')
        elif 'Approved Date' in record:
            record['item_date'] = parse_date(record.pop('Approved Date'), '%m/%d/%Y')
        elif 'Notification Date' in record:
            record['item_date'] = parse_date(record.pop('Notification Date'), '%m/%d/%Y')
        else:
            raise ScraperBroken("Didn't find a date in %r" % record)

        if 'Business Name' in record:
            record['business_name'] = record.pop('Business Name')
        elif 'Current Business Name' in record:
            record['business_name'] = record.pop('Current Business Name')
        else:
            record['business_name'] = ''

        if 'Applicant(s)' in record:
            record['applicant'] = record.pop('Applicant(s)')
        elif 'Current Applicant(s)' in record:
            record['applicant'] = record.pop('Current Applicant(s)')
        else:
            record['applicant'] = ''

        record['new_business_name'] = record.pop('New Business Name', '')
        record['new_applicant'] = record.pop('New Applicant(s)', '')

        license_types = record['Liquor License Type'].split('; ')
        license_types = [re.sub(r'^\d+,\s+', '', lt) for lt in license_types]
        record['license_types'] = [re.sub('^DIRECT SHIPMENT RECEIVER-(?:IN/OUT WA|IN WA ONLY)$', 'DIRECT SHIPMENT RECEIVER', lt) for lt in license_types]

        try:
            record['title'] = {
                ('DISCONTINUED LIQUOR LICENSES', 'DISCONTINUED'): u'Liquor license discontinued for %s',
                ('NEW LIQUOR LICENSE APPLICATIONS', 'ASSUMPTION'): u'%s applied to assume license',
                ('NEW LIQUOR LICENSE APPLICATIONS', 'NEW APPLICATION'): u'%s applied for new liquor license',
                ('NEW LIQUOR LICENSE APPLICATIONS', 'ADDED/CHANGE OF CLASS/IN LIEU'): u'%s applied for additional liquor license class',
                ('NEW LIQUOR LICENSE APPLICATIONS', 'ADDED/CHANGE OF TRADENAME'): u'%s applied for trade name change',
                ('NEW LIQUOR LICENSE APPLICATIONS', 'CHANGE OF CORPORATE NAME'): u'%s applied for corporate name change',
                ('NEW LIQUOR LICENSE APPLICATIONS', 'CHANGE OF CORPORATE OFFICER'): u'%s applied to add or remove a corporate officer',
                ('NEW LIQUOR LICENSE APPLICATIONS', 'CHANGE OF LOCATION'): u'%s applied for change of location',
                ('NEW LIQUOR LICENSE APPLICATIONS', 'CHANGE OF LLC MEMBER'): u'%s applied to add or remove an LLC member',
                ('NEW LIQUOR LICENSE APPLICATIONS', 'IN LIEU'): u'%s applied to change liquor license class',
                ('RECENTLY APPROVED LIQUOR LICENSES', 'ADDED FEES'): u'%s approved for addition of fees',
                ('RECENTLY APPROVED LIQUOR LICENSES', 'ASSUMPTION'): u'%s approved to assume license',
                ('RECENTLY APPROVED LIQUOR LICENSES', 'NEW APPLICATION'): u'%s approved for new liquor license',
                ('RECENTLY APPROVED LIQUOR LICENSES', 'ADDED/CHANGE OF CLASS/IN LIEU'): u'%s approved for additional liquor license class',
                ('RECENTLY APPROVED LIQUOR LICENSES', 'ADDED/CHANGE OF TRADENAME'): u'%s approved for trade name change',
                ('RECENTLY APPROVED LIQUOR LICENSES', 'CHANGE OF CORPORATE NAME'): u'%s approved for corporate name change',
                ('RECENTLY APPROVED LIQUOR LICENSES', 'CHANGE OF CORPORATE OFFICER'): u'%s approved to add or remove a corporate officer',
                ('RECENTLY APPROVED LIQUOR LICENSES', 'CHANGE OF LOCATION'): u'%s approved for change of location',
                ('RECENTLY APPROVED LIQUOR LICENSES', 'CHANGE OF LLC MEMBER'): u'%s approved to add or remove an LLC member',
                ('RECENTLY APPROVED LIQUOR LICENSES', 'IN LIEU'): u'%s approved to change liquor license class',
            }[(record['category'], record['Application Type'])]
        except KeyError:
            self.logger.warn('Got unsupported combo %r and %r', record['category'], record['Application Type'])
            raise SkipRecord
        record['title'] = record['title'] % record['business_name']

        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=record['item_date'])
            qs = qs.by_attribute(self.schema_fields['license_number'], record['License Number'])
            qs = qs.by_attribute(self.schema_fields['application_type'], record['Application Type'], is_lookup=True)
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            return

        application_type = self.get_or_create_lookup('application_type', list_record['Application Type'], list_record['Application Type'])
        license_types = [self.get_or_create_lookup('license_type', lt, lt, make_text_slug=False) for lt in list_record['license_types']]
        category = self.get_or_create_lookup('category', list_record['category'], list_record['category'], make_text_slug=False)

        json_data = {
            'business_name': list_record['business_name'],
            'new_business_name': list_record['new_business_name'],
            'new_address': list_record['new_address'],
        }

        attributes = {
            'applicant': list_record['applicant'],
            'new_applicant': list_record['new_applicant'],
            'license_number': list_record['License Number'],
            'category': category.id,
            'application_type': application_type.id,
            'license_type': ','.join([str(lt.id) for lt in license_types]),
            'details': DjangoJSONEncoder().encode(json_data),
        }
        self.create_newsitem(
            attributes,
            title=list_record['title'],
            item_date=list_record['item_date'],
            location_name=list_record['clean_address'],
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    LiquorLicenseScraper('King', 'SEATTLE').update()
