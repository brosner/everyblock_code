"""
Import script for DC crime data.
http://data.octo.dc.gov/Main_DataCatalog_Go.aspx?category=6&view=All
Metadata: http://data.octo.dc.gov/Metadata.aspx?id=3
"""

from django.contrib.gis.geos import Point
from ebdata.retrieval.scrapers.list_detail import SkipRecord
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
from cStringIO import StringIO
from lxml import etree
import re
import zipfile

class CrimeScraper(NewsItemListDetailScraper):
    schema_slugs = ('crime',)
    has_detail = False

    def list_pages(self):
        # Download the latest ZIP file, extract it and yield the XML file within.
        z = self.get_html('http://data.octo.dc.gov/feeds/crime_incidents/crime_incidents_current_plain.zip')
        zf = zipfile.ZipFile(StringIO(z))
        yield zf.read('crime_incidents_current_plain.xml')

    def parse_list(self, text):
        xml = etree.fromstring(text)
        strip_ns = re.compile(r'^\{.*?\}').sub
        for el in xml.findall('{http://dc.gov/dcstat/types/1.0/}ReportedCrime'):
            yield dict([(strip_ns('', child.tag), child.text) for child in el])

    def clean_list_record(self, record):
        if record['lat'] == '0' or record['long'] == '0':
            raise SkipRecord('Got 0 for lat/long')
        record['lat'] = float(record['lat'])
        record['long'] = float(record['long'])
        record['report_date'] = parse_date(record['reportdatetime'].split('T')[0], '%Y-%m-%d')
        record['address'] = record['blocksiteaddress'].replace(' B/O ', ' block of ')
        if record['narrative'].upper() == 'NO NARRATIVE IS AVAILABLE.':
            record['narrative'] == 'Not available'
        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            qs = qs.by_attribute(self.schema_fields['nid'], record['nid'])
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        # The method is relative to offense, so create a multi-value key for it.
        method_code = '%s -- %s' % (list_record['offense'], list_record['method'])

        offense = self.get_or_create_lookup('offense', list_record['offense'], list_record['offense'])
        method = self.get_or_create_lookup('method', method_code, method_code)
        shift = self.get_or_create_lookup('shift', list_record['shift'], list_record['shift'])
        attributes = {
            'nid': list_record['nid'],
            'crime_control_number': list_record['ccn'],
            'narrative': list_record['narrative'],
            'offense': offense.id,
            'method': method.id,
            'shift': shift.id,
        }
        title = method.name
        if old_record is None:
            self.create_newsitem(
                attributes,
                title=title,
                item_date=list_record['report_date'],
                location=Point(list_record['long'], list_record['lat']),
                location_name=list_record['address'],
            )
        else:
            # TODO: Include location Point object in new_values?
            new_values = {'title': title, 'item_date': list_record['report_date'], 'location_name': list_record['address']}
            self.update_existing(old_record, new_values, attributes)

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    CrimeScraper().update()
