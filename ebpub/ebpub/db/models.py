from django.contrib.gis.db import models
from django.contrib.gis.db.models import Count
from django.db import connection, transaction
from ebpub.streets.models import Block
from ebpub.utils.text import slugify
import datetime

def field_mapping(schema_id_list):
    """
    Given a list of schema IDs, returns a dictionary of dictionaries, mapping
    schema_ids to dictionaries mapping the fields' name->real_name.
    Example return value:
        {1: {u'crime_type': 'varchar01', u'crime_date', 'date01'},
         2: {u'permit_number': 'varchar01', 'to_date': 'date01'},
        }
    """
    # schema_fields = [{'schema_id': 1, 'name': u'crime_type', 'real_name': u'varchar01'},
    #                  {'schema_id': 1, 'name': u'crime_date', 'real_name': u'date01'}]
    result = {}
    for sf in SchemaField.objects.filter(schema__id__in=(schema_id_list)).values('schema', 'name', 'real_name'):
        result.setdefault(sf['schema'], {})[sf['name']] = sf['real_name']
    return result

class SchemaManager(models.Manager):
    def get_query_set(self):
        return super(SchemaManager, self).get_query_set().filter(is_public=True)

class Schema(models.Model):
    name = models.CharField(max_length=32)
    plural_name = models.CharField(max_length=32)
    indefinite_article = models.CharField(max_length=2) # 'a' or 'an'
    slug = models.CharField(max_length=32, unique=True)
    min_date = models.DateField() # the earliest available NewsItem.pub_date for this Schema
    last_updated = models.DateField()
    date_name = models.CharField(max_length=32) # human-readable name for the NewsItem.item_date field
    date_name_plural = models.CharField(max_length=32)
    importance = models.SmallIntegerField() # bigger number is more important
    is_public = models.BooleanField(db_index=True)
    is_special_report = models.BooleanField()

    # whether RSS feed should collapse many of these into one
    can_collapse = models.BooleanField()

    # whether a newsitem_detail page exists for NewsItems of this Schema
    has_newsitem_detail = models.BooleanField()

    # whether aggregate charts are allowed for this Schema
    allow_charting = models.BooleanField()

    # whether attributes should be preloaded for NewsItems of this Schema, in the list view
    uses_attributes_in_list = models.BooleanField()

    # number of records to show on place_overview
    number_in_overview = models.SmallIntegerField()

    objects = models.Manager()
    public_objects = SchemaManager()

    def __unicode__(self):
        return self.name

    def url(self):
        return '/%s/' % self.slug

    def icon_slug(self):
        if self.is_special_report:
            return 'special-report'
        return self.slug

class SchemaInfo(models.Model):
    schema = models.ForeignKey(Schema)
    short_description = models.TextField()
    summary = models.TextField()
    source = models.TextField()
    grab_bag_headline = models.CharField(max_length=128, blank=True)
    grab_bag = models.TextField(blank=True)
    short_source = models.CharField(max_length=128)
    update_frequency = models.CharField(max_length=64)
    intro = models.TextField()

    def __unicode__(self):
        return unicode(self.schema)

