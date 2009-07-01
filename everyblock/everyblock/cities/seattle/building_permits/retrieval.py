"""
Scraper for Seattle building permits

http://web1.seattle.gov/dpd/dailyissuance/Default.aspx
"""

from django.utils.text import capfirst
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
import datetime
import re

PERMIT_CATEGORIES = (
    ('chkContruction', 'Construction'),
    ('chkLandUse', 'Land Use'),
    ('chkOtc', 'Over the Counter'),
)

class Scraper(NewsItemListDetailScraper):
    schema_slugs = ['building-permits']
    has_detail = False
    parse_list_re = re.compile(r'<tr class="ReportRow[^>]*>\s*<td[^>]*>(?P<permit_number>.*?)</td><td[^>]*>(?P<permit_type>.*?)</td><td[^>]*>(?P<location>.*?)</td><td[^>]*>(?P<description>.*?)</td>')
    sleep = 1
    uri = 'http://web1.seattle.gov/dpd/dailyissuance/Default.aspx'

    def __init__(self, *args, **kwargs):
        self.start_date = kwargs.pop('start_date', None)
        super(Scraper, self).__init__(*args, **kwargs)

    def list_pages(self):
        viewstate = re.search(r'<input type="hidden" name="__VIEWSTATE" value="(.*?)" />', self.get_html(self.uri)).group(1)
        if self.start_date:
            date = self.start_date
        else:
            date = datetime.date.today() - datetime.timedelta(days=7)
        while date <= datetime.date.today():
            for key, name in PERMIT_CATEGORIES:
                params = {
                    '__EVENTARGUMENT': '',
                    '__EVENTTARGET': 'btnSearch',
                    '__VIEWSTATE': viewstate,
                    'dgIssuedPermits_LCS': '0',
                    'dgIssuedPermits_LSD': 'Ascending',
                    'txtIssuanceDate': date.strftime('%m/%d/%Y'),
                    'txtIssuanceDate_OriginalText': date.strftime('%m/%d/%Y'),
                }
                params[key] = 'on'
                yield (name, date, self.get_html(self.uri, params))
            date += datetime.timedelta(days=1)

    def parse_list(self, page):
        category, date, html = page
        records = super(Scraper, self).parse_list(html)
        for record in records:
            record['date'] = date
            record['category'] = category
            yield record

    def clean_list_record(self, record):
        record['location'] = re.sub(r'\s+', ' ', record['location'])
        return record

    def existing_record(self, list_record):
        record = None
        qs = NewsItem.objects.filter(schema__id=self.schema.id)
        qs = qs.by_attribute(self.schema_fields['permit_number'], list_record['permit_number'])
        try:
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            return
        category_lookup = self.get_or_create_lookup('category', list_record['category'], list_record['category'], make_text_slug=False)
        permit_type_lookup = self.get_or_create_lookup('permit_type', capfirst(list_record['permit_type'].lower()), list_record['permit_type'], make_text_slug=False)
        attributes = {
            'permit_number': list_record['permit_number'],
            'category': category_lookup.id,
            'permit_type': permit_type_lookup.id,
            'description': list_record['description']
        }
        self.create_newsitem(
            attributes,
            title=category_lookup.name,
            item_date=list_record['date'],
            url="http://web1.seattle.gov/DPD/permitstatus/Project.aspx?id=%s" % list_record['permit_number'],
            location_name=list_record['location']
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    Scraper(start_date=datetime.date(2008, 1, 1)).update()

