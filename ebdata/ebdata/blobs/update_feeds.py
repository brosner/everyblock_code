"""
RSS-feed retriever
"""

from ebdata.blobs.geotagging import save_locations_for_page
from ebdata.blobs.models import Seed, Page
from ebdata.retrieval import UnicodeRetriever
from ebdata.retrieval import log # Register the logging hooks.
from ebdata.templatemaker.htmlutils import printer_friendly_link
from ebdata.textmining.treeutils import make_tree
from ebpub.utils.dates import parse_date
import feedparser
import cgi
import datetime
import logging
import re
import time
import urllib
import urlparse

strip_tags = lambda x: re.sub(r'<[^>]*>', ' ', x).replace('&nbsp;', ' ')
server_authority_re = re.compile('^(?:([^\@]+)\@)?([^\:]+)(?:\:(.+))?$')
url_collapse_re = re.compile('([^/]+/\.\./?|/\./|//|/\.$|/\.\.$)')

def remove_query_string(url):
    bits = urlparse.urlparse(url)
    return urlparse.urlunparse(bits[:4] + ('',) + bits[5:])

def add_query_string(url, new_values):
    bits = urlparse.urlparse(url)
    qs = cgi.parse_qs(bits[4], keep_blank_values=True)
    qs.update(new_values)
    return urlparse.urlunparse(bits[:4] + (urllib.urlencode(qs, doseq=True),) + bits[5:])

def normalize_url(base_href, url, normalize_www_flag):
    """
    Normalizes the given URL:
        * Joins it with base_href if it doesn't already have a domain.
        * Lowercases the scheme (WWW.GOOGLE.COM -> www.google.com).
        * Removes the port (80 or 443) if it's default.
        * Collapses '../' and './'.
        * Alphabetizes the query string by its keys.
        * If it ends in '/index.html', removes the 'index.html'.
        * Normalizes the 'www.' subdomain according to normalize_www_flag.
    Returns None if the URL is invalid.

    normalize_www_flag should be either 1, 2 or 3:
        * 1 = Remove the 'www.' subdomain, if it exists.
        * 2 = Add a 'www.' subdomain, if a subdomain doesn't exist.
        * 3 = Don't touch the subdomain.
    """
    # Inspired by http://www.mnot.net/python/urlnorm.py -- BSD license.
    url = urlparse.urljoin(base_href, url)
    scheme, authority, path, parameters, query, fragment = urlparse.urlparse(url)
    scheme = scheme.lower()
    if '.' not in authority:
        return None
    if authority:
        userinfo, host, port = server_authority_re.match(authority).groups()
        if host[-1] == '.':
            host = host[:-1]

        # Normalize the www subdomain, if necessary.
        if normalize_www_flag == 1 and host.startswith('www.'):
            host = host[4:]
        elif normalize_www_flag == 2 and host.count('.') == 1:
            host = 'www.' + host

        authority = host.lower()
        if userinfo:
            authority = "%s@%s" % (userinfo, authority)
        if port and port != {'http': '80', 'https': '443'}.get(scheme):
            authority = "%s:%s" % (authority, port)

    if scheme.startswith('http'):
        last_path = path
        while 1:
            path = url_collapse_re.sub('/', path, 1)
            if last_path == path:
                break
            last_path = path
    if not path:
        path = '/'
    if path.endswith('/index.html'):
        path = path[:-10] # Trim trailing "index.html".
    if query:
        # Reorder the query string to alphabetize the keys.
        query_bits = sorted(cgi.parse_qsl(query, keep_blank_values=True))
        query = '&'.join(['%s=%s' % (k, v) for k, v in query_bits])
    return urlparse.urlunparse((scheme, authority, path, parameters, query, ''))

try:
    # any() built-in only in Python >= 2.5
    any
except NameError:
    def any(iterable):
        for element in iterable:
            if element:
                return True
        return False