class SchemaField(models.Model):
    schema = models.ForeignKey(Schema)
    name = models.CharField(max_length=32)
    real_name = models.CharField(max_length=10) # 'varchar01', 'varchar02', etc.
    pretty_name = models.CharField(max_length=32) # human-readable name, for presentation
    pretty_name_plural = models.CharField(max_length=32) # plural human-readable name
    display = models.BooleanField() # whether to display value on the public site
    is_lookup = models.BooleanField() # whether the value is a foreign key to Lookup
    is_filter = models.BooleanField()
    is_charted = models.BooleanField() # whether schema_detail displays a chart for this field
    display_order = models.SmallIntegerField()
    is_searchable = models.BooleanField() # whether the value is searchable by content

    def __unicode__(self):
        return u'%s - %s' % (self.schema, self.name)

    def _get_slug(self):
        return self.name.replace('_', '-')
    slug = property(_get_slug)

    def _datatype(self):
        return self.real_name[:-2]
    datatype = property(_datatype)

    def is_type(self, *data_types):
        """
        Returns True if this SchemaField is of *any* of the given data types.

        Allowed values are 'varchar', 'date', 'time', 'datetime', 'bool', 'int'.
        """
        for t in data_types:
            if t == self.real_name[:-2]:
                return True
        return False

    def is_many_to_many_lookup(self):
        """
        Returns True if this SchemaField is a many-to-many lookup.
        """
        return self.is_lookup and not self.is_type('int')

    def all_lookups(self):
        if not self.is_lookup:
            raise ValueError('SchemaField.all_lookups() can only be called if is_lookup is True')
        return Lookup.objects.filter(schema_field__id=self.id).order_by('name')

    def browse_by_title(self):
        "Returns FOO in 'Browse by FOO', for this SchemaField."
        if self.is_type('bool'):
            return u'whether they %s' % self.pretty_name_plural
        return self.pretty_name

    def smart_pretty_name(self):
        """
        Returns the pretty name for this SchemaField, taking into account
        many-to-many fields.
        """
        if self.is_many_to_many_lookup():
            return self.pretty_name_plural
        return self.pretty_name

class SchemaFieldInfo(models.Model):
    schema = models.ForeignKey(Schema)
    schema_field = models.ForeignKey(SchemaField)
    help_text = models.TextField()

    def __unicode__(self):
        return unicode(self.schema_field)

class LocationType(models.Model):
    name = models.CharField(max_length=255) # e.g., "Ward" or "Congressional District"
    plural_name = models.CharField(max_length=64) # e.g., "Wards"
    scope = models.CharField(max_length=64) # e.g., "Chicago" or "U.S.A."
    slug = models.CharField(max_length=32, unique=True)
    is_browsable = models.BooleanField() # whether this is displayed on location_type_list
    is_significant = models.BooleanField() # whether this is used to display aggregates, etc.

    def __unicode__(self):
        return u'%s, %s' % (self.name, self.scope)

    def url(self):
        return '/locations/%s/' % self.slug

class Location(models.Model):
    name = models.CharField(max_length=255) # e.g., "35th Ward"
    normalized_name = models.CharField(max_length=255, db_index=True)
    slug = models.CharField(max_length=32, db_index=True)
    location_type = models.ForeignKey(LocationType)
    location = models.GeometryField(null=True)
    centroid = models.PointField(null=True)
    display_order = models.SmallIntegerField()
    city = models.CharField(max_length=255)
    source = models.CharField(max_length=64)
    area = models.FloatField(blank=True, null=True) # in square meters
    population = models.IntegerField(blank=True, null=True) # from the 2000 Census
    user_id = models.IntegerField(blank=True, null=True)
    is_public = models.BooleanField()
    description = models.TextField(blank=True)
    creation_date = models.DateTimeField(blank=True, null=True)
    last_mod_date = models.DateTimeField(blank=True, null=True)
    objects = models.GeoManager()

    class Meta:
        unique_together = (('slug', 'location_type'),)

    def __unicode__(self):
        return self.name

    def url(self):
        return '/locations/%s/%s/' % (self.location_type.slug, self.slug)

    def rss_url(self):
        return '/rss%s' % self.url()

    def alert_url(self):
        return '%salerts/' % self.url()

    def edit_url(self):
        return '/locations/%s/edit/%s/' % (self.location_type.slug, self.slug)

    # Give Location objects a "pretty_name" attribute for interoperability with
    # Block objects. (Parts of our app accept either a Block or Location.)
    def _get_name(self):
        return self.name
    pretty_name = property(_get_name)

    def _is_custom(self):
        return self.location_type.slug == 'custom'
    is_custom = property(_is_custom)

