from django.conf.urls.defaults import *
from django.contrib.syndication.views import feed as feed_view
from django.views.generic import date_based, list_detail
from django.contrib import admin
from ebblog.blog.models import Entry
from ebblog.blog import feeds

admin.autodiscover()

info_dict = {
    'queryset': Entry.objects.order_by('pub_date'),
    'date_field': 'pub_date',
}

FEEDS = {
    'rss': feeds.BlogEntryFeed,
}

urlpatterns = patterns('',
    (r'^(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\w{1,2})/(?P<slug>\w+)/$', date_based.object_detail, dict(info_dict, slug_field='slug')),
    (r'^(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\w{1,2})/$', date_based.archive_day, info_dict),
    (r'^(?P<year>\d{4})/(?P<month>[a-z]{3})/$', date_based.archive_month, info_dict),
    (r'^(?P<year>\d{4})/$', date_based.archive_year, info_dict),
    (r'^(rss)/$', feed_view, {'feed_dict': FEEDS}),
    (r'^archives/', list_detail.object_list, {'queryset': Entry.objects.order_by('-pub_date'), 'template_name': 'blog/archive.html'}),
    (r'^$', date_based.archive_index, dict(info_dict, template_name='homepage.html')),
    ('^admin/', include(admin.site.urls)),
)
