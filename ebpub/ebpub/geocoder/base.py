from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from ebpub.geocoder.parser.parsing import normalize, parse, ParsingError
from ebpub.geocoder.models import GeocoderCache
from ebpub.streets.models import Block, StreetMisspelling, Intersection
import re

block_re = re.compile(r'^(\d+)[-\s]+(?:blk|block)\s+(?:of\s+)?(.*)$', re.IGNORECASE)
intersection_re = re.compile(r'(?<=.) (?:and|\&|at|near|@|around|towards?|off|/|(?:just )?(?:north|south|east|west) of|(?:just )?past) (?=.)', re.IGNORECASE)
# segment_re = re.compile(r'^.{1,40}?\b(?:between .{1,40}? and|from .{1,40}? to) .{1,40}?$', re.IGNORECASE) # TODO

class GeocodingException(Exception):
    pass

class AmbiguousResult(GeocodingException):
    def __init__(self, choices, message=None):
        self.choices = choices
        if message is None:
            message = "Address DB returned %s results" % len(choices)
        self.message = message

    def __str__(self):
        return self.message

class DoesNotExist(GeocodingException):
    pass

class UnparseableLocation(GeocodingException):
    pass

class InvalidBlockButValidStreet(GeocodingException):
    def __init__(self, block_number, street_name, block_list):
        self.block_number = block_number
        self.street_name = street_name
        self.block_list = block_list
    
class Address(dict):
    "A simple container class for representing a single street address."
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self._cache_hit = False

    @property
    def latitude(self):
        if self["point"]:
            return self["point"].lat
    lat = latitude

    @property
    def longitude(self):
        if self["point"]:
            return self["point"].lng
    lng = longitude

    def __unicode__(self):
        return u", ".join([self[k] for k in ["address", "city", "state", "zip"]])

    @classmethod
    def from_cache(cls, cached):
        """
        Builds an Address object from a GeocoderCache result object.
        """
        fields = {
            'address': cached.address,
            'city': cached.city,
            'state': cached.state,
            'zip': cached.zip,
            'point': cached.location,
            'intersection_id': cached.intersection_id,
        }
        try:
            block_obj = cached.block
        except ObjectDoesNotExist:
            fields.update({'block': None})
        else:
            fields.update({'block': block_obj})
        try:
            intersection_obj = cached.intersection
        except ObjectDoesNotExist:
            fields.update({'intersection': None})
        else:
            fields.update({'intersection': intersection_obj})
        obj = cls(fields)
        obj._cache_hit = True
        return obj

class Geocoder(object):
    """
    Generic Geocoder class.

    Subclasses must override the following attribute:

        _do_geocode(self, location_string)
            Actually performs the geocoding. The base class implementation of
            geocode() calls this behind the scenes.
    """
    def __init__(self, use_cache=True):
        self.use_cache = use_cache

    def geocode(self, location):
        """
        Geocodes the given location, handling caching behind the scenes.
        """
        location = normalize(location)
        result, cache_hit = None, False

        # Get the result (an Address instance), either from the cache or by
        # calling _do_geocode().
        if self.use_cache:
            try:
                cached = GeocoderCache.objects.filter(normalized_location=location)[0]
            except IndexError:
                pass
            else:
                result = Address.from_cache(cached)
                cache_hit = True

        if result is None:
            try:
                result = self._do_geocode(location)
            except AmbiguousResult, e:
                # If multiple results were found, check whether they have the
                # same point. If they all have the same point, don't raise the
                # AmbiguousResult exception -- just return the first one.
                # 
                # An edge case is if result['point'] is None. This could happen
                # if the geocoder found locations, not points. In that case,
                # just raise the AmbiguousResult.
                result = e.choices[0]
                if result['point'] is None:
                    raise
                for i in e.choices[1:]:
                    if i['point'] != result['point']:
                        raise

        # Save the result to the cache if it wasn't in there already.
        if not cache_hit and self.use_cache:
            GeocoderCache.populate(location, result)

        return result

