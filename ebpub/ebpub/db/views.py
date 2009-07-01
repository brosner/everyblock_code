from django import template
from django.conf import settings
from django.core.cache import cache
from django.http import Http404, HttpResponse, HttpResponseRedirect, HttpResponsePermanentRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template.loader import select_template
from django.utils import dateformat, simplejson
from django.utils.datastructures import SortedDict
from django.db.models import Q
from ebgeo.utils.clustering.shortcuts import cluster_newsitems
from ebgeo.utils.clustering.json import ClusterJSON
from ebpub.db import constants
from ebpub.db.models import NewsItem, Schema, SchemaInfo, SchemaField, Lookup, LocationType, Location, SearchSpecialCase
from ebpub.db.models import AggregateDay, AggregateLocation, AggregateLocationDay, AggregateFieldLookup
from ebpub.db.utils import smart_bunches, populate_attributes_if_needed, populate_schema, today
from ebpub.utils.dates import daterange, parse_date
from ebpub.geocoder import SmartGeocoder, AmbiguousResult, DoesNotExist, GeocodingException, InvalidBlockButValidStreet
from ebpub.geocoder.parser.parsing import normalize, ParsingError
from ebpub.preferences.models import HiddenSchema
from ebpub.savedplaces.models import SavedPlace
from ebpub.streets.models import Street, City, Block, Intersection
from ebpub.streets.utils import full_geocode
from ebpub.utils.view_utils import eb_render
from ebpub.metros.allmetros import METRO_DICT, get_metro
import datetime
import random
import re
import urllib

BLOCK_RADIUS_COOKIE_NAME = 'radius'
BLOCK_RADIUS_CHOICES = {'1': .0015, '3': .0035, '8': .007} # number of blocks -> number of geographic degrees
BLOCK_RADIUS_DEFAULT = '8'
HIDE_ADS_COOKIE_NAME = 'h'
HIDE_SCHEMA_INTRO_COOKIE_NAME = 'schemaintro'
DEFAULT_LOCTYPE_SLUG = 'neighborhoods'
POPULATION_SCALE = 1000 # newsitems per POPULATION_SCALE people

################################
# HELPER FUNCTIONS (NOT VIEWS) #
################################

radius_url = lambda radius: '%s-block%s' % (radius, radius != '1' and 's' or '')

def has_staff_cookie(request):
    return request.COOKIES.get(settings.STAFF_COOKIE_NAME) == settings.STAFF_COOKIE_VALUE

def get_schema_manager(request):
    if has_staff_cookie(request):
        return Schema.objects
    else:
        return Schema.public_objects

def block_radius_value(request):
    # Returns a tuple of (xy_radius, block_radius, cookies_to_set).
    if 'radius' in request.GET and request.GET['radius'] in BLOCK_RADIUS_CHOICES:
        block_radius = request.GET['radius']
        cookies_to_set = {BLOCK_RADIUS_COOKIE_NAME: block_radius}
    else:
        if request.COOKIES.get(BLOCK_RADIUS_COOKIE_NAME) in BLOCK_RADIUS_CHOICES:
            block_radius = request.COOKIES[BLOCK_RADIUS_COOKIE_NAME]
        else:
            block_radius = BLOCK_RADIUS_DEFAULT
        cookies_to_set = {}
    return BLOCK_RADIUS_CHOICES[block_radius], block_radius, cookies_to_set

def get_date_chart_agg_model(schemas, start_date, end_date, agg_model, kwargs=None):
    kwargs = kwargs or {}
    counts = {}
    for agg in agg_model.objects.filter(schema__id__in=[s.id for s in schemas], date_part__range=(start_date, end_date), **kwargs):
        counts.setdefault(agg.schema_id, {})[agg.date_part] = agg.total
    return get_date_chart(schemas, start_date, end_date, counts)

def get_date_chart(schemas, start_date, end_date, counts):
    """
    Returns a list that's used to display a date chart for the given
    schemas. Note that start_date and end_date should be datetime.date objects,
    NOT datetime.datetime objects.

    counts should be a nested dictionary: {schema_id: {date: count}}

    The list will be in order given by the `schemas` parameter.
    """
    result = []
    for schema in schemas:
        if schema.id not in counts:
            result.append({
                'schema': schema,
                'dates': [{'date': d, 'count': 0} for d in daterange(start_date, end_date)],
                'max_count': 0,
                'total_count': 0,
                'latest_date': None,
            })
        else:
            dates = [{'date': d, 'count': counts[schema.id].get(d, 0)} for d in daterange(start_date, end_date)]
            nonzero_dates = [d['date'] for d in dates if d['count']]
            if nonzero_dates:
                latest_date = max(nonzero_dates)
            else:
                latest_date = None
            result.append({
                'schema': schema,
                'dates': dates,
                'max_count': max(d['count'] for d in dates),
                'total_count': sum(d['count'] for d in dates),
                'latest_date': latest_date,
            })
    return result

def url_to_place(*args, **kwargs):
    # Given args and kwargs captured from the URL, returns the place.
    # This relies on "place_type" being provided in the URLpattern.
    parse_func = kwargs['place_type'] == 'block' and url_to_block or url_to_location
    return parse_func(*args)

def url_to_block(city_slug, street_slug, from_num, to_num, predir, postdir):
    params = {
        'street_slug': street_slug,
        'predir': (predir and predir.upper() or ''),
        'postdir': (postdir and postdir.upper() or ''),
        'from_num': int(from_num),
        'to_num': int(to_num),
    }
    if city_slug:
        city = City.from_slug(city_slug).norm_name
        city_filter = Q(left_city=city) | Q(right_city=city)
    else:
        city_filter = Q()
    b_list = list(Block.objects.filter(city_filter, **params))

    if not b_list:
        raise Http404()

    return b_list[0]

def url_to_location(type_slug, slug):
    return get_object_or_404(Location.objects.select_related(), location_type__slug=type_slug, slug=slug)

def parse_pid(pid):
    """
    Returns a tuple of (place, block_radius, xy_radius), where block_radius and
    xy_radius are None for Locations.

    PID examples:
        'b:12;1' (block ID 12, 1-block radius)
        'l:32' (location ID 32)
    """
    try:
        place_type, place_id = pid.split(':')
        if place_type == 'b':
            place_id, block_radius = place_id.split('.')
        place_id = int(place_id)
    except (KeyError, ValueError):
        raise Http404('Invalid place')
    if place_type == 'b':
        try:
            xy_radius = BLOCK_RADIUS_CHOICES[block_radius]
        except KeyError:
            raise Http404('Invalid radius')
        return (get_object_or_404(Block, id=place_id), block_radius, xy_radius)
    elif place_type == 'l':
        return (get_object_or_404(Location, id=place_id), None, None)
    else:
        raise Http404

