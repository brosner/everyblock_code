"""
Scraper for Mecklenberg County Board Minutes

http://www.charmeck.org/Departments/BOCC/Meetings/Meeting+Minutes/Home.htm
"""

from ebdata.blobs.geotagging import save_locations_for_page
from ebdata.blobs.models import Page, Seed
from ebdata.parsing.pdftotext import pdf_to_text
from ebdata.retrieval.scrapers.base import BaseScraper
from dateutil.parser import parse as parse_date
from lxml.html import document_fromstring
import os
import datetime

ROOT_URI = 'http://www.charmeck.org/Departments/BOCC/Meetings/Meeting+Minutes/Home.htm'

class BoardMinutesScraper(BaseScraper):
    schema_name = 'county-board-proceedings'

    def get_to_file(self, *args, **kwargs):
        if self.retriever._cookies:
            # Build the Cookie header manually. We get:
            #   socket.error: (54, 'Connection reset by peer')
            # if we send newline separated cookies. Semicolon separated works fine.
            cookie = self.retriever._cookies.output(attrs=[], header='', sep=';').strip()
            kwargs['send_cookies'] = False
            kwargs['headers'] = {'Cookie': cookie}
        return self.retriever.get_to_file(*args, **kwargs)

    def list_pages(self):
        html = self.get_html(ROOT_URI)
        t = document_fromstring(html)
        for link in t.xpath("//table[@id='Table8']//a"):
            if not link.get('href')[-4:] == '.pdf':
                continue
            url = "http://www.charmeck.org%s" % link.get('href')
            title = link.text or ''
            if self.already_downloaded(url):
                continue
            pdf_path = self.get_to_file(url)
            yield {
                'title': title,
                'url': url,
                'data': self.parse_pdf(pdf_path),
                'date': parse_date(title, fuzzy=True)
            }
            os.unlink(pdf_path) # Clean up the temporary file.

    def parse_pdf(self, pdf_path):
        return pdf_to_text(pdf_path, keep_layout=True, raw=False).decode('Latin-1')

    def already_downloaded(self, url):
        try:
            blobs = Page.objects.filter(url=url)[0]
            return True
        except IndexError:
            return False

    def save(self, page):
        if not hasattr(self, 'seed'):
            self.seed = Seed.objects.get(schema__slug__exact=self.schema_name)
        p = Page.objects.create(
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
        )
        save_locations_for_page(p)
        return p

    def update(self):
        for page in self.list_pages():
            self.save(page)

    def get_headline(self, page):
        return "Mecklenberg County Board item, %s" % page['date'].strftime('%B %d, %Y')

if __name__ == '__main__':
    from ebdata.retrieval import log_debug
    BoardMinutesScraper().update()
