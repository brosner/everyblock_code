"""
Philly city press release scraper.

http://ework.phila.gov/philagov/news/address.asp
"""

from ebdata.blobs.scrapers import IncrementalCrawler
import re

class PhillyCityPressReleaseCrawler(IncrementalCrawler):
    schema = 'city-press-releases'
    seed_url = 'http://ework.phila.gov/'
    date_headline_re = re.compile(r'(?si)<td valign="top" width="150" class="reldate">(?P<article_date>\d\d?/\d\d?/\d\d\d\d)</td></tr><tr><td valign="top" class="title">(?P<article_headline>.*?)</td>')
    date_format = '%m/%d/%Y'
    max_blanks = 3

    def public_url(self, id_value):
        return 'http://ework.phila.gov/philagov/news/prelease.asp?id=%s' % id_value

    def id_for_url(self, url):
        return url.split('id=')[1]

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    PhillyCityPressReleaseCrawler().update()
