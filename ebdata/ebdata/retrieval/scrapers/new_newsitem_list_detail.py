from ebdata.retrieval.models import ScrapedPage, NewsItemHistory, LIST_PAGE, DETAIL_PAGE
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper as BaseScraper
from ebdata.retrieval.scrapers.list_detail import SkipRecord
from ebdata.retrieval.scrapers.base import ScraperBroken
from ebpub.db.models import NewsItem
import datetime

class NewsItemListDetailScraper(BaseScraper):
    def get_page(self, *args, **kwargs):
        """
        Calls NewsItemScraper's get_html method and returns an unsaved ``Page``
        object wrapping the html.
        """
        schema = kwargs.get('schema', None)
        schema = schema or self.schema
        html = super(NewsItemListDetailScraper, self).get_html(*args, **kwargs)
        return ScrapedPage(url=args[0], when_crawled=datetime.datetime.now(), html=html, schema=schema)

    def update_from_string(self, list_page):
        """
        For scrapers with has_detail=False, runs the equivalent of update() on
        the given string.

        This is useful if you've got cached versions of HTML that you want to
        parse.

        Subclasses should not have to override this method.
        """
        # TODO: Setting the page type should probably happen somewhere else.
        list_page.page_type = LIST_PAGE
        self.num_skipped = 0
        for list_record in self.parse_list(list_page.html):
            try:
                list_record = self.clean_list_record(list_record)
            except SkipRecord, e:
                self.num_skipped += 1
                self.logger.debug("Skipping list record for %r: %s " % (list_record, e))
                continue
            except ScraperBroken, e:
                # Re-raise the ScraperBroken with some addtional helpful information.
                raise ScraperBroken('%r -- %s' % (list_record, e))
            self.logger.debug("Clean list record: %r" % list_record)

            old_record = self.existing_record(list_record)
            self.logger.debug("Existing record: %r" % old_record)

            if self.has_detail and self.detail_required(list_record, old_record):
                self.logger.debug("Detail page is required")
                try:
                    detail_page = self.get_detail(list_record)
                    # TODO: Setting the page type should probably happen somewhere else.
                    detail_page.page_type = DETAIL_PAGE
                    detail_record = self.parse_detail(detail_page.html, list_record)
                    detail_record = self.clean_detail_record(detail_record)
                except SkipRecord, e:
                    self.num_skipped += 1
                    self.logger.debug("Skipping detail record for list %r: %s" % (list_record, e))
                    continue
                except ScraperBroken, e:
                    # Re-raise the ScraperBroken with some addtional helpful information.
                    raise ScraperBroken('%r -- %s' % (list_record, e))
                self.logger.debug("Clean detail record: %r" % detail_record)
            else:
                self.logger.debug("Detail page is not required")
                detail_page = None
                detail_record = None

            self.save(old_record, list_record, detail_record, list_page, detail_page)

    def create_newsitem(self, attributes, list_page=None, detail_page=None, **kwargs):
        """
        Creates and saves a NewsItem with the given kwargs. Returns the new
        NewsItem.

        kwargs MUST have the following keys:
            title
            item_date
            location_name
        For any other kwargs whose values aren't provided, this will use
        sensible defaults.

        attributes is a dictionary to use to populate this NewsItem's Attribute
        object.
        """
        block = location = None
        if 'location' not in kwargs:
            location = self.geocode(kwargs['location_name'])
            if location:
                block = location['block']
                location = location['point']

        # Normally we'd just use "schema = kwargs.get('schema', self.schema)",
        # but self.schema will be evaluated even if the key is found in
        # kwargs, which raises an error when using multiple schemas.
        schema = kwargs.get('schema', None)
        schema = schema or self.schema

        ni = NewsItem.objects.create(
            schema=schema,
            title=kwargs['title'],
            description=kwargs.get('description', ''),
            url=kwargs.get('url', ''),
            pub_date=kwargs.get('pub_date', self.start_time),
            item_date=kwargs['item_date'],
            location=kwargs.get('location', location),
            location_name=kwargs['location_name'],
            location_object=kwargs.get('location_object', None),
            block=kwargs.get('block', block)
        )
        ni.attributes = attributes
        if list_page is not None:
            NewsItemHistory.objects.record_history(ni, list_page)
        if detail_page is not None:
            NewsItemHistory.objects.record_history(ni, detail_page)
        self.logger.info(u'Created NewsItem ID %s' % ni.id)
        self.num_added += 1
        return ni

    def update_existing(self, newsitem, new_values, new_attributes, list_page=None, detail_page=None):
        """
        Given an existing NewsItem and dictionaries new_values and
        new_attributes, determines which values and attributes have changed
        and saves the object and/or its attributes if necessary.
        """
        # First, check the NewsItem's values.
        newsitem_updated = False
        for k, v in new_values.items():
            if getattr(newsitem, k) != v:
                self.logger.info('ID %s %s changed from %r to %r' % (newsitem.id, k, getattr(newsitem, k), v))
                setattr(newsitem, k, v)
                newsitem_updated = True
        if newsitem_updated:
            if list_page is not None:
                NewsItemHistory.objects.record_history(newsitem, list_page)
            if detail_page is not None:
                NewsItemHistory.objects.record_history(newsitem, detail_page)
            newsitem.save()
            self.num_changed += 1
        # Next, check the NewsItem's attributes.
        for k, v in new_attributes.items():
            if newsitem.attributes[k] != v:
                self.logger.info('ID %s %s changed from %r to %r' % (newsitem.id, k, newsitem.attributes[k], v))
                newsitem.attributes[k] = v
