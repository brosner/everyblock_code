import re

# Regex notes:
#   * This is *not* a case-insensitive regex, because we assume
#     capitalized words are special (street names).
#   * All data matched by capturing parentheses is concatenated together, so
#     if you don't want to include something in the resulting string, don't
#     capture it.

# STREET_NAME is a fragment of a regular expression that is used in several
# places in our "real" regular expression (ADDRESSES_RE) below. The one tricky
# thing about it is that it includes a "CAPTURE_START" placeholder instead of
# a capturing opening parenthesis. This lets us create two versions of the
# regex -- STREET_NAME_CAPTURE and STREET_NAME_NOCAPTURE.
STREET_NAME = r"""
    # Here, we define some common false positives and tell the regex to ignore them.
    (?!
        [Aa][Ss][Ss][Oo][Cc][Ii][Aa][Tt][Ee][Dd]\ [Pp][Rr][Ee][Ss][Ss] # associated press
        |
        [Uu][Nn][Ii][Vv][Ee][Rr][Ss][Ii][Tt][Yy]\ [Oo][Ff]             # university of
    )
    # DIRECTION
    %(CAPTURE_START)s
        (?:
            [NSEWnsew]\.?
            |
            (?:
                [Nn][Oo][Rr][Tt][Hh] |
                [Ss][Oo][Uu][Tt][Hh] |
                [Ee][Aa][Ss][Tt] |
                [Ww][Ee][Ss][Tt] |
                [Nn][Oo][Rr][Tt][Hh][Ee][Aa][Ss][Tt] |
                [Ee][Aa][Ss][Tt][Ww][Ee][Ss][Tt] |
                [Ss][Oo][Uu][Tt][Hh][Ee][Aa][Ss][Tt] |
                [Ss][Oo][Uu][Tt][Hh][Ww][Ee][Ss][Tt]
            )
            |
            (?:
                N\.?W | S\.?W | N\.?E | S\.?E
            )\.?
        )
        \ +                                        # space (but not newline)
    )?
    (?:
        # STREET NAME
        %(CAPTURE_START)s
            # Numbered street names with a suffix ("3rd", "4th").
            \d+(?:st|ST|nd|ND|rd|RD|th|TH|d|D)

            |

            # Or, numbered street names without a suffix ("3", "4")
            # but with a street type.
            \d+
            (?=
                \ +
                (?:Ave|Avenue|Blvd|Boulevard|Bvd|Cir|Circle|Court|Ct|Dr|Drive|
                   Lane|Ln|Parkway|Pkwy|Place|Plaza|Pl|Plz|Point|Pt|Pts|Rd|Rte|
                   Sq|Sqs|Street|Streets|St|Sts|Terrace|Ter|Terr|Trl|Way|Wy
                )
                \b
            )

            |

            # Or, street names that don't start with numbers.
            (?:
                # Optional prefixes --
                # "St", as in "St Louis"
                # "Dr. Martin", as in "Dr. Martin Luther King"
                (?:
                    [Ss][Tt]\.?
                    |
                    [Dd][Rr]\.?\ [Mm][Aa][Rr][Tt][Ii][Nn]
                )
                \ +
            )?
            (?:
                Mass\.(?=\ +[Aa]ve)  # Special case: "Mass." abbr. for "Massachussetts Ave."
                                     # Needs to be special-cased because of the period.
                |
                (?:Avenue|Ave\.?)\ +[A-Z]       # Special case: "Avenue X"
                |
                [A-Z][a-z][A-Za-z]*  # One initial-capped word
                |
                [A-Z]\b              # Single-letter street name (e.g., K St. in DC)
                (?!\.\w)             # Avoid '20 U.S.A.'
            )
        )
        (?:
            # Here, we list the options with street suffixes first, so that
            # the suffix abbreviations are treated as the last part of the
            # street name, to avoid overeagerly capturing "123 Main St. The".
            %(CAPTURE_START)s
                \ +(?:Ave|Blvd|Bvd|Cir|Ct|Dr|Ln|Pkwy|Pl|Plz|Pt|Pts|Rd|Rte|Sq|Sqs|St|Sts|Ter|Terr|Trl|Wy)\.
                |
                \ +[A-Z][a-z][A-Za-z]*\ (?:Ave|Blvd|Bvd|Cir|Ct|Dr|Ln|Pkwy|Pl|Plz|Pt|Pts|Rd|Rte|Sq|Sqs|St|Sts|Ter|Terr|Trl|Wy)\.
                |
                (?:,?\ Jr\.?,?|\ +[A-Z][a-z][A-Za-z]*){2}\ +(?:Ave|Blvd|Bvd|Cir|Ct|Dr|Ln|Pkwy|Pl|Plz|Pt|Pts|Rd|Rte|Sq|Sqs|St|Sts|Ter|Terr|Trl|Wy)\.
                |
                (?:,?\ Jr\.?,?|\ +[A-Z][a-z][A-Za-z]*){3}\ +(?:Ave|Blvd|Bvd|Cir|Ct|Dr|Ln|Pkwy|Pl|Plz|Pt|Pts|Rd|Rte|Sq|Sqs|St|Sts|Ter|Terr|Trl|Wy)\.
                |
                (?:,?\ Jr\.?,?|\ +[A-Z][a-z][A-Za-z]*){4}\ +(?:Ave|Blvd|Bvd|Cir|Ct|Dr|Ln|Pkwy|Pl|Plz|Pt|Pts|Rd|Rte|Sq|Sqs|St|Sts|Ter|Terr|Trl|Wy)\.
                |
                (?:,?\ Jr\.?,?|\ +[A-Z][a-z][A-Za-z]*){5}\ +(?:Ave|Blvd|Bvd|Cir|Ct|Dr|Ln|Pkwy|Pl|Plz|Pt|Pts|Rd|Rte|Sq|Sqs|St|Sts|Ter|Terr|Trl|Wy)\.
                |
                (?:,?\ Jr\.?,?|\ +[A-Z][a-z][A-Za-z]*){1,5}
            )?
            # OPTIONAL POST-DIR
            (?:
                # Standard post-dir format
                %(CAPTURE_START)s
                    ,?\s(?:N\.?E|S\.?E|N\.?W|S\.?W|N|S|E|W)\.?
                )
                # Avoid greedily capturing more letters, like
                # '123 Main St, New England' to '123 Main St, N'
                (?![A-Za-z])

                |

                # Or, a special-case for DC quadrants, to find stuff like:
                # "600 H Street in NE Washington"
                # "600 H Street in the NE quadrant"
                # "600 H Street in northeast DC"

                # Note that this is NOT captured, so that it's excluded from
                # the final output.
                ,?
                \s in
                %(CAPTURE_START)s
                    \s
                )
                (?:
                    (?:the|far) \s
                )?

                %(CAPTURE_START)s
                    (?:NE|SE|NW|SW|[Nn]ortheast|[Ss]outheast|[Nn]orthwest|[Ss]outhwest)
                    (?=
                        \s (?:quadrant|D\.?C\.?|Washington)
                    )
                )
            )?
        )?
    )
"""
STREET_NAME_CAPTURE = STREET_NAME % {'CAPTURE_START': '('}
STREET_NAME_NOCAPTURE = STREET_NAME % {'CAPTURE_START': '(?:'}

