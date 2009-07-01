# -*- coding: utf-8 -*-
"""
Scraper for Seattle land use bulletins

http://web1.seattle.gov/dpd/luib/Default.aspx
"""

from django.utils.text import capfirst
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
from ebpub.utils.text import smart_title
import re

class Scraper(NewsItemListDetailScraper):
    schema_slugs = ['land-use-bulletins']
    parse_list_re = re.compile(r'<td><a href="Notice.aspx\?BID=(?P<bid>\d+)&amp;NID=(?P<nid>\d+)"><nobr>(?P<project_number>.*?)</nobr></a></td><td[^>]*>(?P<location>.*?)</td><td[^>]*><a[^>]*>(?P<bulletin_type>.*?)</a></td>')
    parse_detail_regexes = {
        'description': re.compile(r'(?s)<tr id="trProjectDescription">\s*<td[^>]*>(.*?)</td>'),
        'zone': re.compile(r'(?s)<span id=\"lblZoning\"[^>]*>(.*?)</span>'),
        'application_date': re.compile(r'(?s)<span id=\"lblApplicationDate\"[^>]*>(.*?)</span>'),
        'complete_date': re.compile(r'(?s)<span id=\"lblCompleteDate\"[^>]*>(.*?)</span>'),
    }
    sleep = 1
    list_uri = 'http://web1.seattle.gov/dpd/luib/Default.aspx'
    detail_uri = 'http://web1.seattle.gov/dpd/luib/Notice.aspx?BID=%s&NID=%s'

    def __init__(self, *args, **kwargs):
        self.get_archive = kwargs.pop('get_archive', None)
        super(Scraper, self).__init__(*args, **kwargs)

    def list_pages(self):
        html = self.get_html(self.list_uri)
        viewstate = re.search(r'<input type="hidden" name="__VIEWSTATE" value="(.*?)" />', html).group(1)
        options = []
        for m in re.compile(r'\{"Text":"(?P<date>\d{2}/\d{2}/\d{4})","Value":"(?P<value>\d+)",.*?"ClientID":"RadComboBox1_c(?P<index>\d+)"\}').finditer(html):
            options.append(m.groupdict())
        # If we aren't scraping the entire archive, just grab pages for the
        # last couple of days.
        if not self.get_archive:
            options = options[:2]
        for option in options:
            params = {
                '__EVENTTARGET': 'RadComboBox1',
                '__EVENTARGUMENT': 'TextChange',
                '__VIEWSTATE': viewstate,
                'RadComboBox1_Input': option['date'],
                'RadComboBox1_text': option['date'],
                'RadComboBox1_value': option['value'],
                'RadComboBox1_index': option['index'],
                'RadComboBox1_clientWidth': '',
                'RadComboBox1_clientHeight': '',
                'RadGrid1PostDataValue': '',
                'RadAJAXControlID': 'RadAjaxManager2',
                'httprequest': 'true',
            }
            yield (option['date'], self.get_html(self.list_uri, params))

    def parse_list(self, page):
        date, html = page
        records = super(Scraper, self).parse_list(html)
        for record in records:
            record['bulletin_date'] = date
            yield record

    def clean_zone(self, zone):
        zone = zone.strip().upper()
        zone = re.sub(r'[\.|\'|’]', '', zone)
        misspellings = (
            ('AIPORT', 'AIRPORT'),
            ('AIPRT', 'AIRPORT'),
            ('AIRPRT', 'AIRPORT'),
            ('ARTERL', 'ARTERIAL'),
            ('COMMCERCIAL', 'COMMERCIAL'),
            ('CMRCL', 'COMMERCIAL'),
            ('COMMERCL', 'COMMERCIAL'),
            ('DOWNTWN', 'DOWNTOWN'),
            ('GENRL', 'GENERAL'),
            ('HIGHT', 'HEIGHT'),
            ('PARAKING', 'PARKING'),
            ('ARTERIAL WITH 100 FT', 'ARTERIAL WITHIN 100 FT'),
            ('C1 65', 'C1-65'),
            ('CORE2', 'CORE 2'),
            ('GENERAL1', 'GENERAL 1'),
            ('GENERAL2', 'GENERAL 2'),
            ('NC 2-40', 'NC2-40'),
            ('NC2 40', 'NC2-40'),
            ('ZONNING', 'ZONING'),
        )
        # Normalize DIST vs DISTRICT
        zone = re.sub(r'\bDIST\b', 'DISTRICT', zone)
        # Normalize FT vs FEET
        zone = re.sub(r'\bFEET\b', 'FT', zone)
        zone = re.sub(r'COMMERCIAL(\d+)', r'COMMERCIAL \1', zone)
        zone = re.sub(r'COMMERCIAL-', r'COMMERCIAL ', zone)
        zone = re.sub(r'GENERAL(\d+)', r'GENERAL \1', zone)
        zone = re.sub(r'LOWRISE-(\d+)', r'LOWRISE \1', zone)
        zone = zone.replace('100FT', '100 FT')

        zone = re.sub(r'ARTERIAL WITHIN 100$', r'ARTERIAL WITHIN 100 FT', zone)
        zone = re.sub(r'STEEP SLOPE \(>=40$', r'STEEP SLOPE (>=40%)', zone)
        zone = re.sub(r'SCENIC VIEW WITHIN 500$', r'SCENIC VIEW WITHIN 500 FT', zone)
        zone = re.sub(r'URBAN VIL$', r'URBAN VILLAGE', zone)

        for incorrect, correct in misspellings:
            zone = zone.replace(incorrect, correct)
        return zone

    def clean_list_record(self, record):
        record['bulletin_date'] = parse_date(record['bulletin_date'], '%m/%d/%Y')
        return record

    def existing_record(self, list_record):
        qs = NewsItem.objects.filter(schema__id=self.schema.id)
        qs = qs.by_attribute(self.schema_fields['bid'], list_record['bid'])
        qs = qs.by_attribute(self.schema_fields['nid'], list_record['nid'])
        try:
            return qs[0]
        except IndexError:
            return None

    def detail_required(self, list_record, old_record):
        return old_record is None

    def get_detail(self, list_record):
        html = self.get_html(self.detail_uri % (list_record['bid'], list_record['nid']))
        return html

    def parse_detail(self, page, list_record):
        record = {}
        for key, detail_re in self.parse_detail_regexes.items():
            m = detail_re.search(page)
            if m is None:
                record[key] = None
            else:
                record[key] = m.group(1)
        return record

    def clean_detail_record(self, record):
        zones = record['zone'] and record['zone'].split(',') or []
        record['zone'] = [self.clean_zone(z) for z in zones if z != '&nbsp;']
        for key in ['application_date', 'complete_date']:
            if record.has_key(key):
                record[key] = parse_date(record[key], '%m/%d/%Y')
            else:
                record[key] = None
        return record

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            return
        if list_record['location'] == '&nbsp;':
            return
        bulletin_type_lookup = self.get_or_create_lookup('bulletin_type', capfirst(list_record['bulletin_type'].lower()), list_record['bulletin_type'].upper(), make_text_slug=False)
        zone_lookups = []
        for z in detail_record['zone']:
            zone_lookup = self.get_or_create_lookup('zone', capfirst(z.lower()), z, make_text_slug=False)
            zone_lookups.append(zone_lookup)
        attributes = {
            'project_number': list_record['project_number'],
            'description': detail_record.get('description', None),
            'bulletin_type': bulletin_type_lookup.id,
            'application_date': detail_record['application_date'],
            'complete_date': detail_record['complete_date'],
            'zone': ','.join([str(z.id) for z in zone_lookups]),
            'bid': list_record['bid'],
            'nid': list_record['nid'],
        }
        self.create_newsitem(
            attributes,
            title=bulletin_type_lookup.name,
            url='http://web1.seattle.gov/dpd/luib/Notice.aspx?BID=%s&NID=%s' % (list_record['bid'], list_record['nid']),
            item_date=list_record['bulletin_date'],
            location_name=smart_title(list_record['location'])
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    Scraper(get_archive=True).update()
