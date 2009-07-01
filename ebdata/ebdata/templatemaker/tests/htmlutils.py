from ebdata.templatemaker.htmlutils import percent_linked_text, printer_friendly_link
from ebdata.templatemaker.htmlutils import remove_empty_tags, brs_to_paragraphs
from ebdata.textmining.treeutils import preprocess
from lxml.html import document_fromstring
from lxml import etree
import unittest

class PercentLinkedTextTestCase(unittest.TestCase):
    def assertPercentLinked(self, html, expected):
        """
        Asserts that the given HTML string has the expected percentage of
        linked text.
        """
        tree = document_fromstring(html)
        self.assertEqual(percent_linked_text(tree), expected)

    def test_basic1(self):
        self.assertPercentLinked('<p><a href=".">Test</a></p>', 1.0)

    def test_basic2(self):
        self.assertPercentLinked('<p>Test</p>', 0.0)

    def test_basic3(self):
        self.assertPercentLinked('<p><a href=".">Test</a>Test</p>', 0.5)

    def test_basic4(self):
        self.assertPercentLinked('<p><a href=".">Test test</a>Test test</p>', 0.5)

    def test_basic5(self):
        self.assertPercentLinked('<p><a href=".">Test</a></p><p>Test2</p>', 4.0 / 9.0)

    def test_empty(self):
        self.assertPercentLinked('<p></p>', 0.0)

class PrinterFriendlyLinkTestCase(unittest.TestCase):
    def assertPrinterFriendlyLink(self, html, expected):
        """
        Asserts that the given HTML string has the expected printer-friendly
        URL.
        """
        tree = document_fromstring(html)
        self.assertEqual(printer_friendly_link(tree), expected)

    def test_empty1(self):
        self.assertPrinterFriendlyLink('<p></p>', None)

    def test_empty2(self):
        self.assertPrinterFriendlyLink('<p><a></a></p>', None)

    def test_empty3(self):
        self.assertPrinterFriendlyLink('<p><a href=""></a></p>', None)

    def test_empty4(self):
        self.assertPrinterFriendlyLink('<p><a href="/1/print/"></a></p>', None)

    def test_noprint1(self):
        self.assertPrinterFriendlyLink('<p><a href="">print</a></p>', None)

    def test_noprint2(self):
        self.assertPrinterFriendlyLink('<p><a href="foo">print</a></p>', None)

    def test_noprint3(self):
        self.assertPrinterFriendlyLink('<p><a href="print"></a></p>', None)

    def test_noprint4(self):
        self.assertPrinterFriendlyLink('<p><a href="print">foo</a></p>', None)

    def test_hit1(self):
        self.assertPrinterFriendlyLink('<p><a href="/1/print/">print</a></p>', '/1/print/')

    def test_hit2(self):
        self.assertPrinterFriendlyLink('<p><a href="/1/print/">printer</a></p>', '/1/print/')

    def test_hit3(self):
        self.assertPrinterFriendlyLink('<p><a href="/1/print/">printer-friendly</a></p>', '/1/print/')

    def test_hit4(self):
        self.assertPrinterFriendlyLink('<p><a href="/1/print/">this link happens to include the word print</a></p>', '/1/print/')

    def test_hit5(self):
        self.assertPrinterFriendlyLink('<p><a href="/1/printer/">printer-friendly</a></p>', '/1/printer/')

    def test_hit_with_child(self):
        self.assertPrinterFriendlyLink('<a href="/mediakit/print/"><img/>Print</a>', '/mediakit/print/')

    def test_case_insensitive1(self):
        self.assertPrinterFriendlyLink('<p><a href="/1/PRINT/">A PRINT VERSION</a></p>', '/1/PRINT/')

    def test_case_insensitive2(self):
        self.assertPrinterFriendlyLink('<p><a href="/1/Print/">Print version</a></p>', '/1/Print/')

    def test_multiple_links1(self):
        self.assertPrinterFriendlyLink('<a href="/1/print/">print 1</a><a href="/2/print/">print 2</a>', '/1/print/')

    def test_multiple_links_first_javascript(self):
        self.assertPrinterFriendlyLink('<a href="javascript:print();">print</a> <p><a href="/1/print/">print</a></p>', '/1/print/')

    def test_javascript1(self):
        self.assertPrinterFriendlyLink('<a href="javascript:print();">print</a>', None)

    def test_javascript2(self):
        self.assertPrinterFriendlyLink('<a href=" javascript:print(); "> print </a>', None)

    def test_false_positive_print_edition1(self):
        self.assertPrinterFriendlyLink('<a href="/news/printedition/front/">Print Edition</a>', None)

    def test_false_positive_print_edition2(self):
        self.assertPrinterFriendlyLink('<a href="/news/printedition/front/">Print-Edition</a>', None)

    def test_false_positive_print_edition3(self):
        self.assertPrinterFriendlyLink('<a href="/news/printedition/front/">Print edition</a>', None)

    def test_false_positive_print_edition4(self):
        self.assertPrinterFriendlyLink('<a href="/1/print/">Print edition</a>', None)

    def test_false_positive_reprint1(self):
        self.assertPrinterFriendlyLink('<a href="/services/site/la-reprint-request-splash,0,6731163.htmlstory">Reprint</a>', None)

    def test_false_positive_reprint2(self):
        self.assertPrinterFriendlyLink('<a href="/reprints">Reprints</a>', None)

    def test_false_positive_print_advertising1(self):
        self.assertPrinterFriendlyLink('<a href="/mediakit/print/">Print advertising</a>', None)

    def test_false_positive_print_advertising2(self):
        self.assertPrinterFriendlyLink('<a href="/mediakit/print/">Print ads</a>', None)