ADDRESSES_RE = re.compile(r"""(?x)
    (?<!-|/|:|,|\.|\$) # These various characters are not allowed before an address/intersection.
    \b

    # Ignore things that look like dates -- e.g., "21 May 2009".
    # This is a problem e.g. in cases where there's a May Street.
    (?!
        \d+\s+
        (?:January|February|March|April|May|June|July|August|September|October|November|December)
        ,?\s+
        \d\d\d\d
    )

    # Ignore intersections that are prefixed by "University of", like
    # "University of Texas at Austin". This is a common false positive.
    (?<!
        [Uu][Nn][Ii][Vv][Ee][Rr][Ss][Ii][Tt][Yy]\s[Oo][Ff]\s
    )

    (?:
        # SEGMENT ("FOO BETWEEN BAR AND BAZ")
        (?:
            %(STREET_NAME_CAPTURE)s (,?\ + between \ +) %(STREET_NAME_CAPTURE)s (,?\ + and \ +) %(STREET_NAME_CAPTURE)s
            |
            %(STREET_NAME_CAPTURE)s (,?\ + from \ +) %(STREET_NAME_CAPTURE)s (,?\ + to \ +) %(STREET_NAME_CAPTURE)s
        )

        |

        # BLOCK/ADDRESS
        (?:
            (
                (?:
                    (?:\d+|[Ff][Ii][Rr][Ss][Tt])[-\ ]
                        (?:(?:[Nn][Oo][Rr][Tt][Hh]|[Ss][Oo][Uu][Tt][Hh]|[Ee][Aa][Ss][Tt]|[Ww][Ee][Ss][Tt])\ )?
                    [Bb][Ll][Oo][Cc][Kk]\ [Oo][Ff]
                    |
                    \d+\ *-\ *\d+
                    |
                    \d+
                )
                \ +
            )
            %(STREET_NAME_CAPTURE)s

            # ignore the intersection in parenthesis so that it's not picked
            # up as a separate location. We do this by consuming the string
            # but *not* capturing it.
            (?:
                \ +
                \(?
                between
                \ +
                %(STREET_NAME_NOCAPTURE)s
                \ +
                and
                \ +
                %(STREET_NAME_NOCAPTURE)s
                \)?
            )?
        )

        |

        # INTERSECTION
        (?:
            # Common intersection prefixes. They're included here so that the
            # regex doesn't include them as part of the street name.
            (?:
                (?:
                    [Nn]ear |
                    [Aa]t |
                    [Oo]n |
                    [Tt]o |
                    [Aa]round |
                    [Ii]ntersection\ of |
                    [Cc]orner\ of |
                    [Aa]rea\ of |
                    [Aa]reas?\ surrounding |
                    vicinity\ of |
                    ran\ down |
                    running\ down |
                    crossed
                )
                \ +
            )?
            \b
            (?:%(STREET_NAME_CAPTURE)s)
            (\ +)
            (
                (?:
                    [Aa][Nn][Dd] |
                    [Aa][Tt] |
                    [Nn][Ee][Aa][Rr] |
                    & |
                    [Aa][Rr][Oo][Uu][Nn][Dd] |
                    [Tt][Oo][Ww][Aa][Rr][Dd][Ss]? |
                    [Oo][Ff][Ff] |
                    (?:[Jj][Uu][Ss][Tt]\ )?(?:[Nn][Oo][Rr][Tt][Hh]|[Ss][Oo][Uu][Tt][Hh]|[Ee][Aa][Ss][Tt]|[Ww][Ee][Ss][Tt])\ [Oo][Ff] |
                    (?:[Jj][Uu][Ss][Tt]\ )?[Pp][Aa][Ss][Tt]
                )
                \ +
            )
            (?:%(STREET_NAME_CAPTURE)s)
        )
    )

    # OPTIONAL CITY SUFFIX
    (?:
        (?:
            ,?\s+in |
            ,
        )
        \s+

        # CITY NAME
        (
            [A-Z][a-z][A-Za-z]*                   # One initial-capped word
            (?:
                ,?\ Jr\.?,?
                |
                \ [A-Z][a-z][A-Za-z]*
                |
                -[A-Za-z]+                        # Hyphenated words (e.g. "Croton-on-Hudson" in NY)
            ){0,4}  # Initial-capped words
        )
    )?
    """ % {'STREET_NAME_CAPTURE': STREET_NAME_CAPTURE, 'STREET_NAME_NOCAPTURE': STREET_NAME_NOCAPTURE})

def parse_addresses(text):
    """
    Returns a list of all addresses found in the given string, as tuples in the
    format (address, city).
    """
    # This assumes the last parenthetical grouping in ADDRESSES_RE is the city.
    return [(''.join(bits[:-1]), bits[-1]) for bits in ADDRESSES_RE.findall(text)]

def tag_addresses(text, pre='<addr>', post='</addr>'):
    """
    "Tags" any addresses in the given string by surrounding them with pre and post.
    Returns the resulting string.

    Note that only the addresses are tagged, not the cities (if cities exist).
    """
    def _re_handle_address(m):
        bits = m.groups()
        return pre + ''.join(filter(None, bits[:-1])) + (bits[-1] and (', %s' % bits[-1]) or '') + post
    return ADDRESSES_RE.sub(_re_handle_address, text)
