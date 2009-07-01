"""
Custom template tags for dealing with json.
"""

from django import template
from django.conf import settings
from django.utils import simplejson

register = template.Library()


def json_value(value, arg):
    data = simplejson.loads(value)
    try:
        return data[arg]
    except KeyError:
        if settings.DEBUG:
            raise
        return None

register.filter('json_value', json_value)
