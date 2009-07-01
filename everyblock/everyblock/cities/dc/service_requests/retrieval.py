"""
Import script for DC service requests.
http://data.octo.dc.gov/Main_DataCatalog_Go.aspx?category=0&view=All
Metadata: http://data.octo.dc.gov/Metadata.aspx?id=4
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

class ServiceRequestScraper(NewsItemListDetailScraper):
    schema_slugs = ('service-requests',)
    has_detail = False

    def list_pages(self):
        # Download the latest ZIP file, extract it and yield the XML file within.
        z = self.get_html('http://data.octo.dc.gov/feeds/src/src_current_plain.zip')
        zf = zipfile.ZipFile(StringIO(z))
        yield zf.read('src_current_plain.xml')

    def parse_list(self, text):
        xml = etree.fromstring(text)
        strip_ns = re.compile(r'^\{.*?\}').sub
        for el in xml.findall('{http://dc.gov/dcstat/types/1.0/}ServiceRequest'):
            yield dict([(strip_ns('', child.tag), child.text) for child in el])
    
    def clean_list_record(self, record):
        if record['lat'] == '0' or record['long'] == '0':
            raise SkipRecord('Got 0 for lat/long')
        if record['lat'] is None or record['long'] is None:
            raise SkipRecord('Got no value for lat/long')
        if (record['lat'] == '' or record['long'] == 0) and record['siteaddress'] == '':
            raise SkipRecord('No value found for lat/long or address')
        record['lat'] = float(record['lat'])
        record['long'] = float(record['long'])
        if record['servicetypecode'] in ('METERS',):
            raise SkipRecord('Skipping parking meter data')
        record['order_date'] = parse_date(record['serviceorderdate'].split('T')[0], '%Y-%m-%d')
        record['add_date'] = parse_date(record['adddate'].split('T')[0], '%Y-%m-%d')
        if record['resolutiondate']:
            record['resolution_date'] = parse_date(record['resolutiondate'].split('T')[0], '%Y-%m-%d')
        else:
            record['resolution_date'] = None
        if record['inspectiondate']:
            record['inspection_date'] = parse_date(record['inspectiondate'].split('T')[0], '%Y-%m-%d')
        else:
            record['inspection_date'] = None
        if record['serviceduedate']:
            record['service_due_date'] = parse_date(record['serviceduedate'].split('T')[0], '%Y-%m-%d')
        else:
            record['service_due_date'] = None
        record['service_notes'] = record['servicenotes'] or ''
        record['inspection_complete'] = (record['inspectionflag'] == 'Y')
        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            qs = qs.by_attribute(self.schema_fields['request_id'], record['servicerequestid'])
            return qs[0]
        except IndexError:
            return None
    
    def save(self, old_record, list_record, detail_record):
        agency = self.get_or_create_lookup('agency', list_record['agencyabbreviation'], list_record['agencyabbreviation'])
        request_type_code = self.get_or_create_lookup('request_type_code', list_record['servicetypecodedescription'], list_record['servicetypecode'])
        request_type = self.get_or_create_lookup('request_type', list_record['servicecodedescription'], list_record['servicecode'])
        resolution = self.get_or_create_lookup('resolution', list_record['resolution'], list_record['resolution'])
        status = self.get_or_create_lookup('status', list_record['serviceorderstatus'], list_record['serviceorderstatus'])
        priority = self.get_or_create_lookup('priority', list_record['servicepriority'], list_record['servicepriority'])
        attributes = {
            'request_id': list_record['servicerequestid'],
            'dcstat_location_id': list_record['dcstatlocationkey'],
            'dcstat_address_id': list_record['dcstataddresskey'],
            'mar_id': list_record['maraddressrepositoryid'],
            'agency': agency.id,
            'request_type_code': request_type_code.id,
            'request_type': request_type.id,
            'resolution': resolution.id,
            'status': status.id,
            'priority': priority.id,
            'add_date': list_record['add_date'],
            'resolution_date': list_record['resolution_date'],
            'inspection_date': list_record['inspection_date'],
            'service_due_date': list_record['service_due_date'],
            'service_call_count': list_record['servicecallcount'],
            'notes': list_record['service_notes'],
            'inspection_complete': list_record['inspection_complete'],
        }
        title = request_type.name
        if old_record is None:
            kwargs = {}
	    if list_record['long'] is not None and list_record['lat'] is not None:
	        kwargs['location'] = Point(list_record['long'], list_record['lat'])
            self.create_newsitem(
                attributes,
                title=title,
                item_date=list_record['order_date'],
                location_name=list_record.get('siteaddress') or '(long, lat)',
		**kwargs
            )
        else:
            # TODO: Include location Point object in new_values?
            new_values = {'title': title, 'item_date': list_record['order_date']}
            if list_record['siteaddress'] is not None:
                new_values['location_name'] = list_record['siteaddress']
            self.update_existing(old_record, new_values, attributes)

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    ServiceRequestScraper().update()
