import os

DEBUG = True

DATABASE_ENGINE = 'postgresql_psycopg2'
DATABASE_USER = ''
DATABASE_HOST = ''
DATABASE_NAME = 'wiki'

INSTALLED_APPS = (
    'ebwiki.wiki',
)

TEMPLATE_DIRS = (
    os.path.normpath(os.path.join(os.path.dirname(__file__), 'templates')),
)

ROOT_URLCONF = 'ebwiki.wiki.urls'

WIKI_DOC_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), 'media'))
