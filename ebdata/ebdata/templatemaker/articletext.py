from ebdata.retrieval.utils import convert_entities
from lxml import etree
import decimal
import re

is_punctuated = re.compile(ur"""
    [\.\!\?]
    (?:\s+|"|'|\xe2\x80\x9d|\u201d|\u2019|\)){0,3}
    \s*
    $
""", re.VERBOSE).search

def article_text_sections(tree):
    """
    Given an HTML tree of a news article (or blog entry permalink), deduces
    which part of it is text and returns a list of lists of strings, with each
    string representing a paragraph and each list of strings representing a
    "section" of the page.
    """

    # The basic algorithm here is to combine all text within the same block
    # (e.g., a <div>).

    MIN_NUM_PARAGRAPHS = 3
    MIN_NUM_PUNCTUATED = 3

    # In order for a paragraph to be counted toward MIN_NUM_PUNCTUATED, it must
    # have this number of characters.
    MIN_CHARS_IN_PARAGRAPH = 30

    # If this many paragraphs with MIN_CHARS_IN_PARAGRAPH are included in the
    # section, then the section will be included, regardless of failing
    # MIN_PERCENTAGE_PUNCTUATED.
    NUM_PARAGRAPHS_SAFE_GUESS = 6

    # In order for a section to be included in the result, at least this
    # percentage of paragraphs in the section must be punctuated.
    MIN_PERCENTAGE_PUNCTUATED = decimal.Decimal('.5')

    block_tags = set(['blockquote', 'dd', 'div', 'dt', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'h7', 'h8', 'li', 'p', 'td', 'th', 'tr'])
    drop_tags_only = set(['a', 'abbr', 'acronym', 'b', 'center', 'dir', 'dl', 'em', 'font', 'form', 'hr', 'i', 'label', 'menu', 'ol', 'pre', 'small', 'span', 'strong', 'sub', 'sup', 'table', 'tbody', 'tfoot', 'thead', 'topic', 'u', 'ul', 'wbr'])
    drop_tags_and_contents = set(['applet', 'area', 'button', 'embed', 'img', 'iframe', 'head', 'input', 'link', 'map', 'meta', 'noscript', 'object', 'option', 'script', 'select', 'spacer', 'style', 'textarea', 'title'])
    layout_tags = set(['div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'h7', 'h8', 'td', 'th', 'tr'])
    is_open_tag = re.compile('^<[^/][^>]+>$').search
    is_close_tag = re.compile('^</[^>]+>$').search
    ignored_paragraphs = set(['del.icio.us', 'digg', 'email', 'e-mail editor', 'e-mail story', 'no comments', 'print', 'print article', 'printer-friendly', 'printer version', 'reprints'])

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

    for element in tree.getiterator():
        if element.tag in block_tags:
            if element.tag in layout_tags:
                element.text = '\n<%s>\n%s\n' % (element.tag, (element.text or ''))
                element.tail = '\n</%s>\n%s\n' % (element.tag, (element.tail or ''))
            element.drop_tag()

    try:
        tree.body
    except IndexError:
        # In some cases, the article is missing a <body> tag, and tree.body
        # will result in an IndexError. Just skip these.
        return []

    new_html = etree.tostring(tree.body, method='html')
    new_html = convert_entities(new_html)
    lines = re.split(r'\s*\n+\s*', new_html.strip())
    result = []
    sections = []
    for line in lines:
        if is_open_tag(line):
            result.append([])
        elif is_close_tag(line):
            last_bit = result.pop()
            if len(last_bit) >= MIN_NUM_PARAGRAPHS:
                sections.append(last_bit)
        else: # It's text, not a tag.
            try:
                result[-1].append(line)
            except IndexError: # No tags seen yet.
                result.append([line])

    # Cut out the sections that don't contain enough punctuated sentences.
    final_sections = []
    for section in sections:
        count = 0
        to_delete = []
        for i, paragraph in enumerate(section):
            if paragraph.lower() in ignored_paragraphs:
                to_delete.append(i)
            elif is_punctuated(paragraph) and len(paragraph) >= MIN_CHARS_IN_PARAGRAPH:
                count += 1
        percent_punctuated = decimal.Decimal(count) / decimal.Decimal(len(section))
        if count >= NUM_PARAGRAPHS_SAFE_GUESS or (count >= MIN_NUM_PUNCTUATED and percent_punctuated >= MIN_PERCENTAGE_PUNCTUATED):
            for i in reversed(to_delete): # Delete in reverse so that index order is preserved.
                del section[i]
            final_sections.append(section)
    return final_sections

def article_text(tree):
    """
    Simple wrapper around article_text_sections() that "flattens" sections into
    a single section.
    """
    result = []
    for section in article_text_sections(tree):
        result.extend(section)
    return result

if __name__ == "__main__":
    from ebdata.retrieval import UnicodeRetriever
    from ebdata.textmining.treeutils import make_tree
    import sys
    html = UnicodeRetriever().get_html(sys.argv[1])
    lines = article_text(make_tree(html))
    print lines
