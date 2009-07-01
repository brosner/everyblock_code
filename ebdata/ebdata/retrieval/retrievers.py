"""
Retriever classes.

A Retriever class simply knows how to retrieve a resource off of the Web. It
knows nothing about *scraping*, i.e., parsing the contents of Web pages.
"""

import httplib2
from Cookie import SimpleCookie, CookieError
from urllib import urlencode
from urlparse import urljoin
import logging
import time
import socket

class RetrievalError(Exception):
    "Couldn't retrieve data"
    pass

class PageNotFoundError(RetrievalError):
    "Couldn't retrieve data"
    pass


class Default:
    # Used to determine whether a default argument was given to Retriever.__init__().
    pass

LOG_ENTRY_FMT = "%(timestamp)s\t%(method)s\t%(uri)s\t%(status)s\t%(elapsed)s\t%(size)s"

class Retriever(object):
    'HTTP client.'
    def __init__(self, user_agent=None, cache=Default, timeout=20, sleep=0):
        # Use cache=None to explicitly turn off caching.
        # If you don't provide cache, then it will cache in
        # settings.HTTP_CACHE, or '/tmp/eb_scraper_cache' if
        # the setting is undefined.
        # sleep should be the number of seconds to sleep between requests.
        from django.conf import settings
        if cache is Default:
            cache = getattr(settings, 'HTTP_CACHE', '/tmp/eb_scraper_cache')
        self.h = httplib2.Http(cache, timeout=timeout)
        self.h.force_exception_to_status_code = False
        self.h.follow_redirects = False
        self.user_agent = user_agent or 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.0)'
        self._cookies = SimpleCookie()
        self.logger = logging.getLogger('eb.retrieval.retriever')
        self.sleep = sleep

        # Keep track of whether we've downloaded any pages yet.
        # This makes sure we don't sleep before the very first requested page.
        self.page_downloaded = False

    def clear_cookies(self):
        self._cookies = SimpleCookie()

    def get_html_and_headers(self, uri, data=None, headers=None, send_cookies=True, follow_redirects=True, raise_on_error=True):
        "Retrieves the resource and returns a tuple of (content, header dictionary)."
        # Sleep, if necessary, but only if a page has already been downloaded
        # with this retriever. (We don't want to sleep before the very first
        # request that a retriever makes, because that would be unnecessary.)
        if self.sleep and self.page_downloaded:
            self.logger.debug('Sleeping for %s seconds', self.sleep)
            time.sleep(self.sleep)
        self.page_downloaded = True

        # Prepare the request.
        if not headers:
            headers = {}
        headers['user-agent'] = headers.get('user-agent', self.user_agent)
        if send_cookies and self._cookies:
            # Some broken ASP.NET servers put "\r\n" in there, so we replace
            # that with semicolon to get proper behavior.
            headers['Cookie'] = self._cookies.output(attrs=[], header='').strip().replace('\r\n', ';')
        method = data and "POST" or "GET"
        body = data and urlencode(data) or None
        if method == "POST" and body:
            headers.setdefault('Content-Type', 'application/x-www-form-urlencoded')

        # Get the response.
        resp_headers = None
        for attempt_number in range(3):
            self.logger.debug('Attempt %s: %s %s', attempt_number + 1, method, uri)
            if data:
                self.logger.debug('%r', data)
            try:
                resp_headers, content = self.h.request(uri, method, body=body, headers=headers)
                if resp_headers['status'] == '500':
                    self.logger.debug("Request got a 500 error: %s %s", method, uri)
                    continue # Try again.
                break
            except socket.timeout:
                self.logger.debug("Request timed out after %s seconds: %s %s", self.h.timeout, method, uri)
                continue # Try again.
            except socket.error, e:
                self.logger.debug("Got socket error: %s", e)
                continue # Try again.
            except httplib2.ServerNotFoundError:
                raise RetrievalError("Could not %s %r: server not found" % (method, uri))
        if resp_headers is None:
            raise RetrievalError("Request timed out 3 times: %s %s" % (method, uri))

        # Raise RetrievalError if necessary.
        if raise_on_error and resp_headers['status'] in ('400', '408', '500'):
            raise RetrievalError("Could not %s %r: HTTP status %s" % (method, uri, resp_headers['status']))
        if raise_on_error and resp_headers['status'] == '404':
            raise PageNotFoundError("Could not %s %r: HTTP status %s" % (method, uri, resp_headers['status']))

        # Set any received cookies.
        if 'set-cookie' in resp_headers:
            try:
                self._cookies.load(resp_headers['set-cookie'])
            except CookieError:
                # Skip invalid cookies.
                pass

        # Handle redirects that weren't caught by httplib2 for whatever reason.
        if follow_redirects and resp_headers['status'] in ('301', '302', '303'):
            try:
                new_location = resp_headers['location']
            except KeyError:
                raise RetrievalError('Got redirect, but the response was missing a "location" header. Headers were: %r' % resp_headers)
            self.logger.debug('Got %s redirect', resp_headers['status'])

            # Some broken Web apps send relative URLs in their "Location"
            # headers in redirects. Detect that and use urljoin() to get a full
            # URL.
            if not new_location.startswith('http://') and not new_location.startswith('https://'):
                new_location = urljoin(uri, new_location)
            # Clear the POST data, if any, so that we do a GET request.
            if data:
                data = {}
                del headers['Content-Type']
            return Retriever.get_html_and_headers(self, new_location, data, headers, send_cookies)

        return content, resp_headers

    def get_html(self, uri, data=None, headers=None, send_cookies=True, follow_redirects=True, raise_on_error=True):
        "Retrieves the resource and returns it as raw HTML."
        return self.get_html_and_headers(uri, data, headers, send_cookies, follow_redirects, raise_on_error)[0]

    def get_to_file(self, *args, **kwargs):
        """
        Downloads the given URI and saves it to a temporary file. Returns the
        full filename of the temporary file.
        """
        import os
        from tempfile import mkstemp
        fd, name = mkstemp()
        fp = os.fdopen(fd, 'wb')
        fp.write(self.get_html(*args, **kwargs))
        fp.close()
        return name

class UnicodeRetriever(Retriever):
    """
    Like Retriever, but get_html() returns a Unicode object instead of a
    bytestring. It uses the chardet module to determine the encoding to use.
    """
    def __init__(self, *args, **kwargs):
        # errors can be 'strict', 'ignore' or 'replace'. See Python docs.
        self.error_handling = kwargs.pop('errors', 'strict')
        Retriever.__init__(self, *args, **kwargs)

    def get_html_and_headers(self, *args, **kwargs):
        encoding, content, headers = self.get_encoding_html_and_headers(*args, **kwargs)
        return content.decode(encoding, self.error_handling), headers

    def get_encoding_html_and_headers(self, *args, **kwargs):
        """
        Returns a tuple of (encoding, html_bytestring, headers).

        This is useful if you don't know whether you want to decode the string
        until *after* calling this method. (Perhaps you want to inspect the
        headers.)
        """
        import chardet
        content, headers = Retriever.get_html_and_headers(self, *args, **kwargs)
        guess = chardet.detect(content)
        # Maybe this should take into account guess['confidence']?
        return guess['encoding'], content, headers
