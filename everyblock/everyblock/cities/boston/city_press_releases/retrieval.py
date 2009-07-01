"""
Boston city press release scraper.

http://www.cityofboston.gov/news/
Example: http://www.cityofboston.gov/news/default.aspx?id=3910
"""

from ebdata.blobs.scrapers import IncrementalCrawler
import re

class BostonCityPressReleaseCrawler(IncrementalCrawler):
    schema = 'city-press-releases'
    seed_url = 'http://www.cityofboston.gov/news/'
    date_headline_re = re.compile(r'(?si)<span id="lblTitle">(?P<article_headline>[^>]*)</span>.*?<span id="lblDate">(?P<article_date>\d\d?/\d\d?/\d\d\d\d)</span>')
    date_format = '%m/%d/%Y'
    max_blanks = 8

    def public_url(self, id_value):
        return 'http://www.cityofboston.gov/news/default.aspx?id=%s' % id_value

    def id_for_url(self, url):
        return url.split('id=')[1]

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    BostonCityPressReleaseCrawler().update()
