"""
Utilities useful for scraping.
"""

import re
import htmlentitydefs
from ebgeo.utils.geodjango import smart_transform
from django.contrib.gis.geos import GEOSGeometry

multispace_re = re.compile(r'\s\s+')

def norm_dict_space(d, *keys):
    """
    >>> d = {'name': '  john  smith ',
    ...      ' address': ' 123  main st'}
    >>> norm_dict_space(d, 'name', 'address')
    >>> d
    {'name': 'john smith', 'address': '123 main st'}
    """
    for key in keys:
        d[key] = multispace_re.sub(' ', d[key]).strip()

def obj_dict_merge(obj, update_dict, ignore_attrs=None):
    """Updates the attributes of obj with the values in update_dict.

    Takes a list of attributes to ignore.

    Returns True if any of obj's attributes were updated, False otherwise.
    """
    if not ignore_attrs:
        ignore_attrs = []
    changed = False
    for attr in obj.__dict__.keys():
        if attr not in ignore_attrs and update_dict.has_key(attr):
            update_val = update_dict[attr]
            if getattr(obj, attr) != update_val:
                setattr(obj, attr, update_val)
                changed = True
    return changed, obj

# From http://effbot.org/zone/re-sub.htm#unescape-html
def convert_entities(text):
    """
    Converts HTML entities in the given string (e.g., '&#28;' or '&nbsp;') to
    their corresponding characters.
    """
    NAMED_ENTITY_SPECIAL_CASES = {
        'apos': u"'",
    }
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            entity = text[1:-1]
            try:
                text = unichr(htmlentitydefs.name2codepoint[entity])
            except KeyError:
                try:
                    return NAMED_ENTITY_SPECIAL_CASES[entity]
                except KeyError:
                    pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)

def locations_are_close(geom_a, geom_b, max_distance=200):
    """
    Verifies that two locations are within a certain distance from
    each other. Returns a tuple of (is_close, distance), where
    is_close is True only if the locations are within max_distance.

    Assumes max_distance is in meters.
    """
    # Both geometries must be GEOSGeometry for the distance method.
    if not (isinstance(geom_a, GEOSGeometry) and isinstance(geom_b, GEOSGeometry)):
        raise ValueError, 'both geometries must be GEOSGeometry instances'
    carto_srid = 3395 # SRS in meters
    geom_a = smart_transform(geom_a, carto_srid)
    geom_b = smart_transform(geom_b, carto_srid)
    distance = geom_a.distance(geom_b)
    return (distance < max_distance), distance
