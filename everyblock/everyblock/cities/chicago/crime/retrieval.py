"""
Screen scraper for Chicago Police CLEARmap crime site
http://gis.chicagopolice.org/
"""

from django.contrib.gis.geos import Point
from ebdata.retrieval.scrapers.base import ScraperBroken
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.text import smart_title
import datetime
import re
import time
from xml.dom import minidom

class CrimeScraper(NewsItemListDetailScraper):
    schema_slugs = ('crime',)
    has_detail = False

    def __init__(self, start_date=None, end_date=None):
        super(CrimeScraper, self).__init__()
        self.start_date, self.end_date = start_date, end_date

    def call_clearpath(self, where, offset=0, limit=2000):
        """
        Makes a request to the CPD site with the given WHERE clause (a list)
        and offset/limit. Returns a DOM object of the parsed XML.

        Note that the maximum limit is 2000. All results will always return
        at most 2000 records.
        """
        # Example valid WHERE clauses:
        #     GIS.clearMap_crime_90days.DATEOCC between {ts &apos;2007-09-01 00:00:00&apos;} AND {ts &apos;2007-09-01 23:59:59&apos;}
        #     GIS.clearMap_crime_90days.DATEOCC &gt;= {ts &apos;2007-09-01&apos;}
        # Good documentation is available here:
        #     http://edndoc.esri.com/arcims/9.2/elements/get_features.htm
        xml_request = """
            <?xml version="1.0" encoding="UTF-8" ?>
            <ARCXML VERSION="1.1">
            <REQUEST>
                <GET_FEATURES outputmode="xml" geometry="true" globalenvelope="false" envelope="false" compact="true" beginrecord="%(offset)s" featurelimit="%(limit)s">
                    <LAYER id="999" type="featureclass">
                        <DATASET name="GIS.clearMap_crime_90days" type="point" workspace="sde_ws-1"  />
                    </LAYER>
                    <SPATIALQUERY where="%(where)s" subfields="#ALL#"></SPATIALQUERY>
                </GET_FEATURES>
            </REQUEST>
            </ARCXML>""" % {'where': ' AND '.join(where), 'offset': offset, 'limit': limit}
        data = {
            'ArcXMLRequest': xml_request.strip(),
            'JavaScriptFunction': 'parent.MapFrame.processXML',
            'BgColor': '#000000',
            'FormCharset': 'ISO-8859-1',
            'RedirectURL': '',
            'HeaderFile': '',
            'FooterFile': '',
        }
        url = 'http://gis.chicagopolice.org/servlet/com.esri.esrimap.Esrimap?ServiceName=clearMap&CustomService=Query&ClientVersion=4.0&Form=True&Encode=False'
        html = self.get_html(url, data)

        # The resulting HTML has some XML embedded in it. Extract that.
        m = re.search(r"var XMLResponse='(.*?)';\s*parent\.MapFrame\.processXML", html)
        if not m:
            raise ScraperBroken('"var XMLResponse" XML not found')
        raw_xml = m.group(1)

        # Clean invalid XML --
        # Attributes that start with "#".
        raw_xml = raw_xml.replace('#', 'Z')
        # Unescaped ampersands.
        raw_xml = re.sub(r'&(?!amp;)', '&amp;', raw_xml)
        # Unescaped '<' signs (shows up in "<18" in attributes).
        raw_xml = raw_xml.replace(r'<18', '&lt;18')

        return minidom.parseString(raw_xml)

    def list_pages(self):
        # Note that this method yields XML objects, not strings, because
        # it parses the XML in order to determine the pagination needs.
        if self.start_date and self.end_date:
            where = ['GIS.clearMap_crime_90days.DATEOCC between {ts &apos;%s 00:00:00&apos;} AND {ts &apos;%s 23:59:59&apos;}' % (self.start_date, self.end_date)]
        else:
            where = []
        offset, limit = 0, 2000
        while 1:
            xml = self.call_clearpath(where, offset=offset, limit=limit)
            yield xml
            # Keep paginating and loading pages until <FEATURECOUNT hasmore="false">.
            if xml.getElementsByTagName('FEATURECOUNT')[0].getAttribute('hasmore') == 'false':
                break
            offset += limit

    def parse_list(self, xml):
        # Note that the argument is XML because list_pages() returns XML
        # objects, not strings.

        # Maps our field name to the data column name.
        xml_attributes = (
            ('beat', 'BEAT_NUM'),
            ('secondary_type_id', 'CURR_IUCR'),
            ('crime_datetime', 'DATEOCC'),
            ('secondary_type', 'DESCRIPTION'),
            ('primary_type', 'PRIMARY'),
            ('domestic', 'DOMESTIC_I'),
            ('fbi_cd', 'FBI_CD'),
            ('fbi_type', 'FBI_DESCR'),
            ('place', 'LOCATION_DESCR'),
            # ('police_id', 'OBJECTID'), # We don't save the police ID, because it appears to change randomly.
            ('case_number', 'RD'),
            ('status', 'STATUS'),
            ('addr_direction', 'STDIR'),
            ('addr_block', 'STNUM'),
            ('addr_street', 'STREET'),
            ('ward', 'WARD'),
        )

        for report in xml.getElementsByTagName('FEATURE'):
            crime = report.getElementsByTagName('FIELDS')[0]
            x_coord, y_coord = report.getElementsByTagName('COORDS')[0].childNodes[0].nodeValue.split(' ')
            yield dict(
                [('x_coord', x_coord), ('y_coord', y_coord)] + \
                [(att, crime.getAttribute('GIS.clearMap_crime_90days.%s' % col)) for att, col in xml_attributes]
            )

    def clean_list_record(self, record):
        # Convert the 'DATEOCC' field to a Python date object.
        dt = datetime.datetime(*time.gmtime(int(record.pop('crime_datetime')) / 1000)[:6])
        record['crime_date'] = dt.date()
        record['crime_time'] = dt.time()
        record['domestic'] = (record['domestic'] == 'Y')
        record['x_coord'] = float(record['x_coord'])
        record['y_coord'] = float(record['y_coord'])
        return record

    def existing_record(self, record):
        try:
            return NewsItem.objects.filter(schema__id=self.schema.id).by_attribute(self.schema_fields['case_number'], record['case_number'])[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        secondary_type = self.get_or_create_lookup('secondary_type', list_record['secondary_type'], list_record['secondary_type_id'])
        real_address = '%s %s %s' % (list_record['addr_block'], list_record['addr_direction'], list_record['addr_street'])
        block_address = '%s00 block %s. %s' % (list_record['addr_block'][:-2], list_record['addr_direction'], smart_title(list_record['addr_street']))

        crime_location = Point(list_record['x_coord'], list_record['y_coord'], srid=102671)
        crime_location = self.safe_location(real_address, crime_location, 375)

        new_attributes = {
            'is_outdated': False,
            'case_number': list_record['case_number'],
            'crime_time': list_record['crime_time'],
            'primary_type': self.get_or_create_lookup('primary_type', list_record['primary_type'], list_record['primary_type']).id,
            'secondary_type': secondary_type.id,
            'place': self.get_or_create_lookup('place', list_record['place'], list_record['place']).id,
            'beat': self.get_or_create_lookup('beat', list_record['beat'], list_record['beat']).id,
            'domestic': list_record['domestic'],
            'xy': '%s;%s' % (list_record['x_coord'], list_record['y_coord']),
            'real_address': real_address,
        }
        if old_record is None:
            self.create_newsitem(
                new_attributes,
                title=secondary_type.name,
                url='http://gis.chicagopolice.org/',
                item_date=list_record['crime_date'],
                location=crime_location,
                location_name=block_address,
            )
        else:
            # This crime already exists in our database, but check whether any
            # of the values have changed.
            new_values = {'title': secondary_type.name, 'item_date': list_record['crime_date'], 'location_name': block_address}
            self.update_existing(old_record, new_values, new_attributes)

def update_current():
    """
    Runs the crime updater for the latest 7 days and oldest 3 days.
    """
    today = datetime.date.today()

    # The latest date with available crimes is 8 days ago, but that might not
    # have *every* crime for that day, so we use 9 days ago.
    latest_available = today - datetime.timedelta(9)

    # The oldest date with available crimes is 97 days ago.
    oldest_available = today - datetime.timedelta(97)

    # Update the latest 7 days and the oldest 3 days.
    # The reasoning here is that crime data changes, so we can't just scrape
    # each day once and never check it again -- but we also don't want to have
    # to scrape *every* available day every day. So we compromise and scrape
    # the latest 7 days and the oldest 3 days.
    s = CrimeScraper(latest_available - datetime.timedelta(6), latest_available)
    s.update()
    s = CrimeScraper(oldest_available, oldest_available + datetime.timedelta(2))
    s.update()

if __name__ == "__main__":
    update_current()