def has_clusters(cluster_dict):
    """
    Determines whether the cluster_dict has any actual clusters.

    Catches the case where a queryset has no items that have been geocoded.

    Cluster dicts have keys which are scales, and values which are lists of
    Bunch objects, so this function simply tests to see if any of the lists are
    not empty.
    """
    def any(iterable):
        for element in iterable:
            if not element:
                return False
        return True

    return any(cluster_dict.values())

def block_bbox(block, radius):
    """
    Assumes `block' has `wkt' attribute
    """
    try:
        from osgeo import ogr
    except ImportError:
        import ogr
    env = ogr.CreateGeometryFromWkt(block.wkt).Buffer(radius).GetEnvelope()
    return (env[0], env[2], env[1], env[3])

def make_search_buffer(geom, block_radius):
    """
    Returns a polygon of a buffer around a block's centroid. `geom'
    should be the centroid of the block. `block_radius' is number of
    blocks.
    """
    return geom.buffer(BLOCK_RADIUS_CHOICES[str(block_radius)]).envelope

##############
# AJAX VIEWS #
##############

def validate_address(request):
    # Validates that request.GET['address'] can be parsed with the address parser.
    if not request.GET.get('address', '').strip():
        raise Http404
    geocoder = SmartGeocoder()
    try:
        result = {'address': geocoder.geocode(request.GET['address'])['address']}
    except (DoesNotExist, ParsingError, InvalidBlockButValidStreet):
        result = {}
    except AmbiguousResult, e:
        if get_metro()['multiple_cities']:
            result = {'addresses': [add['address'] + ', ' + add['city'] for add in e.choices]}
        else:
            result = {'addresses': [add['address'] for add in e.choices]}
    return HttpResponse(simplejson.dumps(result), mimetype="application/javascript")

def ajax_wkt(request):
    # JSON -- returns a list of WKT strings for request.GET['q'].
    # If it can't be geocoded, the list is empty.
    # If it's ambiguous, the list has multiple elements.
    q = request.GET.get('q', '').strip()
    if not q:
        wkt_list = []
    else:
        try:
            result = full_geocode(q)
        except DoesNotExist:
            wkt_list = []
        except Exception:
            wkt_list = []
        else:
            if result['type'] == 'block':
                wkt_list = []
            elif result['type'] in ('location', 'place'):
                if result['ambiguous']:
                    wkt_list = [r.wkt for r in result['result']]
                else:
                    wkt_list = [result['result'].location.wkt]
            elif result['type'] == 'address':
                if result['ambiguous']:
                    wkt_list = [r['point'].wkt for r in result['result']]
                else:
                    wkt_list = [result['result']['point'].wkt]
            else:
                wkt_list = []
    return HttpResponse(simplejson.dumps(wkt_list), mimetype="application/javascript")

def ajax_map_popups(request):
    """
    JSON -- returns a list of lists for request.GET['q'] (a comma-separated
    string of NewsItem IDs).

    The structure of the inner lists is [newsitem_id, popup_html, schema_name]
    """
    try:
        newsitem_ids = map(int, request.GET['q'].split(','))
    except (KeyError, ValueError):
        raise Http404('Invalid query')
    if len(newsitem_ids) >= 400:
        raise Http404('Too many points') # Security measure.
    ni_list = list(NewsItem.objects.filter(id__in=newsitem_ids).select_related().order_by('schema__id'))
    populate_attributes_if_needed(ni_list, list(set([ni.schema for ni in ni_list])))
    result = []
    current_schema = current_template = None
    for ni in ni_list:
        schema = ni.schema
        if current_schema != schema:
            template_list = ['db/snippets/newsitem_list_ungrouped/%s.html' % schema.slug,
                             'db/snippets/newsitem_list/%s.html' % schema.slug,
                             'db/snippets/newsitem_list.html']
            current_template = select_template(template_list)
            current_schema = schema
        html = current_template.render(template.Context({'schema': schema, 'newsitem_list': [ni], 'num_newsitems': 1}))
        result.append([ni.id, html, schema.name[0].upper() + schema.name[1:]])
    return HttpResponse(simplejson.dumps(result), mimetype="application/javascript")

def ajax_place_newsitems(request):
    """
    JSON -- expects request.GET['pid'] and request.GET['s'] (a schema ID).
    """
    try:
        s = Schema.public_objects.get(id=int(request.GET['s']))
    except (KeyError, ValueError, Schema.DoesNotExist):
        raise Http404('Invalid Schema')
    place, block_radius, xy_radius = parse_pid(request.GET.get('pid', ''))
    if isinstance(place, Block):
        search_buffer = make_search_buffer(place.location.centroid, block_radius)
        newsitem_qs = NewsItem.objects.filter(location__bboverlaps=search_buffer)
    else:
        newsitem_qs = NewsItem.objects.filter(newsitemlocation__location__id=place.id)

    # Make the JSON output. Note that we have to call dumps() twice because the
    # bunches are a special case.
    ni_list = list(newsitem_qs.filter(schema__id=s.id).order_by('-item_date')[:50])
    bunches = simplejson.dumps(cluster_newsitems(ni_list, 26), cls=ClusterJSON)
    id_list = simplejson.dumps([ni.id for ni in ni_list])
    return HttpResponse('{"bunches": %s, "ids": %s}' % (bunches, id_list), mimetype="application/javascript")

def ajax_place_lookup_chart(request):
    """
    JSON -- expects request.GET['pid'] and request.GET['sf'] (a SchemaField ID).
    """
    try:
        sf = SchemaField.objects.select_related().get(id=int(request.GET['sf']), schema__is_public=True)
    except (KeyError, ValueError, SchemaField.DoesNotExist):
        raise Http404('Invalid SchemaField')
    place, block_radius, xy_radius = parse_pid(request.GET.get('pid', ''))
    qs = NewsItem.objects.filter(schema__id=sf.schema.id)
    filter_url = place.url()[1:]
    if isinstance(place, Block):
        search_buffer = make_search_buffer(place.location.centroid, block_radius)
        qs = qs.filter(location__bboverlaps=search_buffer)
        filter_url += radius_url(block_radius) + '/'
    else:
        qs = qs.filter(newsitemlocation__location__id=place.id)
    total_count = qs.count()
    top_values = qs.top_lookups(sf, 10)
    return render_to_response('db/snippets/lookup_chart.html', {
        'lookup': {'sf': sf, 'top_values': top_values},
        'total_count': total_count,
        'schema': sf.schema,
        'filter_url': filter_url,
    })

