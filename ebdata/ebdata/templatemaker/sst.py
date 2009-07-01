"""
Template implementation that uses the Site Style Tree concept, as described
in this paper:

    L. Yi and B. Liu. Eliminating noisy information in web pages for data mining.
    In ACM Conf. on Knowledge Discovery and Data Mining (SIGKDD), 2003.
    http://citeseer.ist.psu.edu/yi03eliminating.html
"""

from ebdata.templatemaker.listdiff import longest_common_substring
from ebdata.textmining.treeutils import make_tree_and_preprocess
from lxml import etree
import time

class NoMatch(Exception):
    pass

def element_hash_strict(el):
    """
    Returns a hash of the given etree Element, such that it can be used
    in a longest_common_substring comparison against another tree.
    """
    # <br> tags should never be marked as the same as other <br> tags, so use
    # the current time to introduce enough entropy. Note that we use '%.10f'
    # instead of str(time.time()) because str() rounds the number to two
    # decimal places, resulting in identical results for subsequent tags.
    if el.tag == 'br':
        return '%.10f' % time.time()

    attrs = sorted(dict(el.attrib).items())
    return (el.tag, attrs, el.text, el.tail)

def element_hash_loose(el):
    if el.tag == 'br':
        return '%.10f' % time.time()
    if el.tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'title'):
        return el.tag
    return (el.tag, el.text)

def tree_diff_children(list1, list2, hash_func, algorithm):
    # list1 and list2 are lists of etree Elements.
    if list1 == list2 == []:
        return []
    # Try to find the longest common substring, according to hash_func().
    # First we use element_hash_strict(), but then we use element_hash_loose()
    # as a fallback.
    best_size, offset1, offset2 = longest_common_substring([hash_func(el) for el in list1], [hash_func(el) for el in list2])
    result = []
    if best_size == 0:
        if hash_func == element_hash_strict:
            result.extend(tree_diff_children(list1, list2, element_hash_loose, algorithm))
        else:
            result.append(etree.Element('MULTITAG_HOLE'))
    if offset1 > 0 and offset2 > 0:
        # There's leftover stuff on the left side of BOTH lists.
        result.extend(tree_diff_children(list1[:offset1], list2[:offset2], element_hash_strict, algorithm))
    elif offset1 > 0 or offset2 > 0:
        # There's leftover stuff on the left side of ONLY ONE of the lists.
        result.append(etree.Element('MULTITAG_HOLE'))
    if best_size > 0:
        for i in range(best_size):
            child = tree_diff(list1[offset1+i], list2[offset2+i], algorithm)
            result.append(child)
        if (offset1 + best_size < len(list1)) and (offset2 + best_size < len(list2)):
            # There's leftover stuff on the right side of BOTH lists.
            result.extend(tree_diff_children(list1[offset1+best_size:], list2[offset2+best_size:], element_hash_strict, algorithm))
        elif (offset1 + best_size < len(list1)) or (offset2 + best_size < len(list2)):
            # There's leftover stuff on the right side of ONLY ONE of the lists.
            result.append(etree.Element('MULTITAG_HOLE'))
    return result

def tree_diff(tree1, tree2, algorithm=1):
    """
    Returns a "diff" of the two etree objects, using these placeholders in case
    of differences:
        TEXT_HOLE -- used when the 'text' differs
        TAIL_HOLE -- used when the 'tail' differs
        ATTRIB_HOLE -- used when an attribute value (or existence) differs
        MULTITAG_HOLE -- used when an element's children differ

    This assumes tree1 and tree2 share the same root tag, e.g. "<html>".
    """
    # Copy the element (but not its children).
    result = etree.Element(tree1.tag)
    result.text = (tree1.text != tree2.text) and 'TEXT_HOLE' or tree1.text
    result.tail = (tree1.tail != tree2.tail) and 'TAIL_HOLE' or tree1.tail
    attrs1, attrs2 = dict(tree1.attrib), dict(tree2.attrib)
    for k1, v1 in attrs1.items():
        if attrs2.pop(k1, None) == v1:
            result.attrib[k1] = v1
        else:
            result.attrib[k1] = 'ATTRIB_HOLE'
    for k2 in attrs2.keys():
        result.attrib[k2] = 'ATTRIB_HOLE'
    if algorithm == 1:
        for child in tree_diff_children(list(tree1), list(tree2), element_hash_strict, algorithm):
            result.append(child)
    elif algorithm == 2:
        if [child.tag for child in tree1] == [child.tag for child in tree2]:
            for i, child in enumerate(tree1):
                diff_child = tree_diff(child, tree2[i], algorithm)
                result.append(diff_child)
        else:
            result.append(etree.Element('MULTITAG_HOLE'))
    else:
        raise ValueError('Got invalid algorithm: %r' % algorithm)
    return result

