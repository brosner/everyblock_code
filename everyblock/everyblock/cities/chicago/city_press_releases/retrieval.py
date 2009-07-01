from ebdata.blobs.scrapers import IncrementalCrawler
import re

class ChicagoCityPressReleaseCrawler(IncrementalCrawler):
    schema = 'city-press-releases'
    seed_url = 'http://egov.cityofchicago.org/'
    date_headline_re = re.compile(r'(?s)E-mail: <a href="mailto:[^"]*">.*?</a><br>\s*(?P<article_date>.*?)\s*</td>\s*</tr>\s*<tr>\s*<td align="center" class="bodytextbold">(?P<article_headline>.*?)</td>')
    date_format = '%A, %B %d, %Y'
    max_blanks = 60

    def public_url(self, id_value):
        return 'http://egov.cityofchicago.org/city/webportal/portalContentItemAction.do?contenTypeName=COC_EDITORIAL&topChannelName=HomePage&contentOID=%s' % id_value

    def retrieval_url(self, id_value):
        return 'http://egov.cityofchicago.org/city/webportal/jsp/content/showNewsItem.jsp?print=true&contenTypeName=1006&contentOID=%s' % id_value

    def id_for_url(self, url):
        return url.split('contentOID=')[1]

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    ChicagoCityPressReleaseCrawler().update()
