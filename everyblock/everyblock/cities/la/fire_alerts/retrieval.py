"""
Scraper for fire alerts in Los Angeles

http://groups.google.com/group/LAFD_ALERT/
RSS: http://groups.google.com/group/LAFD_ALERT/feed/rss_v2_0_msgs.xml?num=50
"""

from ebdata.retrieval.scrapers.base import ScraperBroken
from ebdata.retrieval.scrapers.list_detail import RssListDetailScraper, SkipRecord
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
import datetime
import re

class AlertScraper(NewsItemListDetailScraper, RssListDetailScraper):
    schema_slugs = ('fire-alerts',)
    has_detail = False
    sleep = 4

    def list_pages(self):
        yield self.get_html('http://groups.google.com/group/LAFD_ALERT/feed/rss_v2_0_msgs.xml?num=50')

    def clean_list_record(self, rss_record):
        record = {
            'pub_date': datetime.date(*rss_record.pop('updated_parsed')[:3]),
            'summary': rss_record['summary'].strip(),
        }
        if re.search(r'^(?i)\*UPDATE:', record['summary']):
            m = re.search(r'^\*UPDATE:\s*(?P<location_name>[^\*]*)\*\s*(?P<description>.*)\s*-\s*(?P<reporter>.*?)\#\#\#$', record['summary'])
            if not m:
                self.logger.warn('Could not parse update %r' % record['summary'])
                raise SkipRecord('Could not parse update %r' % record['summary'])
            record.update(m.groupdict())
            record.update({
                'is_update': True,
                'incident_type': '',
                'fire_station': '',
                'radio_channels': '',
                'incident_time': '',
            })
        else: # Not an update
            m = re.search(r'^\*(?P<incident_type>[^\*]*)\*\s*(?P<location_name>[^;]*);\s*MAP (?:\d+[- ]\w\d)?;\s*FS (?P<fire_station>\d+); (?P<description>.*?); Ch:(?P<radio_channels>[\d, ]+)\s*@(?P<incident_time>\d\d?:\d\d [AP]M)?\s*-(?P<reporter>.*?)\#\#\#$', record['summary'])
            if not m:
                raise SkipRecord('Could not parse %r' % record['summary'])
            record.update(m.groupdict())
            record['incident_type'] = record['incident_type'].upper() # Normalize
            record['radio_channels'] = ','.join(record['radio_channels'].split(','))
            record['is_update'] = False
        record['description'] = record['description'].replace('&nbsp;', ' ').replace('&quot;', '"').replace('&amp;', '&').strip()
        record['location_name'] = record['location_name'].strip()

        # Get the incident ID and message ID from the Google Groups URL.
        # We'll use these as unique identifiers.
        m = re.search(r'browse_thread/thread/(?P<incident_id>[^/]*)/(?P<message_id>[^\?]*)\?', rss_record['link'])
        if not m:
            raise ScraperBroken('Got weird URL: %r', rss_record['link'])
        record.update(m.groupdict())
        record['link'] = rss_record['link']

        # I can't figure out why this record is causing errors, so for now
        # we'll just skip it.
        if record['message_id'] == '0faabeab3aad8492':
            raise SkipRecord()

        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            qs = qs.by_attribute(self.schema_fields['message_id'], record['message_id'])
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            return
        incident_type = self.get_or_create_lookup('incident_type', list_record['incident_type'], list_record['incident_type'], make_text_slug=False)
        reporter = self.get_or_create_lookup('reporter', list_record['reporter'], list_record['reporter'])
        fire_station = self.get_or_create_lookup('fire_station', list_record['fire_station'], list_record['fire_station'])
        attributes = {
            'incident_type': incident_type.id,
            'description': list_record['summary'],
            'reporter': reporter.id,
            'fire_station': fire_station.id,
            'incident_time': list_record['incident_time'],
            'incident_id': list_record['incident_id'],
            'message_id': list_record['message_id'],
        }
        if list_record['is_update']:
            title = 'Update' # TODO: Better title that takes into account the incident type.
        else:
            title = incident_type.name
        self.create_newsitem(
            attributes,
            title=title,
            description=list_record['description'],
            url=list_record['link'],
            item_date=list_record['pub_date'],
            location_name=list_record['location_name'],
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    AlertScraper().update()
