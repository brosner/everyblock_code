"""
Screen scraper for Houston restaurant-inspection data
http://houston.tx.gegov.com/media/search.cfm
"""

from django.core.serializers.json import DjangoJSONEncoder
from ebdata.retrieval.scrapers.base import ScraperBroken
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
import datetime
import re

FACILITY_TYPES = (
    ('042', 'Assisted Living Centers'),
    ('120', 'Bakery - Retail'),
    ('121', 'Bakery - Wholesale'),
    ('062', 'Bar - Full Service'),
    ('060', 'Bar - Restricted'),
    ('061', 'Bar - Single Service'),
    ('080', 'Catering Establishment'),
    ('130', 'Commercial Food Processors - Non PHF Only'),
    ('131', 'Commercial Food Processors - PHF'),
    ('081', 'Commissary - Mobile Food Unit'),
    ('101', 'Convenience Grocery - Open foods'),
    ('100', 'Convenience Grocery - Packaged'),
    ('052', 'Day Care Center - Adults'),
    ('050', 'Day Care Center - Open Foods'),
    ('051', 'Day Care Center - Packaged Foods Only'),
    ('181', 'Food Pantry - Open Foods'),
    ('180', 'Food Pantry - Packaged'),
    # ('044', 'Halfway Houses'),
    ('040', 'Hospitals'),
    ('072', 'Mobile - Conventional, Restricted, Motorized'),
    ('073', 'Mobile - Conventional, Restricted, Non-motorized'),
    ('071', 'Mobile - Conventional, Unrestricted , Non-motorized'),
    ('070', 'Mobile - Conventional, Unrestricted, Motorized'),
    ('142', 'Mobile - Fixed Location, Restricted'),
    ('143', 'Mobile - Fixed Location, Unrestricted'),
    ('074', 'Mobile - Ice Cream Only Motorized'),
    ('075', 'Mobile - Ice Cream Only Non-motorized'),
    ('140', 'Mobile - Park, Restricted'),
    ('141', 'Mobile - Park, Unrestricted'),
    ('041', 'Nursing Homes'),
    ('043', 'Other Care Facilities'),
    ('112', 'Produce Certified Farmer\'s Market'),
    ('110', 'Produce Establishment'),
    ('111', 'Produce Peddler'),
    ('001', 'Restaurant - Full Service'),
    ('002', 'Restaurant - Single Service'),
    ('091', 'Retail Food Market - Multi Service'),
    ('092', 'Retail Food Market - Seafood Only'),
    ('090', 'Retail Food Market with Meat Market'),
    ('183', 'Salvage Store - Open Foods'),
    ('182', 'Salvage Store - Packaged'),
    ('036', 'School Athletic Concessions'),
    ('035', 'School Cafeteria - College/University'),
    ('030', 'School Cafeteria - Elementary'),
    ('032', 'School Cafeteria - High School'),
    ('031', 'School Cafeteria - Intermediate / Middle / Jr. High'),
    ('033', 'School Cafeteria - Private'),
    ('034', 'School Cafeteria - PTO'),
    ('163', 'Temporary Food Establishment - Combined Booths'),
    ('162', 'Temporary Food Establishment - Community Based Organization'),
    ('161', 'Temporary Food Establishment - Packaged Foods Only'),
    ('160', 'Temporary Food Establishments - Open Foods'),
    # ('151', 'Warehouses +A85'),
    # ('150', 'Warehouses - No Potentially Hazardous Foods'),
)

detail_url = lambda list_record: 'http://houston.tx.gegov.com/media/search.cfm?q=d&f=%s&i=%s' % (list_record['business_id'], list_record['inspection_id'])
detail_violations_re = re.compile(r'(?si)<tr[^>]*>\s*<td[^>]*>(?P<number>\d+)</td>\s*<td[^>]*><a href="#" onmouseover="ddrivetip\(\'(?P<description>.*?)\',\'[^\']*\', \d+\)"[^>]*>Houston Ordinance Violation: (?P<code>.*?)</a></td>\s*<td[^>]*>(?P<result>.*?)</td>\s*</tr>')

