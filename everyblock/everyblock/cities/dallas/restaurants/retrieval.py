"""
Screen scraper for Dallas restaurant inspections.
http://www2.dallascityhall.com/FoodInspection/SearchScores.cfm
"""

from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem, Location
from ebpub.utils.dates import parse_date
from ebpub.utils.text import smart_title
from django.utils import simplejson as json
import md5
import re

class RestaurantScraper(NewsItemListDetailScraper):
    schema_slugs = ('restaurant-inspections',)
    has_detail = False
    parse_list_re = re.compile(r'(?m)<tr[^>]*>\s+<td[^>]*>(?P<name>.*?)</td>\s+<!--<td[^>]*><a href="[^"]*">.*?</a></td>-->\s+<td[^>]*><a href="[^"]*">(?P<address>.*?)</a></td>\s+<!--\s+<td[^>]*>.*?</td>\s+-->\s+<!--\s+<td[^>]*>.*?</td>\s+-->\s+<!--\s+<td[^>]*>.*?</td>\s+-->\s+<!--\s+<td[^>]*>.*?</td>\s+-->\s+<td[^>]*>(?P<suite>.*?)</td>\s+<td[^>]*>(?P<zipcode>.*?)</td>\s+<td[^>]*>(?P<mapsco>.*?)</td>\s+<td[^>]*>(?P<inspection_date>.*?)</td>\s+<td[^>]*>(?P<score>\d+?)</td>\s+<td[^>]*>(?P<inspection_type>.*?)</td>\s+</tr>')
    next_re = re.compile(r'<a href="(.*?)">Next</a>')

    def list_pages(self):
        uri = 'http://www2.dallascityhall.com/FoodInspection/SearchScoresAction.cfm'
        zip_codes = [l.name for l in Location.objects.filter(location_type__slug='zipcodes')]
        for zipcode in zip_codes:
            params = {
                'NAME': '',
                'STNO': '',
                'STNAME': '',
                'ZIP': str(zipcode),
                'Submit': 'Search+Scores'
            }
            html = self.get_html(uri, params)
            yield html
            while 1:
                m = self.next_re.search(html)
                if m is None:
                    break
                next_uri = 'http://www2.dallascityhall.com/FoodInspection/' + m.group(1)
                html = self.get_html(next_uri)
                yield html

    def clean_list_record(self, record):
        record['inspection_date'] = parse_date(record['inspection_date'], '%m/%d/%Y')
        record['address'] = re.sub(r'\s+', ' ', record['address'])

        score = int(record['score'])
        if score <= 59:
            record['result'] = 'UNACCEPTABLE'
        elif score <= 69 and score >= 60:
            record['result'] = 'FAILING'
        elif score <= 79 and score >= 70:
            record['result'] = 'PASSING'
        elif score <= 89 and score >= 80:
            record['result'] = 'GOOD'
        elif score <= 100 and score >= 90:
            record['result'] = 'VERY_GOOD'
        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=record['inspection_date'])
            qs = qs.filter(location_name=record['address'])
            qs = qs.by_attribute(self.schema_fields['name'], record['name'])
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        inspection_type = self.get_or_create_lookup('inspection_type', list_record['inspection_type'], list_record['inspection_type'])
        result = self.get_or_create_lookup('result', list_record['result'], list_record['result'])

        # Make up a unique id so we can show other inspections at this
        # facility on the detail page.
        eb_facility_id = md5.new('%s:%s' % (list_record['name'], list_record['address'])).hexdigest()
        json_data = {
            'zipcode': list_record['zipcode'],
            'suite': list_record['suite'],
            'mapsco': list_record['mapsco']
        }
        kwargs = {
            'title': smart_title(list_record['name'].decode('utf-8')),
            'item_date': list_record['inspection_date'],
            'location_name': list_record['address']
        }
        attributes = {
            'name': list_record['name'].decode('utf-8'),
            'inspection_type': inspection_type.id,
            'result': result.id,
            'score': list_record['score'],
            'eb_facility_id': eb_facility_id,
            'json': json.dumps(json_data)
        }
        if old_record is None:
            self.create_newsitem(attributes, **kwargs)
        else:
            self.update_existing(old_record, kwargs, attributes)

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    RestaurantScraper().update()
