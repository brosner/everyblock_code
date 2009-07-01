from django.contrib.localflavor.us.models import USStateField
from django.contrib.gis.db import models
from django.contrib.gis.geos import fromstr
from django.db.models import Q
from ebpub.metros.allmetros import get_metro
import operator
import re

class ImproperCity(Exception):
    pass

def proper_city(block):
    """
    Returns the "proper" city for block.

    This function is necessary because in the Block model there are
    two sides of the street, and the city on the left side could
    differ from the city on the right. This function uses knowledge
    about metros and cities to return the canonical city
    for our purposes for a block.

    Note that if ImproperCity is raised, it implies that there is a
    mismatch between the block data and our understanding about what
    should be in there. i.e., neither the left nor right side city is
    one of our metros or city within a multiple-city metro.
    """
    from ebpub.db.models import Location
    metro = get_metro()
    if metro['multiple_cities']:
        cities = set([l.name.upper() for l in Location.objects.filter(location_type__slug=metro['city_location_type']).exclude(location_type__name__startswith='Unknown')])
    else:
        cities = set([metro['city_name'].upper()])
    # Determine the block's city, which because of blocks that
    # border two different municipalities, and because of metros
    # with multiple cities like NYC and Miami-Dade, means checking
    # both sides of the block and comparing with known city names.
    block_city = None
    if block.left_city != block.right_city:
        # Note that if both left_city and right_city are valid, then we
        # return the left_city.
        if block.left_city in cities:
            block_city = block.left_city
        elif block.right_city in cities:
            block_city = block.right_city
    elif block.left_city in cities:
        block_city = block.left_city
    if block_city is None:
        raise ImproperCity("Error: Unknown city '%s' from block %s (%s)" % (block.left_city, block.id, block))
    return block_city

class BlockManager(models.GeoManager):
    def search(self, street, number=None, predir=None, suffix=None, postdir=None, city=None, state=None, zipcode=None, strict_number=False):
        """
        Searches the blocks for the given address bits. Returns a list
        of 2-tuples, (block, geocoded_pt).

        geocoded_pt will be None if number is None.

        We make these assumptions about the input:

            * Everything is already in all-uppercase
            * The predir and postdir have been standardized

        strict_number=True means that, if a number is given, it must
        be within a side of the street's from and to number range, and
        that its parity (even / odd) matches that of the number range.

        strict_number=False, the default, means that if a canonical
        block is not found for this number (i.e., one that meets the
        conditions of strict_number=True), then as long as the number
        is within a number range, we don't enforce the parity
        matching. This is friendlier to the user. For example, 3181
        would match the block 3180-3188.
        """
        filters = {'street': street.upper()}
        sided_filters = []
        if predir:
            filters['predir'] = predir.upper()
        if suffix:
            filters['suffix'] = suffix.upper()
        if postdir:
            filters['postdir'] = postdir.upper()
        if city:
            city_filter = Q(left_city=city.upper()) | Q(right_city=city.upper())
            sided_filters.append(city_filter)
        if state:
            state_filter = Q(left_state=state.upper()) | Q(right_state=state.upper())
            sided_filters.append(state_filter)
        if zipcode:
            zip_filter = Q(left_zip=zipcode) | Q(right_zip=zipcode)
            sided_filters.append(zip_filter)

        qs = self.filter(*sided_filters, **filters)

        # If a number was given, search against the address ranges in the
        # Block table.
        if number:
            number = int(re.sub(r'\D', '', number))
            block_tuples = []
            for block in qs.filter(from_num__lte=number, to_num__gte=number):
                contains, from_num, to_num = block.contains_number(number)
                if contains:
                    block_tuples.append((block, from_num, to_num))
            blocks = []
            if block_tuples:
                from django.db import connection
                cursor = connection.cursor()
                for block, from_num, to_num in block_tuples:
                    try:
                        fraction = (float(number) - from_num) / (to_num - from_num)
                    except ZeroDivisionError:
                        fraction = 0.5
                    # We rely on PostGIS line_interpolate_point() because there
                    # isn't a matching GeoDjango/Python API.
                    cursor.execute('SELECT line_interpolate_point(%s, %s)', [block.geom.wkt, fraction])
                    wkb_hex = cursor.fetchone()[0]
                    blocks.append((block, fromstr(wkb_hex)))
        else:
            blocks = list([(b, None) for b in qs])
        return blocks

