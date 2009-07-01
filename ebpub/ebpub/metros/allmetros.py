from django.conf import settings

METRO_LIST = settings.METRO_LIST
METRO_DICT = dict([(m['short_name'], m) for m in METRO_LIST])

def get_metro(short_name=None):
    if short_name is None:
        short_name = settings.SHORT_NAME
    return METRO_DICT[short_name]