class PreprocessTestCase(unittest.TestCase):
    def assertPreprocess(self, html, expected, **kwargs):
        # The test strings should *not* have <html> and <body> tags, for the
        # sake of brevity.
        html = '<html><body>%s</body></html>' % html
        expected = '<html><body>%s</body></html>' % expected

        result_tree = preprocess(document_fromstring(html), **kwargs)
        got = etree.tostring(result_tree)
        self.assertEqual(got, expected)

    def test_comments1(self):
        self.assertPreprocess(
            '<h1><!-- test --></h1>',
            '<h1/>'
        )

    def test_comments2(self):
        self.assertPreprocess(
            '<h1>A<!-- test --></h1>',
            '<h1>A</h1>'
        )

    def test_comments3(self):
        self.assertPreprocess(
            '<h1><!-- test -->B</h1>',
            '<h1>B</h1>'
        )

    def test_comments4(self):
        self.assertPreprocess(
            '<h1>A<!-- test -->B</h1>',
            '<h1>AB</h1>'
        )

    def test_comments5(self):
        self.assertPreprocess(
            '<h1>A <!-- test -->B</h1>',
            '<h1>A B</h1>'
        )

    def test_comments6(self):
        self.assertPreprocess(
            '<h1><!-- <p> </p> --></h1>',
            '<h1/>'
        )

    def test_dropstyle1(self):
        self.assertPreprocess(
            '<style type="text/css">p { font-weight: 10px; }</style><p>Hello</p>',
            '<p>Hello</p>'
        )

    def test_dropstyle2(self):
        self.assertPreprocess(
            '<STYLE type="text/css">p { font-weight: 10px; }</STYLE><p>Hello</p>',
            '<p>Hello</p>'
        )

    def test_droplink1(self):
        self.assertPreprocess(
            '<link rel="stylesheet" /><p>Hello</p>',
            '<p>Hello</p>'
        )

    def test_dropmeta1(self):
        self.assertPreprocess(
            '<meta  /><p>Hello</p>',
            '<p>Hello</p>'
        )

    def test_dropscript1(self):
        self.assertPreprocess(
            '<script type="text/javascript">alert("hello");</script><p>Hello</p>',
            '<p>Hello</p>'
        )

    def test_dropnoscript1(self):
        self.assertPreprocess(
            '<noscript>Turn on JavaScript.</noscript><p>Hello</p>',
            '<p>Hello</p>'
        )

    def test_drop_tags1_control(self):
        self.assertPreprocess(
            '<b>Hello there</b>',
            '<b>Hello there</b>'
        )

    def test_drop_tags1(self):
        self.assertPreprocess(
            '<b>Hello there</b>',
            'Hello there',
            drop_tags=('b',),
        )

    def test_drop_tags_with_defaults(self):
        self.assertPreprocess(
            '<b>Hello there</b><style type="text/css">div { border: 1px; }</style>',
            'Hello there',
            drop_tags=('b',),
        )

    def test_drop_trees1_control(self):
        self.assertPreprocess(
            'That is <b>cool</b>',
            'That is <b>cool</b>'
        )

    def test_drop_trees1(self):
        self.assertPreprocess(
            'That is <b>cool</b>',
            'That is ',
            drop_trees=('b',)
        )

    def test_dropattrs1_control(self):
        self.assertPreprocess(
            '<div id="head">Hi</div>',
            '<div id="head">Hi</div>'
        )

    def test_dropattrs1(self):
        self.assertPreprocess(
            '<div id="head">Hi</div>',
            '<div>Hi</div>',
            drop_attrs=('id',)
        )

