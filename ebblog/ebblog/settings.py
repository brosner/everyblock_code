import os

DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = '/tmp/ebblog.db'
DATABASE_USER = ''
DATABASE_HOST = ''
DATABASE_PORT = ''

ROOT_URLCONF = 'ebblog.urls'

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'ebblog.blog',
)

TEMPLATE_DIRS = (
    os.path.normpath(os.path.join(os.path.dirname(__file__), 'templates')),
)
