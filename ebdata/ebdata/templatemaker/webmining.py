from ebdata.templatemaker.htmlutils import remove_empty_tags, brs_to_paragraphs
from ebdata.templatemaker.sst import extract
from ebdata.textmining.treeutils import make_tree_and_preprocess, preprocess
from lxml import etree
import re

def mine_page(html, other_pages):
    result = []
    for hole in extract(html, other_pages):
        # Differences in attribute values aren't relevant.
        if hole['type'] == 'attrib' or not hole['value'] or not hole['value'].strip():
            continue

        # # Differences in links are likely navigation, and can be ignored.
        # if hole['type'] == 'text' and hole['tag'] == 'a':
        #     continue

        # If it's a multitag value, clean its HTML a bit.
        if hole['type'] == 'multitag':
            tree = make_tree_and_preprocess(hole['value'])

            # Drop a bunch of tags that can muck up the display.
            tree = preprocess(tree,
                drop_tags=('a', 'area', 'b', 'center', 'font', 'form', 'img', 'input', 'map', 'small', 'sub', 'sup', 'topic'),
                drop_trees=('applet', 'button', 'embed', 'iframe', 'object', 'select', 'textarea'),
                drop_attrs=('background', 'border', 'cellpadding', 'cellspacing', 'class', 'clear', 'id', 'rel', 'style', 'target'))

            remove_empty_tags(tree, ('br',))
            tree = brs_to_paragraphs(tree)

            # The [6:-7] cuts off the '<body>' and '</body>'.
            try:
                body = tree.body
            except IndexError:
                continue # lxml raises an IndexError if there's no <body>.

            # Skip bits that don't have at least one letter or number.
            # Note: If this code is ever internationalized, this will have to be
            # removed.
            if not re.search('[A-Za-z0-9]', body.text_content()):
                continue

            string = etree.tostring(body, method='html')[6:-7]
        else:
            string = hole['value']

            # Skip bits that don't have at least one letter or number.
            # Note: If this code is ever internationalized, this will have to be
            # removed.
            if not re.search('[A-Za-z0-9]', string):
                continue

        # Clean up newlines, tabs and &nbsp;.
        string = re.sub('[\n\t]', ' ', string.strip())
        string = string.replace('&nbsp;', ' ')
        string = string.replace('&#160;', ' ')

        result.append(string)
    return result