class AttributesDescriptor(object):
    """
    This class provides the functionality that makes the attributes available
    as `attributes` on a model instance.
    """
    def __get__(self, instance, instance_type=None):
        if instance is None:
            raise AttributeError("%s must be accessed via instance" % self.__class__.__name__)
        if not hasattr(instance, '_attributes_cache'):
            select_dict = field_mapping([instance.schema_id])[instance.schema_id]
            instance._attributes_cache = AttributeDict(instance.id, instance.schema_id, select_dict)
        return instance._attributes_cache

    def __set__(self, instance, value):
        if instance is None:
            raise AttributeError("%s must be accessed via instance" % self.__class__.__name__)
        if not isinstance(value, dict):
            raise ValueError('Only a dictionary is allowed')
        mapping = field_mapping([instance.schema_id])[instance.schema_id].items()
        values = [value.get(k, None) for k, v in mapping]
        cursor = connection.cursor()
        cursor.execute("""
            UPDATE %s
            SET %s
            WHERE news_item_id = %%s
            """ % (Attribute._meta.db_table, ','.join(['%s=%%s' % v for k, v in mapping])),
                values + [instance.id])
        # If no records were updated, that means the DB doesn't yet have a
        # row in the attributes table for this news item. Do an INSERT.
        if cursor.rowcount < 1:
            cursor.execute("""
                INSERT INTO %s (news_item_id, schema_id, %s)
                VALUES (%%s, %%s, %s)""" % (Attribute._meta.db_table, ','.join([v for k, v in mapping]), ','.join(['%s' for k in mapping])),
                [instance.id, instance.schema_id] + values)
        transaction.commit_unless_managed()

class AttributeDict(dict):
    """
    A dictionary-like object that serves as a wrapper around attributes for a
    given NewsItem.
    """
    def __init__(self, news_item_id, schema_id, mapping):
        dict.__init__(self)
        self.news_item_id = news_item_id
        self.schema_id = schema_id
        self.mapping = mapping # name -> real_name dictionary
        self.cached = False

    def __do_query(self):
        if not self.cached:
            atts = Attribute.objects.filter(news_item__id=self.news_item_id).extra(select=self.mapping).values(*self.mapping.keys())[0]
            self.update(atts)
            self.cached = True

    def get(self, *args, **kwargs):
        self.__do_query()
        return dict.get(self, *args, **kwargs)

    def __getitem__(self, name):
        self.__do_query()
        return dict.__getitem__(self, name)

    def __setitem__(self, name, value):
        cursor = connection.cursor()
        real_name = self.mapping[name]
        cursor.execute("""
            UPDATE %s
            SET %s = %%s
            WHERE news_item_id = %%s
            """ % (Attribute._meta.db_table, real_name), [value, self.news_item_id])
        # If no records were updated, that means the DB doesn't yet have a
        # row in the attributes table for this news item. Do an INSERT.
        if cursor.rowcount < 1:
            cursor.execute("""
                INSERT INTO %s (news_item_id, schema_id, %s)
                VALUES (%%s, %%s, %%s)""" % (Attribute._meta.db_table, real_name),
                [self.news_item_id, self.schema_id, value])
        transaction.commit_unless_managed()
        dict.__setitem__(self, name, value)

