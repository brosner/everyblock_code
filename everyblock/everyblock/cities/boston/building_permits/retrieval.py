"""
Screen scraper for Boston building permits.
http://www.cityofboston.gov/isd/building/asofright/default.asp
"""

from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
from ebpub.utils.text import smart_title
import re
import urllib

# These are the neighborhoods that can be searched-by at
# http://www.cityofboston.gov/isd/building/asofright/default.asp
NEIGHBORHOODS = (
    'Allston',
    'Back Bay',
    'Beacon Hill',
    'Brighton',
    'Charlestown',
    'Chinatown',
    'Dorchester',
    'Dorchester (Lower Mills)',
    'Dorchester (Meeting House Hill)',
    'Dorchester (Neponset, Cedar Grove)',
    'Dorchester (Savin Hill)',
    'East Boston',
    'Fenway',
    'Financial District',
    'Hyde Park',
    'Jamaica Plain',
    'Mattapan',
    'Mission Hill',
    'North Dorchester',
    'NorthEnd',
    'Roslindale',
    'Roxbury',
    'South Boston',
    'South End',
    'West End',
    'West Roxbury',
)

class PermitScraper(NewsItemListDetailScraper):
    schema_slugs = ('building-permits',)
    has_detail = False
    parse_list_re = re.compile(r'<tr[^>]*><td[^>]*>(?P<permit_date>\d\d?/\d\d/\d{4})\s*</td><td[^>]*>(?P<address>[^<]*)<br/>(?P<neighborhood>[^<]*)</td><td[^>]*>(?P<owner>[^<]*)</td><td[^>]*>(?P<description>[^<]*)</td></tr>', re.IGNORECASE | re.DOTALL)

    def list_pages(self):
        for name in NEIGHBORHOODS:
            url = 'http://www.cityofboston.gov/isd/building/asofright/default.asp?ispostback=true&nhood=%s' % urllib.quote_plus(name)
            yield self.get_html(url)

    def clean_list_record(self, record):
        record['permit_date'] = parse_date(record['permit_date'], '%m/%d/%Y')
        record['description'] = re.sub(r'[\r\n]+', ' ', record['description']).strip()
        record['description'] = record['description'].decode('iso-8859-1') # Avoid database-level encoding errors
        record['clean_address'] = smart_title(record['address'])
        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=record['permit_date'])
            qs = qs.by_attribute(self.schema_fields['raw_address'], record['address'])
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            self.logger.debug('Record already exists')
            return

        attributes = {
            'raw_address': list_record['address'],
            'description': list_record['description'],
            'owner': list_record['owner'],
        }
        self.create_newsitem(
            attributes,
            title='Building permit issued at %s' % list_record['clean_address'],
            description=list_record['description'],
            item_date=list_record['permit_date'],
            location_name=list_record['clean_address'],
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    PermitScraper().update()
