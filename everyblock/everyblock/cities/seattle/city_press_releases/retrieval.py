"""
Seattle city press release scraper.

http://www.seattle.gov/news/
Example: http://www.seattle.gov/news/detail.asp?ID=8622
"""

from ebdata.blobs.scrapers import IncrementalCrawler
import re

class SeattleCityPressReleaseCrawler(IncrementalCrawler):
    schema = 'city-press-releases'
    seed_url = 'http://www.seattle.gov/news/'
    date_headline_re = re.compile(r'(?si)<b>SUBJECT:</b>&nbsp;&nbsp; (?P<article_headline>.*?)\s*</tr>.*?<b>FOR IMMEDIATE RELEASE:&nbsp;&nbsp;&nbsp;</b><br>\s*(?P<article_date>\d\d?/\d\d?/\d\d\d\d)')
    date_format = '%m/%d/%Y'
    max_blanks = 8

    def public_url(self, id_value):
        return 'http://www.seattle.gov/news/detail.asp?ID=%s' % id_value

    def id_for_url(self, url):
        return url.split('ID=')[1]

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    SeattleCityPressReleaseCrawler().update()