class NewsItemQuerySet(models.query.GeoQuerySet):
    def prepare_attribute_qs(self):
        clone = self._clone()
        if 'db_attribute' not in clone.query.extra_tables:
            clone.query.extra_tables += ('db_attribute',)
        clone.query.extra_where += ('db_newsitem.id = db_attribute.news_item_id',)
        return clone

    def by_attribute(self, schema_field, att_value, is_lookup=False):
        """
        Returns a QuerySet of NewsItems whose attribute value for the given
        SchemaField is att_value. If att_value is a list, this will do the
        equivalent of an "OR" search, returning all NewsItems that have an
        attribute value in the att_value list.

        This handles many-to-many lookups correctly behind the scenes.

        If is_lookup is True, then att_value is treated as the 'code' of a
        Lookup object, and the Lookup's ID will be retrieved for use in the
        query.
        """
        clone = self.prepare_attribute_qs()
        real_name = str(schema_field.real_name)
        if not isinstance(att_value, (list, tuple)):
            att_value = [att_value]
        if is_lookup:
            att_value = Lookup.objects.filter(schema_field__id=schema_field.id, code__in=att_value)
            if not att_value:
                # If the lookup values don't exist, then there aren't any
                # NewsItems with this attribute value. Note that we aren't
                # using QuerySet.none() here, because we want the result to
                # be a NewsItemQuerySet, and none() returns a normal QuerySet.
                clone.query.extra_where += ('1=0',)
                return clone
            att_value = [val.id for val in att_value]
        if schema_field.is_many_to_many_lookup():
            # We have to use a regular expression search to look for all rows
            # with the given att_value *somewhere* in the column. The [[:<:]]
            # thing is a word boundary.
            for value in att_value:
                if not str(value).isdigit():
                    raise ValueError('Only integer strings allowed for att_value in many-to-many SchemaFields')
            clone.query.extra_where += ("db_attribute.%s ~ '[[:<:]]%s[[:>:]]'" % (real_name, '|'.join([str(val) for val in att_value])),)
        elif None in att_value:
            if att_value != [None]:
                raise ValueError('by_attribute() att_value list cannot have more than one element if it includes None')
            clone.query.extra_where += ("db_attribute.%s IS NULL" % real_name,)
        else:
            clone.query.extra_where += ("db_attribute.%s IN (%s)" % (real_name, ','.join(['%s' for val in att_value])),)
            clone.query.extra_params += tuple(att_value)
        return clone

    def date_counts(self):
        """
        Returns a dictionary mapping {item_date: count}.
        """
        # TODO: values + annotate doesn't seem to play nice with GeoQuerySet
        # at the moment. This is the changeset where it broke:
        # http://code.djangoproject.com/changeset/10326
        from django.db.models.query import QuerySet
        qs = QuerySet.values(self, 'item_date').annotate(count=models.Count('id'))
        return dict([(v['item_date'], v['count']) for v in qs])

    def top_lookups(self, schema_field, count):
        """
        Returns a list of {lookup, count} dictionaries representing the top
        Lookups for this QuerySet.
        """
        real_name = "db_attribute." + str(schema_field.real_name)
        if schema_field.is_many_to_many_lookup():
            clone = self.prepare_attribute_qs().filter(schema__id=schema_field.schema_id)
            clone = clone.extra(where=[real_name + " ~ ('[[:<:]]' || db_lookup.id || '[[:>:]]')"])
            # We want to count the current queryset and get a single
            # row for injecting into the subsequent Lookup query, but
            # we don't want Django's aggregation support to
            # automatically group by fields that aren't relevant and
            # would cause multiple rows as a result. So we call
            # `values()' on a field that we're already filtering by,
            # in this case, schema, as essentially a harmless identify
            # function.
            clone = clone.values('schema').annotate(count=Count('schema'))
            qs = Lookup.objects.filter(schema_field__id=schema_field.id)
            qs = qs.extra(select={'lookup_id': 'id', 'item_count': clone.values('count').query})
        else:
            qs = self.prepare_attribute_qs().extra(select={'lookup_id': real_name})
            qs.query.group_by = [real_name]
            qs = qs.values('lookup_id').annotate(item_count=Count('id'))
        ids_and_counts = [(v['lookup_id'], v['item_count']) for v in qs.values('lookup_id', 'item_count').order_by('-item_count') if v['item_count']][:count]
        lookup_objs = Lookup.objects.in_bulk([i[0] for i in ids_and_counts])
        return [{'lookup': lookup_objs[i[0]], 'count': i[1]} for i in ids_and_counts]

    def text_search(self, schema_field, query):
        """
        Returns a QuerySet of NewsItems whose attribute for
        a given schema field matches a text search query.
        """
        clone = self.prepare_attribute_qs()
        query = query.lower()
        clone.query.extra_where += ("db_attribute." + str(schema_field.real_name) + " ILIKE %s",)
        clone.query.extra_params += ("%%%s%%" % query,)
        return clone

