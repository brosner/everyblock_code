"""
Utility functions for munging address/block/street names.
"""

import re
from ebpub.utils.text import smart_title, slugify

def make_street_pretty_name(street, suffix):
    street_name = smart_title(street)
    if suffix:
        street_name += u' %s.' % smart_title(suffix)
    return street_name

def make_block_number(left_from_num, left_to_num, right_from_num, right_to_num):
    lo_num = min([x for x in (left_from_num, left_to_num, right_from_num, right_to_num) if x])
    hi_num = max([x for x in (left_from_num, left_to_num, right_from_num, right_to_num) if x])
    if lo_num == hi_num:
        number = unicode(lo_num)
    elif lo_num and not hi_num:
        number = unicode(lo_num)
    elif hi_num and not lo_num:
        number = unicode(hi_num)
    else:
        number = u'%s-%s' % (lo_num, hi_num)
    return number

def make_pretty_directional(directional):
    """
    Returns a formatted directional.

    e.g.:

        N -> N.
        NW -> N.W.
    """
    return "".join(u"%s." % c for c in directional)

def make_pretty_name(left_from_num, left_to_num, right_from_num, right_to_num, predir, street, suffix, postdir=None):
    """
    Returns a tuple of (street_pretty_name, block_pretty_name) for the
    given address bits.
    """
    street_name = make_street_pretty_name(street, suffix)
    num_part = make_block_number(left_from_num, left_to_num, right_from_num, right_to_num)
    predir_part = predir and make_pretty_directional(predir) or u''
    postdir_part = postdir and make_pretty_directional(postdir) or u''
    block_name = u'%s %s %s %s' % (num_part, predir_part, street_name, postdir_part)
    block_name = re.sub('\s+', ' ', block_name).strip()
    return street_name, block_name

def make_dir_street_name(block):
    """
    Returns a street name from a block with the directional included.

    If the block has a ``predir``, the directional is prepended:

        "W. Diversey Ave."

    If the block has a ``postdir``, the directional is appended:

        "18th St. N.W."
    """
    name = make_street_pretty_name(block.street, block.suffix)
    if block.predir:
        name = u"%s %s" % (make_pretty_directional(block.predir), name)
    if block.postdir:
        name = u"%s %s" % (name, make_pretty_directional(block.postdir))
    return name

def pretty_name_from_blocks(block_a, block_b):
    return u"%s & %s" % (make_dir_street_name(block_a), make_dir_street_name(block_b))

def slug_from_blocks(block_a, block_b):
    slug = u"%s-and-%s" % (slugify(make_dir_street_name(block_a)),
                           slugify(make_dir_street_name(block_b)))
    # If it's too long for the slug field, drop the directionals
    if len(slug) > 64:
        slug = u"%s-and-%s" % (slugify(make_street_pretty_name(block_a.street, block_a.suffix)),
                               slugify(make_street_pretty_name(block_b.street, block_b.suffix)))
    # If it's still too long, drop the suffixes
    if len(slug) > 64:
        slug = u"%s-and-%s" % (slugify(block_a.street),
                               slugify(block_b.street))

    return slug
