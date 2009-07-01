from django.conf.urls.defaults import *
from ebpub.savedplaces import views as savedplaces_views
from ebpub.preferences import views as preferences_views
import views # relative import

urlpatterns = patterns('',
    (r'^dashboard/$', views.dashboard),
    (r'^login/$', views.login),
    (r'^logout/$', views.logout),
    (r'^register/$', views.register),
    (r'^password-change/$', views.request_password_change),
    (r'^email-sent/$', 'django.views.generic.simple.direct_to_template', {'template': 'accounts/email_sent.html'}),
    (r'^saved-places/add/$', savedplaces_views.ajax_save_place),
    (r'^saved-places/delete/$', savedplaces_views.ajax_remove_place),
    (r'^hidden-schemas/add/$', preferences_views.ajax_save_hidden_schema),
    (r'^hidden-schemas/delete/$', preferences_views.ajax_remove_hidden_schema),
    (r'^api/saved-places/$', savedplaces_views.json_saved_places),
    (r'^c/$', views.confirm_email),
    (r'^r/$', views.password_reset),
)
