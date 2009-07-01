from django.conf.urls.defaults import *
from ebgeo.maps import views
from ebgeo.maps.tilecache_service import request_pat as tile_request_pat

urlpatterns = patterns('',
    (r'^tile%s' % tile_request_pat, views.get_tile),
    (r'^locator/(?P<version>\d+\.\d+)/(?P<city>\w{1,32})\.(?P<extension>(?:png|jpg|gif))$', views.locator_map),
    (r'^browser/export_pdf/$', views.export_pdf),
    (r'^marker_(?P<radius>\d{1,2})\.png$', views.get_marker),
)
