"""
Common utilities for creating and cleaning lxml HTML trees.
"""

from lxml.html import document_fromstring
import re

def make_tree(html):
    """
    Returns an lxml tree for the given HTML string (either Unicode or
    bytestring).

    This is better than lxml.html.document_fromstring because this takes care
    of a few known issues.
    """
    # Normalize newlines. Otherwise, "\r" gets converted to an HTML entity
    # by lxml.
    html = re.sub('\r\n', '\n', html)

    # Remove <?xml> declaration in Unicode objects, because it causes an error:
    # "ValueError: Unicode strings with encoding declaration are not supported."
    # Note that the error only occurs if the <?xml> tag has an "encoding"
    # attribute, but we remove it in all cases, as there's no downside to
    # removing it.
    if isinstance(html, unicode):
        html = re.sub(r'^\s*<\?xml\s+.*?\?>', '', html)

    return document_fromstring(html)

def make_tree_and_preprocess(html):
    """
    Returns an lxml tree for the given HTML string (either Unicode or
    bytestring). Also preprocesses the HTML to remove data that isn't relevant
    to text mining (see the docstring for preprocess()).
    """
    tree = make_tree(html)
    return preprocess(tree)

def preprocess(tree, drop_tags=(), drop_trees=(), drop_attrs=()):
    """
    Preprocesses a HTML etree to remove data that isn't relevant to text mining.
    The tree is edited in place, but it's also the return value, for
    convenience.

    Specifically, this does the following:
        * Removes all comments and their contents.
        * Removes these tags and their contents:
            <style>, <link>, <meta>, <script>, <noscript>, plus all of drop_trees.
        * For all tags in drop_tags, removes the tags (but keeps the contents).
        * Removes all namespaced attributes in all elements.
    """
    tags_to_drop = set(drop_tags)
    trees_to_drop = set(['style', 'link', 'meta', 'script', 'noscript'])
    for tag in drop_trees:
        trees_to_drop.add(tag)

    elements_to_drop = []
    for element in tree.getiterator():
        if element.tag in tags_to_drop or not isinstance(element.tag, basestring): # If it's a comment...
            element.drop_tag()
        elif element.tag in trees_to_drop:
            elements_to_drop.append(element)
        for attname in element.attrib.keys():
            if ':' in attname or attname in drop_attrs:
                del element.attrib[attname]
    for e in elements_to_drop:
        e.drop_tree()
    return tree
