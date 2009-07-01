from django.conf.urls.defaults import *
from django.conf import settings
from django.views.generic.simple import direct_to_template
from everyblock.utils.redirecter import redirecter
import views # relative import

urlpatterns = patterns('',
    (r'^$', direct_to_template, {'template': 'admin/index.html'}),
    (r'^schemas/$', views.schema_list),
    (r'^schemas/(\d{1,6})/$', views.edit_schema),
    (r'^schemas/(\d{1,6})/lookups/(\d{1,6})/$', views.edit_schema_lookups),
    (r'^schemafields/$', views.schemafield_list),
    (r'^sources/$', views.blob_seed_list),
    (r'^sources/add/$', views.add_blob_seed),
    (r'^scraper-history/$', views.scraper_history_list),
    (r'^scraper-history/([-\w]{4,32})/$', views.scraper_history_schema),
    (r'^set-staff-cookie/$', views.set_staff_cookie),
    (r'^newsitems/(\d{1,6})/$', views.newsitem_details),
    (r'^geocoder-success-rates/$', views.geocoder_success_rates),
)
