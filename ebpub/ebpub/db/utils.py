from django.conf import settings
import datetime

def smart_bunches(newsitem_list, max_days=5, max_items_per_day=100):
    """
    Helper function that takes a list of NewsItems, ordered descending by
    pub_date, and returns a list of NewsItems that's been optimized for
    display in timelines.

    Assumes each NewsItem has a pub_date_date attribute!

    The logic is:
        * Go backwards in time until there are 5 full days' worth of news
          (not necessarily 5 consecutive days).
        * If, for any day, there are more than 100 items, stop at that day
          (inclusive).
        * Any NewsItems in the list with a pub_date equal to the oldest
          pub_date in the list will be removed. This is because we cannot
          assume *all* of the items with that pub_date are in the list.
    """
    if newsitem_list:
        current_date = None
        days_seen = 0
        stop_at_next_day = False
        end_index = None
        oldest_pub_date = newsitem_list[-1].pub_date_date
        for i, ni in enumerate(newsitem_list):
            if ni.pub_date_date != current_date:
                days_seen += 1
                current_date = ni.pub_date_date
                items_in_current_day = 1
                if stop_at_next_day or days_seen > max_days or ni.pub_date_date == oldest_pub_date:
                    end_index = i
                    break
            else:
                items_in_current_day += 1
                if items_in_current_day > max_items_per_day:
                    stop_at_next_day = True
        if end_index is not None:
            del newsitem_list[end_index:]
    return newsitem_list

def populate_attributes_if_needed(newsitem_list, schema_list):
    """
    Helper function that takes a list of NewsItems and sets ni.attribute_values
    to a dictionary of attributes {field_name: value} for all NewsItems whose
    schemas have uses_attributes_in_list=True. This is accomplished with a
    minimal amount of database queries.

    The values in the attribute_values dictionary are Lookup instances in the
    case of Lookup fields. Otherwise, they're the direct values from the
    Attribute table.

    schema_list should be a list of all Schemas that are referenced in
    newsitem_list.

    Note that the list is edited in place; there is no return value.
    """
    from ebpub.db.models import Attribute, Lookup, SchemaField
    # To accomplish this, we determine which NewsItems in ni_list require
    # attribute prepopulation, and run a single DB query that loads all of the
    # attributes. Another way to do this would be to load all of the attributes
    # when loading the NewsItems in the first place (via a JOIN), but we want
    # to avoid joining such large tables.
    preload_schema_ids = set([s.id for s in schema_list if s.uses_attributes_in_list])
    if not preload_schema_ids:
        return
    preloaded_nis = [ni for ni in newsitem_list if ni.schema_id in preload_schema_ids]
    if not preloaded_nis:
        return
    # fmap = {schema_id: {'fields': [(name, real_name)], 'lookups': [real_name1, real_name2]}}
    fmap = {}
    attribute_columns_to_select = set(['news_item'])
    for sf in SchemaField.objects.filter(schema__id__in=[s.id for s in schema_list]).values('schema', 'name', 'real_name', 'is_lookup'):
        fmap.setdefault(sf['schema'], {'fields': [], 'lookups': []})['fields'].append((sf['name'], sf['real_name']))
        if sf['is_lookup']:
            fmap[sf['schema']]['lookups'].append(sf['real_name'])
        attribute_columns_to_select.add(str(sf['real_name']))

    att_dict = dict([(i['news_item'], i) for i in Attribute.objects.filter(news_item__id__in=[ni.id for ni in preloaded_nis]).values(*list(attribute_columns_to_select))])

    # Determine which Lookup objects need to be retrieved.
    lookup_ids = set()
    for ni in preloaded_nis:
        for real_name in fmap[ni.schema_id]['lookups']:
            value = att_dict[ni.id][real_name]
            if ',' in str(value):
                lookup_ids.update(value.split(','))
            else:
                lookup_ids.add(value)

    # Retrieve only the Lookups that are referenced in preloaded_nis.
    lookup_ids = [i for i in lookup_ids if i]
    if lookup_ids:
        lookup_objs = Lookup.objects.in_bulk(lookup_ids)
    else:
        lookup_objs = {}

    # Set 'attribute_values' for each NewsItem in preloaded_nis.
    for ni in preloaded_nis:
        att = att_dict[ni.id]
        att_values = {}
        for field_name, real_name in fmap[ni.schema_id]['fields']:
            value = att[real_name]
            if real_name in fmap[ni.schema_id]['lookups']:
                if real_name.startswith('int'):
                    value = lookup_objs[value]
                else: # Many-to-many lookups are comma-separated strings.
                    value = [lookup_objs[int(i)] for i in value.split(',') if i]
            att_values[field_name] = value
        ni.attribute_values = att_values

def populate_schema(newsitem_list, schema):
    for ni in newsitem_list:
        # TODO: This relies on undocumented Django APIs -- the "_schema_cache" name.
        ni._schema_cache = schema

def today():
    if settings.EB_TODAY_OVERRIDE:
        return settings.EB_TODAY_OVERRIDE
    return datetime.date.today()
