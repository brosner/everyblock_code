"""
Screen scraper for California liquor-license data.
http://www.abc.ca.gov/datport/SubscrMenu.asp
"""

from ebdata.retrieval.scrapers.base import ScraperBroken
from ebdata.retrieval.scrapers.list_detail import SkipRecord
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
import re

GEOCODES = {
    'la': 1993,
    'sf': 3800,
    'sanjose': 4313,
}

license_types_re = re.compile(r'(?si)<b>\d\) License Type:</b> (?P<license_type>.*?)</td></tr><tr><td><b>\s*License Type Status:</b>  (?P<license_type_status>.*?)</td></tr><tr><td><b>\s*Status Date: </b> (?P<status_date>.*?) <b>\s*Term: (?P<term>.*?)</td></tr><tr><td><b>\s*Original Issue Date: </b> (?P<original_issue_date>.*?) <b>\s*Expiration Date: </b> (?P<expiration_date>.*?) </tr><tr><td><b>\s*Master: </b> (?P<master>.*?)\s*<b>\s*Duplicate: </b> (?P<duplicate>.*?) <b>\s*Fee Code: </b> (?P<fee_code>.*?)</td></tr>')

detail_url = lambda page_id: 'http://www.abc.ca.gov/datport/LQSdata.asp?ID=%s' % page_id