def ajax_place_date_chart(request):
    """
    JSON -- expects request.GET['pid'] and request.GET['s'] (a Schema ID).
    """
    try:
        s = Schema.public_objects.get(id=int(request.GET['s']))
    except (KeyError, ValueError, Schema.DoesNotExist):
        raise Http404('Invalid Schema')
    place, block_radius, xy_radius = parse_pid(request.GET.get('pid', ''))
    qs = NewsItem.objects.filter(schema__id=s.id)
    filter_url = place.url()[1:]
    if isinstance(place, Block):
        search_buffer = make_search_buffer(place.location.centroid, block_radius)
        qs = qs.filter(location__bboverlaps=search_buffer)
        filter_url += radius_url(block_radius) + '/'
    else:
        qs = qs.filter(newsitemlocation__location__id=place.id)
    # TODO: Ignore future dates
    end_date = qs.order_by('-item_date').values('item_date')[0]['item_date']
    start_date = end_date - datetime.timedelta(days=30)
    counts = qs.filter(schema__id=s.id, item_date__gte=start_date, item_date__lte=end_date).date_counts()
    date_chart = get_date_chart([s], end_date - datetime.timedelta(days=30), end_date, {s.id: counts})[0]
    return render_to_response('db/snippets/date_chart.html', {
        'schema': s,
        'date_chart': date_chart,
        'filter_url': filter_url,
    })

def ajax_location_type_list(request):
    loc_types = LocationType.objects.order_by('plural_name').values('id', 'slug', 'plural_name')
    response = HttpResponse(mimetype='application/javascript')
    simplejson.dump(list(loc_types), response)
    return response

def ajax_location_list(request, loc_type_id):
    locations = Location.objects.filter(location_type__pk=loc_type_id, is_public=True).order_by('display_order').values('id', 'slug', 'name')
    if not locations:
        raise Http404()
    response = HttpResponse(mimetype='application/javascript')
    simplejson.dump(list(locations), response)
    return response

def ajax_location(request, loc_id):
    try:
        location = Location.objects.get(pk=int(loc_id))
    except (ValueError, Location.DoesNotExist):
        raise Http404()
    loc_obj = dict([(k, getattr(location, k)) for k in ('name', 'area', 'id', 'normalized_name', 'slug', 'population')])
    loc_obj['wkt'] = location.location.wkt
    loc_obj['centroid'] = location.centroid.wkt
    response = HttpResponse(mimetype='application/javascript')
    simplejson.dump(loc_obj, response)
    return response

#########
# VIEWS #
#########

def homepage(request):
    end_date = today()
    start_date = end_date - datetime.timedelta(days=30)

    sparkline_schemas = list(Schema.public_objects.filter(allow_charting=True, is_special_report=False))

    # Order by slug to ensure case-insensitive ordering. (Kind of hackish.)
    lt_list = LocationType.objects.filter(is_significant=True).order_by('slug').extra(select={'count': 'select count(*) from db_location where is_public=True and location_type_id=db_locationtype.id'})
    street_count = Street.objects.count()
    more_schemas = Schema.public_objects.filter(allow_charting=False).order_by('name')

    # Get the public records.
    date_charts = get_date_chart_agg_model(sparkline_schemas, start_date, end_date, AggregateDay)
    empty_date_charts, non_empty_date_charts = [], []
    for chart in date_charts:
        if chart['total_count']:
            non_empty_date_charts.append(chart)
        else:
            empty_date_charts.append(chart)
    non_empty_date_charts.sort(lambda a, b: cmp(b['total_count'], a['total_count']))
    empty_date_charts.sort(lambda a, b: cmp(a['schema'].plural_name, b['schema'].plural_name))

    # Get the news articles.
    ni_list = NewsItem.objects.select_related().filter(schema__slug='news-articles', item_date__gt=start_date).order_by('-item_date')[:100]
    if ni_list:
        populate_schema(ni_list, ni_list[0].schema)
        populate_attributes_if_needed(ni_list, [ni_list[0].schema])

    article_bunches = cluster_newsitems(ni_list, 26)
    try:
        num_articles = [s for s in date_charts if s['schema'].slug == 'news-articles'][0]['total_count']
    except IndexError:
        num_articles = 0

    # Get the featured neighborhood.
    # This automatically chooses a neighborhood with at least 2 recent news articles.
    neighborhoods_with_articles = AggregateLocationDay.objects.filter(
        schema__slug='news-articles', location_type__slug='neighborhoods', total__gte=2,
        date_part__gte=end_date - datetime.timedelta(days=7),
        date_part__lt=end_date + datetime.timedelta(days=1))

    if neighborhoods_with_articles:
        # First try neighborhoods with 4 or more articles. Fall back to any
        # neighborhood with at least 2 articles.
        fn_ids = [x.location_id for x in neighborhoods_with_articles if x.total >= 4]
        if not fn_ids:
            fn_ids = [x.location_id for x in neighborhoods_with_articles]
        fn = Location.objects.get(id=random.choice(fn_ids))
    else:
        # If no neighborhoods have articles, just pick a random neighborhood.
        try:
            fn = Location.objects.filter(location_type__slug='neighborhoods', is_public=True)[0]
        except IndexError:
            # If no neighborhoods have been added to the DB yet, that's fine.
            fn = None

    if fn is not None:
        # Get the featured neighborhood news articles.
        qs = NewsItem.objects.filter(schema__slug='news-articles', newsitemlocation__location__id=fn.id, item_date__gte=start_date, item_date__lte=end_date)
        fn_article_count = qs.count()
        fn_all_articles = list(qs.select_related().order_by('-item_date')[:10])
        fn_articles = []
        if fn_all_articles:
            populate_attributes_if_needed(fn_all_articles, [fn_all_articles[0].schema])
            # Remove any articles whose headlines, excerpts or sources are duplicate.
            headlines, excerpts, sources = set(), set(), set()
            for a in fn_all_articles:
                # Calculate a hash of the excerpt by removing spaces. We use this
                # for duplicate comparison.
                excerpt_hash = re.sub(r'\s', '', a.attribute_values['excerpt'])
                if a.title not in headlines and excerpt_hash not in excerpts and a.attribute_values['source'].name not in sources:
                    headlines.add(a.title)
                    excerpts.add(excerpt_hash)
                    sources.add(a.attribute_values['source'].name)
                    fn_articles.append(a)
                    if len(fn_articles) == 3:
                        break

        # Get the featured neighborhood public records.
        fn_date_charts = get_date_chart_agg_model(sparkline_schemas, start_date, end_date, AggregateLocationDay, kwargs={'location__id': fn.id})
        fn_empty_date_charts, fn_non_empty_date_charts = [], []
        for chart in fn_date_charts:
            if chart['total_count']:
                fn_non_empty_date_charts.append(chart)
            else:
                fn_empty_date_charts.append(chart)
        fn_non_empty_date_charts.sort(lambda a, b: cmp(b['total_count'], a['total_count']))
        fn_empty_date_charts.sort(lambda a, b: cmp(a['schema'].plural_name, b['schema'].plural_name))
    else:
        fn_articles = fn_article_count = fn_non_empty_date_charts = fn_empty_date_charts = None

    return eb_render(request, 'homepage.html', {
        'location_type_list': lt_list,
        'street_count': street_count,
        'all_bunches': simplejson.dumps(article_bunches, cls=ClusterJSON),
        'newsitem_list': ni_list,
        'more_schemas': more_schemas,
        'featured_neighborhood': fn,
        'featured_neighborhood_articles': fn_articles,
        'featured_neighborhood_article_count': fn_article_count,
        'num_articles': num_articles,
        'non_empty_date_charts': non_empty_date_charts,
        'empty_date_charts': empty_date_charts,
        'fn_non_empty_date_charts': fn_non_empty_date_charts,
        'fn_empty_date_charts': fn_empty_date_charts,
    })

