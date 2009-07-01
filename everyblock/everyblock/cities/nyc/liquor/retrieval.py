"""
Scraper for NYC liquor licenses.

http://www.trans.abc.state.ny.us/JSP/query/PublicQueryAdvanceSearchPage.jsp
"""

from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem, Location
from ebpub.streets.models import Misspelling
from ebpub.utils.text import smart_title
from dateutil.parser import parse
from lxml.html import document_fromstring
import datetime
import re

smart_business_title = lambda s: smart_title(s, ["LLC", "BBQ"])

nyc_counties = {
    "NEW": "New York",
    "KING": "Kings",
    "BRON": "Bronx",
    "RICH": "Richmond",
    "QUEE": "Queens"
}

class LiquorLicenseScraper(NewsItemListDetailScraper):
    schema_slugs = ('liquor-licenses',)
    uri = 'http://www.trans.abc.state.ny.us/servlet/ApplicationServlet'
    sleep = 0

    def __init__(self, *args, **kwargs):
        self.start_date = kwargs.pop('start_date', None)
        self.first_page = True # False once we've retreived the first list page
        self.failed_cities = {}
        super(LiquorLicenseScraper, self).__init__(*args, **kwargs)

    def list_pages(self):
        if self.start_date is None:
            self.start_date = datetime.datetime.now() - datetime.timedelta(days=7)

        for county in nyc_counties.keys():
            if self.first_page:
                html = self.get_html(self.uri, {
                    'category': 'NonePremise',
                    'city': '',
                    'county': county,
                    'dateType': 'rd', # Date received
                    'endDay': '1',
                    'endMonth': '1',
                    'endYear': '',
                    'licenseStatus': 'al',
                    'pageName': 'com.ibm.nysla.data.publicquery.PublicQueryAdvanceSearchPage',
                    'startDay': str(self.start_date.day),
                    'startMonth': str(self.start_date.month),
                    'startYear': str(self.start_date.year),
                    'validated': 'true',
                    'zipCode': '',
                })

                m = re.search(r'Displaying records \d+ - (\d+)', html)
                last_result_num = m.group(1)
                m = re.search(r'Found (\d+) matches', html)
                total = m.group(1)

                self.first_page = False
                yield html

            while 1:
                # next_list_page will return None when we reach the last page
                page = self.next_list_page()
                if page is None:
                    self.first_page = True
                    break
                yield page

    def next_list_page(self):
        html = self.get_html(self.uri, {
            'NextButton': '+Next+',
            'pageName': 'com.ibm.nysla.data.publicquery.PublicQueryAdvanceSearchPageResults',
            'validated': 'true'
        })
        m = re.search(r'Displaying records \d+ - (\d+)', html)
        last_result_num = m.group(1)
        m = re.search(r'Found (\d+) matches', html)
        total = m.group(1)
        print "%s/%s" % (last_result_num, total)
        if last_result_num == total:
            return None
        return html

    def parse_list(self, page):
        t = document_fromstring(page)
        for tr in t.xpath("//tr/td[@class='displayvalue']/parent::*"):
            record = {
                'name': tr[0][0].text_content().strip(),
                'url': tr[0][0].get('href'),
                'address': re.sub(r'[\r|\n|\t]+', ' ', tr[1].text_content()).strip(),
                'license_class': tr[2].text_content(),
                'license_type': tr[3].text_content(),
                'expiration_date': tr[4].text_content(),
                'status': tr[5].text_content()
            }
            record['serial_number'] = re.search(r'serialNumber=(\d+)&', record['url']).group(1)
            yield record

    def get_detail(self, list_record):
        return self.get_html('http://www.trans.abc.state.ny.us' + list_record['url'])

    def detail_required(self, list_record, old_record):
        return True

    def parse_detail(self, page, list_record):
        t = document_fromstring(page)
        record = {}
        for tr in t.xpath("//td[@class='displayvalue']/parent::*"):
            key = tr[1].text_content() or ''
            value = tr[2].text_content() or ''
            record[key.strip()] = value.strip()

        # If there's no filing date, this detail page is related to another
        # license. Go get the dates from that page.
        if not record.has_key('Filing Date:'):
            a = t.xpath("//div[@class='instructions']//a")[0]
            page = self.get_html('http://www.trans.abc.state.ny.us' + a.get('href'))
            t = document_fromstring(page)
            parent_record = {}
            for tr in t.xpath("//td[@class='displayvalue']/parent::*"):
                key = tr[1].text_content() or ''
                value = tr[2].text_content() or ''
                parent_record[key.strip()] = value.strip()
            dates = {
                'Filing Date:': parent_record['Filing Date:'],
                'Effective Date:': parent_record['Effective Date:'],
                'Expiration Date:': parent_record['Expiration Date:'],
            }
            record.update(dates)
        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            return qs.by_attribute(self.schema_fields['serial_number'], record['serial_number'])[0]
        except IndexError:
            return None

    def clean_list_record(self, record):
        return record

    def clean_detail_record(self, record):
        if not record.has_key('Filing Date:'):
            return None
        # dateutil.parser.parse will return the current date when given an empty
        # string, so we test for that here and set the cleaned dates to None
        # for empty strings rather than using parse.
        record['effective_date'] = record['Effective Date:'] and parse(record['Effective Date:'], fuzzy=True).date() or None
        record['expiration_date'] = record['Expiration Date:'] and parse(record['Expiration Date:'], fuzzy=True).date() or None
        record['filing_date'] = record['Filing Date:'] and parse(record['Filing Date:'], fuzzy=True).date() or None
        record['address'] = record['Address:'].split(' AKA ')[0]
	if record['address'] == '':
	    # No address. Bail out on cleaning.
	    return record
        record['address2'] = record['']
        record['premises_name'] = smart_business_title(record['Premises Name:'])
        record['city'] = re.match(r'([\w|\s]+), N', record['address2']).groups(1)[0].strip()
        # Normalize things like "Broadway At 65th Street, Manhattan" and
        # "351 353 West 14th Street, Manhattan"
        record['address'] = re.sub(r'(\d+)\s(\d+)', r'\1', record['address']).replace(' AT ', ' and ')

        record['city'] = record['city'].upper().strip()
        try:
            record['city'] = Misspelling.objects.get(incorrect=record['city']).correct
        except Misspelling.DoesNotExist:
            pass
        if record['city'] == 'NEW YORK':
            record['city'] = 'MANHATTAN'
        return record

    def save(self, old_record, list_record, detail_record):
        # Throw away records with no filing date. We need to draw a line
        # somewhere. That line is here.
        if detail_record['filing_date'] is None:
            return
        if detail_record['filing_date'] < datetime.date(2008, 1, 1):
            return
        if detail_record['address'] == '':
	    return
        # If we can't find the city in the locations table, skip this record.
        try:
            loc = Location.objects.select_related().get(normalized_name=detail_record['city'])
            # If we have a neighborhood, the city should be the borough.
            if loc.location_type.slug == 'neighborhoods':
                detail_record['city'] = loc.city
        except Location.DoesNotExist:
            self.failed_cities[detail_record['city']] = self.failed_cities.get(detail_record['city'], 0) + 1
            return

        status = self.get_or_create_lookup('status', detail_record['License Status:'], detail_record['License Status:'], make_text_slug=False)
        license_type = self.get_or_create_lookup('license_type', smart_title(detail_record['License Type:']), detail_record['License Type:'], make_text_slug=False)

        premises_name = detail_record['premises_name']
        pretty_date = detail_record['filing_date'].strftime('%B %d, %Y')
        title = 'Application for %s' % premises_name
        item_date = detail_record['filing_date']
        location_name = smart_title("%s, %s" % (detail_record['address'], detail_record['city']))
        attributes = {
            'serial_number': list_record['serial_number'],
            'effective_date': detail_record['effective_date'],
            'expiration_date': detail_record['expiration_date'],
            'premises_name': premises_name,
            'status': status.id,
            'license_type': license_type.id,
        }
        if old_record is None:
            self.create_newsitem(
                attributes,
                title=title,
                item_date=item_date,
                location_name=location_name,
                url='http://www.trans.abc.state.ny.us' + list_record['url']
            )
        else:
            # This license already exists in our database, but it may have
            # changed status, so save any new values.
            new_values = {
                'title': title,
                'item_date': item_date,
                'location_name': location_name,
            }
            self.update_existing(old_record, new_values, attributes)

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    scraper = LiquorLicenseScraper()
    scraper.update()
    print scraper.failed_cities