class LiquorLicenseScraper(NewsItemListDetailScraper):
    """
    A base class that encapsulates how to scrape California liquor licenses.

    Do not instantiate this class directly; use one of the subclasses.
    """
    schema_slugs = ('liquor-licenses',)
    has_detail = True
    parse_detail_re = re.compile(r'(?si)License Number:  </b>.*? <b>\s*Status:  </b>(?P<status>.*?)</td></tr><tr><td><b>Primary Owner:  </b>(?P<primary_owner>.*?)</td></tr><td><b>ABC Office of Application:  </b>(?P<office_of_application>.*?)</td></tr></tr><tr><td bgcolor=#260066 class=header><font color=white> <b>Business Name </font></b></td></tr>(?P<business_name>.*?)<tr><td bgcolor=#260066 class=header><font color=white> <b>Business Address </font></b></td><td bgcolor=#260066 class=header></td></tr><tr><td><b>Address: </b>(?P<address>.*?)<b>Census Tract: </b>(?P<census_tract>.*?)</td></tr><tr><td><b>City: </b>(?P<city>.*?)     <b>County: </b>(?P<county>.*?)</td></tr><tr><td><b>State: </b>(?P<state>.*?)     <b>Zip Code: </b>(?P<zipcode>.*?)</td></tr><tr><td bgcolor=#260066 class=header><font color=white> <b>Licensee Information </font></b></td></tr><tr><td><b>Licensee: </b>.*?</td></tr><tr><td bgcolor=#260066 class=header><font color=white> <B>License Types </font></b></td></tr><tr><td>(?P<license_types>.*?)<tr><td bgcolor=#260066 class=header><font color=white> <b>Current Disciplinary Action </font>')

    def parse_list(self, page):
        page = page.replace('&nbsp;', ' ')

        # First, get the report date by looking for "Report as of XXXX".
        m = re.search(r'(?i)report as of (\w+ \d\d?, \d\d\d\d)</U>', page)
        if not m:
            raise ScraperBroken('Could not find "Report as of" in page')
        report_date = parse_date(m.group(1), '%B %d, %Y')

        # Determine the headers by looking at the <th> tags, and clean them up
        # to match our style for keys in the list_record dictionary (lower
        # case, underscores instead of spaces).
        headers = [h.lower() for h in re.findall('(?i)<th[^>]*>(?:<a[^>]+>)?\s*(.*?)\s*(?:</a>)?</th>', page)]
        headers = [h.replace('<br>', ' ') for h in headers]
        headers = [re.sub(r'[^a-z]', ' ', h) for h in headers]
        headers = [re.sub(r'\s+', '_', h.strip()) for h in headers]

        # Dynamically construct a regex based on the number of headers.
        # Note that this assumes that at most *one* of the headers has an
        # empty name; if more than one header has an empty name, this regex
        # will have multiple named groups with the same name, which will cause
        # an error.
        pattern = '(?si)<tr valign=top class=report_column>%s</tr>'% '\s*'.join(['\s*<td[^>]*>\s*(?:<center>)?\s*(?P<%s>.*?)\s*(?:</center>)?\s*</td[^>]*>\s*' % (h or 'number') for h in headers])
        for record in re.finditer(pattern, page):
            yield dict(record.groupdict(), report_date=report_date)

    def clean_list_record(self, record):
        try:
            license_number = record.pop('license_num')
        except KeyError:
            license_number = record.pop('license_number')
        m = re.search(r'(?i)<a href=.*?LQSdata\.asp\?ID=(\d+)>\s*(\d+)\s*</a>', license_number)
        if not m:
            raise ScraperBroken('License number link not found in %r' % license_number)
        record['place_id'], record['license_number'] = m.groups()
        return record

    def get_detail(self, record):
        url = detail_url(record['place_id'])
        return self.get_html(url)

    def parse_detail(self, page, list_record):
        # They use a ton of &nbsp;s for some reason, so convert them to spaces
        # to make the parse_detail_re regex more readable.
        page = page.replace('&nbsp;', ' ')
        return NewsItemListDetailScraper.parse_detail(self, page, list_record)

    def clean_detail_record(self, record):
        if 'No Active DBA found' in record['business_name']:
            record['business_name'] = ''
        else:
            m = re.search(r'(?si)<tr><td><b>Doing Business As: </b>(.*?)</td></tr>', record['business_name'])
            if not m:
                raise ScraperBroken('Got unknown business_name value %r' % record['business_name'])
            record['business_name'] = m.group(1)
        record['address'] = record['address'].strip()

        # There can be multiple license types, so this requires further parsing
        # to create a list.
        license_types = []
        for m in license_types_re.finditer(record['license_types']):
            d = m.groupdict()
            d['status_date'] = parse_date(d['status_date'], '%d-%b-%Y')
            if not d['status_date']:
                # Skip license types that don't have a status date, because
                # a NewsItem is required to have an item_date, and we don't
                # care about licenses that don't have a change date.
                continue
            d['original_issue_date'] = parse_date(d['original_issue_date'], '%d-%b-%Y')
            d['expiration_date'] = parse_date(d['expiration_date'], '%d-%b-%Y')
            d['term'] = d['term'].replace('</B>', '').strip()
            license_types.append(d)
        record['license_types'] = license_types

        return record

    def existing_record(self, record):
        # We don't have enough information from the list_record to determine
        # whether this record exists.
        return None

    def detail_required(self, list_record, old_record):
        # Always download the detail page.
        return True

    def save(self, old_record, list_record, detail_record):
        # Each status change only applies to a single license type (e.g.
        # "Winegrower"). The list page says which license type we're interested
        # in, but only the detail page has the description, so we have to use
        # one to look up the other.
        try:
            license = [t for t in detail_record['license_types'] if t['license_type'][:2] == list_record['type']][0]
        except IndexError:
            raise ScraperBroken('License type %r not found on detail page' % list_record['type'])

        license_type = self.get_or_create_lookup('type', license['license_type'][5:], list_record['type'])
        status = self.get_or_create_lookup('status', license['license_type_status'], license['license_type_status'])
        if not list_record.has_key('action'):
            list_record['action'] = '' # Status changes do not have actions
        action = self.get_or_create_lookup('action', list_record['action'], list_record['action'])

        if self.record_type.code == 'STATUS_CHANGE':
            old_status = self.get_or_create_lookup('old_status', list_record['status_from'], list_record['status_from'])
            new_status = self.get_or_create_lookup('new_status', list_record['status_to'], list_record['status_to'])
        else:
            # New licesnses and new application have no old status.
            old_status = self.get_or_create_lookup('old_status', 'None', 'NONE')
            new_status = self.get_or_create_lookup('new_status', list_record['status'], list_record['status'])

        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=list_record['report_date'])
            qs = qs.by_attribute(self.schema_fields['page_id'], list_record['place_id'])
            qs = qs.by_attribute(self.schema_fields['type'], license_type.id)

            if self.record_type.code == 'STATUS_CHANGE':
                qs = qs.by_attribute(self.schema_fields['old_status'], old_status.id)
                qs = qs.by_attribute(self.schema_fields['new_status'], new_status.id)
            else:
                qs = qs.by_attribute(self.schema_fields['action'], action.id)

            old_record = qs[0]
        except IndexError:
            pass
        else:
            return # No need to save again, if this record already exists.

        title = '%s for %s' % (self.record_type.name, detail_record['business_name'] or detail_record['primary_owner'])

        attributes = {
            'page_id': list_record['place_id'],
            'address': detail_record['address'],
            'business_name': detail_record['business_name'],
            'original_issue_date': license['original_issue_date'],
            'expiration_date': license['expiration_date'],
            'type': license_type.id,
            'status': status.id,
            'license_number': list_record['license_number'],
            'primary_owner': detail_record['primary_owner'],
            'action': action.id,
            'record_type': self.record_type.id,
            'old_status': old_status.id,
            'new_status': new_status.id,
        }
        self.create_newsitem(
            attributes,
            title=title,
            url=detail_url(list_record['place_id']),
            item_date=license['status_date'],
            location_name=detail_record['address'],
        )

