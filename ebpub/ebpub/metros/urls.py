from django.conf.urls.defaults import *
from django.views.generic import list_detail
from ebpub.metros import views
from ebpub.metros.models import Metro

urlpatterns = patterns('',
    (r'^$', list_detail.object_list, {'queryset': Metro.objects.order_by('name'), 'template_object_name': 'metro'}),
    (r'^lookup/$', views.lookup_metro),
)
