"""
Screen scraper for Atlanta building permits.
http://atlantaga.govhost.com/government/planning_onlinepermits.aspx?section=City%20Services
"""

from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
import datetime
import re

class PermitScraper(NewsItemListDetailScraper):
    schema_slugs = ('building-permits',)
    has_detail = False
    parse_list_re = re.compile(r'(?m)Permit No:\s+(?P<permit_number>.*?)\s+NPU:\s+(?P<npu>.*?)\s+Issued:\s+(?P<issue_date>\d{2}/\d{2}/\d{4})\s+Address:\s+(?P<address>.*?)\s+Scope:\s+(?P<scope>.*?)\s+Inspector:\s+(?P<inspector>.*?)\s+Cost:\s+(?P<cost>.*?)\s+Contractor:\s+(?P<contractor>.*?)\s+Owner:\s+(?P<owner>.*?)\s+')

    def __init__(self, years=None):
        super(PermitScraper, self).__init__()
        # Scrape the years given, or use the year from yesterday. This will
        # allow a final scrape of the previous year on Jan 1.
        self.years = years or [(datetime.date.today() - datetime.timedelta(days=1)).year]

    def list_pages(self):
        uri = 'http://apps.atlantaga.gov/citydir/dpcd/dpcd%%20web/buildings/%s%s.txt'
        for year in self.years:
            for letter_range in ['ag', 'hm', 'ns', 'tz']:
                for record in self.get_html(uri % (letter_range, year)).split('Premit No:'):
                    yield record

    def clean_list_record(self, record):
        record['issue_date'] = parse_date(record['issue_date'], '%m/%d/%Y')
        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            qs = qs.by_attribute(self.schema_fields['permit_number'], record['permit_number'])
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            self.logger.debug('Record already exists')
            return

        scope = self.get_or_create_lookup('scope', list_record['scope'], list_record['scope'], make_text_slug=False)
        npu = self.get_or_create_lookup('npu', list_record['npu'], list_record['npu'], make_text_slug=False)

        attributes = {
            'permit_number': list_record['permit_number'],
            'scope': scope.id,
            'npu': npu.id,
            'cost': list_record['cost'],
            'owner': list_record['owner'],
            'contractor': list_record['contractor'],
        }
        self.create_newsitem(
            attributes,
            title='Building permit issued at %s' % list_record['address'],
            item_date=list_record['issue_date'],
            location_name=list_record['address'],
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    PermitScraper().update()