def search(request, schema_slug=''):
    "Performs a location search and redirects to the address/xy page."
    # Check whether a schema was provided.
    if schema_slug:
        try:
            schema = get_schema_manager(request).get(slug=schema_slug)
        except Schema.DoesNotExist:
            raise Http404('Schema does not exist')
        url_prefix = schema.url()[:-1]
    else:
        schema = None
        url_prefix = ''

    # Get the query.
    q = request.GET.get('q', '').strip()
    if not q:
        return HttpResponseRedirect(url_prefix + '/') # TODO: Do something better than redirecting.

    # For /search/?type=alert, we redirect results to the alert page, not the
    # place page.
    if request.GET.get('type', '') == 'alert':
        url_method = 'alert_url'
    else:
        url_method = 'url'

    # Try to geocode it using full_geocode().
    try:
        result = full_geocode(q, search_places=False)
    except: # TODO: Naked except clause.
        pass
    else:
        if result['ambiguous']:
            if result['type'] == 'block':
                return eb_render(request, 'db/search_invalid_block.html', {
                    'query': q,
                    'choices': result['result'],
                    'street_name': result['street_name'],
                    'block_number': result['block_number']
                })
            else:
                return eb_render(request, 'db/did_you_mean.html', {'query': q, 'choices': result['result']})
        elif result['type'] == 'location':
            return HttpResponseRedirect(url_prefix + getattr(result['result'], url_method)())
        elif result['type'] == 'address':
            # Block
            if result['result']['block']:
                return HttpResponseRedirect(url_prefix + getattr(result['result']['block'], url_method)())
            # Intersection
            try:
                intersection = Intersection.objects.get(id=result['result']['intersection_id'])
            except Intersection.DoesNotExist:
                pass
            else:
                return HttpResponseRedirect(url_prefix + getattr(intersection, url_method)())

    # Failing the geocoding, look in the special-case table.
    try:
        special_case = SearchSpecialCase.objects.get(query=normalize(q))
    except SearchSpecialCase.DoesNotExist:
        pass
    else:
        if special_case.redirect_to:
            return HttpResponseRedirect(special_case.redirect_to)
        else:
            return eb_render(request, 'db/search_special_case.html', {'query': q, 'special_case': special_case})

    # Failing that, display a list of ZIP codes if this looks like a ZIP.
    if re.search(r'^\s*\d{5}(?:-\d{4})?\s*$', q):
        z_list = Location.objects.filter(location_type__slug='zipcodes', is_public=True).select_related().order_by('name')
        if z_list:
            return eb_render(request, 'db/search_error_zip_list.html', {'query': q, 'zipcode_list': z_list})

    # Failing all of that, display the search error page.
    lt_list = LocationType.objects.filter(is_significant=True).order_by('name')
    return eb_render(request, 'db/search_error.html', {'query': q, 'locationtype_list': lt_list})

def newsitem_detail(request, schema_slug, year, month, day, newsitem_id):
    try:
        date = datetime.date(int(year), int(month), int(day))
    except ValueError:
        raise Http404('Invalid day')
    ni = get_object_or_404(NewsItem.objects.select_related(), id=newsitem_id)

    if ni.schema.slug != schema_slug or ni.item_date != date:
        raise Http404
    if not ni.schema.is_public and not has_staff_cookie(request):
        raise Http404('Not public')

    if not ni.schema.has_newsitem_detail:
        return HttpResponsePermanentRedirect(ni.url)

    atts = ni.attributes_for_template()
    has_location = ni.location is not None

    if has_location:
        locations_within = Location.objects.select_related().filter(location__intersects=ni.location)
    else:
        locations_within = ()

    hide_ads = (request.COOKIES.get(HIDE_ADS_COOKIE_NAME) == 't')

    templates_to_try = ('db/newsitem_detail/%s.html' % ni.schema.slug, 'db/newsitem_detail.html')
    if 'new' in request.GET: # TODO: Remove this after feature is implemented.
        templates_to_try = ('db/newsitem_detail_new.html',) + templates_to_try
    return eb_render(request, templates_to_try, {
        'newsitem': ni,
        'attribute_list': [att for att in atts if att.sf.display],
        'attribute_dict': dict((att.sf.name, att) for att in atts),
        'has_location': has_location,
        'locations_within': locations_within,
        'hide_ads': hide_ads,
    })

def schema_list(request):
    schemainfo_list = SchemaInfo.objects.select_related().filter(schema__is_public=True, schema__is_special_report=False).order_by('schema__plural_name')
    schemafield_list = list(SchemaField.objects.filter(is_filter=True).order_by('display_order'))
    browsable_locationtype_list = LocationType.objects.filter(is_significant=True)

    # Populate s_list, which contains a schema and schemafield list for each schema.
    s_list = []
    for s in schemainfo_list:
        s_list.append({
            'schema': s.schema,
            'schemainfo': s,
            'schemafield_list': [sf for sf in schemafield_list if sf.schema_id == s.schema_id],
        })

    return eb_render(request, 'db/schema_list.html', {
        'schema_list': s_list,
        'browsable_locationtype_list': browsable_locationtype_list,
    })

