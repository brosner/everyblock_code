from ebdata.textmining.treeutils import make_tree_and_preprocess
from listdiff import longest_common_substring # relative import
from lxml import etree

elements_with_ids = etree.XPath('//*[normalize-space(@id)!=""]')

def identical_elements(list1, list2, debug):
    """
    Returns a list of (elements_to_delete, elements_whose_tail_should_be_removed)
    tuples.

    list1 and list2 should both be lists of etree Elements.
    """
    # list1 and list2 are lists of etree Elements.
    if list1 == list2 == []:
        if debug:
            print "identical_elements() got empty lists"
        return []
    hash_list1 = [(el.tag, el.attrib.get('id'), el.attrib.get('class')) for el in list1]
    hash_list2 = [(el.tag, el.attrib.get('id'), el.attrib.get('class')) for el in list2]
    best_size, offset1, offset2 = longest_common_substring(hash_list1, hash_list2)
    if debug:
        print "Got these two lists:\n  %r\n  %r\nMatch:\n  %r" % (hash_list1, hash_list2, hash_list1[offset1:offset1+best_size])
    if best_size == 0:
        return []
    result = []
    if offset1 > 0 and offset2 > 0:
        # There's leftover stuff on the left side of BOTH lists.
        if debug:
            print "Leftovers on left of BOTH"
        result.extend(identical_elements(list1[:offset1], list2[:offset2], debug))
    for i in range(best_size):
        child1, child2 = list1[offset1+i], list2[offset2+i]
        if debug:
            print "Children:\n  %r\n  %r" % (child1, child2)
            print '%r    %r' % (etree.tostring(child1, method='html'), etree.tostring(child2, method='html'))
        if child1.tag == child2.tag and dict(child1.attrib) == dict(child2.attrib) and child1.text == child2.text and list(child1) == list(child2):
            if debug:
                print "Identical!"
            tail_removals = []
            if child1.tail == child2.tail:
                tail_removals.append(child1)
            # If the previous sibling's tails are equal, remove those.
            if i > 0 and list1[offset1+i-1].tail == list2[offset2+i-1].tail:
                tail_removals.append(list1[offset1+i-1])
            result.append(([child1, child2], tail_removals))
        else:
            if debug:
                print "No matches; descending into children"
            result.extend(identical_elements(list(child1), list(child2), debug))
    if (offset1 + best_size < len(list1)) and (offset2 + best_size < len(list2)):
        # There's leftover stuff on the right side of BOTH lists.
        if debug:
            print "Leftovers on right of BOTH"
        result.extend(identical_elements(list1[offset1+best_size:], list2[offset2+best_size:], debug))
    return result

def strip_template(tree1, tree2, check_ids=True, debug=False):
    """
    Given two etree trees, determines the duplicate/redundant elements in
    both and strips those redundancies from both trees (in place).

    If check_ids is True, then this will also check for duplicate elements
    by ID. This helps to find duplicates at different levels of the tree --
    by default (without check_ids), this function only finds duplicates if
    they're at the same position in the HTML tree.

    Returns the number of redundant elements that have been removed.
    """
    # TODO:
    #    Solve the sidebar problem -- delete them

    # Assemble a list of trees to compare. Obviously, first we just compare the
    # given trees -- but if check_ids is True, then we also compare the
    # subtrees containing "id" attributes.
    tree_pairs = [(tree1, tree2)]
    if check_ids:
        ids2 = dict([(el.get('id'), el) for el in elements_with_ids(tree2)])
        other_pairs = [(el.getparent(), ids2[el.get('id')].getparent()) for el in elements_with_ids(tree1) if el.get('id') in ids2]
        tree_pairs.extend(other_pairs)

    # Run the algorithm multiple times until no similarities remain. This is
    # sort of inelegant, but it works.
    num_removed = 0
    for tree1, tree2 in tree_pairs:
        if debug:
            print 'NEW TREE PAIR:\n  %r\n  %r' % (tree1, tree2)
        while 1:
            if debug:
                print 'New round'
            if tree1 is None and tree2 is None:
                break
            result = identical_elements(list(tree1), list(tree2), debug)
            if debug:
                print "strip_template() result:\n%r" % result
            if not result:
                break
            for drops, tail_removals in result:
                for removal in tail_removals:
                    removal.tail = ''
                for drop in drops:
                    drop.drop_tree()
            num_removed += len(result)
    return num_removed

def clean_page(html, other_page):
    """
    Wrapper around the various cleaning functions. This accepts and returns
    strings instead of trees.
    """
    tree1 = make_tree_and_preprocess(html)
    tree2 = make_tree_and_preprocess(other_page)
    strip_template(tree1, tree2)
    # drop_useless_tags(tree1)
    # remove_empty_tags(tree1, ('div', 'span', 'td', 'tr', 'table'))
    return etree.tostring(tree1, method='html'), etree.tostring(tree2, method='html')
