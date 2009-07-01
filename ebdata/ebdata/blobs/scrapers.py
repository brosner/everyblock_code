"""
Generic scrapers that create Pages based on some common Web site patterns.
"""

from django.conf import settings
from django.utils.html import strip_tags
from ebdata.blobs.geotagging import save_locations_for_page
from ebdata.blobs.models import Seed, Page
from ebdata.retrieval import UnicodeRetriever, RetrievalError
from ebdata.retrieval import log # Register the logging hooks.
from ebpub.utils.dates import parse_date
import datetime
import logging

class NoPagesYet(Exception):
    pass

class NoSeedYet(Exception):
    pass

class SpecializedCrawler(object):
    """
    Base class for Page crawlers.
    """

    schema = None
    seed_url = None
    date_headline_re = None
    date_format = None
    retriever = None

    def __init__(self):
        try:
            self.seed = Seed.objects.get(url=self.seed_url)
        except Seed.DoesNotExist:
            raise NoSeedYet('You need to add a Seed with the URL %r' % self.seed_url)
        self.logger = logging.getLogger('eb.retrieval.%s.%s' % (settings.SHORT_NAME, self.schema))
        if self.retriever is None:
            self.retriever = UnicodeRetriever(cache=None, sleep=self.seed.delay)

    def save_page(self, unique_id):
        """
        Downloads the page with the given unique ID (possibly a numeric ID, or
        a URL) and saves it as a Page object. Returns the Page object, or None
        if the page couldn't be found.

        The page won't be retrieved/saved if it's already in the database. In
        this case, the existing Page object will be returned.
        """
        self.logger.debug('save_page(%s)', unique_id)
        retrieval_url = self.retrieval_url(unique_id)
        public_url = self.public_url(unique_id)

        try:
            p = Page.objects.get(seed__id=self.seed.id, url=public_url)
        except Page.DoesNotExist:
            pass
        else:
            self.logger.debug('Skipping already-saved URL %s', public_url)
            return p

        try:
            html = self.retriever.get_html(retrieval_url).strip()
        except (RetrievalError, UnicodeDecodeError):
            return None
        if not html:
            self.logger.debug('Got empty page for %s', retrieval_url)
            return None
        self.logger.debug('Got VALID page for %s', retrieval_url)

        m = self.date_headline_re.search(html)
        if not m:
            self.logger.debug('Could not find date/headline on %s', retrieval_url)
            return None
        article_date, article_headline = m.groupdict()['article_date'], m.groupdict()['article_headline']
        try:
            article_date = parse_date(article_date, self.date_format)
        except ValueError:
            self.logger.debug('Got unparseable date %r on %s', article_date, retrieval_url)
            return None
        article_headline = strip_tags(article_headline)
        if len(article_headline) > 255:
            article_headline = article_headline[:252] + '...'

        p = Page.objects.create(
            seed=self.seed,
            url=public_url,
            scraped_url=retrieval_url,
            html=html,
            when_crawled=datetime.datetime.now(),
            is_article=True,
            is_pdf=False,
            is_printer_friendly=False,
            article_headline=article_headline,
            article_date=article_date,
            has_addresses=None,
            when_geocoded=None,
            geocoded_by='',
            times_skipped=0,
            robot_report='',
        )
        self.logger.debug('Created Page ID %s' % p.id)
        save_locations_for_page(p)
        return p

    ######################################
    # METHODS SUBCLASSES SHOULD OVERRIDE #
    ######################################

    def public_url(self, unique_id):
        "Given the ID value, returns the URL that we should publish."
        raise NotImplementedError()

    def retrieval_url(self, unique_id):
        "Given the ID value, returns the URL that we should scrape."
        return self.public_url(unique_id)

class IncrementalCrawler(SpecializedCrawler):
    """
    Crawler that populates the blobs.Page table by incrementing IDs.

    This is a very "dumb" but effective technique for crawling sites such
    as cityofchicago.org whose pages have incremental ID numbers.

    LIMITATIONS/ASSUMPTIONS:

    * This assumes that the URL for each retrieved page is in the same format,
      such that ordering by the URL will result in the highest ID.
    * This assumes that a Seed exists with url=self.seed_url.
    * Before running update(), at least one Page with the given seed must
      exist. Otherwise the retriever won't know what the latest page is!
    """

    max_blanks = 10

    ##################################################
    # METHODS SUBCLASSES SHOULD NOT HAVE TO OVERRIDE #
    ##################################################

    def max_id(self):
        "Returns the ID of the latest page we've already crawled."
        try:
            latest_page = Page.objects.filter(seed__id=self.seed.id).order_by('-url')[0]
        except IndexError:
            raise NoPagesYet('Seed ID %s has no pages yet' % self.seed.id)
        return int(self.id_for_url(latest_page.url))

    def update(self):
        """
        Determines the ID of the latest page we've already crawled, and crawls
        until self.max_blanks blank pages are reached.
        """
        current_id = self.max_id()
        num_blanks = 0
        while num_blanks < self.max_blanks:
            current_id += 1
            page = self.save_page(current_id)
            if page:
                num_blanks = 0
            else:
                num_blanks += 1

    def save_id_range(self, first_id, last_id):
        """
        Downloads and saves Pages for the given ID range, inclusive. Pages
        won't be saved if they're already in the database.
        """
        for id_value in range(int(first_id), int(last_id)+1):
            self.save_page(id_value)

    ######################################
    # METHODS SUBCLASSES SHOULD OVERRIDE #
    ######################################

    def id_for_url(self, url):
        "Given a URL, returns its ID value. This can be either a string or int."
        raise NotImplementedError()

class PageAreaCrawler(SpecializedCrawler):
    """
    Crawler that finds specific links on a given index page (seed_url)
    and creates a blobs.Page for each link that hasn't yet been created.
    """

    ##################################################
    # METHODS SUBCLASSES SHOULD NOT HAVE TO OVERRIDE #
    ##################################################

    def update(self):
        seed_html = self.retriever.get_html(self.seed_url)
        for url in self.get_links(seed_html):
            self.save_page(url)

    def public_url(self, unique_id):
        return unique_id

    ######################################
    # METHODS SUBCLASSES SHOULD OVERRIDE #
    ######################################

    def get_links(self, html):
        """
        Given the seed HTML, returns the list of links.
        """
        raise NotImplementedError()