def schema_detail(request, slug):
    s = get_object_or_404(get_schema_manager(request), slug=slug)
    try:
        si = SchemaInfo.objects.get(schema__id=s.id)
    except SchemaInfo.DoesNotExist:
        si = None

    if s.is_special_report:
        return schema_detail_special_report(request, s, si)

    location_type_list = LocationType.objects.filter(is_significant=True).order_by('slug')

    if s.allow_charting:
        # For the date range, the end_date is the last non-future date
        # with at least one NewsItem.
        try:
            end_date = NewsItem.objects.filter(schema__id=s.id, item_date__lte=today()).values_list('item_date', flat=True).order_by('-item_date')[0]
        except IndexError:
            latest_dates = date_chart = ()
            start_date = end_date = None
        else:
            start_date = end_date - datetime.timedelta(days=constants.NUM_DAYS_AGGREGATE)
            date_chart = get_date_chart_agg_model([s], start_date, end_date, AggregateDay)[0]
            latest_dates = [date['date'] for date in date_chart['dates'] if date['count']]

        # Populate schemafield_list and lookup_list.
        schemafield_list = list(s.schemafield_set.filter(is_filter=True).order_by('display_order'))
        LOOKUP_MIN_DISPLAYED = 7
        LOOKUP_BUFFER = 4
        lookup_list = []
        for sf in schemafield_list:
            if not (sf.is_charted and sf.is_lookup):
                continue
            top_values = list(AggregateFieldLookup.objects.filter(schema_field__id=sf.id).select_related('lookup').order_by('-total')[:LOOKUP_MIN_DISPLAYED + LOOKUP_BUFFER])
            if len(top_values) == LOOKUP_MIN_DISPLAYED + LOOKUP_BUFFER:
                top_values = top_values[:LOOKUP_MIN_DISPLAYED]
                has_more = True
            else:
                has_more = False
            lookup_list.append({'sf': sf, 'top_values': top_values, 'has_more': has_more})

        location_chartfield_list = []

        unknowns = AggregateLocation.objects.filter(
                schema__id=s.id,
                location__slug='unknown').select_related('location')
        unknown_dict = dict([(u.location_type_id, u.total) for u in unknowns])

        # Populate location_chartfield_list.
        for lt in location_type_list:
            # Collect the locations in the location_type here so we don't have
            # to query them again when grouping them with the newsitem totals
            locations = dict([(loc.id, loc) for loc in lt.location_set.iterator()])

            ni_totals = AggregateLocation.objects.filter(
                schema__id=s.id,
                location_type__id=lt.id,
                location__is_public=True).select_related('location').order_by('-total')

            if ni_totals:
                location_chartfield_list.append({'location_type': lt, 'locations': ni_totals[:9], 'unknown': unknown_dict.get(lt.id, 0)})
        ni_list = ()
    else:
        latest_dates = schemafield_list = date_chart = lookup_list = location_chartfield_list = ()
        ni_list = list(NewsItem.objects.filter(schema__id=s.id).order_by('-item_date')[:30])
        populate_schema(ni_list, s)
        populate_attributes_if_needed(ni_list, [s])

    textsearch_sf_list = list(SchemaField.objects.filter(schema__id=s.id, is_searchable=True).order_by('display_order'))
    boolean_lookup_list = [sf for sf in SchemaField.objects.filter(schema__id=s.id, is_filter=True, is_lookup=False).order_by('display_order') if sf.is_type('bool')]

    templates_to_try = ('db/schema_detail/%s.html' % s.slug, 'db/schema_detail.html')

    # The HIDE_SCHEMA_INTRO_COOKIE_NAME cookie is a comma-separated list of
    # schema IDs for schemas whose intro text should *not* be displayed.
    hide_intro = str(s.id) in request.COOKIES.get(HIDE_SCHEMA_INTRO_COOKIE_NAME, '').split(',')

    return eb_render(request, templates_to_try, {
        'schema': s,
        'schemainfo': si,
        'schemafield_list': schemafield_list,
        'location_type_list': location_type_list,
        'date_chart': date_chart,
        'lookup_list': lookup_list,
        'location_chartfield_list': location_chartfield_list,
        'boolean_lookup_list': boolean_lookup_list,
        'search_list': textsearch_sf_list,
        'newsitem_list': ni_list,
        'latest_dates': latest_dates[-3:],
        'hide_intro': hide_intro,
        'hide_intro_cookie_name': HIDE_SCHEMA_INTRO_COOKIE_NAME,
        'start_date': s.min_date,
        'end_date': today(),
    })

def schema_detail_special_report(request, schema, schemainfo):
    ni_list = NewsItem.objects.filter(schema__id=schema.id)
    populate_schema(ni_list, schema)
    populate_attributes_if_needed(ni_list, [schema])
    bunches = cluster_newsitems(ni_list, 26)

    if schema.allow_charting:
        browsable_locationtype_list = LocationType.objects.filter(is_significant=True)
        schemafield_list = list(schema.schemafield_set.filter(is_filter=True).order_by('display_order'))
    else:
        browsable_locationtype_list = []
        schemafield_list = []

    templates_to_try = ('db/schema_detail/%s.html' % schema.slug, 'db/schema_detail_special_report.html')
    return eb_render(request, templates_to_try, {
        'schema': schema,
        'schemainfo': schemainfo,
        'newsitem_list': ni_list,
        'nothing_geocoded': not has_clusters(bunches),
        'all_bunches': simplejson.dumps(bunches, cls=ClusterJSON),
        'browsable_locationtype_list': browsable_locationtype_list,
        'schemafield_list': schemafield_list,
    })

def schema_about(request, slug):
    s = get_object_or_404(get_schema_manager(request), slug=slug)
    si = get_object_or_404(SchemaInfo, schema__id=s.id)
    return eb_render(request, 'db/schema_about.html', {'schemainfo': si, 'schema': s})

