"""
Site-specific scrapers for NYC news sources that don't have RSS feeds.
"""

from ebdata.blobs.scrapers import IncrementalCrawler
import re

class BrooklynEagleCrawler(IncrementalCrawler):
    schema = 'news-articles'
    seed_url = 'http://www.brooklyneagle.com/'
    date_headline_re = re.compile(r'<b><span class="f24">(?P<article_headline>.*?)</span></b><div align="justify" class="f11">.*?, published online <span[^>]*>(?P<article_date>\d\d?-\d\d?-\d\d\d\d)</span></div>')
    date_format = '%m-%d-%Y'
    max_blanks = 7

    def public_url(self, id_value):
        # Note that the category_id doesn't matter.
        return 'http://www.brooklyneagle.com/categories/category.php?id=%s' % id_value

    def id_for_url(self, url):
        return url.split('id=')[1]

class Ny1Crawler(IncrementalCrawler):
    schema = 'news-articles'
    seed_url = 'http://www.ny1.com/'
    date_headline_re = re.compile(r'<span id="ArPrint_lblArHeadline" class="blackheadline1">(?P<article_headline>.*?)</span><br />\s*<span id="ArPrint_lblArPostDate" class="black11">(?:<strong>Updated&nbsp;</strong>)?(?P<article_date>\d\d?/\d\d?/\d\d\d\d)')
    date_format = '%m/%d/%Y'
    max_blanks = 7

    def public_url(self, id_value):
        return 'http://www.ny1.com/Default.aspx?ArID=%s' % id_value

    def retrieval_url(self, id_value):
        return 'http://www.ny1.com/printarticle.aspx?ArID=%s' % id_value

    def id_for_url(self, url):
        return url.split('ArID=')[1]

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    BrooklynEagleCrawler().update()
    Ny1Crawler().update()
