"""
Screen scraper for Boston restaurant inspections.

http://www.cityofboston.gov/isd/health/mfc/search.asp
"""

from django.core.serializers.json import DjangoJSONEncoder
from ebdata.retrieval.scrapers.base import ScraperBroken
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
from ebpub.utils.text import smart_title
import re

parse_main_re = re.compile(r"<tr[^>]*><td[^>]*><a href='insphistory\.asp\?licno=(?P<restaurant_id>\d+)'>(?P<restaurant_name>[^<]*)</a></td><td[^>]*>(?P<address>[^<]*)</td><td[^>]*>(?P<neighborhood>[^<]*)</td></tr>")
detail_violations_re = re.compile(r"<tr[^>]*><td[^>]*><span[^>]*>(?P<stars>\*+)</span></td><td[^>]*><span[^>]*>(?P<status>[^<]*)</span></td><td[^>]*><span[^>]*>(?P<code>[^<]*)</span></td><td[^>]*><span[^>]*>(?P<description>[^<]*)</span></td><td[^>]*>(?P<location>.*?)</td><td[^>]*>(?P<comment>.*?)</td></tr>", re.DOTALL)
detail_url = lambda inspection_id: 'http://www.cityofboston.gov/isd/health/mfc/viewinsp.asp?inspno=%s' % inspection_id

strip_tags = lambda x: re.sub(r'(?s)</?[^>]*>', '', x).replace('&nbsp;', ' ').strip()

class RestaurantScraper(NewsItemListDetailScraper):
    schema_slugs = ('restaurant-inspections',)
    parse_list_re = re.compile(r"<a href='viewinsp\.asp\?inspno=(?P<inspection_id>\d+)'>(?P<inspection_date>[^<]*)</a></span> - <span[^>]*>(?P<result>[^<]*)</span>")
    parse_detail_re = re.compile(r"<tr><th[^>]*>[^<]*</th><th[^>]*>Status</th><th[^>]*>Code Violation</th><th[^>]*>Description</th><th[^>]*>Location</th><th[^>]*>Comment</th></tr>(?P<body>.*?)</table>", re.DOTALL)
    sleep = 5

    def __init__(self, name_start=''):
        # name_start, if given, should be a string of the first restaurant name
        # to start scraping, alphabetically. This is useful if you've run the
        # scraper and it's broken several hours into it -- you can pick up
        # around where it left off.
        NewsItemListDetailScraper.__init__(self)
        self.name_start = name_start.lower()

    def list_pages(self):
        # Submit the search form with ' ' as the neighborhood to get *every*
        # restaurant in the city.
        #
        # Note that this site is technically *three* levels deep -- there's a
        # main list of all restaurants, then a list of inspections for each
        # restaurant, then a page for each inspection. Because this is slightly
        # different than a strict list-detail site, list_pages() yields the
        # inspection pages, not the main page.
        url = 'http://www.cityofboston.gov/isd/health/mfc/search.asp'
        html = self.get_html(url, {'ispostback': 'true', 'restname': '', 'cboNhood': ' '}).decode('ISO-8859-2')
        for record in parse_main_re.finditer(html):
            record = record.groupdict()
            if self.name_start and record['restaurant_name'].lower() < self.name_start:
                self.logger.debug('Skipping %r due to name_start %r', record['restaurant_name'], self.name_start)
                continue
            url = 'http://www.cityofboston.gov/isd/health/mfc/insphistory.asp?licno=%s' % record['restaurant_id']
            yield (record, self.get_html(url))

    def parse_list(self, record_html):
        list_record, html = record_html
        for record in NewsItemListDetailScraper.parse_list(self, html):
            yield dict(list_record, **record)

    def clean_list_record(self, record):
        record['inspection_date'] = parse_date(record['inspection_date'], '%A, %B %d, %Y')
        record['address'] = smart_title(record['address'])
        record['restaurant_name'] = smart_title(record['restaurant_name'])
        record['result'] = smart_title(record['result'])
        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            qs = qs.by_attribute(self.schema_fields['inspection_id'], record['inspection_id'])
            return qs[0]
        except IndexError:
            return None

    def detail_required(self, list_record, old_record):
        return old_record is None

    def get_detail(self, record):
        return self.get_html(detail_url(record['inspection_id'])).decode('ISO-8859-2')

    def clean_detail_record(self, record):
        body = record.pop('body')
        violations = [m.groupdict() for m in detail_violations_re.finditer(body)]
        if not violations and not 'There are no violations for this inspection' in body:
            raise ScraperBroken('Could not find violations')
        for vio in violations:
            vio['severity'] = {1: 'Non critical', 2: 'Critical', 3: 'Critical foodborne illness'}[vio.pop('stars').count('*')]
            vio['comment'] = strip_tags(vio['comment']).strip()
            vio['location'] = strip_tags(vio['location']).strip()
        record['violation_list'] = violations
        return record

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            return # We already have this inspection.

        result = self.get_or_create_lookup('result', list_record['result'], list_record['result'])
        violation_lookups = [self.get_or_create_lookup('violation', v['description'], v['code'], make_text_slug=False) for v in detail_record['violation_list']]
        violation_lookup_text = ','.join([str(v.id) for v in violation_lookups])

        # There's a bunch of data about every particular violation, and we
        # store it as a JSON object. Here, we create the JSON object.
        v_lookup_dict = dict([(v.code, v) for v in violation_lookups])
        v_list = [{'lookup_id': v_lookup_dict[v['code']].id, 'comment': v['comment'], 'location': v['location'], 'severity': v['severity'], 'status': v['status']} for v in detail_record['violation_list']]
        violations_json = DjangoJSONEncoder().encode(v_list)

        title = '%s inspected: %s' % (list_record['restaurant_name'], result.name)
        attributes = {
            'restaurant_id': list_record['restaurant_id'],
            'inspection_id': list_record['inspection_id'],
            'restaurant_name': list_record['restaurant_name'],
            'result': result.id,
            'violation': violation_lookup_text,
            'details': violations_json,
        }
        self.create_newsitem(
            attributes,
            title=title,
            url=detail_url(list_record['inspection_id']),
            item_date=list_record['inspection_date'],
            location_name=list_record['address'],
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    RestaurantScraper().update()