def schema_filter(request, slug, urlbits):
    # Due to the way our custom filter UI works, address, date and text
    # searches come in a query string instead of in the URL. Here, we validate
    # those searches and do a redirect so that the address and date are in
    # urlbits.
    if request.GET.get('address', '').strip():
        xy_radius, block_radius, cookies_to_set = block_radius_value(request)
        address = request.GET['address'].strip()
        result = None
        try:
            result = SmartGeocoder().geocode(address)
        except AmbiguousResult, e:
            address_choices = e.choices
        except (GeocodingException, ParsingError):
            address_choices = ()
        if result:
            if result['block']:
                new_url = request.path + result['block'].url()[1:] + radius_url(block_radius) + '/'
            elif result['intersection']:
                new_url = request.path + result['intersection'].url()[1:] + radius_url(block_radius) + '/'
            else:
                raise NotImplementedError('Reached invalid geocoding type: %r' % result)
            return HttpResponseRedirect(new_url)
        else:
            return eb_render(request, 'db/filter_bad_address.html', {
                'address_choices': address_choices,
                'address': address,
                'radius': block_radius,
                'radius_url': radius_url(block_radius),
            })
    if request.GET.get('start_date', '').strip() and request.GET.get('end_date', '').strip():
        try:
            start_date = parse_date(request.GET['start_date'], '%m/%d/%Y')
            end_date = parse_date(request.GET['end_date'], '%m/%d/%Y')
        except ValueError:
            return HttpResponseRedirect('../')
        if start_date.year < 1900 or end_date.year < 1900:
            # This prevents strftime from throwing a ValueError.
            raise Http404('Dates before 1900 are not supported.')
        new_url = request.path + '%s,%s' % (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')) + '/'
        return HttpResponseRedirect(new_url)
    if request.GET.get('textsearch', '').strip() and request.GET.get('q', '').strip():
        new_url = request.path + 'by-%s/%s/' % (request.GET['textsearch'], urllib.quote(request.GET['q']))
        return HttpResponseRedirect(new_url)

    s = get_object_or_404(get_schema_manager(request), slug=slug, is_special_report=False)
    if not s.allow_charting:
        return HttpResponsePermanentRedirect(s.url())
    filter_sf_list = list(SchemaField.objects.filter(schema__id=s.id, is_filter=True).order_by('display_order'))
    textsearch_sf_list = list(SchemaField.objects.filter(schema__id=s.id, is_searchable=True).order_by('display_order'))

    # Use SortedDict to preserve the display_order.
    filter_sf_dict = SortedDict([(sf.slug, sf) for sf in filter_sf_list] + [(sf.slug, sf) for sf in textsearch_sf_list])

    # Create the initial QuerySet of NewsItems.
    start_date = s.min_date
    end_date = today()
    qs = NewsItem.objects.filter(schema__id=s.id, item_date__lte=end_date).order_by('-item_date')

    lookup_descriptions = []

    # urlbits is a string describing the filters (or None, in the case of
    # "/filter/"). Cycle through them to see which ones are valid.
    urlbits = urlbits or ''
    urlbits = filter(None, urlbits.split('/')[::-1]) # Reverse them, so we can use pop().
    filters = SortedDict()
    date_filter_applied = location_filter_applied = False
    while urlbits:
        bit = urlbits.pop()

        # Date range
        if bit == 'by-date' or bit == 'by-pub-date':
            if date_filter_applied:
                raise Http404('Only one date filter can be applied')
            try:
                date_range = urlbits.pop()
            except IndexError:
                raise Http404('Missing date range')
            try:
                start_date, end_date = date_range.split(',')
                start_date = datetime.date(*map(int, start_date.split('-')))
                end_date = datetime.date(*map(int, end_date.split('-')))
            except (IndexError, ValueError, TypeError):
                raise Http404('Missing or invalid date range')
            if bit == 'by-date':
                date_field_name = 'item_date'
                label = s.date_name
            else:
                date_field_name = 'pub_date'
                label = 'date published'
            gte_kwarg = '%s__gte' % date_field_name
            lt_kwarg = '%s__lt' % date_field_name
            kwargs = {
                gte_kwarg: start_date,
                lt_kwarg: end_date+datetime.timedelta(days=1)
            }
            qs = qs.filter(**kwargs)
            if start_date == end_date:
                value = dateformat.format(start_date, 'N j, Y')
            else:
                value = u'%s \u2013 %s' % (dateformat.format(start_date, 'N j, Y'), dateformat.format(end_date, 'N j, Y'))
            filters['date'] = {'name': 'date', 'label': label, 'short_value': value, 'value': value, 'url': '%s/%s,%s' % (bit, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))}
            date_filter_applied = True

        # Lookup
        elif bit.startswith('by-'):
            sf_slug = bit[3:]
            try:
                # Pop it so that we can't get subsequent lookups for this SchemaField.
                sf = filter_sf_dict.pop(sf_slug)
            except KeyError:
                raise Http404('Invalid SchemaField slug')
            if sf.is_lookup:
                if urlbits:
                    look = get_object_or_404(Lookup, schema_field__id=sf.id, slug=urlbits.pop())
                    qs = qs.by_attribute(sf, look.id)
                    if look.description:
                        lookup_descriptions.append(look)
                    filters[sf.name] = {'name': sf.name, 'label': sf.pretty_name, 'short_value': look.name, 'value': look.name, 'url': 'by-%s/%s' % (sf.slug, look.slug)}
                else: # List of available lookups.
                    lookup_list = Lookup.objects.filter(schema_field__id=sf.id).order_by('name')
                    filters['lookup'] = {'name': 'lookup', 'label': None, 'value': 'By ' + sf.pretty_name, 'url': None}
                    return eb_render(request, 'db/filter_lookup_list.html', {
                        'schema': s,
                        'filters': filters,
                        'lookup_type': sf.pretty_name,
                        'lookup_list': lookup_list,
                    })
            elif sf.is_type('bool'): # Boolean field.
                if urlbits:
                    slug = urlbits.pop()
                    try:
                        real_val = {'yes': True, 'no': False, 'na': None}[slug]
                    except KeyError:
                        raise Http404('Invalid boolean field URL')
                    qs = qs.by_attribute(sf, real_val)
                    value = {True: 'Yes', False: 'No', None: 'N/A'}[real_val]
                    filters[sf.name] = {'name': sf.name, 'label': sf.pretty_name, 'short_value': value, 'value': u'%s%s: %s' % (sf.pretty_name[0].upper(), sf.pretty_name[1:], value), 'url': 'by-%s/%s' % (sf.slug, slug)}
                else:
                    filters['lookup'] = {'name': sf.name, 'label': None, 'value': u'By whether they ' + sf.pretty_name_plural, 'url': None}
                    return eb_render(request, 'db/filter_lookup_list.html', {
                        'schema': s,
                        'filters': filters,
                        'lookup_type': u'whether they ' + sf.pretty_name_plural,
                        'lookup_list': [{'slug': 'yes', 'name': 'Yes'}, {'slug': 'no', 'name': 'No'}, {'slug': 'na', 'name': 'N/A'}],
                    })
            else: # Text-search field.
                if not urlbits:
                    raise Http404('Text search lookup requires search params')
                query = urlbits.pop()
                qs = qs.text_search(sf, query)
                filters[sf.name] = {'name': sf.name, 'label': sf.pretty_name, 'short_value': query, 'value': query, 'url': 'by-%s/%s' % (sf.slug, query)}

        # Street/address
        elif bit.startswith('streets'):
            if location_filter_applied:
                raise Http404('Only one location filter can be applied')
            try:
                if get_metro()['multiple_cities']:
                    city_slug = urlbits.pop()
                else:
                    city_slug = ''
                street_slug = urlbits.pop()
                block_range = urlbits.pop()
            except IndexError:
                raise Http404()
            try:
                block_radius = urlbits.pop()
            except IndexError:
                xy_radius, block_radius, cookies_to_set = block_radius_value(request)
                return HttpResponseRedirect(request.path + radius_url(block_radius) + '/')
            m = re.search('^%s$' % constants.BLOCK_URL_REGEX, block_range)
            if not m:
                raise Http404('Invalid block URL')
            block = url_to_block(city_slug, street_slug, *m.groups())
            m = re.search(r'^(\d)-blocks?$', block_radius)
            if not m:
                raise Http404('Invalid block radius')
            block_radius = m.group(1)
            if block_radius not in BLOCK_RADIUS_CHOICES:
                raise Http404('Invalid block radius')
            search_buffer = make_search_buffer(block.location.centroid, block_radius)
            qs = qs.filter(location__bboverlaps=search_buffer)
            value = '%s block%s around %s' % (block_radius, (block_radius != '1' and 's' or ''), block.pretty_name)
            filters['location'] = {
                'name': 'location',
                'label': 'Area',
                'short_value': value,
                'value': value,
                'url': block.url()[1:] + radius_url(block_radius),
                'location_name': block.pretty_name,
                'location_object': block,
            }
            location_filter_applied = True

        # Location
        elif bit.startswith('locations'):
            if location_filter_applied:
                raise Http404('Only one location filter can be applied')
            if not urlbits:
                raise Http404()
            location_type_slug = urlbits.pop()
            if urlbits:
                loc = url_to_location(location_type_slug, urlbits.pop())
                qs = qs.filter(newsitemlocation__location__id=loc.id)
                filters['location'] = {
                    'name': 'location',
                    'label': loc.location_type.name,
                    'short_value': loc.name,
                    'value': loc.name,
                    'url': 'locations/%s/%s' % (location_type_slug, loc.slug),
                    'location_name': loc.name,
                    'location_object': loc,
                }
                location_filter_applied = True
            else: # List of available locations for this location type.
                lookup_list = Location.objects.filter(location_type__slug=location_type_slug, is_public=True).order_by('display_order')
                if not lookup_list:
                    raise Http404()
                location_type = lookup_list[0].location_type
                filters['location'] = {'name': 'location', 'label': None, 'value': 'By ' + location_type.name, 'url': None}
                return eb_render(request, 'db/filter_lookup_list.html', {
                    'schema': s,
                    'filters': filters,
                    'lookup_type': location_type.name,
                    'lookup_list': lookup_list,
                })

        else:
            raise Http404('Invalid filter type')

    # Get the list of top values for each lookup that isn't being filtered-by.
    # LOOKUP_MIN_DISPLAYED sets the number of records to display for each lookup
    # type. Normally, the UI displays a "See all" link, but the link is removed
    # if there are fewer than (LOOKUP_MIN_DISPLAYED + LOOKUP_BUFFER) records.
    LOOKUP_MIN_DISPLAYED = 7
    LOOKUP_BUFFER = 4
    lookup_list, boolean_lookup_list, search_list = [], [], []
    for sf in filter_sf_dict.values():
        if sf.is_searchable:
            search_list.append(sf)
        elif sf.is_type('bool'):
            boolean_lookup_list.append(sf)
        elif sf.is_lookup:
            top_values = AggregateFieldLookup.objects.filter(schema_field__id=sf.id).select_related('lookup').order_by('-total')[:LOOKUP_MIN_DISPLAYED+LOOKUP_BUFFER]
            if len(top_values) == LOOKUP_MIN_DISPLAYED + LOOKUP_BUFFER:
                top_values = top_values[:LOOKUP_MIN_DISPLAYED]
                has_more = True
            else:
                has_more = False
            lookup_list.append({'sf': sf, 'top_values': top_values, 'has_more': has_more})

    # Get the list of LocationTypes if a location filter has *not* been applied.
    if location_filter_applied:
        location_type_list = []
    else:
        location_type_list = LocationType.objects.filter(is_significant=True).order_by('slug')

    # Do the pagination. We don't use Django's Paginator class because it uses
    # SELECT COUNT(*), which we want to avoid.
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        raise Http404('Invalid page')
    idx_start = (page - 1) * constants.FILTER_PER_PAGE
    idx_end = page * constants.FILTER_PER_PAGE

    # Get one extra, so we can tell whether there's a next page.
    ni_list = list(qs[idx_start:idx_end+1])
    if page > 1 and not ni_list:
        raise Http404('No objects on page %s' % page)
    if len(ni_list) > constants.FILTER_PER_PAGE:
        has_next = True
        ni_list = ni_list[:-1]
    else:
        has_next = False
        idx_end = idx_start + len(ni_list)
    has_previous = page > 1

    populate_schema(ni_list, s)
    populate_attributes_if_needed(ni_list, [s])
    bunches = cluster_newsitems(ni_list, 26)

    return eb_render(request, 'db/filter.html', {
        'schema': s,
        'newsitem_list': ni_list,

        # Pagination stuff
        'has_next': has_next,
        'has_previous': has_previous,
        'page_number': page,
        'previous_page_number': page - 1,
        'next_page_number': page + 1,
        'page_start_index': idx_start + 1,
        'page_end_index': idx_end,

        'nothing_geocoded': not has_clusters(bunches),
        'all_bunches': simplejson.dumps(bunches, cls=ClusterJSON),
        'lookup_list': lookup_list,
        'boolean_lookup_list': boolean_lookup_list,
        'search_list': search_list,
        'location_type_list': location_type_list,
        'filters': filters,
        'date_filter_applied': date_filter_applied,
        'location_filter_applied': location_filter_applied,
        'lookup_descriptions': lookup_descriptions,
        'start_date': start_date,
        'end_date': end_date,
    })

