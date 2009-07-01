from ebdata.blobs.scrapers import PageAreaCrawler
import re
import urlparse

class MiamiPressReleaseScraper(PageAreaCrawler):
    schema = 'city-press-releases'
    seed_url = 'http://www.miamigov.com/cms/comm/1724.asp'
    date_headline_re = re.compile(r'(?si)For Immediate Release<br>(?:[a-z]+, )?(?P<article_date>[a-z]+ \d\d?, \d\d\d\d)</p>.*?<FONT size=5>(?P<article_headline>.*?)</FONT>')
    date_format = '%B %d, %Y'

    def get_links(self, html):
        m = re.search(r'(?si)<div id="pageHeader">\s*News&nbsp;\s*</div>(.*?)<hr id="footerHR" />', html)
        area = m.group(1)
        return [urlparse.urljoin(self.seed_url, link) for link in re.findall('<a href="([^"]*)"', area)]

class CoralGablesPressReleaseScraper(PageAreaCrawler):
    schema = 'city-press-releases'
    seed_url = 'http://www.citybeautiful.net/CGWeb/newslist.aspx?newsid=ALL'
    date_headline_re = re.compile(r"(?si)<font class ='bodycopy'>(?P<article_date>\d\d?/\d\d?/\d\d\d\d): </font><font class='headline'>(?P<article_headline>.*?)</font>")
    date_format = '%m/%d/%Y'

    def get_links(self, html):
        return [urlparse.urljoin(self.seed_url, link) for link in re.findall("<a href='([^']*)'>Read full story</a>", html)]

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    MiamiPressReleaseScraper().update()
    CoralGablesPressReleaseScraper().update()
