from ebdata.retrieval.utils import convert_entities
from lxml import etree
import re

def html_to_paragraph_list(tree):
    """
    Given an HTML tree, removes HTML tags and returns a list of strings, with
    each string representing a paragraph/block.
    """
    block_tags = set(['blockquote', 'dd', 'div', 'dt', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'h7', 'h8', 'li', 'p', 'td', 'th', 'tr'])
    drop_tags_only = set(['a', 'abbr', 'acronym', 'b', 'center', 'dir', 'dl', 'em', 'font', 'form', 'hr', 'i', 'label', 'menu', 'ol', 'pre', 'small', 'span', 'strong', 'sub', 'sup', 'table', 'tbody', 'tfoot', 'thead', 'topic', 'u', 'ul', 'wbr'])
    drop_tags_and_contents = set(['applet', 'area', 'button', 'embed', 'img', 'iframe', 'head', 'input', 'link', 'map', 'meta', 'noscript', 'object', 'option', 'script', 'select', 'spacer', 'style', 'textarea', 'title'])

    elements_to_drop = []
    for element in tree.getiterator():
        if not isinstance(element.tag, basestring): # If it's a comment...
            element.drop_tag()
            continue
        if element.text and '\n' in element.text:
            element.text = element.text.replace('\n', ' ')
        if element.tail and '\n' in element.tail:
            element.tail = element.tail.replace('\n', ' ')
        if element.tag in block_tags:
            element.text = '\n' + (element.text or '')
            element.tail = '\n' + (element.tail or '')
            element.drop_tag()
        elif element.tag == 'br':
            element.tail = '\n' + (element.tail or '')
            element.drop_tag()
        elif element.tag in drop_tags_only:
            element.drop_tag()
        elif element.tag in drop_tags_and_contents:
            elements_to_drop.append(element)
        elif element.tag not in ('html', 'body'): # Unknown tag!
            element.drop_tag()
    for e in elements_to_drop:
        e.drop_tree()

    try:
        tree.body
    except IndexError:
        return ''
    else:
        new_html = etree.tostring(tree.body, method='html')[6:-7] # strip <body> and </body>
        new_html = convert_entities(new_html)
        return re.split(r'\s*\n+\s*', new_html.strip())