class RestaurantScraper(NewsItemListDetailScraper):
    schema_slugs = ('food-inspections',)
    parse_list_re = re.compile(r'(?si)<tr bgcolor="[^"]+">\s*<td[^>]*>\s*<a href="[^"]+&f=(?P<business_id>[^&]+)[^"]*&i=(?P<inspection_id>[^&"]+)[^"]*">(?P<business_name>.*?)</a>\s*<br>\s*(?P<address>[^<]*?)\s*</td>\s*<td[^>]*>\s*(?P<site>[^<]*?)\s*</td>\s*<td[^>]*>\s*(?P<inspection_date>\d\d?/\d\d?/\d\d\d\d)\s*</td>\s*<td[^>]*>\s*(?P<status>[^<]*?)\s*</td>')
    parse_detail_re = re.compile(r'(?si)<td[^>]*>Insp\. Date</td>\s*<td[^>]*>Insp\. Site</td>\s*<td[^>]*>Status</td>\s*<td[^>]*>Activity</td>\s*</tr>\s*</table>\s*<table[^>]*>\s*<tr[^>]*>\s*<td[^>]*>(?P<inspection_date>\d\d?/\d\d?/\d\d\d\d)</td>\s*<td[^>]*>(?P<site>[^<]*)</td>\s*<td[^>]*>(?P<status>[^<]*)</td>\s*\s*<td[^>]*>(?P<activity>[^<]*)</td>\s*</tr>.*?<table[^>]*>(?P<violations_html>.*?)</table>')
    sleep = 2

    def __init__(self, start_date=None, end_date=None):
        NewsItemListDetailScraper.__init__(self, use_cache=False)
        if start_date is None:
            today = datetime.date.today()
            start_date, end_date = today - datetime.timedelta(days=5), today
        self.start_date, self.end_date = start_date, end_date

    def list_pages(self):
        # Submit a search for each facility type.
        for code, facility_type in FACILITY_TYPES:
            data = {
                'q': 's',
                'e': '',
                'k': '',
                'r': '',
                'tp': code,
                'sd': self.start_date.strftime('%m/%d/%Y'),
                'ed': self.end_date.strftime('%m/%d/%Y'),
                'z': 'ALL',
                'm': 'LIKE',
                'maxrows': '500',
            }
            html = self.get_html('http://houston.tx.gegov.com/media/search.cfm', data, send_cookies=False)
            # Convert to Unicode to handle non-ASCII characters.
            html = html.decode('iso-8859-1')
            yield (facility_type, html)

    def parse_list(self, page):
        facility_type, html = page
        for record in NewsItemListDetailScraper.parse_list(self, html):
            yield dict(record, facility_type=facility_type)

    def clean_list_record(self, record):
        record['inspection_date'] = parse_date(record['inspection_date'], '%m/%d/%Y')
        record['detail_url'] = detail_url(record)
        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=record['inspection_date'])
            qs = qs.by_attribute(self.schema_fields['business_id'], record['business_id'])
            qs = qs.by_attribute(self.schema_fields['inspection_id'], record['inspection_id'])
            return qs[0]
        except IndexError:
            return None

    def detail_required(self, list_record, old_record):
        return old_record is None

    def get_detail(self, record):
        # Convert to Unicode to handle non-ASCII characters.
        return self.get_html(record['detail_url'], send_cookies=False).decode('iso-8859-1')

    def clean_detail_record(self, record):
        violations = []
        last_number = 0
        for vio_bits in detail_violations_re.finditer(record.pop('violations_html')):
            vio = vio_bits.groupdict()

            # This is a sanity check of the scraper regex to make sure we get
            # every violation. The source data gives a sequential integer
            # number to each violation, so we just make sure the numbers are
            # indeed sequential. If they're not, then our regex is too strict.
            number = int(vio.pop('number'))
            if number - last_number != 1:
                raise ScraperBroken('Did not detect violation #%s at %s' % (number - 1, record['detail_url']))
            last_number = number

            # Unescape the JavaScript string escaping.
            vio['description'] = vio['description'].replace(r"\'", "'")

            vio['result'] = re.sub(r'\s*<br>\s*', ', ', vio['result'])

            # Skip violations with an empty code. This happens if there are no
            # violations (in this case, the site displays a single, empty
            # violation).
            if vio['code']:
                # We can't just use the violation code to determine uniqueness
                # of the violation type, because sometimes there are violations
                # with the same codes but different descriptions. Here, we use
                # a combination of the code and description as the primary key
                # for the Lookup object. (This will be used by
                # get_or_create_lookup() later.)
                code_for_db = '%s %s' % (vio['code'], vio['description'])
                vio['code_for_db'] = code_for_db[:255] # Fit database column limit.
                violations.append(vio)
        record['violation_list'] = violations
        return record

    def save(self, old_record, list_record, detail_record):
        if detail_record is None:
            return # No need to update the record.

        # This bit of logic lives here because it requires access to both
        # detail_record and list_record.
        if detail_record['activity'] in ('Door Notice (008)', 'Establishment Out of Business (009)'):
            list_record['status'] = 'Unavailable'

        status = self.get_or_create_lookup('status', list_record['status'], list_record['status'], make_text_slug=False)
        activity = self.get_or_create_lookup('activity', detail_record['activity'], detail_record['activity'], make_text_slug=False)
        facility_type = self.get_or_create_lookup('facility_type', list_record['facility_type'], list_record['facility_type'], make_text_slug=False)
        violation_lookups = [self.get_or_create_lookup('violation', v['code'], v['code_for_db'], v['description'], make_text_slug=False) for v in detail_record['violation_list']]
        violation_lookup_text = ','.join([str(v.id) for v in violation_lookups])

        # There's a bunch of data about every particular violation, and we
        # store it as a JSON object. Here, we create the JSON object.
        v_lookup_dict = dict([(v.code, v) for v in violation_lookups])
        v_list = [{'lookup_id': v_lookup_dict[v['code_for_db']].id, 'result': v['result']} for v in detail_record['violation_list']]
        violations_json = DjangoJSONEncoder().encode(v_list)

        title = list_record['business_name']
        attributes = {
            'status': status.id,
            'activity': activity.id,
            'facility_type': facility_type.id,
            'site': detail_record['site'],
            'business_id': list_record['business_id'],
            'inspection_id': list_record['inspection_id'],
            'business_name': list_record['business_name'],
            'violation': violation_lookup_text,
            'details': violations_json,
        }
        if old_record is None:
            self.create_newsitem(
                attributes,
                title=title,
                url=list_record['detail_url'],
                item_date=list_record['inspection_date'],
                location_name=list_record['address'],
            )
        else:
            new_values = {'title': title, 'item_date': list_record['inspection_date'], 'location_name': list_record['address']}
            self.update_existing(old_record, new_values, attributes)

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    start_date = datetime.date(2009, 5, 1)
    end_date = datetime.date(2009, 5, 1)
    s = RestaurantScraper(start_date=start_date, end_date=end_date).update()
