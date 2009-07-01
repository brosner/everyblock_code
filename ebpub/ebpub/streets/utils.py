from ebpub.db.models import Location
from ebpub.geocoder import SmartGeocoder, AmbiguousResult, InvalidBlockButValidStreet
from ebpub.geocoder.parser.parsing import normalize
from ebpub.streets.models import Misspelling, Place

def full_geocode(query, search_places=True):
    """
    Tries the full geocoding stack on the given query (a string):
        * Normalizes whitespace/capitalization
        * Searches the Misspelling table to corrects location misspellings
        * Searches the Location table
        * Failing that, searches the Place table (if search_places is True)
        * Failing that, uses the given geocoder to parse this as an address
        * Failing that, raises whichever error is raised by the geocoder --
          except AmbiguousResult, in which case all possible results are
          returned

    Returns a dictionary of {type, result, ambiguous}, where ambiguous is True
    or False and type can be:
        * 'location' -- in which case result is a Location object.
        * 'place' -- in which case result is a Place object. (This is only
          possible if search_places is True.)
        * 'address' -- in which case result is an Address object as returned
          by geocoder.geocode().
        * 'block' -- in which case result is a list of Block objects.

    If ambiguous is True, result will be a list of objects.
    """
    query = normalize(query)

    # First, try correcting the spelling ("LAKEVIEW" -> "LAKE VIEW").
    try:
        miss = Misspelling.objects.get(incorrect=query)
    except Misspelling.DoesNotExist:
        pass
    else:
        query = miss.correct

    # Search the Location table.
    try:
        loc = Location.objects.get(normalized_name=query)
    except Location.DoesNotExist:
        pass
    else:
        return {'type': 'location', 'result': loc, 'ambiguous': False}

    # Search the Place table, for stuff like "Sears Tower".
    if search_places:
        places = Place.objects.filter(normalized_name=query)
        if len(places) == 1:
            return {'type': 'place', 'result': places[0], 'ambiguous': False}
        elif len(places) > 1:
            return {'type': 'place', 'result': places, 'ambiguous': True}

    # Try geocoding this as an address.
    geocoder = SmartGeocoder()
    try:
        result = geocoder.geocode(query)
    except AmbiguousResult, e:
        return {'type': 'address', 'result': e.choices, 'ambiguous': True}
    except InvalidBlockButValidStreet, e:
        return {'type': 'block', 'result': e.block_list, 'ambiguous': True, 'street_name': e.street_name, 'block_number': e.block_number}
    except:
        raise
    return {'type': 'address', 'result': result, 'ambiguous': False}
