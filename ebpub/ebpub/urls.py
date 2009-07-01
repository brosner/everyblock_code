from django.conf import settings
from django.conf.urls.defaults import *
from ebpub.alerts import views as alert_views
from ebpub.db import feeds, views
from ebpub.db.constants import BLOCK_URL_REGEX
from ebpub.petitions import views as petition_views
from ebpub.utils.urlresolvers import metro_patterns

if settings.DEBUG:
    urlpatterns = patterns('',
        (r'^(?P<path>(?:images|scripts|styles|openlayers).*)$', 'django.views.static.serve', {'document_root': settings.EB_MEDIA_ROOT}),
    )
else:
    urlpatterns = patterns('')

urlpatterns += patterns('',
    (r'^$', views.homepage),
    (r'^search/$', views.search),
    (r'^news/$', views.schema_list),
    (r'^locations/$', 'django.views.generic.simple.redirect_to', {'url': '/locations/neighborhoods/'}),
    (r'^locations/([-_a-z0-9]{1,32})/$', views.location_type_detail),
    (r'^locations/([-_a-z0-9]{1,32})/([-_a-z0-9]{1,32})/$', views.place_detail, {'place_type': 'location', 'detail_page': True}),
    (r'^locations/([-_a-z0-9]{1,32})/([-_a-z0-9]{1,32})/overview/$', views.place_detail, {'place_type': 'location'}),
    (r'^locations/([-_a-z0-9]{1,32})/([-_a-z0-9]{1,32})/feeds/$', views.feed_signup, {'place_type': 'location'}),
    (r'^locations/([-_a-z0-9]{1,32})/([-_a-z0-9]{1,32})/alerts/$', alert_views.signup, {'place_type': 'location'}),
    (r'^rss/(.+)/$', feeds.feed_view),
    (r'^maps/', include('ebgeo.maps.urls')),
    (r'^accounts/', include('ebpub.accounts.urls')),
    (r'^validate-address/$', views.validate_address),
    (r'^alerts/unsubscribe/\d\d(\d{1,10})\d/$', alert_views.unsubscribe),
    (r'^petitions/([-\w]{4,32})/$', petition_views.form_view, {'is_schema': False}),
    (r'^petitions/([-\w]{4,32})/thanks/$', petition_views.form_thanks, {'is_schema': False}),
    (r'^api/wkt/$', views.ajax_wkt),
    (r'^api/map-popups/$', views.ajax_map_popups),
    (r'^api/place-recent-items/$', views.ajax_place_newsitems),
    (r'^api/place-lookup-chart/$', views.ajax_place_lookup_chart),
    (r'^api/place-date-chart/$', views.ajax_place_date_chart),
    (r'^api/map-browser/location-types/$', views.ajax_location_type_list),
    (r'^api/map-browser/location-types/(\d{1,9})/$', views.ajax_location_list),
    (r'^api/map-browser/locations/(\d{1,9})/$', views.ajax_location),
)

urlpatterns += metro_patterns(
    multi=(
        (r'^streets/$', views.city_list),
        (r'^streets/([-a-z]{3,40})/$', views.street_list),
        (r'^streets/([-a-z]{3,40})/([-a-z0-9]{1,64})/$', views.block_list),
        (r'^streets/([-a-z]{3,40})/([-a-z0-9]{1,64})/%s/$' % BLOCK_URL_REGEX, views.place_detail, {'place_type': 'block', 'detail_page': True}),
        (r'^streets/([-a-z]{3,40})/([-a-z0-9]{1,64})/%s/overview/$' % BLOCK_URL_REGEX, views.place_detail, {'place_type': 'block'}),
        (r'^streets/([-a-z]{3,40})/([-a-z0-9]{1,64})/%s/feeds/$' % BLOCK_URL_REGEX, views.feed_signup, {'place_type': 'block'}),
        (r'^streets/([-a-z]{3,40})/([-a-z0-9]{1,64})/%s/alerts/$' % BLOCK_URL_REGEX, alert_views.signup, {'place_type': 'block'}),
    ),
    single=(
        (r'^streets/()$', views.street_list),
        (r'^streets/()([-a-z0-9]{1,64})/$', views.block_list),
        (r'^streets/()([-a-z0-9]{1,64})/%s/$' % BLOCK_URL_REGEX, views.place_detail, {'place_type': 'block', 'detail_page': True}),
        (r'^streets/()([-a-z0-9]{1,64})/%s/overview/$' % BLOCK_URL_REGEX, views.place_detail, {'place_type': 'block'}),
        (r'^streets/()([-a-z0-9]{1,64})/%s/feeds/$' % BLOCK_URL_REGEX, views.feed_signup, {'place_type': 'block'}),
        (r'^streets/()([-a-z0-9]{1,64})/%s/alerts/$' % BLOCK_URL_REGEX, alert_views.signup, {'place_type': 'block'}),
    )
)

urlpatterns += patterns('',
    (r'^([-\w]{4,32})/$', views.schema_detail),
    (r'^([-\w]{4,32})/about/$', views.schema_about),
    (r'^([-\w]{4,32})/search/$', views.search),
    (r'^([-\w]{4,32})/petition/$', petition_views.form_view, {'is_schema': True}),
    (r'^([-\w]{4,32})/petition/thanks/$', petition_views.form_thanks, {'is_schema': True}),
    (r'^([-\w]{4,32})/by-date/(\d{4})/(\d\d?)/(\d\d?)/(\d{1,8})/$', views.newsitem_detail),
    (r'^([-\w]{4,32})/(?:filter/)?([^/].+/)?$', views.schema_filter),
)
