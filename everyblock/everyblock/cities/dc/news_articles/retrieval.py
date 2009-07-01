"""
Site-specific scrapers for DC news sources that don't have RSS feeds.
"""

from ebdata.blobs.scrapers import IncrementalCrawler
import re

class WashingtonCityPaperCrawler(IncrementalCrawler):
    schema = 'news-articles'
    seed_url = 'http://www.washingtoncitypaper.com/'
    date_headline_re = re.compile(r'(?s)<h1 class="article-headline">(?P<article_headline>.*?)</h1>.*?<span class="article-date">Posted: (?P<article_date>\w+ \d\d?, \d\d\d\d)</span>')
    date_format = '%B %d, %Y'
    max_blanks = 7

    def public_url(self, id_value):
        return 'http://www.washingtoncitypaper.com/display.php?id=%s' % id_value

    def retrieval_url(self, id_value):
        return 'http://www.washingtoncitypaper.com/printerpage.php?id=%s' % id_value

    def id_for_url(self, url):
        return url.split('id=')[1]

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    WashingtonCityPaperCrawler().update()