class AddressGeocoder(Geocoder):
    def _do_geocode(self, location_string):
        # Parse the address.
        try:
            locations = parse(location_string)
        except ParsingError, e:
            raise

        all_results = []
        for loc in locations:
            loc_results = self._db_lookup(loc)
            # If none were found, maybe the street was misspelled. Check that.
            if not loc_results and loc['street']:
                try:
                    misspelling = StreetMisspelling.objects.get(incorrect=loc['street'])
                    loc['street'] = misspelling.correct
                except StreetMisspelling.DoesNotExist:
                    pass
                else:
                    loc_results = self._db_lookup(loc)
                # Next, try removing the street suffix, in case an incorrect
                # one was given.
                if not loc_results and loc['suffix']:
                    loc_results = self._db_lookup(dict(loc, suffix=None))
                # Next, try looking for the street, in case the street
                # exists but the address doesn't.
                if not loc_results and loc['number']:
                    kwargs = {'street': loc['street']}
                    sided_filters = []
                    if loc['city']:
                        city_filter = Q(left_city=loc['city']) | Q(right_city=loc['city'])
                        sided_filters.append(city_filter)
                    b_list = Block.objects.filter(*sided_filters, **kwargs).order_by('predir', 'from_num', 'to_num')
                    if b_list:
                        raise InvalidBlockButValidStreet(loc['number'], b_list[0].street_pretty_name, b_list)
            all_results.extend(loc_results)

        if not all_results:
            raise DoesNotExist("Geocoder db couldn't find this location: %r" % location_string)
        elif len(all_results) == 1:
            return all_results[0]
        else:
            raise AmbiguousResult(all_results)

    def _db_lookup(self, location):
        """
        Given a location dict as returned by parse(), looks up the address in
        the DB. Always returns a list of Address dictionaries (or an empty list
        if no results are found).
        """
        if not location['number']:
            return []

        # Query the blocks database.
        try:
            blocks = Block.objects.search(
                street=location['street'],
                number=location['number'],
                predir=location['pre_dir'],
                suffix=location['suffix'],
                postdir=location['post_dir'],
                city=location['city'],
                state=location['state'],
                zipcode=location['zip'],
            )
        except Exception, e:
            # TODO: replace with Block-specific exception
            raise Exception("Road segment db query failed: %r" % e)
        return [self._build_result(location, block, geocoded_pt) for block, geocoded_pt in blocks]

    def _build_result(self, location, block, geocoded_pt):
        return Address({
            'address': unicode(" ".join([str(s) for s in [location['number'], block.predir, block.street_pretty_name, block.postdir] if s])),
            'city': block.city.title(),
            'state': block.state,
            'zip': block.zip,
            'block': block,
            'intersection_id': None,
            'point': geocoded_pt,
            'url': block.url(),
            'wkt': str(block.location),
        })

class BlockGeocoder(AddressGeocoder):
    def _do_geocode(self, location_string):
        m = block_re.search(location_string)
        if not m:
            raise ParsingError("BlockGeocoder somehow got an address it can't parse: %r" % location_string)
        new_location_string = ' '.join(m.groups())
        return AddressGeocoder._do_geocode(self, new_location_string)

class IntersectionGeocoder(Geocoder):
    def _do_geocode(self, location_string):
        sides = intersection_re.split(location_string)
        if len(sides) != 2:
            raise ParsingError("Couldn't parse intersection: %r" % location_string)

        # Parse each side of the intersection to a list of possibilities.
        # Let the ParseError exception propagate, if it's raised.
        left_side = parse(sides[0])
        right_side = parse(sides[1])

        all_results = []
        seen_intersections = set()
        for street_a in left_side:
            street_a['street'] = StreetMisspelling.objects.make_correction(street_a['street'])
            for street_b in right_side:
                street_b['street'] = StreetMisspelling.objects.make_correction(street_b['street'])
                for result in self._db_lookup(street_a, street_b):
                    if result["intersection_id"] not in seen_intersections:
                        seen_intersections.add(result["intersection_id"])
                        all_results.append(result)

        if not all_results:
            raise DoesNotExist("Geocoder db couldn't find this intersection: %r" % location_string)
        elif len(all_results) == 1:
            return all_results.pop()
        else:
            raise AmbiguousResult(list(all_results), "Intersections DB returned %s results" % len(all_results))

    def _db_lookup(self, street_a, street_b):
        try:
            intersections = Intersection.objects.search(
                predir_a=street_a["pre_dir"],
                street_a=street_a["street"],
                suffix_a=street_a["suffix"],
                postdir_a=street_a["post_dir"],
                predir_b=street_b["pre_dir"],
                street_b=street_b["street"],
                suffix_b=street_b["suffix"],
                postdir_b=street_b["post_dir"]
            )
        except Exception, e:
            raise DoesNotExist("Intersection db query failed: %r" % e)
        return [self._build_result(i) for i in intersections]

    def _build_result(self, intersection):
        return Address({
            'address': intersection.pretty_name,
            'city': intersection.city,
            'state': intersection.state,
            'zip': intersection.zip,
            'intersection_id': intersection.id,
            'intersection': intersection,
            'block': None,
            'point': intersection.location,
            'url': intersection.url(),
            'wkt': str(intersection.location),
        })

# THIS IS NOT YET FINISHED
#
# class SegmentGeocoder(Geocoder):
#     def _do_geocode(self, location_string):
#         bits = segment_re.findall(location_string)
#         g = IntersectionGeocoder()
#         try:
#             point1 = g.geocode('%s and %s' % (bits[0], bits[1]))
#             point2 = g.geocode('%s and %s' % (bits[0], bits[2]))
#         except DoesNotExist, e:
#             raise DoesNotExist("Segment query failed: %r" % e)
#         # TODO: Make a line from the two points, and return that.

class SmartGeocoder(Geocoder):
    def _do_geocode(self, location_string):
        if intersection_re.search(location_string):
            geocoder = IntersectionGeocoder()
        elif block_re.search(location_string):
            geocoder = BlockGeocoder()
        else:
            geocoder = AddressGeocoder()
        return geocoder._do_geocode(location_string)