def tree_extract_children(list1, list2, hash_func, algorithm):
    # list1 and list2 are lists of etree Elements.
    if list1 == list2 == []:
        return []
    best_size, offset1, offset2 = longest_common_substring([hash_func(el) for el in list1], [hash_func(el) for el in list2])
    result = []
    if best_size == 0:
        if [el.tag for el in list1] == ['MULTITAG_HOLE']:
            data = ''.join([etree.tostring(child, method='html') for child in list2])
            result.append({'type': 'multitag', 'value': data, 'tag': None})
        elif hash_func == element_hash_strict:
            result.extend(tree_extract_children(list1, list2, element_hash_loose, algorithm))
        else:
            raise NoMatch('Brain tag had children %r, but sample had %r' % (list1, list2))
    if offset1 > 0 and offset2 > 0:
        # There's leftover stuff on the left side of BOTH lists.
        result.extend(tree_extract_children(list1[:offset1], list2[:offset2], element_hash_strict, algorithm))
    elif offset1 > 0:
        # There's leftover stuff on the left side of ONLY the brain.
        if [el.tag for el in list1[:offset1]] == ['MULTITAG_HOLE']:
            result.append({'type': 'multitag', 'value': '', 'tag': None})
        else:
            raise NoMatch('Brain tag had children %r, but sample had %r' % (list1[:offset1], list2))
    elif offset2 > 0:
        # There's leftover stuff on the left side of ONLY the sample.
        raise NoMatch('Brain tag had children %r, but sample had %r' % (list1, list2))
    if best_size > 0:
        for i in range(best_size):
            child_result = tree_extract(list1[offset1+i], list2[offset2+i], algorithm)
            result.extend(child_result)
        if (offset1 + best_size < len(list1)) or (offset2 + best_size < len(list2)):
            # There's leftover stuff on the right side of EITHER list.
            child_result = tree_extract_children(list1[offset1+best_size:], list2[offset2+best_size:], element_hash_strict, algorithm)
            result.extend(child_result)
    return result

def tree_extract(brain, sample, algorithm):
    """
    Given two etrees -- a brain (the result of a tree_diff()) and a sample
    to extract from -- this returns a list of raw data from the sample.

    Each element in the resulting list is a dict of {type, value}, where:
        type is either 'attrib', 'text', 'multitag' or 'tail'
        value is a string of the raw data
    """
    result = []

    # Extract ATTRIB_HOLE.
    brain_attrs = sorted(dict(brain.attrib).items()) # Sort, to be deterministic in output.
    sample_attrs = dict(sample.attrib)
    for k, brain_value in brain_attrs:
        if brain_value == 'ATTRIB_HOLE':
            result.append({'type': 'attrib', 'value': sample_attrs.pop(k, ''), 'tag': brain.tag})
        else:
            sample_value = sample_attrs.pop(k, None)
            if brain_value != sample_value:
                raise NoMatch('<%s> %r attribute had different values: %r and %r' % (brain.tag, k, brain_value, sample_value))
    if sample_attrs:
        # If any attributes are left in sample_attrs, they weren't in the brain.
        raise NoMatch('<%s> attributes exist in sample but not in brain: %r' % (brain.tag, sample_attrs))

    # Extract TEXT_HOLE.
    if brain.text == 'TEXT_HOLE':
        result.append({'type': 'text', 'value': sample.text, 'tag': brain.tag})
    elif brain.text != sample.text:
        raise NoMatch('<%s> text had different values: %r and %r' % (brain.tag, brain.text, sample.text))

    # Extract MULTITAG_HOLE.
    brain_children = [child.tag for child in brain]
    sample_children = [child.tag for child in sample]
    if 'MULTITAG_HOLE' in brain_children:
        if algorithm == 1:
            multitag_result = tree_extract_children(list(brain), list(sample), element_hash_strict, algorithm)
            result.extend(multitag_result)
        elif algorithm == 2:
            data = ''.join([etree.tostring(child) for child in sample])
            result.append({'type': 'multitag', 'value': data, 'tag': None})
        else:
            ValueError('Got invalid algorithm: %r' % algorithm)
    elif brain_children == sample_children:
        for i, child in enumerate(brain):
            child_result = tree_extract(child, sample[i], algorithm)
            result.extend(child_result)
    else:
        raise NoMatch('Brain <%s> tag had children %r, but sample had %s' % \
            (brain.tag, brain_children, sample_children))

    # Extract TAIL_HOLE.
    if brain.tail == 'TAIL_HOLE':
        # Note that we use brain.getparent() here to get the tag that contains the tail text.
        result.append({'type': 'tail', 'value': sample.tail, 'tag': brain.getparent().tag})
    elif brain.tail != sample.tail:
        raise NoMatch('<%s> tail had different values: %r and %r' % (brain.tag, brain.tail, sample.tail))

    return result

class Template(object):
    def __init__(self, algorithm=1):
        # algorithm can be either 1 or 2.
        #     1 -- Smarter algorithm that removes more noise, but might fail.
        #     2 -- Dumber algorithm that doesn't remove as much noise, but it
        #          never fails.
        self.htmltree = None
        self.algorithm = algorithm

    def learn(self, html):
        tree = make_tree_and_preprocess(html)
        if self.htmltree is None:
            self.htmltree = tree
        else:
            self.htmltree = tree_diff(self.htmltree, tree, self.algorithm)

    def as_text(self):
        return etree.tostring(self.htmltree, method='html')

    def extract(self, html):
        tree = make_tree_and_preprocess(html)
        if self.htmltree is None:
            raise ValueError('This template has not learned anything yet.')
        return tree_extract(self.htmltree, tree, self.algorithm)

def extract(html, other_pages):
    """
    Given an HTML page string and list of other pages, creates a Template
    and extracts the data from the page.
    """
    # First try algorithm 1, because it's more effective. But if it fails,
    # fall back to algorithm 2.
    for algorithm in (1, 2):
        t = Template(algorithm=algorithm)
        for sample in [html] + other_pages:
            t.learn(sample)
        try:
            return t.extract(html)
        except NoMatch:
            if algorithm == 1:
                continue
            else:
                raise
    raise NoMatch('Reached end of extract() without having gotten a match')
