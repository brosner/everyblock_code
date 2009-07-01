import re
import urllib
from django.http import Http404
from django.conf import settings
from django.core.cache import cache
from django.template import Template
from django.template.context import RequestContext
from django.db import connection
from ebpub.metros.allmetros import METRO_DICT

class CachedTemplateMiddleware(object):
    # Re-renders any text/html responses through the template system again,
    # to catch any template code that's been bubbled up via the {% raw %}
    # template tag.
    #
    # Also checks the cache for cached requests. Note that cached requests
    # use keys like "chicago/locations/neighborhoods/", and the
    # value in the cache is assumed to be an HttpResponse object.
    def process_view(self, request, view_func, view_args, view_kwargs):
        response = None

        # If '__raw__' is provided in the query string, then we don't hit
        # the cache. This is because the populate_cache() function in
        # everyblock.utils needs a hook for making a request that bypasses
        # the cache. If it didn't have this hook, then it would just read
        # the existing page from the cache and put it back in the cache!
        if request.method == 'GET' and '__raw__' not in request.GET:
            # e.g., "chicago/locations/neighborhoods/"
            cache_key = '%s%s' % (settings.SHORT_NAME, request.path)
            # URL-encode the cache_key, because it's built from
            # the request.path, which may contain control characters
            # (like spaces) that the memcached backend doesn't allow.
            cache_key = urllib.quote(cache_key)
            response = cache.get(cache_key, None)

        if response is None:
            response = view_func(request, *view_args, **view_kwargs)

        # For simplicity, there's a backdoor to get the raw template for any
        # page -- '__raw__' in the query string.
        if '__raw__' not in request.GET and response['content-type'].startswith('text/html'):
            t = Template('{% load raw %}{% raw silent %}' + response.content + '{% endraw %}')
            response.content = t.render(RequestContext(request))

        return response

class DynamicCitySettingsMiddleware(object):
    """
    Sets certain Django settings dynamically based on the city short
    name as derived from the EB_CITY_SLUG environment variable.
    """
    def process_request(self, request):
        # We look to see if the web server has set the EB_CITY_SLUG
        # environment variable, and use that if so, since it will be
        # slightly faster than doing it ourselves in Python. But we
        # fall back to that if it's not.
        short_name = request.environ.get('EB_CITY_SLUG')
        if short_name is None:
            raise Http404(u'unknown city') 
        if short_name not in METRO_DICT:
            raise Http404(u'unknown city')

        # Reset the database connection
        conn = connection
        conn.connection = None
        conn.settings_dict['DATABASE_NAME'] = short_name
        settings.DATABASE_NAME = short_name

        settings.TEMPLATE_DIRS = (
            '/home/eb/templates/base',
            '/home/eb/templates/cities/' + short_name,
        )
        try:
            settings.TIME_ZONE = METRO_DICT[short_name]['time_zone']
        except KeyError:
            raise Http404(u'time zone not set')
        settings.SHORT_NAME = short_name

        return None