def location_type_detail(request, slug):
    lt = get_object_or_404(LocationType, slug=slug)
    order_by = get_metro()['multiple_cities'] and ('city', 'display_order') or ('display_order',)
    loc_list = Location.objects.filter(location_type__id=lt.id, is_public=True).order_by(*order_by)
    lt_list = [{'location_type': i, 'is_current': i == lt} for i in LocationType.objects.filter(is_significant=True).order_by('plural_name')]
    return eb_render(request, 'db/location_type_detail.html', {
        'location_type': lt,
        'location_list': loc_list,
        'location_type_list': lt_list,
    })

def city_list(request):
    c_list = [City.from_norm_name(c['city']) for c in Street.objects.distinct().values('city').order_by('city')]
    return eb_render(request, 'db/city_list.html', {'city_list': c_list})

def street_list(request, city_slug):
    city = city_slug and City.from_slug(city_slug) or None
    kwargs = city_slug and {'city': city.norm_name} or {}
    streets = list(Street.objects.filter(**kwargs).order_by('street', 'suffix'))
    if not streets:
        raise Http404('This city has no streets')
    return eb_render(request, 'db/street_list.html', {
        'street_list': streets,
        'city': city,
    })

def block_list(request, city_slug, street_slug):
    city = city_slug and City.from_slug(city_slug) or None
    kwargs = {'street_slug': street_slug}
    if city_slug:
        city_filter = Q(left_city=city.norm_name) | Q(right_city=city.norm_name)
    else:
        city_filter = Q()
    blocks = Block.objects.filter(city_filter, **kwargs).order_by('postdir', 'predir', 'from_num', 'to_num')
    if not blocks:
        raise Http404
    return eb_render(request, 'db/block_list.html', {
        'block_list': blocks,
        'first_block': blocks[0],
        'city': city,
    })

