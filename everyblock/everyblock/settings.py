import os

DEBUG = True

SHORT_NAME = 'chicago'

DATABASE_ENGINE = 'postgresql_psycopg2'
DATABASE_USER = ''
DATABASE_HOST = ''
DATABASE_NAME = SHORT_NAME

INSTALLED_APPS = (
    'django.contrib.humanize',
    'ebpub.db',
    'everyblock.staticmedia',
)

TEMPLATE_DIRS = (
    os.path.normpath(os.path.join(os.path.dirname(__file__), 'templates')),
)

ROOT_URLCONF = 'everyblock.urls'

# See ebpub.settings for how to configure METRO_LIST
METRO_LIST = (
)

EB_MEDIA_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), 'media'))
EB_MEDIA_URL = ''

AUTOVERSION_STATIC_MEDIA = False
