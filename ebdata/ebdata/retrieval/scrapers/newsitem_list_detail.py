from django.conf import settings
from django.db import transaction
from ebdata.retrieval.scrapers.list_detail import ListDetailScraper
from ebdata.retrieval.utils import locations_are_close
from ebpub.db.models import Schema, NewsItem, Lookup, DataUpdate, field_mapping
from ebpub.geocoder import SmartGeocoder, GeocodingException, ParsingError
from ebpub.utils.text import address_to_block
import datetime

class NewsItemListDetailScraper(ListDetailScraper):
    """
    A ListDetailScraper that saves its data into the NewsItem table.

    Subclasses are required to set the `schema_slugs` attribute.

    self.schemas lazily loads the list of Schema objects the first time it's
    accessed. It is a dictionary in the format {slug: Schema}.

    self.schema is available if schema_slugs has only one element. It's the
    Schema object.

    self.lookups lazily loads a dictionary of all SchemaFields with
    lookup=True. The dictionary is in the format {name: schemafield}. If
    schema_slug has more than one element, self.lookups is a dictionary in the
    format {schema_slug: {name: schemafield}}.

    self.schema_field_mapping lazily loads a dictionary of each SchemaField,
    mapping the name to the real_name. If schema_slug has more than one element,
    self.schema_field_mapping is a dictionary in the format
    {schema_slug: {name: real_name}}.
    """
    schema_slugs = None
    logname = None

    def __init__(self, *args, **kwargs):
        if self.logname is None:
            self.logname = '%s.%s' % (settings.SHORT_NAME, self.schema_slugs[0])
        super(NewsItemListDetailScraper, self).__init__(*args, **kwargs)
        self._schema_cache = None
        self._schemas_cache = None
        self._lookups_cache = None
        self._schema_fields_cache = None
        self._schema_field_mapping_cache = None
        self._geocoder = SmartGeocoder()

    # schemas, schema, lookups and schema_field_mapping are all lazily loaded
    # so that this scraper can be run (in raw_data(), xml_data() or
    # display_data()) without requiring a valid database to be set up.

    def _get_schemas(self):
        if self._schemas_cache is None:
            self._schemas_cache = dict([(s, Schema.objects.get(slug=s)) for s in self.schema_slugs])
        return self._schemas_cache
    schemas = property(_get_schemas)

    def _get_schema(self):
        if self._schema_cache is None:
            if len(self.schema_slugs) > 1:
                raise AttributeError('self.schema is only available if len(schema_slugs) == 1')
            self._schema_cache = self.schemas[self.schema_slugs[0]]
        return self._schema_cache
    schema = property(_get_schema)

    def _get_lookups(self):
        if self._lookups_cache is None:
            lc = dict([(s.slug, dict([(sf.name, sf) for sf in s.schemafield_set.filter(is_lookup=True)])) for s in self.schemas.values()])
            if len(self.schema_slugs) == 1:
                lc = lc[self.schema_slugs[0]]
            self._lookups_cache = lc
        return self._lookups_cache
    lookups = property(_get_lookups)

    def _get_schema_fields(self):
        if self._schema_fields_cache is None:
            sfs = dict([(s.slug, dict([(sf.name, sf) for sf in s.schemafield_set.all()])) for s in self.schemas.values()])
            if len(self.schema_slugs) == 1:
                sfs = sfs[self.schema_slugs[0]]
            self._schema_fields_cache = sfs
        return self._schema_fields_cache
    schema_fields = property(_get_schema_fields)

    def _get_schema_field_mapping(self):
        if self._schema_field_mapping_cache is None:
            schema_objs = self.schemas.values()
            mapping = field_mapping([s.id for s in schema_objs])
            fm = dict([(s.slug, mapping[s.id]) for s in schema_objs])
            if len(self.schema_slugs) == 1:
                fm = fm[self.schema_slugs[0]]
            self._schema_field_mapping_cache = fm
        return self._schema_field_mapping_cache
    schema_field_mapping = property(_get_schema_field_mapping)

    def get_or_create_lookup(self, schema_field_name, name, code, description='', schema=None, make_text_slug=True):
        """
        Returns the Lookup instance matching the given Schema slug, SchemaField
        name and Lookup.code, creating it (with the given name/code/description)
        if it doesn't already exist.

        If make_text_slug is True, then a slug will be created from the given
        name. If it's False, then the slug will be the Lookup's ID.
        """
        if len(self.schema_slugs) > 1:
            sf = self.lookups[schema][schema_field_name]
        else:
            sf = self.lookups[schema_field_name]
        return Lookup.objects.get_or_create_lookup(sf, name, code, description, make_text_slug, self.logger)

    @transaction.commit_on_success
    def create_newsitem(self, attributes, **kwargs):
        """
        Creates and saves a NewsItem with the given kwargs. Returns the new
        NewsItem.

        kwargs MUST have the following keys:
            title
            item_date
            location_name
        For any other kwargs whose values aren't provided, this will use
        sensible defaults.

        kwargs may optionally contain a 'convert_to_block' boolean. If True,
        this will convert the given kwargs['location_name'] to a block level
        but will use the real (non-block-level) address for geocoding and Block
        association.

        attributes is a dictionary to use to populate this NewsItem's Attribute
        object.
        """
        block = location = None
        if 'location' not in kwargs:
            location = self.geocode(kwargs['location_name'])
            if location:
                block = location['block']
                location = location['point']
        if kwargs.pop('convert_to_block', False):
            kwargs['location_name'] = address_to_block(kwargs['location_name'])
            # If the exact address couldn't be geocoded, try using the
            # normalized location name.
            if location is None:
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
            block=kwargs.get('block', block),
        )
        ni.attributes = attributes
        self.num_added += 1
        self.logger.info(u'Created NewsItem %s (total created in this scrape: %s)', ni.id, self.num_added)
        return ni

    @transaction.commit_on_success
    def update_existing(self, newsitem, new_values, new_attributes):
        """
        Given an existing NewsItem and dictionaries new_values and
        new_attributes, determines which values and attributes have changed
        and saves the object and/or its attributes if necessary.
        """
        newsitem_updated = False
        # First, check the NewsItem's values.
        for k, v in new_values.items():
            if getattr(newsitem, k) != v:
                self.logger.info('ID %s %s changed from %r to %r' % (newsitem.id, k, getattr(newsitem, k), v))
                setattr(newsitem, k, v)
                newsitem_updated = True
        if newsitem_updated:
            newsitem.save()
        # Next, check the NewsItem's attributes.
        for k, v in new_attributes.items():
            if newsitem.attributes[k] != v:
                self.logger.info('ID %s %s changed from %r to %r' % (newsitem.id, k, newsitem.attributes[k], v))
                newsitem.attributes[k] = v
                newsitem_updated = True
        if newsitem_updated:
            self.num_changed += 1
            self.logger.debug('Total changed in this scrape: %s', self.num_changed)
        else:
            self.logger.debug('No changes to NewsItem %s detected', newsitem.id)

    def update(self):
        """
        Updates the Schema.last_updated fields after scraping is done.
        """
        self.num_added = 0
        self.num_changed = 0
        update_start = datetime.datetime.now()

        # We use a try/finally here so that the DataUpdate object is created
        # regardless of whether the scraper raised an exception.
        try:
            got_error = True
            super(NewsItemListDetailScraper, self).update()
            got_error = False
        finally:
            # Rollback, in case the database is in an aborted transaction. his
            # avoids the "psycopg2.ProgrammingError: current transaction is aborted,
            # commands ignored until end of transaction block" error.
            from django.db import connection
            connection._rollback()

            update_finish = datetime.datetime.now()

            # Clear the Schema cache, in case the schemas have been updated in the
            # database since we started the scrape.
            self._schemas_cache = self._schema_cache = None

            for s in self.schemas.values():
                s.last_updated = datetime.date.today()
                s.save()
                DataUpdate.objects.create(
                    schema=s,
                    update_start=update_start,
                    update_finish=update_finish,
                    num_added=self.num_added,
                    num_changed=self.num_changed,
                    # None of our scrapers delete records yet, but we have the
                    # plumbing in place here in case future scrapers need to do
                    # that.
                    num_deleted=0,
                    num_skipped=self.num_skipped,
                    got_error=got_error,
                )

    def geocode(self, location_name):
        """
        Tries to geocode the given location string, returning a Point object
        or None.
        """
        try:
            return self._geocoder.geocode(location_name)
        except (GeocodingException, ParsingError):
            return None

    def safe_location(self, location_name, geom, max_distance=200):
        """
        Returns a location (geometry) to use, given a location_name and
        geometry. This is used for data sources that publish both a geometry
        and a location_name -- we double-check that the geometry is within
        a certain `max_distance` from the geocoded location_name.

        If there's a discrepancy or if the location_name can't be geocoded,
        this returns None.
        """
        location = self.geocode(location_name)
        if location is None:
            return None
        location_point = location['point']
        if not location_point:
            return None
        location_point.srid = 4326
        is_close, distance = locations_are_close(location_point, geom, max_distance)
        if not is_close:
            return None
        return geom