class Block(models.Model):
    pretty_name = models.CharField(max_length=255)
    predir = models.CharField(max_length=2, blank=True, db_index=True)
    street = models.CharField(max_length=255, db_index=True) # Always uppercase!
    street_slug = models.SlugField()
    street_pretty_name = models.CharField(max_length=255)
    suffix = models.CharField(max_length=32, blank=True, db_index=True) # Always uppercase
    postdir = models.CharField(max_length=2, blank=True, db_index=True) # Always uppercase
    left_from_num = models.IntegerField(db_index=True, blank=True, null=True)
    left_to_num = models.IntegerField(db_index=True, blank=True, null=True)
    right_from_num = models.IntegerField(db_index=True, blank=True, null=True)
    right_to_num = models.IntegerField(db_index=True, blank=True, null=True)
    from_num = models.IntegerField(db_index=True, blank=True, null=True)
    to_num = models.IntegerField(db_index=True, blank=True, null=True)
    left_zip = models.CharField(max_length=10, db_index=True, blank=True, null=True) # Possible Plus-4
    right_zip = models.CharField(max_length=10, db_index=True, blank=True, null=True) # Possible Plus-4
    left_city = models.CharField(max_length=255, db_index=True) # Always uppercase
    right_city = models.CharField(max_length=255, db_index=True) # Always uppercase
    left_state = USStateField(db_index=True) # Always uppercase
    right_state = USStateField(db_index=True) # Always uppercase
    parent_id = models.IntegerField(db_index=True, blank=True, null=True) # This field is used for blocks that are alternate names for another block, which is pointed to by this ID
    geom = models.LineStringField()
    objects = BlockManager()

    class Meta:
        db_table = 'blocks'

    def __unicode__(self):
        return self.pretty_name

    def number(self):
        """
        Returns a formatted street number
        """
        if self.from_num == self.to_num:
            return unicode(self.from_num)
        if not self.from_num:
            return unicode(self.to_num)
        if not self.to_num:
            return unicode(self.from_num)
        return u'%s-%s' % (self.from_num, self.to_num)

    def dir_url_bit(self):
        """
        Returns the directional bit of the URL.

        For example, if the pre-directional is "N" and the post-directional is
        blank, returns "n".

        If the pre-directional is "E" and the post-directional is "SW",
        returns "e-sw".

        If the pre-directional is blank and the post-directional is "e",
        return "-e".

        If both are blank, returns the empty string.
        """
        url = []
        if self.predir:
            url.append(self.predir.lower())
        if self.postdir:
            url.extend(['-', self.postdir.lower()])
        return ''.join(url)

    def url(self):
        return '%s%s%s/' % (self.street_url(), self.number(), self.dir_url_bit())

    def street_url(self):
        if get_metro()['multiple_cities']:
            return '/streets/%s/%s/' % (self.city_object().slug, self.street_slug)
        else:
            return '/streets/%s/' % self.street_slug

    def rss_url(self):
        return '/rss%s' % self.url()

    def alert_url(self):
        return '%salerts/' % self.url()

    def city_object(self):
        return City.from_norm_name(self.city)

    def contains_number(self, number):
        """
        Returns a tuple of (boolean, from_num, to_num), where boolean is
        True if this Block contains the given address number. The from_num
        and to_num values are the ones that were used to calculate it.

        Checks both the block range and the parity (even vs. odd numbers).
        """
        parity = number % 2
        if self.left_from_num and self.right_from_num:
            left_parity = self.left_from_num % 2
            # If this block's left side has the same parity as the right side,
            # all bets are off -- just use the from_num and to_num.
            if self.right_to_num % 2 == left_parity or self.left_to_num % 2 == self.right_from_num % 2:
                from_num, to_num = self.from_num, self.to_num
            elif left_parity == parity:
                from_num, to_num = self.left_from_num, self.left_to_num
            else:
                from_num, to_num = self.right_from_num, self.right_to_num
        elif self.left_from_num:
            from_parity, to_parity = self.left_from_num % 2, self.left_to_num % 2
            from_num, to_num = self.left_from_num, self.left_to_num
            # If the parity is equal for from_num and to_num, make sure the
            # parity of the number is the same.
            if (from_parity == to_parity) and from_parity != parity:
                return False, from_num, to_num
        else:
            from_parity, to_parity = self.right_from_num % 2, self.right_to_num % 2
            from_num, to_num = self.right_from_num, self.right_to_num
            # If the parity is equal for from_num and to_num, make sure the
            # parity of the number is the same.
            if (from_parity == to_parity) and from_parity != parity:
                return False, from_num, to_num
        return (from_num <= number <= to_num), from_num, to_num

    def _get_location(self):
        return self.geom
    location = property(_get_location)

    def _get_city(self):
        if not hasattr(self, '_city_cache'):
            self._city_cache = proper_city(self)
        return self._city_cache
    city = property(_get_city)

    def _get_state(self):
        if self.left_state == self.right_state:
            return self.left_state
        else:
            return get_metro()['state_abbr']
    state = property(_get_state)

    def _get_zip(self):
        return self.left_zip
    zip = property(_get_zip)