def generic_place_page(request, template_name, place, extra_context=None):
    extra_context = extra_context or {}
    if place.location is None:
        is_block = False
        place_wkt = ''
    elif isinstance(place, Block):
        is_block = True
        place_wkt = ''
    else:
        is_block = False
        place_wkt = place.location.simplify(tolerance=0.001, preserve_topology=True)
    return eb_render(request, template_name, dict(place=place, is_block=is_block, place_wkt=place_wkt, **extra_context))

def place_detail(request, *args, **kwargs):
    schema_manager = get_schema_manager(request)
    place = url_to_place(*args, **kwargs)
    cookies_to_set, bbox = {}, None
    if place.location is None:
        newsitem_qs = NewsItem.objects.filter(newsitemlocation__location__id=place.id)
        bbox = get_metro()['extent']
        block_radius = None
        nearby_locations = []
        saved_place_lookup = {'location__id': place.id}
    elif isinstance(place, Block):
        xy_radius, block_radius, cookies_to_set = block_radius_value(request)
        search_buf = make_search_buffer(place.location.centroid, block_radius)
        newsitem_qs = NewsItem.objects.filter(location__bboverlaps=search_buf)
        nearby_locations = list(Location.objects.filter(location_type__is_significant=True, location__bboverlaps=search_buf).select_related())
        bbox = search_buf.extent
        saved_place_lookup = {'block__id': place.id}
    else:
        newsitem_qs = NewsItem.objects.filter(newsitemlocation__location__id=place.id)
        search_buf = make_search_buffer(place.location.centroid, 3)
        nearby_locations = Location.objects.filter(location_type__is_significant=True).select_related().exclude(id=place.id).order_by('location_type__id').filter(location__bboverlaps=search_buf)
        bbox = search_buf.extent
        block_radius = None
        saved_place_lookup = {'location__id': place.id}

    # Determine whether this is a saved place.
    is_saved = False
    if request.user:
        saved_place_lookup['user_id'] = request.user.id # TODO: request.user.id should not do a DB lookup
        is_saved = SavedPlace.objects.filter(**saved_place_lookup).count()

    if kwargs.get('detail_page', False):
        is_latest_page = True
        # Check the query string for the max date to use. Otherwise, fall
        # back to today.
        end_date = today()
        if 'start' in request.GET:
            try:
                end_date = parse_date(request.GET['start'], '%m/%d/%Y')
                is_latest_page = False
            except ValueError:
                raise Http404

        # As an optimization, limit the NewsItems to those published in the
        # last few days.
        start_date = end_date - datetime.timedelta(days=constants.LOCATION_DAY_OPTIMIZATION)
        ni_list = newsitem_qs.filter(pub_date__gt=start_date-datetime.timedelta(days=1), pub_date__lt=end_date+datetime.timedelta(days=1)).select_related()
        if not has_staff_cookie(request):
            ni_list = ni_list.filter(schema__is_public=True)
        ni_list = ni_list.extra(
            select={'pub_date_date': 'date(db_newsitem.pub_date)'},
            order_by=('-pub_date_date', '-schema__importance', 'schema')
        )[:constants.NUM_NEWS_ITEMS_PLACE_DETAIL]
        ni_list = smart_bunches(list(ni_list), max_days=5, max_items_per_day=100)
        schemas_used = list(set([ni.schema for ni in ni_list]))
        s_list = schema_manager.filter(is_special_report=False, allow_charting=True).order_by('plural_name')
        populate_attributes_if_needed(ni_list, schemas_used)
        bunches = cluster_newsitems(ni_list, 26)
        if ni_list:
            next_day = ni_list[-1].pub_date - datetime.timedelta(days=1)
        else:
            next_day = None

        hidden_schema_list = []
        if request.user is not None:
            hidden_schema_list = [o.schema for o in HiddenSchema.objects.filter(user_id=request.user.id)]

        context = {
            'newsitem_list': ni_list,
            'nothing_geocoded': not has_clusters(bunches),
            'all_bunches': simplejson.dumps(bunches, cls=ClusterJSON),
            'next_day': next_day,
            'is_latest_page': is_latest_page,
            'hidden_schema_list': hidden_schema_list,
        }
        template_name = 'db/place_detail.html'
    else:
        # Here, the goal is to get the latest nearby NewsItems for each
        # schema. A naive way to do this would be to run the query once for
        # each schema, but we improve on that by grabbing the latest 300
        # items of ANY schema and hoping that several of the schemas include
        # all of their recent items in that list. Then, for any remaining
        # schemas, we do individual queries as a last resort.
        # Note that we iterate over the 300 NewsItems as the outer loop rather
        # than iterating over the schemas as the outer loop, because there are
        # many more NewsItems than schemas.
        s_list = SortedDict([(s.id, [s, [], 0]) for s in schema_manager.filter(is_special_report=False).order_by('plural_name')])
        needed = set(s_list.keys())
        for ni in newsitem_qs.order_by('-item_date', '-id')[:300]: # Ordering by ID ensures consistency across page views.
            s_id = ni.schema_id
            if s_id in needed:
                s_list[s_id][1].append(ni)
                s_list[s_id][2] += 1
                if s_list[s_id][2] == s_list[s_id][0].number_in_overview:
                    needed.remove(s_id)
        sf_dict = {}
        for sf in SchemaField.objects.filter(is_lookup=True, is_charted=True, schema__is_public=True, schema__is_special_report=False).values('id', 'schema_id', 'pretty_name').order_by('schema__id', 'display_order'):
            sf_dict.setdefault(sf['schema_id'], []).append(sf)
        schema_blocks, all_newsitems = [], []
        for s, newsitems, _ in s_list.values():
            if s.id in needed:
                newsitems = list(newsitem_qs.filter(schema__id=s.id).order_by('-item_date', '-id')[:s.number_in_overview])
            populate_schema(newsitems, s)
            schema_blocks.append({
                'schema': s,
                'latest_newsitems': newsitems,
                'has_newsitems': bool(newsitems),
                'lookup_charts': sf_dict.get(s.id),
            })
            all_newsitems.extend(newsitems)
        s_list = [s[0] for s in s_list.values()]
        populate_attributes_if_needed(all_newsitems, s_list)
        s_list = [s for s in s_list if s.allow_charting]
        context = {'schema_blocks': schema_blocks}
        template_name = 'db/place_overview.html'

    context.update({
        'nearby_locations': nearby_locations,
        'block_radius': block_radius,
        'bbox': bbox,
        'filtered_schema_list': s_list,
        'filter_map_by_schema': 'filter' in request.GET,
        'is_saved': is_saved,
    })

    response = generic_place_page(request, template_name, place, context)
    if cookies_to_set:
        for k, v in cookies_to_set.items():
            response.set_cookie(k, v)
    return response

def feed_signup(request, *args, **kwargs):
    place = url_to_place(*args, **kwargs)
    s_list = get_schema_manager(request).filter(is_special_report=False).order_by('plural_name')
    return generic_place_page(request, 'db/feed_signup.html', place, {'schema_list': s_list})
