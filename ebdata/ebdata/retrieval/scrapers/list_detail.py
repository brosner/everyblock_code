from base import BaseScraper, ScraperBroken

class SkipRecord(Exception):
    "Exception that signifies a detail record should be skipped over."
    pass

class StopScraping(Exception):
    "Exception that signifies scraping should stop."
    pass

class ListDetailScraper(BaseScraper):
    """
    A screen-scraper optimized for list-detail types of sites.

    A list-detail site is a site that displays a list of records, which might
    be paginated. Each record might have its own page -- a "detail" page -- or
    the list page might display all available information for that record.

    To use this class, subclass it and implement the following:

        * list_pages()
        * Either parse_list() or parse_list_re
        * existing_record()
        * save()

    If the scraped site does not have detail pages, implement the following:

        * has_detail = False

    If the scraped site has detail pages, implement the following:

        * detail_required()
        * get_detail()
        * Either parse_detail() or parse_detail_re

    These are additional, optional hooks:

        * clean_list_record()
        * clean_detail_record()
    """

    ################################
    # MAIN METHODS FOR OUTSIDE USE #
    ################################

    def display_data(self):
        """
        Retrieves all pages, parses them and prints the data as Python
        dictionaries to standard output.

        This is mainly useful for debugging.
        """
        from pprint import pprint
        for d in self.raw_data():
            pprint(d)

    def raw_data(self):
        """
        Iterator that yields *all* current raw data for this scraper,
        regardless of whether it's existing or not.

        Each record is represented as a {'list', 'detail'} dictionary,
        where `list` is the clean list record and `detail` is the clean
        detail record.
        """
        for page in self.list_pages():
            for list_record in self.parse_list(page):
                try:
                    list_record = self.clean_list_record(list_record)
                except SkipRecord:
                    continue
                if self.has_detail:
                    try:
                        page = self.get_detail(list_record)
                        detail_record = self.parse_detail(page, list_record)
                        detail_record = self.clean_detail_record(detail_record)
                    except SkipRecord:
                        continue
                else:
                    detail_record = None
                yield {'list': list_record, 'detail': detail_record}

    def xml_data(self):
        """
        Iterator that yields *all* current raw data for this scraper,
        regardless of whether it's existing or not, as serialized XML.
        """
        from xml.sax.saxutils import escape
        yield u'<data>'
        for d in self.raw_data():
            yield u'<object>'
            for datatype in ('list', 'detail'):
                for k, v in d[datatype].items():
                    if not isinstance(v, basestring):
                        v = str(v)
                    yield u'  <att name="%s-%s">%s</att>' % (datatype[0], k, escape(v))
            yield u'</object>'
        yield u'</data>'

    def update(self):
        """
        The main scraping method. This retrieves all pages, parses them and
        saves the data.

        Subclasses should not have to override this method.
        """
        self.num_skipped = 0
        self.logger.info("update() started")
        try:
            for page in self.list_pages():
                try:
                    self.update_from_string(page)
                except StopScraping:
                    break
        finally:
            self.logger.info("update() finished")

    def update_from_string(self, page):
        """
        For scrapers with has_detail=False, runs the equivalent of update() on
        the given string.

        This is useful if you've got cached versions of HTML that you want to
        parse.

        Subclasses should not have to override this method.
        """
        for list_record in self.parse_list(page):
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
                    page = self.get_detail(list_record)
                    detail_record = self.parse_detail(page, list_record)
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
                detail_record = None

            self.save(old_record, list_record, detail_record)

    def update_from_dir(self, dirname):
        """
        For scrapers with has_detail=False, runs the equivalent of update() on
        every file in the given directory, in sorted order.

        This is useful if you've got cached versions of HTML that you want to
        parse.

        Subclasses should not have to override this method.
        """
        import os
        filenames = os.listdir(dirname)
        filenames.sort()
        for filename in filenames:
            full_name = os.path.join(dirname, filename)
            self.logger.info("Reading from file %s" % full_name)
            page = open(full_name).read()
            self.update_from_string(page)

    ####################################################
    # INTERNAL METHODS THAT SUBCLASSES SHOULD OVERRIDE #
    ####################################################

    parse_list_re = None
    parse_detail_re = None
    has_detail = True

    def list_pages(self):
        """
        Iterator that yields list pages, as strings.

        Usually, this will only yield a single string, but it might yield
        multiple pages if the list is paginated.
        """
        raise NotImplementedError()

    def parse_list(self, page):
        """
        Given the full HTML of a list page, yields a dictionary of data for
        each record on the page.

        You can either implement this method or define a parse_list_re
        attribute. If you define a parse_list_re attribute, it should be set
        to a compiled regular-expression that finds all the records on a list
        page and uses named groups.
        """
        if self.parse_list_re is not None:
            count = 0
            for record in self.parse_list_re.finditer(page):
                yield record.groupdict()
                count += 1
            if count == 0:
                self.logger.info('%s.parse_list_re found NO records', self.__class__.__name__)
        else:
            raise NotImplementedError()

    def call_cleaners(self, record):
        """
        Given a dictionary returned by parse_list() or parse_detail(),
        calls any method defined whose name match a pattern based on a
        key in dictionary. The value at the key and the entire record
        are passed in as positional arguments. The patten is
        "_clean_KEY".

        For example, if the record contains a key "restaurant",
        call_cleaners() will call a method _clean_restaurant() if it
        exists.

        The _clean_KEY() callable should return a value that will
        replace the value at the key in the dictionary.

        It is up to the subclass's clean_list_record() and
        clean_detail_record() to call call_cleaners().
        """
        for key, value in record.items():
            meth_name = "_clean_%s" % key
            if hasattr(self, meth_name):
                method = getattr(self, meth_name)
                if callable(method):
                    record[key] = method(value, record)
        return record

    def clean_list_record(self, record):
        """
        Given a dictionary as returned by parse_list(), performs any
        necessary cleanup of the data and returns a dictionary.

        For example, this could convert date strings to datetime objects.
        """
        return record

    def existing_record(self, record):
        """
        Given a cleaned list record as returned by clean_list_record(), returns
        the existing record from the data store, if it exists.

        If an existing record doesn't exist, this should return None.
        """
        raise NotImplementedError()

    def detail_required(self, list_record, old_record):
        """
        Given a cleaned list record and the old record (which might be None),
        returns True if the scraper should download the detail page for this
        record.
        """
        raise NotImplementedError()

    def get_detail(self, record):
        """
        Given a cleaned list record as returned by clean_list_record, retrieves
        and returns the HTML for the record's detail page.
        """
        raise NotImplementedError()

    def parse_detail(self, page, list_record):
        """
        Given the full HTML of a detail page, returns a dictionary of data for
        the record represented on that page.

        You can either implement this method or define a parse_detail_re
        attribute. If you define a parse_detail_re attribute, it should be set
        to a compiled regular-expression that parses the record on a detail
        page and uses named groups.
        """
        if self.parse_detail_re is not None:
            m = self.parse_detail_re.search(page)
            if m:
                self.logger.debug('Got a match for parse_detail_re')
                return m.groupdict()
            self.logger.debug('Did not get a match for parse_detail_re')
            return {}
        else:
            raise NotImplementedError()

    def clean_detail_record(self, record):
        """
        Given a dictionary as returned by parse_detail(), performs any
        necessary cleanup of the data and returns a dictionary.

        For example, this could convert date strings to datetime objects.
        """
        return record

    def save(self, old_record, list_record, detail_record):
        """
        Saves the given record to storage.

        list_record and detail_record are both dictionaries representing the
        data from the list page and detail page, respectively. If the scraped
        site does not have detail pages, detail_record will be None.

        old_record is the existing record, as returned by existing_record(). It
        will be None if there is no existing record.
        """
        raise NotImplementedError()

class RssListDetailScraper(ListDetailScraper):
    """
    A ListDetailScraper for sites whose lists are RSS feeds.

    Subclasses should not have to implement parse_list() or get_detail().
    """
    def parse_list(self, page):
        # The page is an RSS feed, so use feedparser to parse it.
        import feedparser
        self.logger.debug("Parsing RSS feed with feedparser")
        feed = feedparser.parse(page)
        for entry in feed['entries']:
            yield entry

    def get_detail(self, record):
        # Assume that the detail page is accessible via the <link> for this
        # entry.
        return self.get_html(record['link'])