class Street(models.Model):
    street = models.CharField(max_length=255, db_index=True) # Always uppercase
    pretty_name = models.CharField(max_length=255)
    street_slug = models.SlugField()
    suffix = models.CharField(max_length=32, blank=True, db_index=True) # Always uppercase
    city = models.CharField(max_length=255, db_index=True) # Always uppercase
    state = USStateField(db_index=True) # Always uppercase

    class Meta:
        db_table = 'streets'

    def __unicode__(self):
        return self.pretty_name

    def url(self):
        if get_metro()['multiple_cities']:
            return '/streets/%s/%s/' % (self.city_object().slug, self.street_slug)
        else:
            return '/streets/%s/' % self.street_slug

    def city_object(self):
        return City.from_norm_name(self.city)

class Misspelling(models.Model):
    incorrect = models.CharField(max_length=255, unique=True) # Always uppercase, single spaces
    correct = models.CharField(max_length=255)

    def __unicode__(self):
        return self.incorrect

class StreetMisspellingManager(models.Manager):
    def make_correction(self, street_name):
        """
        Returns the correct spelling of the given street name. If the given
        street name is already correctly spelled, then it's returned as-is.

        Note that the given street name will be converted to all caps.
        """
        street_name = street_name.upper()
        try:
            return self.get(incorrect=street_name).correct
        except self.model.DoesNotExist:
            return street_name

class StreetMisspelling(models.Model):
    incorrect = models.CharField(max_length=255, unique=True) # Always uppercase, single spaces
    correct = models.CharField(max_length=255)
    objects = StreetMisspellingManager()

    def __unicode__(self):
        return self.incorrect

# A generic place, like "Millennium Park" or "Sears Tower"
class Place(models.Model):
    pretty_name = models.CharField(max_length=255)
    normalized_name = models.CharField(max_length=255) # Always uppercase, single spaces
    address = models.CharField(max_length=255, blank=True)
    location = models.GeometryField()
    objects = models.GeoManager()

    def __unicode__(self):
        if self.address:
            return u'%s (%s)' % (self.pretty_name, self.address)
        return self.pretty_name

    def save(self):
        if not self.normalized_name:
            from ebpub.geocoder.parser.parsing import normalize
            self.normalized_name = normalize(self.pretty_name)
        super(Place, self).save()

class City(object):
    def __init__(self, name, slug, norm_name):
        self.name, self.slug, self.norm_name = name, slug, norm_name

    def from_name(cls, name):
        return cls(name, name.lower().replace(' ', '-'), name.upper())
    from_name = classmethod(from_name)

    def from_slug(cls, slug):
        return cls(slug.title().replace('-', ' '), slug, slug.upper().replace('-', ' '))
    from_slug = classmethod(from_slug)

    def from_norm_name(cls, norm_name):
        return cls(norm_name.title(), norm_name.lower().replace(' ', '-'), norm_name)
    from_norm_name = classmethod(from_norm_name)

