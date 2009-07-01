from ebdata.templatemaker.clean import strip_template
from lxml import etree
from lxml.html import document_fromstring
import unittest

class StripTemplateTestCase(unittest.TestCase):
    def assertStrips(self, html1, html2, expected, num_removals, check_ids=False):
        """
        Asserts that strip_template(html1, html2) will result in the expected
        HTML string, and that the return value is num_removals.
        """
        # The test strings should *not* have <html> and <body> tags, for the
        # sake of brevity.
        tree1 = document_fromstring('<html><body>%s</body></html>' % html1)
        tree2 = document_fromstring('<html><body>%s</body></html>' % html2)
        expected = '<html><body>%s</body></html>' % expected

        got_removals = strip_template(tree1, tree2, check_ids=check_ids)
        got_tree = etree.tostring(tree1, method='html')
        self.assertEqual(got_tree, expected)
        self.assertEqual(got_removals, num_removals)

    def test_noop(self):
        self.assertStrips(
            '<p>Foo</p>',
            '<div>Bar</div>',
            '<p>Foo</p>',
            0,
        )

    def test_header(self):
        self.assertStrips(
            '<p>Header</p><h1>Headline 1</h1>',
            '<p>Header</p><h1>Headline 2</h1>',
            '<h1>Headline 1</h1>',
            1,
        )

    def test_footer(self):
        self.assertStrips(
            '<h1>Headline 1</h1><p>Footer</p>',
            '<h1>Headline 2</h1><p>Footer</p>',
            '<h1>Headline 1</h1>',
            1,
        )

    def test_header_and_footer(self):
        self.assertStrips(
            '<p>Header</p><h1>Headline 1</h1><p>Footer</p>',
            '<p>Header</p><h1>Headline 2</h1><p>Footer</p>',
            '<h1>Headline 1</h1>',
            2,
        )

    def test_header_same_tag(self):
        self.assertStrips(
            '<p>Header</p><p>Article 1</p>',
            '<p>Header</p><p>Article 2</p>',
            '<p>Article 1</p>',
            1,
        )

    def test_footer_same_tag(self):
        self.assertStrips(
            '<p>Article 1</p><p>Footer</p>',
            '<p>Article 2</p><p>Footer</p>',
            '<p>Article 1</p>',
            1,
        )

    def test_header_and_footer_same_tag(self):
        self.assertStrips(
            '<p>Header</p><p>Article 1</p><p>Footer</p>',
            '<p>Header</p><p>Article 2</p><p>Footer</p>',
            '<p>Article 1</p>',
            2,
        )

    def test_nested_1level(self):
        self.assertStrips(
            '<ul><li>News</li></ul><h1>Headline 1</h1>',
            '<ul><li>News</li></ul><h1>Headline 2</h1>',
            '<h1>Headline 1</h1>',
            2,
        )

    def test_nested_2level(self):
        self.assertStrips(
            '<div id="nav"><ul><li>News</li></ul></div><h1>Headline 1</h1>',
            '<div id="nav"><ul><li>News</li></ul></div><h1>Headline 2</h1>',
            '<h1>Headline 1</h1>',
            3,
        )

    def test_header_tail_same(self):
        self.assertStrips(
            '<p>Header</p> Tail <h1>Headline 1</h1>',
            '<p>Header</p> Tail <h1>Headline 2</h1>',
            '<h1>Headline 1</h1>',
            1,
        )

    def test_header_tail_different(self):
        self.assertStrips(
            '<p>Header</p> Tail1 <h1>Headline 1</h1>',
            '<p>Header</p> Tail2 <h1>Headline 2</h1>',
            ' Tail1 <h1>Headline 1</h1>',
            1,
        )

    def test_footer_head_same(self):
        self.assertStrips(
            '<h1>Headline 1</h1> Head <p>Footer</p>',
            '<h1>Headline 2</h1> Head <p>Footer</p>',
            '<h1>Headline 1</h1>',
            1,
        )

    def test_footer_head_different(self):
        self.assertStrips(
            '<h1>Headline 1</h1> Head1 <p>Footer</p>',
            '<h1>Headline 2</h1> Head2 <p>Footer</p>',
            '<h1>Headline 1</h1> Head1 ',
            1,
        )

    def test_same_tags_different_attributes1(self):
        self.assertStrips(
            '<p style="color: red;">Header</p><h1>Headline 1</h1>',
            '<p                    >Header</p><h1>Headline 2</h1>',
            '<p style="color: red;">Header</p><h1>Headline 1</h1>',
            0,
        )

    def test_same_tags_different_attributes2(self):
        self.assertStrips(
            '<p style="color: red;">Header</p><h1>Headline 1</h1>',
            '<p                    >Header</p><h1>Headline 1</h1>',
            '<p style="color: red;">Header</p>',
            1,
        )

    def test_different_level(self):
        """
        If data is identical but at a different level in the tree,
        strip_template() will not find it.
        """
        self.assertStrips(
            '<div><p>Foo</p><p>Bar</p></div>',
            '<p>Foo</p><p>Bar</p>',
            '<div><p>Foo</p><p>Bar</p></div>',
            0,
        )

    def test_ids_header(self):
        # This would be detected with check_ids=False, but this test makes sure
        # it doesn't break anything to use check_ids=True.
        self.assertStrips(
            '<p id="header">Header</p><h1>Headline 1</h1>',
            '<p id="header">Header</p><h1>Headline 2</h1>',
            '<h1>Headline 1</h1>',
            1,
            check_ids=True,
        )

    def test_ids_footer(self):
        self.assertStrips(
            '<h1>Headline 1</h1><p id="footer">Footer</p>',
            '<h1>Headline 2</h1><p id="footer">Footer</p>',
            '<h1>Headline 1</h1>',
            1,
            check_ids=True,
        )

    def test_ids_header_and_footer(self):
        self.assertStrips(
            '<p id="footer">Header</p><h1>Headline 1</h1><p id="footer">Footer</p>',
            '<p id="footer">Header</p><h1>Headline 2</h1><p id="footer">Footer</p>',
            '<h1>Headline 1</h1>',
            2,
            check_ids=True,
        )

    def test_ids_different_level1(self):
        self.assertStrips(
            '<div><p id="first">Foo</p><p id="second">Bar</p></div>',
            '<p id="first">Foo</p><p id="second">Bar</p>',
            '<div></div>',
            2,
            check_ids=True,
        )

    def test_ids_different_level2(self):
        self.assertStrips(
            '<div><p id="first">Foo</p><p id="second">Bar</p>Tail</div>',
            '<p id="first">Foo</p><p id="second">Bar</p>',
            '<div>Tail</div>',
            2,
            check_ids=True,
        )

    def test_ids_different_level3(self):
        self.assertStrips(
            '<div><p id="first">Foo</p><p id="second">Bar</p>Tail</div>',
            '<p id="first">Foo</p><p id="second">Bar</p>Tail',
            '<div></div>',
            2,
            check_ids=True,
        )

if __name__ == "__main__":
    unittest.main()