class FeedUpdater(object):
    def __init__(self, seed, retriever, logger):
        self.seed = seed
        self.retriever = retriever
        self.logger = logger

    def update(self):
        try:
            feed = feedparser.parse(self.seed.url)
        except UnicodeDecodeError:
            self.logger.info('UnicodeDecodeError on %r', self.seed.url)
            return
        for entry in feed['entries']:
            if 'feedburner_origlink' in entry:
                url = entry['feedburner_origlink']
            elif 'pheedo_origLink' in entry:
                url = entry['pheedo_origLink']
            elif 'link' in entry:
                url = entry['link']
            else:
                continue # Skip entries with no link.

            try:
                url = normalize_url(self.seed.base_url, url, self.seed.normalize_www)
            except Exception:
                self.logger.warn('Problem normalizing URL: %r, %r, %r', self.seed.base_url, url, self.seed.normalize_www)
                continue

            if not url:
                self.logger.info('Skipping article with empty URL: %r, %r', self.seed.base_url, url)
                continue

            if len(url) > 512:
                self.logger.warning('Skipping long URL %s', url)
                continue

            article_date = entry.get('updated_parsed') and datetime.date(*entry['updated_parsed'][:3]) or None
            if article_date and article_date > datetime.date.today():
                # Skip articles in the future, because sometimes articles show
                # up in the feed before they show up on the site, and we don't
                # want to retrieve the article until it actually exists.
                self.logger.info('Skipping article_date %s, which is in the future', article_date)
                continue

            url = self.normalize_url(url)

            try:
                title = entry['title']
            except KeyError:
                self.logger.debug('Skipping %s due to missing title', url)
                continue

            if not self.download_page(url, title):
                self.logger.debug('Skipping %s due to download_page()', url)
                continue

            # If we've already retrieved the page, there's no need to retrieve
            # it again.
            try:
                Page.objects.filter(url=url)[0]
            except IndexError:
                pass
            else:
                self.logger.debug('URL %s has already been retrieved', url)
                continue

            # If this seed contains the full content in the RSS feed <summary>,
            # then we just use it instead of downloading the contents.
            if self.seed.rss_full_entry:
                is_printer_friendly = False
                try:
                    html = entry['summary']
                except KeyError:
                    html = entry['description']
            else:
                is_printer_friendly = False
                html = None
                time.sleep(self.seed.delay)

                # First, try deducing for the printer-friendly page, given the URL.
                print_url = self.get_printer_friendly_url(url)
                if print_url is not None:
                    try:
                        html = self.get_article_page(print_url)
                        is_printer_friendly = True
                    except Exception, e:
                        self.logger.info('Error retrieving supposedly accurate printer-friendly page %s: %s', print_url, e)

                # If a printer-friendly page didn't exist, get the real page.
                if html is None:
                    try:
                        html = self.get_article_page(url)
                    except Exception, e:
                        self.logger.info('Error retrieving %s: %s', url, e)
                        continue

                    # If a page was downloaded, try looking for a printer-friendly
                    # link, and download that.
                    print_page = self.get_printer_friendly_page(html, url)
                    if print_page is not None:
                        is_printer_friendly = True
                        html = print_page

                new_html = self.scrape_article_from_page(html)
                if new_html is not None:
                    html = new_html

                if article_date is None:
                    article_date = self.scrape_article_date_from_page(html)

            if not html.strip():
                self.logger.debug('Got empty HTML page')
                continue

            article_headline = strip_tags(title)
            if len(article_headline) > 252:
                article_headline = article_headline[252:] + '...'
            p = Page.objects.create(
                seed=self.seed,
                url=url,
                scraped_url=(is_printer_friendly and print_url or url),
                html=html,
                when_crawled=datetime.datetime.now(),
                is_article=True,
                is_pdf=False,
                is_printer_friendly=is_printer_friendly,
                article_headline=article_headline,
                article_date=article_date,
                has_addresses=None,
                when_geocoded=None,
                geocoded_by='',
                times_skipped=0,
                robot_report='',
            )
            self.logger.info('Created %s story %r', self.seed.base_url, article_headline)
            save_locations_for_page(p)

    def normalize_url(self, url):
        """
        Given the article URL, returns a normalized version of the URL.
        """
        return url

    def download_page(self, url, article_headline):
        """
        Given the URL and headline from RSS, returns True if this page should
        be downloaded, and False if it can be skipped.
        """
        return True

    def get_article_page(self, url):
        return self.retriever.get_html(url)

    def get_printer_friendly_url(self, url):
        """
        Given a story URL, returns the printer-friendly URL, or None if it
        can't be determined.
        """
        return None

    def get_printer_friendly_page(self, html, url):
        """
        Parses the given detail page and returns the printer-friendly page, or
        None if not found.
        """
        print_link = printer_friendly_link(make_tree(html))
        if print_link:
            print_link = urlparse.urljoin(url, print_link)
            try:
                return self.get_article_page(print_link)
            except Exception, e:
                self.logger.debug('Error retrieving printer-friendly page %s: %s', url, e)
                return None
        else:
            return None

    def scrape_article_from_page(self, html):
        """
        Parses the given detail page and returns the article as a string, or
        None if it can't be found.
        """
        return html

    def scrape_article_date_from_page(self, html):
        """
        Parses the given detail page and returns the article date as a
        datetime.date, or None if it can't be found.
        """
        return None

def update(seed_id=None):
    """
    Retrieves and saves every new item for every Seed that is an RSS feed.
    """
    retriever = UnicodeRetriever(cache=None)
    logger = logging.getLogger('eb.retrieval.blob_rss')
    qs = Seed.objects.filter(is_rss_feed=True, is_active=True)
    if seed_id is not None:
        qs = qs.filter(id=seed_id)
    for seed in qs:
        updater = FeedUpdater(seed, retriever, logger)
        updater.update()

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    update()
