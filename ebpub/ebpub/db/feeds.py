from django.contrib.syndication.feeds import Feed
from django.contrib.syndication.views import feed as django_feed_view
from django.http import Http404, HttpResponsePermanentRedirect
from django.utils import simplejson
from django.utils.feedgenerator import Rss201rev2Feed
from ebpub.db.constants import BLOCK_URL_REGEX
from ebpub.db.models import NewsItem, Location
from ebpub.db.utils import populate_attributes_if_needed, today
from ebpub.db.views import make_search_buffer, url_to_block, BLOCK_RADIUS_CHOICES, BLOCK_RADIUS_DEFAULT
from ebpub.metros.allmetros import get_metro
from ebpub.streets.models import Block
import datetime
import re

# RSS feeds powered by Django's syndication framework use MIME type
# 'application/rss+xml'. That's unacceptable to us, because that MIME type
# prompts users to download the feed in some browsers, which is confusing.
# Here, we set the MIME type so that it doesn't do that prompt.
class CorrectMimeTypeFeed(Rss201rev2Feed):
    mime_type = 'application/xml'

# This is a django.contrib.syndication.feeds.Feed subclass whose feed_type
# is set to our preferred MIME type.
class EbpubFeed(Feed):
    feed_type = CorrectMimeTypeFeed

location_re = re.compile(r'^([-_a-z0-9]{1,32})/([-_a-z0-9]{1,32})$')

def bunch_by_date_and_schema(newsitem_list, date_cutoff):
    current_schema_date, current_list = None, []
    for ni in newsitem_list:
        ni_pub_date = ni.pub_date.date()

        # Remove collapsable newsitems that shouldn't be published in the
        # feed yet. See the lengthy comment in AbstractLocationFeed.items().
        if ni.schema.can_collapse and ni_pub_date >= date_cutoff:
            continue

        if current_schema_date != (ni.schema, ni_pub_date):
            if current_list:
                yield current_list
            current_schema_date = (ni.schema, ni_pub_date)
            current_list = [ni]
        else:
            current_list.append(ni)
    if current_list:
        yield current_list

class AbstractLocationFeed(EbpubFeed):
    "Abstract base class for location-specific RSS feeds."

    title_template = 'feeds/streets_title.html'
    description_template = 'feeds/streets_description.html'

    def items(self, obj):
        # Note that items() returns "packed" tuples instead of objects.
        # This is necessary because we return NewsItems and blog entries,
        # plus different types of NewsItems (bunched vs. unbunched).

        # Limit the feed to all NewsItems published in the last four days.
        # We *do* include items from today in this query, but we'll filter
        # those later in this method so that only today's *uncollapsed* items
        # (schema.can_collapse=False) will be included in the feed. We don't
        # want today's *collapsed* items to be included, because more items
        # might be added to the database before the day is finished, and
        # that would result in the RSS item being updated multiple times, which
        # is annoying.
        today_value = today()
        start_date = today_value - datetime.timedelta(days=4)
        end_date = today_value
        # Note: The pub_date__lt=end_date+(1 day) ensures that we don't miss
        # stuff that has a pub_date of the afternoon of end_date. A straight
        # pub_date__range would miss those items.
        qs = NewsItem.objects.select_related().filter(schema__is_public=True, pub_date__gte=start_date, pub_date__lt=end_date+datetime.timedelta(days=1)).extra(select={'pub_date_date': 'date(db_newsitem.pub_date)'}).order_by('-pub_date_date', 'schema__id', 'id')

        # Filter out ignored schemas -- those whose slugs are specified in
        # the "ignore" query-string parameter.
        if 'ignore' in self.request.GET:
            schema_slugs = self.request.GET['ignore'].split(',')
            qs = qs.exclude(schema__slug__in=schema_slugs)

        # Filter wanted schemas -- those whose slugs are specified in the
        # "only" query-string parameter.
        if 'only' in self.request.GET:
            schema_slugs = self.request.GET['only'].split(',')
            qs = qs.filter(schema__slug__in=schema_slugs)

        block_radius = self.request.GET.get('radius', BLOCK_RADIUS_DEFAULT)
        if block_radius not in BLOCK_RADIUS_CHOICES:
            raise Http404('Invalid radius')
        ni_list = list(self.newsitems_for_obj(obj, qs, block_radius))
        schema_list = list(set([ni.schema for ni in ni_list]))
        populate_attributes_if_needed(ni_list, schema_list)

        is_block = isinstance(obj, Block)

        # Note that this decorates the results by returning tuples instead of
        # NewsItems. This is necessary because we're bunching.
        for schema_group in bunch_by_date_and_schema(ni_list, today_value):
            schema = schema_group[0].schema
            if schema.can_collapse:
                yield ('newsitem', obj, schema, schema_group, is_block, block_radius)
            else:
                for newsitem in schema_group:
                    yield ('newsitem', obj, schema, newsitem, is_block, block_radius)

    def item_pubdate(self, item):
        if item[0] == 'newsitem':
            if item[2].can_collapse:
                return item[3][0].pub_date
            return item[3].pub_date
        else:
            raise NotImplementedError()

    def item_link(self, item):
        if item[0] == 'newsitem':
            if item[2].can_collapse:
                return item[1].url() + '#%s-%s' % (item[3][0].schema.slug, item[3][0].pub_date.strftime('%Y%m%d'))
            return item[3].item_url_with_domain()
        else:
            raise NotImplementedError()

    def newsitems_for_obj(self, obj, qs, block_radius):
        raise NotImplementedError('Subclasses must implement this.')

class BlockFeed(AbstractLocationFeed):
    def get_object(self, bits):
        # TODO: This duplicates the logic in the URLconf. Fix Django to allow
        # for RSS feed URL parsing in the URLconf.
        # See http://code.djangoproject.com/ticket/4720
        if get_metro()['multiple_cities']:
            street_re = re.compile(r'^([-a-z]{3,40})/([-a-z0-9]{1,64})/%s$' % BLOCK_URL_REGEX)
        else:
            street_re = re.compile(r'^()([-a-z0-9]{1,64})/%s$' % BLOCK_URL_REGEX)
        m = street_re.search('/'.join(bits))
        if not m:
            raise Block.DoesNotExist
        city_slug, street_slug, from_num, to_num, predir, postdir = m.groups()
        return url_to_block(city_slug, street_slug, from_num, to_num, predir, postdir)

    def title(self, obj):
        return u"EBPUB: %s" % obj.pretty_name

    def link(self, obj):
        return obj.url()

    def description(self, obj):
        return u"EBPUB %s" % obj.pretty_name

    def newsitems_for_obj(self, obj, qs, block_radius):
        search_buffer = make_search_buffer(obj.location.centroid, block_radius)
        return qs.filter(location__bboverlaps=search_buffer)

class LocationFeed(AbstractLocationFeed):
    def get_object(self, bits):
        m = location_re.search('/'.join(bits))
        if not m:
            raise Location.DoesNotExist
        type_slug, slug = m.groups()
        return Location.objects.select_related().get(location_type__slug=type_slug, slug=slug)

    def title(self, obj):
        return u"EBPUB: %s" % obj.name

    def link(self, obj):
        return obj.url()

    def description(self, obj):
        return u"EBPUB %s" % obj.name

    def newsitems_for_obj(self, obj, qs, block_radius):
        return qs.filter(newsitemlocation__location__id=obj.id)

FEEDS = {
    'streets': BlockFeed,
    'locations': LocationFeed,
}

def feed_view(request, *args, **kwargs):
    kwargs['feed_dict'] = FEEDS
    return django_feed_view(request, *args, **kwargs)
