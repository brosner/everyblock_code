"""
Import script for DC construction projects.
http://data.octo.dc.gov/Main_DataCatalog_Go.aspx?category=0&view=All
Metadata: http://data.octo.dc.gov/Metadata.aspx?id=13
"""

from django.contrib.gis.geos import Point
from ebdata.retrieval.scrapers.list_detail import SkipRecord
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
from cStringIO import StringIO
from lxml import etree
import datetime
import re
import zipfile

class ConstructionProjectScraper(NewsItemListDetailScraper):
    schema_slugs = ('road-construction',)
    has_detail = False

    project_xml_sources = (('ccp', 'ccp', 'CCProject'), ('cmpltcp', 'cmpltcp', 'CompletedCProject'))

    def list_pages(self):
        # Download the latest ZIP file, extract it and yield the XML file
        # within. Note that there are two files to check -- the current open
        # projects and the closed projects. We check the closed projects
        # because a project might be removed from the open projects feed.
        for url, file_name, xml_name in self.project_xml_sources:
            z = self.get_html('http://data.octo.dc.gov/feeds/%s/%s_current_plain.zip' % (url, file_name))
            zf = zipfile.ZipFile(StringIO(z))
            yield zf.read('%s_current_plain.xml' % file_name), xml_name

    def parse_list(self, bunch):
        text, xml_name = bunch
        xml = etree.fromstring(text)
        strip_ns = re.compile(r'^\{.*?\}').sub
        for el in xml.findall('{http://dc.gov/dcstat/types/1.0/}%s' % xml_name):
            yield dict([(strip_ns('', child.tag), child.text) for child in el])
    
    def clean_list_record(self, record):
        if record['lat'] == '0' or record['long'] == '0':
            raise SkipRecord('Got 0 for lat/long')
        record['lat'] = float(record['lat'])
        record['long'] = float(record['long'])
        record['location_name'] = '%s %s, from %s to %s' % (record['street'], record['quadrant'], record['fromintersection'], record['tointersection'])
        # record['order_date'] = parse_date(record['serviceorderdate'].split('T')[0], '%Y-%m-%d')
        # record['add_date'] = parse_date(record['adddate'].split('T')[0], '%Y-%m-%d')
        if record['estimatedcompletiondate']:
            record['estimated_completion_date'] = parse_date(record['estimatedcompletiondate'].split('T')[0], '%Y-%m-%d')
        else:
            record['estimated_completion_date'] = None
        if record['actualcompletiondate']:
            record['actual_completion_date'] = parse_date(record['actualcompletiondate'].split('T')[0], '%Y-%m-%d')
        else:
            record['actual_completion_date'] = None
        if record['estimatedstartdate']:
            record['estimated_start_date'] = parse_date(record['estimatedstartdate'].split('T')[0], '%Y-%m-%d')
        else:
            record['estimated_start_date'] = None
        record['project_name'] = record['projectname'] or ''
        record['road_type'] = record['functionalclass'] or 'N/A'
        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            qs = qs.by_attribute(self.schema_fields['project_id'], record['projectid'])
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        work_description = self.get_or_create_lookup('work_description', list_record['workdescription'], list_record['workdescription'])
        road_type = self.get_or_create_lookup('road_type', list_record['road_type'], list_record['road_type'])
        status = self.get_or_create_lookup('status', list_record['status'], list_record['status'])
        attributes = {
            'project_id': list_record['projectid'],
            'project_name': list_record['project_name'],
            'remarks': list_record['remarks'],
            'miles': list_record['miles'],
            'num_blocks': list_record['noofblocks'],
            'percent_completed': list_record['percentcompleted'],
            'work_description': work_description.id,
            'road_type': road_type.id,
            'status': status.id,
            'estimated_completion_date': list_record['estimated_completion_date'],
            'actual_completion_date': list_record['actual_completion_date'],
            'estimated_start_date': list_record['estimated_start_date'],
        }
        title = '%s on %s' % (work_description.name, list_record['street'])
        if old_record is None:
            self.create_newsitem(
                attributes,
                title=title,
                item_date=datetime.date.today(),
                location=Point(list_record['long'], list_record['lat']),
                location_name=list_record['location_name'],
            )
        else:
            # TODO: Include location Point object in new_values?
            new_values = {'title': title, 'location_name': list_record['location_name']}
            self.update_existing(old_record, new_values, attributes)

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    ConstructionProjectScraper().update()