class NewsItemManager(models.GeoManager):
    def get_query_set(self):
        return NewsItemQuerySet(self.model)

    def by_attribute(self, *args, **kwargs):
        return self.get_query_set().by_attribute(*args, **kwargs)

    def text_search(self, *args, **kwargs):
        return self.get_query_set().text_search(*args, **kwargs)

    def date_counts(self, *args, **kwargs):
        return self.get_query_set().date_counts(*args, **kwargs)

    def top_lookups(self, *args, **kwargs):
        return self.get_query_set().top_lookups(*args, **kwargs)

class NewsItem(models.Model):
    schema = models.ForeignKey(Schema)
    title = models.CharField(max_length=255)
    description = models.TextField()
    url = models.TextField(blank=True)
    pub_date = models.DateTimeField(db_index=True)
    item_date = models.DateField(db_index=True)
    location = models.GeometryField(blank=True, null=True)
    location_name = models.CharField(max_length=255)
    location_object = models.ForeignKey(Location, blank=True, null=True)
    block = models.ForeignKey(Block, blank=True, null=True)
    objects = NewsItemManager()
    attributes = AttributesDescriptor()

    def __unicode__(self):
        return self.title

    def item_url(self):
        return '/%s/by-date/%s/%s/%s/%s/' % (self.schema.slug, self.item_date.year, self.item_date.month, self.item_date.day, self.id)

    def item_url_with_domain(self):
        from django.conf import settings
        return 'http://%s.%s%s' % (settings.SHORT_NAME, settings.EB_DOMAIN, self.item_url())

    def item_date_url(self):
        return '/%s/by-date/%s/%s/%s/' % (self.schema.slug, self.item_date.year, self.item_date.month, self.item_date.day)

    def location_url(self):
        if self.location_object_id is not None:
            return self.location_object.url()
        return None

    def attributes_for_template(self):
        """
        Return a list of AttributeForTemplate objects for this NewsItem. The
        objects are ordered by SchemaField.display_order.
        """
        fields = SchemaField.objects.filter(schema__id=self.schema_id).select_related().order_by('display_order')
        field_infos = dict([(obj.schema_field_id, obj.help_text) for obj in SchemaFieldInfo.objects.filter(schema__id=self.schema_id)])
        try:
            attribute_row = Attribute.objects.filter(news_item__id=self.id).values(*[f.real_name for f in fields])[0]
        except KeyError:
            return []
        return [AttributeForTemplate(f, attribute_row, field_infos.get(f.id, None)) for f in fields]

class AttributeForTemplate(object):
    def __init__(self, schema_field, attribute_row, help_text):
        self.sf = schema_field
        self.raw_value = attribute_row[schema_field.real_name]
        self.schema_slug = schema_field.schema.slug
        self.is_lookup = schema_field.is_lookup
        self.is_filter = schema_field.is_filter
        self.help_text = help_text
        if self.is_lookup:
            if self.raw_value == '':
                self.values = []
            elif self.sf.is_many_to_many_lookup():
                try:
                    id_values = map(int, self.raw_value.split(','))
                except ValueError:
                    self.values = []
                else:
                    lookups = Lookup.objects.in_bulk(id_values)
                    self.values = [lookups[i] for i in id_values]
            else:
                self.values = [Lookup.objects.get(id=self.raw_value)]
        else:
            self.values = [self.raw_value]

    def value_list(self):
        """
        Returns a list of {value, url} dictionaries representing each value for
        this attribute.
        """
        from django.utils.dateformat import format, time_format
        urls = [None]
        descriptions = [None]
        if self.is_filter:
            if self.is_lookup:
                urls = [look and '/%s/by-%s/%s/' % (self.schema_slug, self.sf.slug, look.slug) or None for look in self.values]
            elif isinstance(self.raw_value, datetime.date):
                urls = ['/%s/by-%s/%s/%s/%s/' % (self.schema_slug, self.sf.slug, self.raw_value.year, self.raw_value.month, self.raw_value.day)]
            elif self.raw_value in (True, False, None):
                urls = ['/%s/by-%s/%s/' % (self.schema_slug, self.sf.slug, {True: 'yes', False: 'no', None: 'na'}[self.raw_value])]
        if self.is_lookup:
            values = [val and val.name or 'None' for val in self.values]
            descriptions = [val and val.description or None for val in self.values]
        elif isinstance(self.raw_value, datetime.datetime):
            values = [format(self.raw_value, 'F j, Y, P')]
        elif isinstance(self.raw_value, datetime.date):
            values = [format(self.raw_value, 'F j, Y')]
        elif isinstance(self.raw_value, datetime.time):
            values = [time_format(self.raw_value, 'P')]
        elif self.raw_value is True:
            values = ['Yes']
        elif self.raw_value is False:
            values = ['No']
        elif self.raw_value is None:
            values = ['N/A']
        else:
            values = [self.raw_value]
        return [{'value': value, 'url': url, 'description': description} for value, url, description in zip(values, urls, descriptions)]

