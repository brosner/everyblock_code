from django.http import Http404, HttpResponse
import urllib

def redirecter(request):
    "Redirects to a given URL without sending the 'Referer' header."
    try:
        url = request.GET['url']
    except KeyError:
        raise Http404
    if not url.startswith('http://') and not url.startswith('https://'):
        raise Http404
    return HttpResponse('<html><head><meta http-equiv="Refresh" content="0; URL=%s"></head><body>Loading...</body></html>' % urllib.unquote_plus(url))
