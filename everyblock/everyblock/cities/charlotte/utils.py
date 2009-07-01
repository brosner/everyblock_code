from ebdata.retrieval.scrapers.base import ScraperBroken
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from dateutil.relativedelta import relativedelta
import csv
import datetime
import time
import re
from cStringIO import StringIO

LOGIN_URI = 'http://dwexternal.co.mecklenburg.nc.us/ids/login.aspx?ReturnUrl=/ids/&AcceptsCookies=1'
USERNAME = ''
PASSWORD = ''

class MecklenburgScraper(NewsItemListDetailScraper):
    """
    Common functionality for scraping data from http://dwexternal.co.mecklenburg.nc.us
    """
    has_detail = False

    def __init__(self, start_date=None, *args, **kwargs):
        # if a start date isn't provided, start scraping data starting 7 days ago
        self.start_date = start_date or datetime.date.today() - relativedelta(days=7)
        super(MecklenburgScraper, self).__init__(*args, **kwargs)

    def login(self):
        html = self.get_html(LOGIN_URI)
        m = re.search(r'<input type="hidden" name="__VIEWSTATE" value="([^"]*)"', html)
        if not m:
            raise ScraperBroken('VIEWSTATE not found')
        viewstate = m.group(1)
        html = self.get_html(LOGIN_URI, {
            '__EVENTTARGET': '',
            '__EVENTARGUMENT': '',
            '__VIEWSTATE': viewstate,
            'btn_Submit': 'Login',
            'Remember_Password': 'on',
            'User_Name': USERNAME,
            'Password': PASSWORD,
            '_ctl1:QUERY': '',
            'fmt': 'standard'
        }, follow_redirects=False)

    def get_html(self, *args, **kwargs):
        if self.retriever._cookies:
            # Build the Cookie header manually. We get:
            #   socket.error: (54, 'Connection reset by peer')
            # if we send newline separated cookies. Semicolon separated works fine.
            cookie = self.retriever._cookies.output(attrs=[], header='', sep=';').strip()
            kwargs['send_cookies'] = False
            kwargs['headers'] = {'Cookie': cookie}
        return super(MecklenburgScraper, self).get_html(*args, **kwargs)

    def get_viewstate(self, uri=None):
        uri = uri or self.root_uri
        html = self.get_html(self.root_uri)
        m = re.search(r'<input type="hidden" name="__VIEWSTATE" value="([^"]*)"', html)
        if not m:
            raise ScraperBroken('VIEWSTATE not found')
        return m.group(1)

    def date_pairs(self):
        d = self.start_date
        while d < datetime.date.today():
            start = d.strftime('%m/%d/%Y')
            end = (d + relativedelta(days=6)).strftime('%m/%d/%Y')
            d += relativedelta(days=7)
            yield (start, end)

    def list_pages(self):
        viewstate = self.get_viewstate()
        for start, end in self.date_pairs():
            args = self.search_arguments(start, end, viewstate)
            yield self.get_html(self.root_uri, data=args)
            time.sleep(10) # Be nice to their servers.

    def parse_list(self, page):
        reader = csv.DictReader(StringIO(page))
        for row in reader:
            yield row

