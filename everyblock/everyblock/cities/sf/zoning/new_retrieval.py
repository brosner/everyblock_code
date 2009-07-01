"""
Screen scraper for SF zoning changes.
http://sfgov.org/site/planning_meeting.asp?id=15840

"""

import time
from datetime import datetime
from lxml.html import document_fromstring
from ebdata.blobs.models import Blob
from ebdata.retrieval import UnicodeRetriever
from ebpub.db.models import Schema

class ZoningUpdater(object):
    def __init__(self):
        self.url = 'http://sfgov.org/site/planning_meeting.asp?id=15840'
        self.retriever = UnicodeRetriever()
        self.delay = 2

    def update(self):
        for year in self.get_years(self.url):
            self.update_year(year['url'])

    def get_years(self, url):
        html = self.retriever.get_html(url)
        t = document_fromstring(html)
        for a in t.xpath("//table[@id='Table4']//a"):
            year_url = 'http://sfgov.org/site/planning_meeting.asp%s' % a.get('href')[:-8]
            yield {'url': year_url, 'year': a.text}

    def update_year(self, url):
        minutes_schema = Schema.objects.get(slug='zoning-minutes')
        agendas_schema = Schema.objects.get(slug='zoning-agenda')
        for page in self.get_minutes(url):
            self.save_page(page, minutes_schema)
        for page in self.get_agendas(url):
            self.save_page(page, agendas_schema)

    def get_minutes(self, url):
        return self._helper(url, 'Minutes')

    def get_agendas(self, url):
        return self._helper(url, 'Agendas')

    def _helper(self, url, item_type):
        html = self.retriever.get_html(url)
        t = document_fromstring(html)
        for a in t.xpath("//a[@name='%s']/parent::td/parent::tr/following-sibling::*[4]//a" % item_type):
            if '(cancellation notice)' in a.text.lower():
                continue
            url = 'http://sfgov.org/site/%s' % a.get('href')
            yield {'title': a.text, 'url': url}

    def save_page(self, page, schema):
        url = page['url']
        # If we've already retrieved the page, there's no need to retrieve
        # it again.
        try:
            Blob.objects.filter(url=url)[0]
        except IndexError:
            pass
        else:
            #self.logger.debug('URL %s has already been retrieved', url)
            return

        # Fetch the html for the page and save it
        html = self.retriever.get_html(url + '&mode=text')
        b = Blob(
            schema=schema,
            title=page['title'],
            url=url,
            html=html,
            is_pdf=False,
            when_crawled=datetime.now(),
            has_addresses=None,
            when_geocoded=None,
            geocoded_by=''
        ).save()

        time.sleep(self.delay)

def update():
    s = ZoningUpdater()
    s.update()

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    update()
