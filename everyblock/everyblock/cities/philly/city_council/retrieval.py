"""
Scrapers for city council items

http://legislation.phila.gov/calendar/
"""

from ebdata.blobs.models import Seed, Page
from ebdata.parsing.pdftotext import pdf_to_text
from ebdata.retrieval.scrapers.base import BaseScraper, ScraperBroken
from ebpub.utils.dates import parse_date
from lxml.html import document_fromstring
import datetime
import re
import os

ROOT_URI = 'http://legislation.phila.gov/calendar/search.aspx'

class CityCouncilCalendarScraper(BaseScraper):
    def get_viewstate(self, uri):
        html = self.get_html(uri)
        m = re.search(r'<input type="hidden" name="__VIEWSTATE" value="([^"]*)"', html)
        if not m:
            raise ScraperBroken('VIEWSTATE not found')
        return m.group(1)

    def search_args(self):
        viewstate = self.get_viewstate(ROOT_URI)
        return {
            '__EVENTARGUMENT': '',
            '__EVENTTARGET': 'cboBody',
            '__VIEWSTATE': viewstate,
            'cboBody': self.cboBody,
            'cboYear': str(datetime.date.today().year),
            'txtSearchTerm': ''
        }

    def get_pages(self):
        html = self.retriever.get_html(ROOT_URI, self.search_args())
        t = document_fromstring(html)
        for a in t.xpath("//table[@id='grdCalendar']//a"):
            url = a.get('href')
            title = a.text or ''
            if url is None or self.already_downloaded(url):
                continue
            pdf_path = self.retriever.get_to_file(url)
            m = re.search(r'(\d{2}-\d{2}-\d{2})', url)
            date = parse_date(m.group(1), '%y-%m-%d')
            yield {
                'url': url,
                'data': self.parse_pdf(pdf_path),
                'title': title,
                'date': date
            }
            os.unlink(pdf_path) # Clean up the temporary file.

    def parse_pdf(self, pdf_path):
        return pdf_to_text(pdf_path, keep_layout=True, raw=False).decode('Latin-1')

    def already_downloaded(self, url):
        try:
            pages = Page.objects.filter(url=url)[0]
            return True
        except IndexError:
            return False

    def save(self, page):
        if not hasattr(self, 'seed'):
            self.seed = Seed.objects.get(schema__slug__exact=self.schema_name)
        return Page.objects.create(
            seed=self.seed,
            url=page['url'],
            scraped_url=page['url'],
            html=page['data'],
            when_crawled=datetime.datetime.now(),
            is_article=True,
            is_pdf=True,
            is_printer_friendly=False,
            article_headline=self.get_headline(page),
            article_date=page['date'],
            has_addresses=None,
            when_geocoded=None,
            geocoded_by='',
            times_skipped=0,
            robot_report='',
        )

    def update(self):
        for page in self.get_pages():
            self.save(page)

class StreetsAndServicesScraper(CityCouncilCalendarScraper):
    cboBody = '41' # an identifier for streets and services
    schema_name = 'streets-and-services'

    def get_headline(self, page):
        return "City Council Streets and Services committee meeting agenda item, %s" % page['date'].strftime('%B %d, %Y')

class PublicPropertyAndPublicWorksScraper(CityCouncilCalendarScraper):
    cboBody= '42' # an identifier for public propert and public works
    schema_name = 'public-works'

    def get_headline(self, page):
        return "City Council Public Works committee meeting agenda item, %s" % page['date'].strftime('%B %d, %Y')

class ZoningScraper(CityCouncilCalendarScraper):
    cboBody= '53'
    schema_name = 'rules'

    def get_headline(self, page):
        return "City Council committee on Rules meeting agenda item, %s" % page['date'].strftime('%B %d, %Y')

def update():
    StreetsAndServicesScraper().update()
    PublicPropertyAndPublicWorksScraper().update()
    ZoningScraper().update()

if __name__ == '__main__':
    from ebdata.retrieval import log_debug
    update()
