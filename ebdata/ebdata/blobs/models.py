from ebpub.db.models import Schema
from django.db import models
import datetime

class Seed(models.Model):
    url = models.CharField(max_length=512)
    base_url = models.CharField(max_length=512) # e.g., 'http://www.suntimes.com/'
    delay = models.SmallIntegerField()
    depth = models.SmallIntegerField()
    is_crawled = models.BooleanField()
    is_rss_feed = models.BooleanField()
    is_active = models.BooleanField()
    rss_full_entry = models.BooleanField() # If True, then an RSS <entry> contains the whole article.
    normalize_www = models.SmallIntegerField() # 1 = Remove www, 2 = Add www, 3 = Ignore subdomain
    pretty_name = models.CharField(max_length=128) # e.g., 'Chicago Sun-Times'
    schema = models.ForeignKey(Schema) # news-articles, missed-connections, etc.

    # If True, then Pages from this Seed will be automatically address-detected.
    autodetect_locations = models.BooleanField()

    # If True, then robot will use templatemaker.articletext.article_text() to
    # determine Page excerpts.
    guess_article_text = models.BooleanField()

    # If True, then robot will use templatemaker.clean.strip_template() to
    # determine Page excerpts.
    strip_noise = models.BooleanField()

    # An uppercase string of the city that this seed covers -- e.g., 'BROOKLYN'.
    # If given, this city will be used to disambiguate addresses in automatic
    # geocoding.
    city = models.CharField(max_length=64, blank=True)

    def __unicode__(self):
        return self.url

class PageManager(models.Manager):
    def increment_skip(self, page_id):
        # Use this to increment the 'times_skipped' column atomically.
        # I.e., it's better to use this than to call save() on Page objects,
        # because that introduces the possibility of clashes.
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute("UPDATE %s SET times_skipped = times_skipped + 1 WHERE id = %%s" % Page._meta.db_table, (page_id,))
        connection._commit()

    def next_ungeocoded(self, seed_id):
        "Returns the next ungeocoded Page for the given seed_id."
        try:
            return self.select_related().filter(has_addresses__isnull=True, is_article=True, seed__id=seed_id).order_by('times_skipped', 'when_crawled')[0]
        except IndexError:
            raise self.model.DoesNotExist

class Page(models.Model):
    seed = models.ForeignKey(Seed)

    # The publicly displayed URL for this page.
    url = models.CharField(max_length=512, db_index=True)

    # The URL that we actually scraped for this page (possibly a
    # printer-friendly version).
    scraped_url = models.CharField(max_length=512)

    html = models.TextField()
    when_crawled = models.DateTimeField()

    # Whether this page is an "article," as opposed to some sort of index page.
    is_article = models.NullBooleanField()

    # Whether this page is the extracted text of a PDF.
    is_pdf = models.BooleanField()

    # Whether this page is the printer-friendly version.
    is_printer_friendly = models.BooleanField()

    article_headline = models.CharField(max_length=255, blank=True)
    article_date = models.DateField(blank=True, null=True)

    # True = addresses were found
    # False = addresses were not found
    # None = page has not yet been examined
    has_addresses = models.NullBooleanField()

    when_geocoded = models.DateTimeField(blank=True, null=True)
    geocoded_by = models.CharField(max_length=32, blank=True)

    # The number of times this page has been "skipped" in the blob geocoder.
    times_skipped = models.SmallIntegerField()

    robot_report = models.CharField(max_length=255, blank=True)

    objects = PageManager()

    def __unicode__(self):
        return u'%s scraped %s' % (self.url, self.when_crawled)

    def set_no_locations(self, geocoded_by='robot'):
        """
        Marks this Page as geocoded with no locations. Does NOT save it.
        """
        self.has_addresses = False
        self.when_geocoded = datetime.datetime.now()
        self.geocoded_by = geocoded_by
    set_no_locations.alters_data = True

    def mine_page(self):
        """
        Runs templatemaker on this Page and returns the raw mined content, as
        a list of strings.
        """
        from ebdata.templatemaker.webmining import mine_page
        try:
            other_page = self.companion_page()
        except IndexError:
            return [self.html]
        return mine_page(self.html, [other_page.html])

    def auto_excerpt(self):
        """
        Attempts to detect the text of this page (ignoring all navigation and
        other clutter), returning a list of strings. Each string represents a
        paragraph.
        """
        from ebdata.textmining.treeutils import make_tree
        tree = make_tree(self.html)
        if self.seed.rss_full_entry:
            from ebdata.templatemaker.textlist import html_to_paragraph_list
            paras = html_to_paragraph_list(tree)
        else:
            if self.seed.strip_noise:
                from ebdata.templatemaker.clean import strip_template
                try:
                    html2 = self.companion_page().html
                except IndexError:
                    pass
                else:
                    tree2 = make_tree(html2)
                    strip_template(tree, tree2)
            if self.seed.guess_article_text:
                from ebdata.templatemaker.articletext import article_text
                paras = article_text(tree)
            else:
                from ebdata.templatemaker.textlist import html_to_paragraph_list
                paras = html_to_paragraph_list(tree)
        return paras

    def companion_page(self):
        """
        Returns another Page for self.seed, for use in a templatemaker
        duplicate-detection algorithm. Raises IndexError if none exist.
        """
        # To avoid the problem of site redesigns affecting the layout, get an
        # example page that was crawled *just before* the current Page.
        try:
            return Page.objects.filter(seed__id=self.seed_id, is_article=True,
                when_crawled__lt=self.when_crawled, is_pdf=False).order_by('-when_crawled')[0]
        except IndexError:
            # If no pages were crawled directly before this one, then get the page
            # that was crawled directly *after* this one.
            return Page.objects.filter(seed__id=self.seed_id, is_article=True,
                when_crawled__gt=self.when_crawled, is_pdf=False).order_by('when_crawled')[0]

    def newsitems(self):
        """
        Returns a list of {excerpt, location_name} dictionaries for every
        location found in this Page, or an empty list if it has no addresses.
        """
        from ebpub.db.models import Attribute, SchemaField
        if not self.has_addresses:
            return []
        # First, figure out the SchemaFields.
        real_names = dict([(sf.name, sf.real_name.encode('utf8')) for sf in SchemaField.objects.filter(schema__id=self.seed.schema_id, name__in=('excerpt', 'page_id'))])
        return [{'id': att.news_item_id, 'url': att.news_item.item_url_with_domain(), 'excerpt': getattr(att, real_names['excerpt']), 'location_name': att.news_item.location_name} \
            for att in Attribute.objects.select_related().filter(**{real_names['page_id']: self.id, 'schema__id': self.seed.schema_id})]

# Datelines that should be ignored by the blob updater.
class IgnoredDateline(models.Model):
    dateline = models.CharField(max_length=255, unique=True)

    def __unicode__(self):
        return self.dateline