class BlockIntersection(models.Model):
    block = models.ForeignKey(Block)
    intersecting_block = models.ForeignKey(Block, related_name="intersecting_block")
    intersection = models.ForeignKey("Intersection", blank=True, null=True)
    location = models.PointField()

    class Meta:
        unique_together = ("block", "intersecting_block")

    def __unicode__(self):
        return u'%s intersecting %s' % (self.block, self.intersecting_block)

class IntersectionManager(models.GeoManager):
    def search(self, predir_a=None, street_a=None, suffix_a=None, postdir_a=None,
                     predir_b=None, street_b=None, suffix_b=None, postdir_b=None):
        """
        Returns a queryset of intersections.
        """
        # Since intersections are symmetrical---"N. Kimball Ave. & W. Diversey
        # Ave." == "W. Diversey Ave. & N. Kimball Ave."---we use Q
        # objects for the OR reverse of the ordering of the keyword
        # arguments.
        filters = [{}, {}]
        if predir_a:
            filters[0]["predir"] = predir_a.upper()
        if street_a:
            filters[0]["street"] = street_a.upper()
        if suffix_a:
            filters[0]["suffix"] = suffix_a.upper()
        if postdir_a:
            filters[0]["postdir"] = postdir_a.upper()
        if predir_b:
            filters[1]["predir"] = predir_b.upper()
        if street_b:
            filters[1]["street"] = street_b.upper()
        if suffix_b:
            filters[1]["suffix"] = suffix_b.upper()
        if postdir_b:
            filters[1]["postdir"] = postdir_b.upper()
        q1 = reduce(operator.and_, [Q(**{k+"_a": v}) for k,v in filters[0].iteritems()] +
                                   [Q(**{k+"_b": v}) for k,v in filters[1].iteritems()])
        q2 = reduce(operator.and_, [Q(**{k+"_a": v}) for k,v in filters[1].iteritems()] +
                                   [Q(**{k+"_b": v}) for k,v in filters[0].iteritems()])
        qs = self.filter(q1 | q2)
        qs = qs.extra(select={"point": "AsText(location)"})
        return qs

class Intersection(models.Model):
    pretty_name = models.CharField(max_length=255, unique=True) # eg., "N. Kimball Ave. & W. Diversey Ave.
    slug = models.SlugField(max_length=64) # eg., "n-kimball-ave-and-w-diversey-ave"
    # Street A
    predir_a = models.CharField(max_length=2, blank=True, db_index=True) # eg., "N"
    street_a = models.CharField(max_length=255, db_index=True) # eg., "KIMBALL"
    suffix_a = models.CharField(max_length=32, blank=True, db_index=True) # eg., "AVE"
    postdir_a = models.CharField(max_length=2, blank=True, db_index=True) # eg., "NW"
    # Street B
    predir_b = models.CharField(max_length=2, blank=True, db_index=True) # eg., "W"
    street_b = models.CharField(max_length=255, db_index=True) # eg., "DIVERSEY"
    suffix_b = models.CharField(max_length=32, blank=True, db_index=True) # eg., "AVE"
    postdir_b = models.CharField(max_length=2, blank=True, db_index=True) # eg., "SE"
    zip = models.CharField(max_length=10, db_index=True) # Possible Plus-4
    city = models.CharField(max_length=255, db_index=True) # Always uppercase
    state = USStateField(db_index=True) # Always uppercase
    location = models.PointField()
    objects = IntersectionManager()

    class Meta:
        db_table = 'intersections'
        unique_together = ("predir_a", "street_a", "suffix_a", "postdir_a", "predir_b", "street_b", "suffix_b", "postdir_b")

    def __unicode__(self):
        return self.pretty_name

    def reverse_pretty_name(self):
        return u" & ".join(self.pretty_name.split(" & ")[::-1])

    def url(self):
        # Use the URL of the first block found of those which comprise
        # this intersection.
        try:
            first_block = self.blockintersection_set.all()[0].block
        except IndexError:
            return ''
        return first_block.url()

    def alert_url(self):
        return '%salerts/' % self.url()

class Suburb(models.Model):
    # This model keeps track of nearby cities that we don't care about.
    # It's essentially a blacklist.
    name = models.CharField(max_length=255)
    normalized_name = models.CharField(max_length=255, unique=True)

    def __unicode__(self):
        return self.name