class Attribute(models.Model):
    news_item = models.ForeignKey(NewsItem, primary_key=True, unique=True)
    schema = models.ForeignKey(Schema)
    # All data-type field names must end in two digits, because the code assumes this.
    varchar01 = models.CharField(max_length=255, blank=True, null=True)
    varchar02 = models.CharField(max_length=255, blank=True, null=True)
    varchar03 = models.CharField(max_length=255, blank=True, null=True)
    varchar04 = models.CharField(max_length=255, blank=True, null=True)
    varchar05 = models.CharField(max_length=255, blank=True, null=True)
    date01 = models.DateField(blank=True, null=True)
    date02 = models.DateField(blank=True, null=True)
    date03 = models.DateField(blank=True, null=True)
    date04 = models.DateField(blank=True, null=True)
    date05 = models.DateField(blank=True, null=True)
    time01 = models.TimeField(blank=True, null=True)
    time02 = models.TimeField(blank=True, null=True)
    datetime01 = models.DateTimeField(blank=True, null=True)
    datetime02 = models.DateTimeField(blank=True, null=True)
    datetime03 = models.DateTimeField(blank=True, null=True)
    datetime04 = models.DateTimeField(blank=True, null=True)
    bool01 = models.NullBooleanField(blank=True)
    bool02 = models.NullBooleanField(blank=True)
    bool03 = models.NullBooleanField(blank=True)
    bool04 = models.NullBooleanField(blank=True)
    bool05 = models.NullBooleanField(blank=True)
    int01 = models.IntegerField(blank=True, null=True)
    int02 = models.IntegerField(blank=True, null=True)
    int03 = models.IntegerField(blank=True, null=True)
    int04 = models.IntegerField(blank=True, null=True)
    int05 = models.IntegerField(blank=True, null=True)
    int06 = models.IntegerField(blank=True, null=True)
    int07 = models.IntegerField(blank=True, null=True)
    text01 = models.TextField(blank=True, null=True)

    def __unicode__(self):
        return u'Attributes for news item %s' % self.news_item_id