class NewIssuedLicenseScraper(LiquorLicenseScraper):
    def __init__(self, geo_code):
        # geo_code is a numeric code describing the part of California we're
        # interested in. For all the choices, see page three of this PDF:
        # http://www.abc.ca.gov/datport/ABC_Data_Layout.PDF
        LiquorLicenseScraper.__init__(self)
        self.geo_code = str(geo_code)
        self.record_type = self.get_or_create_lookup('record_type', 'New license issued', 'ISSUED')

    def list_pages(self):
        yield self.get_html('http://www.abc.ca.gov/datport/SubscrOption.asp', {'SUBCRIT': 'p_DlyIssApp'})

    def clean_list_record(self, record):
        if record['geo_code'] != self.geo_code:
            raise SkipRecord
        record = LiquorLicenseScraper.clean_list_record(self, record)
        record['type'], record['dup'] = record.pop('type_dup').split('/')
        record['expir_date'] = parse_date(record['expir_date'], '%m/%d/%Y')
        return record

class NewApplicationScraper(LiquorLicenseScraper):
    def __init__(self, geo_code):
        LiquorLicenseScraper.__init__(self)
        self.geo_code = str(geo_code)
        self.record_type = self.get_or_create_lookup('record_type', 'New application', 'APPLICATION')

    def list_pages(self):
        yield self.get_html('http://www.abc.ca.gov/datport/SubscrOption.asp', {'SUBCRIT': 'p_DlyNuApp'})

    def clean_list_record(self, record):
        if record['geo_code'] != self.geo_code:
            raise SkipRecord
        record = LiquorLicenseScraper.clean_list_record(self, record)
        record['type'], record['dup'] = record.pop('type_dup').split('/')
        return record

class StatusChangeScraper(LiquorLicenseScraper):
    def __init__(self, geo_code):
        LiquorLicenseScraper.__init__(self)
        self.geo_code = str(geo_code)
        self.record_type = self.get_or_create_lookup('record_type', 'Status change', 'STATUS_CHANGE')

    def list_pages(self):
        yield self.get_html('http://www.abc.ca.gov/datport/SubscrOption.asp', {'SUBCRIT': 'p_DlyStat'})

    def clean_list_record(self, record):
        if record['geo_code'] != self.geo_code:
            raise SkipRecord
        record = LiquorLicenseScraper.clean_list_record(self, record)
        record['type'], record['dup'] = record.pop('type_dup').split('/')
        record['status_from'], record['status_to'] = record.pop('status_changed_from_to').split(' / ')
        record['transfer_info_from'], record['transfer_info_to'] = record.pop('transfer_info_from_to').split('/')
        record['orig_iss_date'] = parse_date(record['orig_iss_date'], '%m/%d/%Y')
        record['expir_date'] = parse_date(record['expir_date'], '%m/%d/%Y')
        return record

def update_newest(geo_code):
    # San Francisco is geo_code 3800. San Jose is 4313. LA is 1933.
    # You can get the geo_code for a city by looking here:
    # http://www.abc.ca.gov/datport/SubDlyNuRep.asp
    s = NewIssuedLicenseScraper(geo_code)
    s.update()
    s = NewApplicationScraper(geo_code)
    s.update()
    s = StatusChangeScraper(geo_code)
    s.update()

if __name__ == '__main__':
    import sys
    from ebdata.retrieval import log_debug
    try:
        geocode = GEOCODES[sys.argv[1]]
    except (KeyError, IndexError):
        print "Usage: retrieval.py %s" % '|'.join(GEOCODES.keys())
        sys.exit(0)
    update_newest(int(geocode))
