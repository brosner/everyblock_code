import os.path

########################
# CORE DJANGO SETTINGS #
########################

DATABASE_ENGINE = 'postgresql_psycopg2' # ebpub only supports postgresql_psycopg2.
DATABASE_USER = ''
DATABASE_NAME = ''
DATABASE_HOST = ''
DATABASE_PORT = ''
DEBUG = True

TEMPLATE_DIRS = (
    os.path.normpath(os.path.join(os.path.dirname(__file__), 'templates')),
)
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
)
TEMPLATE_CONTEXT_PROCESSORS = (
    'ebpub.accounts.context_processors.user',
)

INSTALLED_APPS = (
    'ebpub.accounts',
    'ebpub.alerts',
    'ebpub.db',
    'ebpub.geocoder',
    'ebpub.petitions',
    'ebpub.preferences',
    'ebpub.savedplaces',
    'ebpub.streets',
    'django.contrib.humanize',
    'django.contrib.sessions',
)

ROOT_URLCONF = 'ebpub.urls'
MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'ebpub.accounts.middleware.UserMiddleware',
)

#########################
# CUSTOM EBPUB SETTINGS #
#########################

# The domain for your site.
EB_DOMAIN = 'example.com'

# This is the short name for your city, e.g. "chicago".
SHORT_NAME = ''

# Set both of these to distinct, secret strings that include two instances
# of '%s' each. Example: 'j8#%s%s' -- but don't use that, because it's not
# secret.
PASSWORD_CREATE_SALT = ''
PASSWORD_RESET_SALT = ''

# Here, we define the different databases we use, giving each one a label
# (like 'users') so we can refer to a particular database via multidb
# managers.
#
# Note that we only need to define databases that are used by multidb
# managers -- not our default database for this settings file. Any Django
# model code that doesn't use the multidb manager will use the standard
# DATABASE_NAME/DATABASE_USER/etc. settings.
#
# THE UPSHOT: If you're only using one database, the only thing you'll need
# to set here is TIME_ZONE.
DATABASES = {
    'users': {
        'DATABASE_HOST': DATABASE_HOST,
        'DATABASE_NAME': DATABASE_NAME,
        'DATABASE_OPTIONS': {},
        'DATABASE_PASSWORD': '',
        'DATABASE_PORT': DATABASE_PORT,
        'DATABASE_USER': DATABASE_USER,
        'TIME_ZONE': '', # Same format as Django's TIME_ZONE setting.
    },
    'metros': {
        'DATABASE_HOST': DATABASE_HOST,
        'DATABASE_NAME': DATABASE_NAME,
        'DATABASE_OPTIONS': {},
        'DATABASE_PASSWORD': '',
        'DATABASE_PORT': DATABASE_PORT,
        'DATABASE_USER': DATABASE_USER, 
        'TIME_ZONE': '', # Same format as Django's TIME_ZONE setting.
    },
}

# The list of all metros this installation covers. This is a tuple of
# dictionaries.
METRO_LIST = (
    # Example dictionary:
    # {
    #     # Extent of the metro, as a longitude/latitude bounding box.
    #     'extent': (-71.191153, 42.227865, -70.986487, 42.396978),
    #
    #     # Whether this should be displayed to the public.
    #     'is_public': True,
    #
    #     # Set this to True if the metro has multiple cities.
    #     'multiple_cities': False,
    #
    #     # The major city in the metro.
    #     'city_name': 'Boston',
    #
    #     # The SHORT_NAME in the settings file (also the subdomain).
    #     'short_name': 'boston',
    #
    #     # The name of the metro, as opposed to the city (e.g., "Miami-Dade" instead of "Miami").
    #     'metro_name': 'Boston',
    #
    #     # USPS abbreviation for the state.
    #     'state': 'MA',
    #
    #     # Full name of state.
    #     'state_name': 'Massachusetts',
    #
    #     # Time zone, as required by Django's TIME_ZONE setting.
    #     'time_zone': 'America/New_York',
    # },
)

EB_MEDIA_ROOT = '' # necessary for static media versioning
EB_MEDIA_URL = '' # leave at '' for development

# Overrides datetime.datetime.today(), for development.
EB_TODAY_OVERRIDE = None

# Filesystem location of shapefiles for maps, e.g., '/home/shapefiles'.
SHAPEFILE_ROOT = ''

# For the 'autoversion' template tag.
AUTOVERSION_STATIC_MEDIA = False

# Connection info for mapserver.
MAPS_POSTGIS_HOST = '127.0.0.1'
MAPS_POSTGIS_USER = ''
MAPS_POSTGIS_PASS = ''
MAPS_POSTGIS_DB = ''

# This is used as a "From:" in e-mails sent to users.
GENERIC_EMAIL_SENDER = 'example@example.com'

# Map stuff.
MAP_SCALES = [614400, 307200, 153600, 76800, 38400, 19200, 9600, 4800, 2400, 1200]
SPATIAL_REF_SYS = '900913' # Spherical Mercator
MAP_UNITS = 'm' # see ebgeo.maps.utils for allowed unit types

# Filesystem location of tilecache config (e.g., '/etc/tilecache/tilecache.cfg').
TILECACHE_CONFIG = ''

# Filesystem location of scraper log.
SCRAPER_LOGFILE_NAME = '/tmp/scraperlog'

DATA_HARVESTER_CONFIG = {}

MAIL_STORAGE_PATH = '/home/mail'

# If this cookie is set with the given value, then the site will give the user
# staff privileges (including the ability to view non-public schemas).
STAFF_COOKIE_NAME = ''
STAFF_COOKIE_VALUE = ''
