import re

slugify = lambda x: re.sub('[-\s]+', '-', re.sub('[^\w\s-]', '', x.strip())).lower()

def intcomma(orig):
    """
    Converts an integer to a string containing commas every three digits.
    For example, 3000 becomes '3,000' and 45000 becomes '45,000'.
    """
    new = re.sub("^(-?\d+)(\d{3})", '\g<1>,\g<2>', orig)
    if orig == new:
        return new
    else:
        return intcomma(new)

def clean_address(addr):
    """
    Given an address string, normalizes it to look pretty.

    >>> clean_address('123 MAIN')
    '123 Main'
    >>> clean_address('123 MAIN ST')
    '123 Main St.'
    >>> clean_address('123 MAIN ST S')
    '123 Main St. S.'
    >>> clean_address('123 AVENUE A')
    '123 Avenue A'
    >>> clean_address('2 N ST LAWRENCE PKWY')
    '2 N. St. Lawrence Pkwy.'
    >>> clean_address('123 NORTH AVENUE') # Don't abbreviate 'AVENUE'
    '123 North Avenue'
    >>> clean_address('123 N. Main St.')
    '123 N. Main St.'
    >>> clean_address('  123  N  WABASH  AVE   ')
    '123 N. Wabash Ave.'
    >>> clean_address('123 MAIN ST SW')
    '123 Main St. S.W.'
    >>> clean_address('123 MAIN ST NE')
    '123 Main St. N.E.'
    >>> clean_address('123 NEW YORK ST NE') # Don't punctuate 'NEW' (which contains 'NE')
    '123 New York St. N.E.'
    >>> clean_address('123 MAIN St Ne')
    '123 Main St. N.E.'
    >>> clean_address('123 MAIN St n.e.')
    '123 Main St. N.E.'
    """
    addr = smart_title(addr)
    addr = re.sub(r'\b(Ave|Blvd|Bvd|Cir|Ct|Dr|Ln|Pkwy|Pl|Plz|Pt|Pts|Rd|Rte|Sq|Sqs|St|Sts|Ter|Terr|Trl|Wy|N|S|E|W)(?!\.)\b', r'\1.', addr)

    # Take care of NE/NW/SE/SW.
    addr = re.sub(r'\b([NSns])\.?([EWew])\b\.?', lambda m: ('%s.%s.' % m.groups()).upper(), addr)

    addr = re.sub(r'\s\s+', ' ', addr).strip()
    return addr

def address_to_block(addr):
    """
    Given an address string, normalizes it to the 100 block level.

    >>> address_to_block('1 N. Main Street')
    '0 block of N. Main Street'
    >>> address_to_block('10 N. Main Street')
    '0 block of N. Main Street'
    >>> address_to_block('123 Main Street')
    '100 block of Main Street'
    >>> address_to_block('123 MAIN STREET')
    '100 block of MAIN STREET'
    >>> address_to_block('4523 Main Street')
    '4500 block of Main Street'
    >>> address_to_block('  123 Main Street')
    '100 block of Main Street'
    """
    return re.sub(r'^\s*(\d+) ', lambda m: '%s block of ' % re.sub('..?$', (len(m.group(1)) > 2 and '00' or '0'), m.group(1)), addr)

def smart_title(s, exceptions=None):
    r"""
    Like .title(), but smarter.

    >>> smart_title('hello THERE')
    'Hello There'
    >>> smart_title('128th street')
    '128th Street'
    >>> smart_title('"what the heck," he said. "let\'s go to the zoo."')
    '"What The Heck," He Said. "Let\'s Go To The Zoo."'
    >>> smart_title('')
    ''
    >>> smart_title('a')
    'A'
    >>> smart_title('(this is a parenthetical.)')
    '(This Is A Parenthetical.)'
    >>> smart_title('non-functional')
    'Non-Functional'
    >>> smart_title("BILL'S HOUSE OF WAX LIPS LLC", ["of", "LLC"])
    "Bill's House of Wax Lips LLC"
    >>> smart_title("The C.I.A.", ["C.I.A."])
    'The C.I.A.'
    """
    result = re.sub(r"(?<=[\s\"\(-])(\w)", lambda m: m.group(1).upper(), s.lower())
    if result:
        result = result[0].upper() + result[1:]

    # Handle the exceptions.
    if exceptions is not None:
        for e in exceptions:
            pat = re.escape(e)
            if re.search("^\w", pat):
                pat = r"\b%s" % pat
            if re.search("\w$", pat):
                pat = r"%s\b" % pat
            pat = r"(?i)%s" % pat
            result = re.sub(pat, e, result)

    return result

def smart_excerpt(text, highlighted_text):
    """
    Returns a short excerpt of the given text with `highlighted_text`
    guaranteed to be in the middle.
    """
    m = re.search('(?:\w+\W+){0,15}%s(?:\W+\w+){0,15}' % highlighted_text, text)
    if not m:
        raise ValueError('Value not found in text')
    excerpt = m.group()
    elipsis_start = not text.startswith(excerpt)
    elipsis_end = not text.endswith(excerpt)
    if elipsis_start:
        excerpt = '...' + excerpt
    if elipsis_end:
        excerpt += '...'
    return excerpt

if __name__ == "__main__":
    import doctest
    doctest.testmod()