class RemoveEmptyTagsTestCase(unittest.TestCase):
    def assertTagsRemoved(self, html, expected, ignore_tags):
        """
        Asserts that removing all empty tags in `html` (except `ignore_tags`)
        will result in the string `expected`.
        """
        html = '<html><body>%s</body></html>' % html
        expected = '<html><body>%s</body></html>' % expected

        tree = document_fromstring(html)
        remove_empty_tags(tree, ignore_tags)
        self.assertEqual(etree.tostring(tree, method='html'), expected)

    def test_basic1(self):
        self.assertTagsRemoved('<p></p>', '', ())

    def test_basic2(self):
        self.assertTagsRemoved('<div></div>', '', ())

    def test_basic3(self):
        self.assertTagsRemoved('<br>', '', ())

    def test_basic4(self):
        self.assertTagsRemoved('a<p></p>b', 'ab', ())

    def test_basic5(self):
        self.assertTagsRemoved(' <p></p> ', '  ', ())

    def test_nested1(self):
        self.assertTagsRemoved('<div><p></p></div>', '', ())

    def test_nested2(self):
        self.assertTagsRemoved('<div><div><p></p></div></div>', '', ())

    def test_nested3(self):
        self.assertTagsRemoved('<div><div><p><br></p></div></div>', '', ())

    def test_nested4(self):
        self.assertTagsRemoved('<p><br></p>', '', ())

    def test_nested5(self):
        self.assertTagsRemoved('<div><p></p><p>Hey<span></span></p></div>', '<div><p>Hey</p></div>', ())

    def test_ignore1(self):
        self.assertTagsRemoved('<div></div>', '', ('br',))

    def test_ignore2(self):
        self.assertTagsRemoved('<br>', '<br>', ('br',))

    def test_ignore3(self):
        self.assertTagsRemoved('<p><br></p>', '<p><br></p>', ('br',))

    def test_wacky(self):
        self.assertTagsRemoved('<div><br/></div><br/>', '', ())

class BreakToParagraphTestCase(unittest.TestCase):
    def assertConverted(self, html, expected):
        html = '<html><body>%s</body></html>' % html
        expected = '<html><body>%s</body></html>' % expected

        tree = document_fromstring(html)
        tree = brs_to_paragraphs(tree)
        self.assertEqual(etree.tostring(tree, method='html'), expected)

    def test_basic1(self):
        self.assertConverted('<h1>Headline</h1>', '<h1>Headline</h1>')

    def test_basic2(self):
        self.assertConverted('<h1>Headline <span>Yo</span></h1>', '<h1>Headline <span>Yo</span></h1>')

    def test_basic3(self):
        self.assertConverted('First line<br>Second line', '<p>First line</p><p>Second line</p>')

    def test_basic4(self):
        self.assertConverted('<div>Hello there</div>', '<div>Hello there</div>')

    def test_empty(self):
        self.assertConverted('', '')

    def test_block_trailing_text(self):
        self.assertConverted('<div><h1>Headline</h1>Paragraph 1<br>Paragraph2</div>',
                             '<div><h1>Headline</h1><p>Paragraph 1</p><p>Paragraph2</p></div>')

    def test_initial_text(self):
        # make sure elements whose contents start with text get that text put into a <p>
        self.assertConverted('<div>Paragraph 1<br>Paragraph2</div>',
                             '<div><p>Paragraph 1</p><p>Paragraph2</p></div>')

    def test_consecutive_brs(self):
        # <br> tags with no intervening text shouldn't result in empty <p> tags
        self.assertConverted('<div>Paragraph 1<br><br><br>Paragraph 2</div>',
                             '<div><p>Paragraph 1</p><p>Paragraph 2</p></div>')

    def test_inline_links(self):
        # make sure inline <a> tags are kept in the <p> we build
        self.assertConverted('<div>Paragraph <a href="">1</a> is here.<br>Paragraph 2</div>',
                             '<div><p>Paragraph <a href="">1</a> is here.</p><p>Paragraph 2</p></div>')

    def test_trailing_whitespace(self):
        # make sure trailing whitespace doesn't get wrapped in p tags, and that
        # the element preceding the whitespace is handled correctly.
        self.assertConverted('<div><p>Paragraph 1<br>Paragraph2</p></div>   ',
                             '<div><p><p>Paragraph 1</p><p>Paragraph2</p></p></div>')

if __name__ == "__main__":
    unittest.main()
