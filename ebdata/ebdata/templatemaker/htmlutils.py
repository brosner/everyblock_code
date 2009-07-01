"""
Utilities for manipulating lxml.html trees.
"""

import re
from lxml import etree
from lxml.html import Element, builder as E

# All text that isn't within an <a> tag.
non_linked_text = etree.XPath("descendant-or-self::*[name()!='a']/text()")

# All text that's within an <a> tag.
linked_text = etree.XPath("descendant-or-self::*[name()='a']/text()")

# All <a> elements whose href and text contain the string 'print'.
# The "translate(x, 'PRINT', 'print')
printer_links = etree.XPath("//a[contains(translate(@href, 'PRINT', 'print'), 'print') or contains(@href, 'pf')][contains(translate(text(), 'PRINT', 'print'), 'print')]")

def percent_linked_text(tree):
    """
    Returns a float representing the percentage of all text within this tree
    that is linked (e.g., is within an <a> tag).
    """
    links_yes = len(''.join([bit.strip() for bit in linked_text(tree) if bit.strip()]))
    links_no = len(''.join([bit.strip() for bit in non_linked_text(tree) if bit.strip()]))
    try:
        return 1.0 * links_yes / (links_yes + links_no)
    except ZeroDivisionError:
        return 0.0

def is_printer_link(href, link_text):
    """
    Helper function that picks up some of the logic that the `printer_links`
    XPath expression can't handle. Returns True if the given URL and link text
    probably are a print link.
    """
    if not re.search(r'(?i)\b(?:print|printer)\b', link_text):
        return False
    if re.search(r'(?i)print[\s-]*(?:edition|advertising|ads)\b', link_text):
        return False
    if re.search(r'(?i)\s*javascript:', href):
        return False
    return True

def printer_friendly_link(tree):
    """
    Returns the 'printer-friendly' URL for the given HTML tree.

    This works by looking for any link that has 'print' in both the link text
    and the URL.

    Returns None if it can't find such a link.
    """
    a_tags = [a for a in printer_links(tree) if is_printer_link(a.attrib['href'], a.text_content())]
    if a_tags:
        # GOTCHA: If there are multiple links, we use the first one.
        link = a_tags[0].attrib['href'].strip()
        if not link.startswith('javascript:'):
            return link
    return None

def remove_empty_tags(tree, ignore_tags):
    """
    Removes all empty tags in the given etree, editing it in place. A tag is
    considered empty if it has no contents (text or tags).

    This works in a reductive manner. If the removal of an empty tag causes its
    parent to become empty, then the parent will be removed, too, recursively.

    ignore_tags should be a tuple of tag names to ignore (i.e., any empty
    tag with a tag name in ignore_tags will not be removed). Each tag name in
    this list should be lowercase.

    The <body> and <html> tags are never removed.
    """
    ignore_tags += ('body', 'html')
    child_removed = False
    for element in tree:
        # The "element.getparent() is not None" check ensures that we don't
        # cause the AssertionError in drop_tree().
        if element.tag not in ignore_tags and (element.text is None or not element.text.strip()) \
                and not list(element) and element.getparent() is not None:
            element.drop_tree()
            child_removed = True
        else:
            remove_empty_tags(element, ignore_tags)
    if child_removed:
        parent = tree.getparent()
        if parent is not None:
            remove_empty_tags(parent, ignore_tags)

def brs_to_paragraphs(tree, inline_tags=None):
    """
    Return an lxml tree with all <br> elements stripped and paragraphs put in
    place where necessary.
    """
    # add these tags to p's that we're currently building, any other tags will
    # close the current p
    inline_tags = inline_tags or ['a']

    # if this tree doesn't have any child elements, just return it as is
    if len(tree) == 0:
        return tree

    # if this tree doesn't contain any <br> tags, we don't need to touch it
    if tree.find('.//br') is None:
        return tree

    # XXX: We're building a whole new tree here and leaving out any attributes.
    # A) That might be a little slower and more memory intensive than modifying
    # the tree in place, and B) we're dropping any attributes on block elements.
    # The latter is probably fine for current use, but certainly not ideal.
    new_tree = Element(tree.tag)

    # if this tree starts out with text, create a new paragraph for it, and
    # add it to the tree
    if tree.text:
        p = E.P()
        p.text = tree.text
        new_tree.append(p)

    for e in tree:
        if e.tag == 'br':
            # avoid adding empty p elements
            if e.tail is None:
                continue
            # start a new p
            p = E.P()
            p.text = e.tail
            new_tree.append(p)
        # if this is a block tag, and it has trailing text, that text needs to
        # go into a new paragraph... only if the tail has actual content and
        # not just whitespace though.
        elif e.tail and re.match('[^\s]', e.tail) and e.tag not in inline_tags:
            p = E.P()
            p.text = e.tail
            e.tail = ''
            new_tree.append(e)
            new_tree.append(p)
        # keep inline tags inside the current paragraph
        elif e.tag in inline_tags:
            p.append(e)
        else:
            new_tree.append(brs_to_paragraphs(e))

    return new_tree
