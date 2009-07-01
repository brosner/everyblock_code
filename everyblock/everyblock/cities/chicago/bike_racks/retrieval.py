"""
Scraper for Chicago bike racks.

http://www.chicagobikes.org/kml/bikeracks.php
"""

from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
from ebpub.utils.text import clean_address
from lxml import etree
import re

class Scraper(NewsItemListDetailScraper):
    schema_slugs = ['bike-racks']
    has_detail = False
    sleep = 1
    rack_id_re = re.compile(r"http://www\.chicagobikes\.org/bikeparking/rackinfo\.php\?id=(\d+)")
    rack_count_re = re.compile(r'(\d+) bike rack')

    def list_pages(self):
        yield self.get_html('')

    def parse_list(self, kml):
        kml = kml.replace('&eacute;', '&#233;')
        kml = kml.replace('UTF-8', 'ISO-8859-2')
        tree = etree.fromstring(kml)
        ns = 'http://earth.google.com/kml/2.1'
        cdot_ns = 'http://www.chicagobikes.org/data'
        for pm in tree.findall('.//{%s}Placemark' % ns):
            description = pm.find('{%s}description' % ns).text
            rack_id = self.rack_id_re.search(description).group(1)
            m = self.rack_count_re.search(description)
            if m:
                rack_count = m.group(1)
            else:
                # Lately the data hasn't been displaying a number:
                # "plural bike racks located here". Just use None in
                # that case.
                rack_count = None
            record = {
                'address': pm.find('{%s}name' % ns).text,
                'installation_date': pm.find('{%s}TimeStamp/{%s}when' % (ns, ns)).text,
                'rack_id': rack_id,
                'rack_count': rack_count,
                'url': 'http://www.chicagobikes.org/bikeparking/rackinfo.php?id=%s' % rack_id
            }
            locname_el =  pm.find('{%s}ExtendedData/{%s}locName' % (ns, cdot_ns))
            if locname_el is not None:
                record['place_name'] = locname_el.text
            yield record

    def clean_list_record(self, list_record):
        list_record['installation_date'] = parse_date(list_record['installation_date'], '%Y-%m-%d')
        try:
            list_record['rack_count'] = int(list_record['rack_count'])
        except TypeError:
            pass
        return list_record

    def existing_record(self, list_record):
        qs = NewsItem.objects.filter(schema__id=self.schema.id)
        qs = qs.by_attribute(self.schema_fields['rack_id'], list_record['rack_id'])
        try:
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        address = clean_address(list_record['address'])
        attributes = {
            'place_name': list_record.get('place_name', ''),
            'rack_id': list_record['rack_id'],
            'rack_count': list_record['rack_count']
        }
        values = {
            'title': 'Bike rack installed near %s' % list_record.get('place_name', address),
            'item_date': list_record['installation_date'],
            'location_name': address,
            'url': list_record['url']
        }
        if old_record is None:
            self.create_newsitem(attributes, **values)
        else:
            self.update_existing(old_record, values, attributes)

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    Scraper().update()
