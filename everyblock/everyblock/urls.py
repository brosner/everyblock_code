from django.conf import settings
from django.conf.urls.defaults import *

if settings.DEBUG:
    urlpatterns = patterns('',
        (r'^(?P<path>(?:images|scripts|styles|openlayers).*)$', 'django.views.static.serve', {'document_root': settings.EB_MEDIA_ROOT}),
    )
else:
    urlpatterns = patterns('')

urlpatterns += patterns('',
    (r'^admin/', include('everyblock.admin.urls')),
)