class LookupManager(models.Manager):
    def get_or_create_lookup(self, schema_field, name, code=None, description='', make_text_slug=True, logger=None):
        """
        Returns the Lookup instance matching the given SchemaField, name and
        Lookup.code, creating it (with the given name/code/description) if it
        doesn't already exist.

        If make_text_slug is True, then a slug will be created from the given
        name. If it's False, then the slug will be the Lookup's ID.
        """
        def log_info(message):
            if logger is None:
                return
            logger.info(message)
        def log_warn(message):
            if logger is None:
                return
            logger.warn(message)
        code = code or name # code defaults to name if it wasn't provided
        try:
            obj = Lookup.objects.get(schema_field__id=schema_field.id, code=code)
        except Lookup.DoesNotExist:
            if make_text_slug:
                slug = slugify(name)
                if len(slug) > 32:
                    # Only bother to warn if we're actually going to use the slug.
                    if make_text_slug:
                        log_warn("Trimming slug %r to %r in order to fit 32-char limit." % (slug, slug[:32]))
                    slug = slug[:32]
            else:
                # To avoid integrity errors in the slug when creating the Lookup,
                # use a temporary dummy slug that's guaranteed not to be in use.
                # We'll change it back immediately afterward.
                slug = '__3029j3f029jf029jf029__'
            if len(name) > 255:
                old_name = name
                name = name[:250] + '...'
                # Save the full name in the description.
                if not description:
                    description = old_name
                log_warn("Trimming name %r to %r in order to fit 255-char limit." % (old_name, name))
            obj = Lookup(schema_field_id=schema_field.id, name=name, code=code, slug=slug, description=description)
            obj.save()
            if not make_text_slug:
                # Set the slug to the ID.
                obj.slug = obj.id
                obj.save()
            log_info('Created %s %r' % (schema_field.name, name))
        return obj

class Lookup(models.Model):
    schema_field = models.ForeignKey(SchemaField)
    name = models.CharField(max_length=255)
    # `code` is the optional internal code to use during retrieval.
    # For example, in scraping Chicago crimes, we use the crime type code
    # to find the appropriate crime type in this table. We can't use `name`
    # in that case, because we've massaged `name` to use a "prettier"
    # formatting than exists in the data source.
    code = models.CharField(max_length=255, blank=True)
    slug = models.CharField(max_length=32, db_index=True)
    description = models.TextField(blank=True)

    objects = LookupManager()

    class Meta:
        unique_together = (('slug', 'schema_field'),)

    def __unicode__(self):
        return u'%s - %s' % (self.schema_field, self.name)

class NewsItemLocation(models.Model):
    news_item = models.ForeignKey(NewsItem)
    location = models.ForeignKey(Location)

    class Meta:
        unique_together = (('news_item', 'location'),)

    def __unicode__(self):
        return u'%s - %s' % (self.news_item, self.location)

class AggregateBaseClass(models.Model):
    schema = models.ForeignKey(Schema)
    total = models.IntegerField()

    class Meta:
        abstract = True

class AggregateAll(AggregateBaseClass):
    # Total items in the schema.
    pass

class AggregateDay(AggregateBaseClass):
    # Total items in the schema with item_date on the given day
    date_part = models.DateField(db_index=True)

class AggregateLocation(AggregateBaseClass):
    # Total items in the schema in location, summed over that last 30 days
    location_type = models.ForeignKey(LocationType)
    location = models.ForeignKey(Location)

class AggregateLocationDay(AggregateBaseClass):
    # Total items in the schema in location with item_date on the given day
    location_type = models.ForeignKey(LocationType)
    location = models.ForeignKey(Location)
    date_part = models.DateField(db_index=True)

class AggregateFieldLookup(AggregateBaseClass):
    # Total items in the schema with schema_field's value = lookup
    schema_field = models.ForeignKey(SchemaField)
    lookup = models.ForeignKey(Lookup)

class SearchSpecialCase(models.Model):
    query = models.CharField(max_length=64, unique=True)
    redirect_to = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=128, blank=True)
    body = models.TextField(blank=True)

    def __unicode__(self):
        return self.query

class DataUpdate(models.Model):
    # Keeps track of each time we update our data.
    schema = models.ForeignKey(Schema)
    update_start = models.DateTimeField()  # When the scraper/importer started running.
    update_finish = models.DateTimeField() # When the scraper/importer finished.
    num_added = models.IntegerField()
    num_changed = models.IntegerField()
    num_deleted = models.IntegerField()
    num_skipped = models.IntegerField()
    got_error = models.BooleanField()

    def __unicode__(self):
        return u'%s started on %s' % (self.schema.name, self.update_start)

    def total_time(self):
        return self.update_finish - self.update_start
