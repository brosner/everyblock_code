from django.conf import settings
from django.core.cache import cache
from django.test.client import ClientHandler
from ebpub.db.models import LocationType, Schema

CACHED_URLS = ('/', '/robots.txt', '/news/', '/streets/')

def iter_urls():
    for url in CACHED_URLS:
        yield url
    for s in Schema.public_objects.all():
        schema_url = s.url()
        yield schema_url
        yield schema_url + 'about/'
    # Cache location type detail pages, but not the root of
    # custom-drawn ones, because that will be unique to the user
    for lt in LocationType.objects.exclude(slug='custom'):
        yield lt.url()

def populate_cache():
    # Here, we make requests directly via a ClientHandler rather than over
    # the live Internet, because we want to cache the whole HttpResponse
    # object, not just the text of the response. In order to do this, we have
    # to set up an environment and pass that to ClientHandler for each request.
    environ = {
        # Set __raw__ so that the templates are only half rendered.
        # (See everyblock.utils.middleware.CachedTemplateMiddleware for more.)
        'QUERY_STRING':      '__raw__=1',
        'REMOTE_ADDR':       '127.0.0.1',
        'REQUEST_METHOD':    'GET',
        'SCRIPT_NAME':       '',
        'SERVER_NAME':       'cacheserver',
        'SERVER_PORT':       '80',
        'SERVER_PROTOCOL':   'HTTP/1.1',
        'wsgi.version':      (1,0),
        'wsgi.url_scheme':   'http',
        'wsgi.multiprocess': True,
        'wsgi.multithread':  False,
        'wsgi.run_once':     False,
    }
    handler = ClientHandler()
    for url in iter_urls():
        cache_key = '%s%s' % (settings.SHORT_NAME, url)
        print cache_key
        response = handler(dict(environ, PATH_INFO=url))
        cache.set(cache_key, response, 60 * 60 * 24) # Cache for 24 hours.

if __name__ == "__main__":
    populate_cache()
