from ebdata.templatemaker.sst import tree_diff, Template, NoMatch
from ebdata.textmining.treeutils import preprocess
from lxml import etree
from lxml.html import document_fromstring
import unittest

class TreeDiffTestCaseAlgorithm1(unittest.TestCase):
    algorithm = 1
    def assertTreeDiff(self, html1, html2, expected):
        """
        Asserts that the given HTML strings will produce a tree_diff of the
        expected HTML string.
        """
        # The test strings should *not* have <html> and <body> tags, for the
        # sake of brevity.
        tree1 = document_fromstring('<html><body>%s</body></html>' % html1)
        tree2 = document_fromstring('<html><body>%s</body></html>' % html2)
        expected = '<html><body>%s</body></html>' % expected

        result_tree = tree_diff(preprocess(tree1), preprocess(tree2), self.algorithm)
        got = etree.tostring(result_tree)
        self.assertEqual(got, expected)

    def test_same1(self):
        self.assertTreeDiff(
            '<h1>test</h1>',
            '<h1>test</h1>',
            '<h1>test</h1>'
        )

    def test_case_insensitive_tags(self):
        self.assertTreeDiff(
            '<h1>test</h1>',
            '<H1>test</H1>',
            '<h1>test</h1>'
        )

    def test_texthole1(self):
        self.assertTreeDiff(
            '<h1>Headline</h1>',
            '<h1>Different</h1>',
            '<h1>TEXT_HOLE</h1>'
        )

    def test_texthole2(self):
        self.assertTreeDiff(
            '<h1>Headline</h1><p>Para</p>',
            '<h1>Different</h1><p>Para</p>',
            '<h1>TEXT_HOLE</h1><p>Para</p>'
        )

    def test_texthole3(self):
        self.assertTreeDiff(
            '<h1>Headline</h1><p>Para</p><p>Final</p>',
            '<h1>Different</h1><p>Para</p><p>Diff</p>',
            '<h1>TEXT_HOLE</h1><p>Para</p><MULTITAG_HOLE/>'
        )

    def test_tailhole1(self):
        self.assertTreeDiff(
            '<p>That was <b>so</b> fun.</p>',
            '<p>That was <b>so</b> boring.</p>',
            '<p>That was <b>so</b>TAIL_HOLE</p>'
        )

    def test_attribhole1(self):
        self.assertTreeDiff(
            '<p id="foo">Hello</p>',
            '<p id="bar">Hello</p>',
            '<p id="ATTRIB_HOLE">Hello</p>'
        )

    def test_attribhole2(self):
        self.assertTreeDiff(
            '<p id="bar" class="1">Hello</p>',
            '<p id="bar" class="2">Hello</p>',
            '<p id="bar" class="ATTRIB_HOLE">Hello</p>'
        )

    def test_attribhole3(self):
        self.assertTreeDiff(
            '<p id="bar">Hello</p>',
            '<p>Hello</p>',
            '<p id="ATTRIB_HOLE">Hello</p>'
        )

    def test_attribhole4(self):
        self.assertTreeDiff(
            '<p>Hello</p>',
            '<p id="bar">Hello</p>',
            '<p id="ATTRIB_HOLE">Hello</p>'
        )

    def test_multitaghole1(self):
        self.assertTreeDiff(
            '<div><p>Yes</p><p>No</p></div>',
            '<div><p>Yes</p><p>No</p><p>Maybe</p></div>',
            '<div><p>Yes</p><p>No</p><MULTITAG_HOLE/></div>'
        )

    def test_multitaghole2(self):
        self.assertTreeDiff(
            '<div>Text <p>Yes</p><p>No</p></div>',
            '<div>Text <p>Yes</p><p>No</p><p>Maybe</p></div>',
            '<div>Text <p>Yes</p><p>No</p><MULTITAG_HOLE/></div>'
        )

    def test_multitaghole3(self):
        self.assertTreeDiff(
            '<div><p>Yes</p><p>No</p> Tail</div>',
            '<div><p>Yes</p><p>No</p><p>Maybe</p> Tail</div>',
            '<div><p>Yes</p><p>No</p>TAIL_HOLE<MULTITAG_HOLE/></div>'
        )

    def test_multitaghole4(self):
        self.assertTreeDiff(
            '<div><p>Yes</p><p>No</p></div>',
            '<div><p>Foo</p><p>Bar</p><p>Maybe</p></div>',
            '<div><MULTITAG_HOLE/></div>'
        )

    def test_multitaghole5(self):
        self.assertTreeDiff(
            '<div><p>Yes</p><p>No</p></div>',
            '<div><p>Yes</p><p>Bar</p><p>Maybe</p></div>',
            '<div><p>Yes</p><MULTITAG_HOLE/></div>'
        )

    def test_multitaghole6(self):
        self.assertTreeDiff(
            '<div><p>Yes</p><p>No</p></div>',
            '<div><p>Yes</p><p id="test">No</p><p>Maybe</p></div>',
            '<div><p>Yes</p><p id="ATTRIB_HOLE">No</p><MULTITAG_HOLE/></div>'
        )

    def test_same_level_p(self): 
        self.assertTreeDiff( 
            '<p>First 1</p>', 
            '<p>Second 1</p><p>Second 2</p>', 
            '<MULTITAG_HOLE/>' 
        ) 

    def test_same_level_h1(self): 
        self.assertTreeDiff( 
            '<h1>First 1</h1>', 
            '<h1>Second 1</h1><p>Second 2</p>', 
            '<h1>TEXT_HOLE</h1><MULTITAG_HOLE/>'
        ) 

    def test_same_level_h2(self): 
        self.assertTreeDiff( 
            '<h2>First 1</h2>', 
            '<h2>Second 1</h2><p>Second 2</p>', 
            '<h2>TEXT_HOLE</h2><MULTITAG_HOLE/>'
        ) 

    def test_same_level_h3(self): 
        self.assertTreeDiff( 
            '<h3>First 1</h3>', 
            '<h3>Second 1</h3><p>Second 2</p>', 
            '<h3>TEXT_HOLE</h3><MULTITAG_HOLE/>'
        ) 

    def test_same_level_h4(self): 
        self.assertTreeDiff( 
            '<h4>First 1</h4>', 
            '<h4>Second 1</h4><p>Second 2</p>', 
            '<h4>TEXT_HOLE</h4><MULTITAG_HOLE/>'
        ) 

    def test_same_level_h5(self): 
        self.assertTreeDiff( 
            '<h5>First 1</h5>', 
            '<h5>Second 1</h5><p>Second 2</p>', 
            '<h5>TEXT_HOLE</h5><MULTITAG_HOLE/>'
        ) 

    def test_same_level_h6(self): 
        self.assertTreeDiff( 
            '<h6>First 1</h6>', 
            '<h6>Second 1</h6><p>Second 2</p>', 
            '<h6>TEXT_HOLE</h6><MULTITAG_HOLE/>'
        ) 

    def test_same_level_a(self): 
        self.assertTreeDiff( 
            '<a>First 1</a>', 
            '<a>Second 1</a><p>Second 2</p>', 
            '<a>TEXT_HOLE</a><MULTITAG_HOLE/>'
        ) 

    def test_same_level1(self):
        self.assertTreeDiff(
            '<h1>Man seen</h1><p>By John Smith</p><p>A man was seen today.</p>',
            '<h1>Bird seen</h1><p>By John Smith</p><p>A bird was seen yesterday.</p>',
            '<h1>TEXT_HOLE</h1><p>By John Smith</p><MULTITAG_HOLE/>'
        )

    def test_same_level2(self):
        self.assertTreeDiff(
            '<p>By John Smith</p><h1>Man seen</h1><p>A man was seen today.</p>',
            '<p>By John Smith</p><h1>Bird seen</h1><p>A bird was seen yesterday.</p>',
            '<p>By John Smith</p><h1>TEXT_HOLE</h1><MULTITAG_HOLE/>'
        )

    def test_same_level3(self):
        self.assertTreeDiff(
            '<p>By John Smith</p><h1>Man seen</h1><p>A man was seen today.</p><p>The end.</p>',
            '<p>By John Smith</p><h1>Bird seen</h1><p>A bird was seen yesterday.</p><p>The end.</p>',
            '<p>By John Smith</p><h1>TEXT_HOLE</h1><MULTITAG_HOLE/><p>The end.</p>'
        )

    def test_confusing(self):
        # Note: The "~" are in here to make this more understandable by vertical alignment.
        self.assertTreeDiff(
            '<ul>~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~<li/>\n\t\t<li/>\n\t\t<li class="current"></li>\n\t\t<li/>\n\t</ul>'.replace('~', ''),
            '<ul><li class="current"></li>\n\t\t<li/>\n\t\t<li/>\n\t\t~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~<li/>\n\t</ul>'.replace('~', ''),
            '<ul><MULTITAG_HOLE/>~~~~~~~~~~~~~~~<li/>\n\t\t<li/>\n\t\t<MULTITAG_HOLE/>~~~~~~~~~~~~~~~<li/>\n\t</ul>'.replace('~', ''),
        )

    def test_mixed1(self):
        self.assertTreeDiff(
            '<h1>Headline</h1><p>This thing</p><br/><div id="footer">Copyright 2006</div>',
            '<h1>Headline 2</h1><p id="first">This thing</p><br/><div id="footer">Copyright 2007</div>',
            '<h1>TEXT_HOLE</h1><p id="ATTRIB_HOLE">This thing</p><MULTITAG_HOLE/>'
        )

    def test_comments_ignored1(self):
        self.assertTreeDiff(
            '<h1><!-- comment --></h1>',
            '<h1></h1>',
            '<h1/>',
        )

    def test_comments_ignored2(self):
        self.assertTreeDiff(
            '<h1>A<!-- comment --></h1>',
            '<h1>A</h1>',
            '<h1>A</h1>',
        )

    def test_comments_ignored3(self):
        self.assertTreeDiff(
            '<h1><!-- comment -->A</h1>',
            '<h1>A</h1>',
            '<h1>A</h1>',
        )

    def test_comments_ignored4(self):
        self.assertTreeDiff(
            '<h1>A<!-- comment -->B</h1>',
            '<h1>AB</h1>',
            '<h1>AB</h1>',
        )

    def test_comments_ignored5(self):
        self.assertTreeDiff(
            '<h1>Title <!-- foo -->here</h1>',
            '<h1>Title here</h1>',
            '<h1>Title here</h1>',
        )

    def test_comments_ignored6(self):
        self.assertTreeDiff(
            '<h1>Title <!-- foo -->here</h1><!--<p>nothing</p>--><p><!--foo-->Paragraph here</p>',
            '<h1>Title here</h1><p>Paragraph here</p>',
            '<h1>Title here</h1><p>Paragraph here</p>',
        )

class TreeDiffTestCaseAlgorithm2(TreeDiffTestCaseAlgorithm1):
    """
    Like TreeDiffTestCaseAlgorithm1, but it uses algorithm 2. As such, it only
    needs to implement the methods whose outcome is different between the two
    algorithms.
    """
    algorithm = 2

    def test_texthole3(self):
        self.assertTreeDiff(
            '<h1>Headline</h1><p>Para</p><p>Final</p>',
            '<h1>Different</h1><p>Para</p><p>Diff</p>',
            '<h1>TEXT_HOLE</h1><p>Para</p><p>TEXT_HOLE</p>'
        )

    def test_multitaghole1(self):
        self.assertTreeDiff(
            '<div><p>Yes</p><p>No</p></div>',
            '<div><p>Yes</p><p>No</p><p>Maybe</p></div>',
            '<div><MULTITAG_HOLE/></div>'
        )

    def test_multitaghole2(self):
        self.assertTreeDiff(
            '<div>Text <p>Yes</p><p>No</p></div>',
            '<div>Text <p>Yes</p><p>No</p><p>Maybe</p></div>',
            '<div>Text <MULTITAG_HOLE/></div>'
        )

    def test_multitaghole3(self):
        self.assertTreeDiff(
            '<div><p>Yes</p><p>No</p> Tail</div>',
            '<div><p>Yes</p><p>No</p><p>Maybe</p> Tail</div>',
            '<div><MULTITAG_HOLE/></div>'
        )

    def test_multitaghole5(self):
        self.assertTreeDiff(
            '<div><p>Yes</p><p>No</p></div>',
            '<div><p>Yes</p><p>Bar</p><p>Maybe</p></div>',
            '<div><MULTITAG_HOLE/></div>'
        )

    def test_multitaghole6(self):
        self.assertTreeDiff(
            '<div><p>Yes</p><p>No</p></div>',
            '<div><p>Yes</p><p id="test">No</p><p>Maybe</p></div>',
            '<div><MULTITAG_HOLE/></div>'
        )
    def test_same_level_h1(self): 
        self.assertTreeDiff( 
            '<h1>First 1</h1>', 
            '<h1>Second 1</h1><p>Second 2</p>', 
            '<MULTITAG_HOLE/>'
        ) 

    def test_same_level_h2(self): 
        self.assertTreeDiff( 
            '<h2>First 1</h2>', 
            '<h2>Second 1</h2><p>Second 2</p>', 
            '<MULTITAG_HOLE/>'
        ) 

    def test_same_level_h3(self): 
        self.assertTreeDiff( 
            '<h3>First 1</h3>', 
            '<h3>Second 1</h3><p>Second 2</p>', 
            '<MULTITAG_HOLE/>'
        ) 

    def test_same_level_h4(self): 
        self.assertTreeDiff( 
            '<h4>First 1</h4>', 
            '<h4>Second 1</h4><p>Second 2</p>', 
            '<MULTITAG_HOLE/>'
        ) 

    def test_same_level_h5(self): 
        self.assertTreeDiff( 
            '<h5>First 1</h5>', 
            '<h5>Second 1</h5><p>Second 2</p>', 
            '<MULTITAG_HOLE/>'
        ) 

    def test_same_level_h6(self): 
        self.assertTreeDiff( 
            '<h6>First 1</h6>', 
            '<h6>Second 1</h6><p>Second 2</p>', 
            '<MULTITAG_HOLE/>'
        ) 

    def test_same_level_a(self): 
        self.assertTreeDiff( 
            '<a>First 1</a>', 
            '<a>Second 1</a><p>Second 2</p>', 
            '<MULTITAG_HOLE/>'
        ) 

    def test_same_level1(self):
        self.assertTreeDiff(
            '<h1>Man seen</h1><p>By John Smith</p><p>A man was seen today.</p>',
            '<h1>Bird seen</h1><p>By John Smith</p><p>A bird was seen yesterday.</p>',
            '<h1>TEXT_HOLE</h1><p>By John Smith</p><p>TEXT_HOLE</p>'
        )

    def test_same_level2(self):
        self.assertTreeDiff(
            '<p>By John Smith</p><h1>Man seen</h1><p>A man was seen today.</p>',
            '<p>By John Smith</p><h1>Bird seen</h1><p>A bird was seen yesterday.</p>',
            '<p>By John Smith</p><h1>TEXT_HOLE</h1><p>TEXT_HOLE</p>'
        )

    def test_same_level3(self):
        self.assertTreeDiff(
            '<p>By John Smith</p><h1>Man seen</h1><p>A man was seen today.</p><p>The end.</p>',
            '<p>By John Smith</p><h1>Bird seen</h1><p>A bird was seen yesterday.</p><p>The end.</p>',
            '<p>By John Smith</p><h1>TEXT_HOLE</h1><p>TEXT_HOLE</p><p>The end.</p>'
        )

    def test_confusing(self):
        # Note: The "~" are in here to make this more understandable by vertical alignment.
        self.assertTreeDiff(
            '<ul>~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~<li/>\n\t\t<li/>\n\t\t<li class="current"></li>\n\t\t<li/>\n\t</ul>'.replace('~', ''),
            '<ul><li class="current"></li>\n\t\t<li/>\n\t\t<li/>\n\t\t~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~<li/>\n\t</ul>'.replace('~', ''),
            '<ul><li class="ATTRIB_HOLE"/>\n\t\t<li/>\n\t\t<li class="ATTRIB_HOLE"/>\n\t\t<li/>\n\t</ul>'.replace('~', ''),
        )

    def test_mixed1(self):
        self.assertTreeDiff(
            '<h1>Headline</h1><p>This thing</p><br/><div id="footer">Copyright 2006</div>',
            '<h1>Headline 2</h1><p id="first">This thing</p><br/><div id="footer">Copyright 2007</div>',
            '<h1>TEXT_HOLE</h1><p id="ATTRIB_HOLE">This thing</p><br/><div id="footer">TEXT_HOLE</div>'
        )

class TemplateExtractionTestCaseAlgorithm1(unittest.TestCase):
    algorithm = 1
    def assertExtracts(self, html_list, expected_data_list):
        """
        Creates a Template from every string in html_list, then extracts the
        data from each of those strings, asserting that the data matches
        expected_data_list.
        """
        t = Template(algorithm=self.algorithm)
        for html in html_list:
            t.learn(html)
        got_data_list = []
        for html in html_list:
            got_data_list.append(t.extract(html))
        self.assertEqual(got_data_list, expected_data_list)

    def assertNoMatch(self, html_list, sample):
        """
        Creates a Template from every string in html_list, then asserts that
        t.extract(sample) raises NoMatch.
        """
        t = Template()
        for html in html_list:
            t.learn(html)
        self.assertRaises(NoMatch, t.extract, sample)

    def test_same1(self):
        self.assertExtracts(
            ['<h1>test</h1>', '<h1>test</h1>'],
            [[], []],
        )

    def test_case_insensitive_tags(self):
        self.assertExtracts(
            ['<h1>test</h1>', '<H1>test</H1>'],
            [[], []],
        )

    def test_texthole1(self):
        self.assertExtracts(
            ['<h1>Headline</h1>', '<h1>Different</h1>'],
            [[{'type': 'text', 'value': 'Headline', 'tag': 'h1'}],
             [{'type': 'text', 'value': 'Different', 'tag': 'h1'}]]
        )

    def test_texthole2(self):
        self.assertExtracts(
            ['<h1>Headline</h1><p>Para</p>', '<h1>Different</h1><p>Para</p>'],
            [[{'type': 'text', 'value': 'Headline', 'tag': 'h1'}],
             [{'type': 'text', 'value': 'Different', 'tag': 'h1'}]]
        )

    def test_texthole3(self):
        self.assertExtracts(
            ['<h1>Headline</h1><p>Para</p><p>Final</p>', '<h1>Different</h1><p>Para</p><p>Diff</p>'],
            [[{'type': 'text', 'value': 'Headline', 'tag': 'h1'}, {'type': 'multitag', 'value': '<p>Final</p>', 'tag': None}],
             [{'type': 'text', 'value': 'Different', 'tag': 'h1'}, {'type': 'multitag', 'value': '<p>Diff</p>', 'tag': None}]]
        )

    def test_tailhole1(self):
        self.assertExtracts(
            ['<p>That was <b>so</b> fun.</p>', '<p>That was <b>so</b> boring.</p>'],
            [[{'type': 'tail', 'value': ' fun.', 'tag': 'p'}],
             [{'type': 'tail', 'value': ' boring.', 'tag': 'p'}]]
        )

    def test_tailhole2(self):
        self.assertExtracts(
            ['<p>That was <em><b>so</b></em> fun.</p>', '<p>That was <em><b>so</b></em> boring.</p>'],
            [[{'type': 'tail', 'value': ' fun.', 'tag': 'p'}],
             [{'type': 'tail', 'value': ' boring.', 'tag': 'p'}]]
        )

    def test_attribhole1(self):
        self.assertExtracts(
            ['<p id="foo">Hello</p>', '<p id="bar">Hello</p>'],
            [[{'type': 'attrib', 'value': 'foo', 'tag': 'p'}],
             [{'type': 'attrib', 'value': 'bar', 'tag': 'p'}]]
        )

    def test_attribhole2(self):
        self.assertExtracts(
            ['<p id="bar" class="1">Hello</p>', '<p id="bar" class="2">Hello</p>'],
            [[{'type': 'attrib', 'value': '1', 'tag': 'p'}],
             [{'type': 'attrib', 'value': '2', 'tag': 'p'}]]
        )

    def test_attribhole3(self):
        self.assertExtracts(
            ['<p id="bar">Hello</p>', '<p>Hello</p>'],
            [[{'type': 'attrib', 'value': 'bar', 'tag': 'p'}],
             [{'type': 'attrib', 'value': '', 'tag': 'p'}]]
        )

    def test_attribhole4(self):
        self.assertExtracts(
            ['<p>Hello</p>', '<p id="bar">Hello</p>'],
            [[{'type': 'attrib', 'value': '', 'tag': 'p'}],
             [{'type': 'attrib', 'value': 'bar', 'tag': 'p'}]]
        )

    def test_attribhole5(self):
        self.assertExtracts(
            ['<p class="klass" id="eyedee">Hello</p>', '<p id="eyedee" class="klass">Hello</p>'],
            [[], []]
        )

    def test_attribhole6(self):
        self.assertExtracts(
            ['<p class="klass" id="eyedee">Hello</p>', '<p id="eyedee2" class="klass2">Hello</p>'],
            [[{'type': 'attrib', 'value': 'klass', 'tag': 'p'}, {'type': 'attrib', 'value': 'eyedee', 'tag': 'p'}],
             [{'type': 'attrib', 'value': 'klass2', 'tag': 'p'}, {'type': 'attrib', 'value': 'eyedee2', 'tag': 'p'}]]
        )

    def test_attribhole7(self):
        self.assertExtracts(
            ['<p class="klass" id="eyedee">Hello</p>', '<p id="eyedee2" class="klass2" newatt="on">Hello</p>'],
            [[{'type': 'attrib', 'value': 'klass', 'tag': 'p'}, {'type': 'attrib', 'value': 'eyedee', 'tag': 'p'}, {'type': 'attrib', 'value': '', 'tag': 'p'}],
             [{'type': 'attrib', 'value': 'klass2', 'tag': 'p'}, {'type': 'attrib', 'value': 'eyedee2', 'tag': 'p'}, {'type': 'attrib', 'value': 'on', 'tag': 'p'}]]
        )

    def test_multitaghole1(self):
        self.assertExtracts(
            ['<div><p>Yes</p><p>No</p></div>', '<div><p>Yes</p><p>No</p><p>Maybe</p></div>'],
            [[{'type': 'multitag', 'value': '', 'tag': None}],
             [{'type': 'multitag', 'value': '<p>Maybe</p>', 'tag': None}]]
        )

    def test_multitaghole2(self):
        self.assertExtracts(
            ['<div>Text <p>Yes</p><p>No</p></div>', '<div>Text <p>Yes</p><p>No</p><p>Maybe</p></div>'],
            [[{'type': 'multitag', 'value': '', 'tag': None}],
             [{'type': 'multitag', 'value': '<p>Maybe</p>', 'tag': None}]]
        )

    def test_multitaghole3(self):
        self.assertExtracts(
            ['<div><p>Yes</p><p>No</p> Tail</div>',
             '<div><p>Yes</p><p>No</p><p>Maybe</p> Tail</div>'],
            [[{'type': 'multitag', 'value': '', 'tag': None}],
             [{'type': 'multitag', 'value': '<p>Maybe</p>', 'tag': None}]]
        )

    def test_multitaghole4(self):
        self.assertExtracts(
            ['<div><p>Yes</p><p>No</p></div>', '<div><p>Foo</p><p>Bar</p><p>Maybe</p></div>'],
            [[{'type': 'multitag', 'value': '<p>Yes</p><p>No</p>', 'tag': None}],
             [{'type': 'multitag', 'value': '<p>Foo</p><p>Bar</p><p>Maybe</p>', 'tag': None}]]
        )

    def test_multitaghole5(self):
        self.assertExtracts(
            ['<div><p>Yes</p><p>No</p></div>', '<div><p>Yes</p><p>Bar</p><p>Maybe</p></div>'],
            [[{'tag': None, 'type': 'multitag', 'value': '<p>No</p>'}],
             [{'tag': None, 'type': 'multitag', 'value': '<p>Bar</p><p>Maybe</p>'}]]
        )

    def test_multitaghole6(self):
        self.assertExtracts(
            ['<div><p>Yes</p><p>No</p></div>', '<div><p>Yes</p><p id="test">No</p><p>Maybe</p></div>'],
            [[{'tag': 'p', 'type': 'attrib', 'value': ''}, {'tag': None, 'type': 'multitag', 'value': ''}],
             [{'tag': 'p', 'type': 'attrib', 'value': 'test'}, {'tag': None, 'type': 'multitag', 'value': '<p>Maybe</p>'}]]
        )

    def test_same_level1(self):
        self.assertExtracts(
            ['<h1>Man seen</h1><p>By John Smith</p><p>A man was seen today.</p>',
             '<h1>Bird seen</h1><p>By John Smith</p><p>A bird was seen yesterday.</p>'],
            [[{'tag': 'h1', 'type': 'text', 'value': 'Man seen'}, {'tag': None, 'type': 'multitag', 'value': '<p>A man was seen today.</p>'}],
             [{'tag': 'h1', 'type': 'text', 'value': 'Bird seen'}, {'tag': None, 'type': 'multitag', 'value': '<p>A bird was seen yesterday.</p>'}]]
        )

    def test_same_level2(self):
        self.assertExtracts(
            ['<p>By John Smith</p><h1>Man seen</h1><p>A man was seen today.</p>',
             '<p>By John Smith</p><h1>Bird seen</h1><p>A bird was seen yesterday.</p>'],
            [[{'tag': 'h1', 'type': 'text', 'value': 'Man seen'}, {'tag': None, 'type': 'multitag', 'value': '<p>A man was seen today.</p>'}],
             [{'tag': 'h1', 'type': 'text', 'value': 'Bird seen'}, {'tag': None, 'type': 'multitag', 'value': '<p>A bird was seen yesterday.</p>'}]]
        )

    def test_same_level3(self):
        self.assertExtracts(
            ['<p>By John Smith</p><h1>Man seen</h1><p>A man was seen today.</p><p>The end.</p>',
             '<p>By John Smith</p><h1>Bird seen</h1><p>A bird was seen yesterday.</p><p>The end.</p>'],
            [[{'tag': 'h1', 'type': 'text', 'value': 'Man seen'}, {'tag': None, 'type': 'multitag', 'value': '<p>A man was seen today.</p>'}],
             [{'tag': 'h1', 'type': 'text', 'value': 'Bird seen'}, {'tag': None, 'type': 'multitag', 'value': '<p>A bird was seen yesterday.</p>'}]]
        )

    def test_confusing1(self):
        self.assertExtracts(
            ['<ul>\n\t\t<li></li>\n\t\t<li></li>\n\t\t<li class="current"></li>\n\t\t<li></li>\n\t</ul>',
             '<ul>\n\t\t<li class="current"></li>\n\t\t<li></li>\n\t\t<li></li>\n\t\t<li></li>\n\t</ul>',
             '<ul>\n\t\t<li></li>\n\t\t<li class="current"></li>\n\t\t<li></li>\n\t\t<li></li>\n\t</ul>'],
            [[{'tag': None, 'type': 'multitag', 'value': ''},
              {'tag': None, 'type': 'multitag', 'value': ''},
              {'tag': None, 'type': 'multitag', 'value': '<li class="current">\n\t\t'}],
             [{'tag': None, 'type': 'multitag', 'value': '<li class="current">\n\t\t'},
              {'tag': None, 'type': 'multitag', 'value': ''},
              {'tag': None, 'type': 'multitag', 'value': ''}],
             [{'tag': None, 'type': 'multitag', 'value': ''},
              {'tag': None, 'type': 'multitag', 'value': '<li class="current">\n\t\t'},
              {'tag': None, 'type': 'multitag', 'value': ''}]]
        )

    def test_confusing2(self):
        self.assertExtracts(
            ['<a>Test</a><hr><a>Foo</a> | <a>Bar</a>',
              '<b>bold:</b> <a>link1</a><input><a>link2</a>'],
            [[{'tag': None, 'type': 'multitag', 'value': ''},
              {'tag': 'a', 'type': 'text', 'value': 'Test'},
              {'tag': None, 'type': 'multitag', 'value': '<hr>'},
              {'tag': 'a', 'type': 'text', 'value': 'Foo'},
              {'tag': 'body', 'type': 'tail', 'value': ' | '},
              {'tag': None, 'type': 'multitag', 'value': '<a>Bar</a>'}],
             [{'tag': None, 'type': 'multitag', 'value': '<b>bold:</b> '},
              {'tag': 'a', 'type': 'text', 'value': 'link1'},
              {'tag': None, 'type': 'multitag', 'value': '<input>'},
              {'tag': 'a', 'type': 'text', 'value': 'link2'},
              {'tag': 'body', 'type': 'tail', 'value': None},
              {'tag': None, 'type': 'multitag', 'value': ''}]]
        )

    def test_mixed1(self):
        self.assertExtracts(
            ['<h1>Headline</h1><p>This thing</p><br/><div id="footer">Copyright 2006</div>',
             '<h1>Headline 2</h1><p id="first">This thing</p><br/><div id="footer">Copyright 2007</div>'],
            [[{'type': 'text', 'value': 'Headline', 'tag': 'h1'}, {'type': 'attrib', 'value': '', 'tag': 'p'}, {'type': 'multitag', 'value': '<br><div id="footer">Copyright 2006</div>', 'tag': None}],
             [{'type': 'text', 'value': 'Headline 2', 'tag': 'h1'}, {'type': 'attrib', 'value': 'first', 'tag': 'p'}, {'type': 'multitag', 'value': '<br><div id="footer">Copyright 2007</div>', 'tag': None}]]
        )

    def test_comments_ignored1(self):
        self.assertExtracts(
            ['<h1><!-- comment --></h1>', '<h1></h1>'],
            [[], []]
        )

    def test_comments_ignored2(self):
        self.assertExtracts(
            ['<h1>A<!-- comment --></h1>', '<h1>A</h1>'],
            [[], []]
        )

    def test_comments_ignored3(self):
        self.assertExtracts(
            ['<h1><!-- comment -->A</h1>', '<h1>A</h1>'],
            [[], []]
        )

    def test_comments_ignored4(self):
        self.assertExtracts(
            ['<h1>A<!-- comment -->B</h1>', '<h1>AB</h1>'],
            [[], []]
        )

    def test_comments_ignored5(self):
        self.assertExtracts(
            ['<h1>Title <!-- foo -->here</h1>', '<h1>Title here</h1>'],
            [[], []]
        )

    def test_comments_ignored6(self):
        self.assertExtracts(
            ['<h1>Title <!-- foo -->here</h1><!--<p>nothing</p>--><p><!--foo-->Paragraph here</p>',
             '<h1>Title here</h1><p>Paragraph here</p>'],
            [[], []]
        )

    def test_nomatch_texthole1(self):
        self.assertNoMatch(
            ['<h1>test</h1>', '<h1>test</h1>'],
            '<h1>bar</h1>',
        )

    def test_nomatch_texthole2(self):
        self.assertNoMatch(
            ['<h1>test</h1><p>Foo</p>', '<h1>test</h1><p>Bar</p>'],
            '<h1>bar</h1><p>Foo</p>',
        )

    def test_nomatch_multitaghole1(self):
        self.assertNoMatch(
            ['<div><p>1</p><p>2</p></div>', '<div><p>1</p><p>2</p></div>'],
            '<div><p>1</p><p>2</p><p>3</p></div>'
        )

    def test_nomatch_tailhole1(self):
        self.assertNoMatch(
            ['<p>This is <b>bolded</b>, right?</p>', '<p>This is <b>bolded</b>, right?</p>'],
            '<p>This is <b>bolded</b>, no?</p>'
        )

    def test_namespaced1(self): 
        self.assertExtracts( 
            ['<h1 foo:bar="ignore">Headline</h1>', '<h1>Different</h1>'], 
            [[{'type': 'text', 'value': 'Headline', 'tag': 'h1'}],
             [{'type': 'text', 'value': 'Different', 'tag': 'h1'}]] 
        ) 

    def test_namespaced2(self): 
        self.assertExtracts( 
            ['<h1>Headline</h1>', '<h1 foo:bar="ignore">Different</h1>'], 
            [[{'type': 'text', 'value': 'Headline', 'tag': 'h1'}],
             [{'type': 'text', 'value': 'Different', 'tag': 'h1'}]] 
        ) 

    def test_namespaced3(self): 
        self.assertExtracts( 
            ['<h1 foo:bar="ignore">Headline</h1>', '<h1 foo:bar="ignore">Different</h1>'], 
            [[{'type': 'text', 'value': 'Headline', 'tag': 'h1'}],
             [{'type': 'text', 'value': 'Different', 'tag': 'h1'}]] 
        ) 

    def test_namespaced4(self): 
        self.assertExtracts( 
            ['<h1 foo:bar="ignore" class="red">Headline</h1>', '<h1 foo:bar="ignore">Different</h1>'], 
            [[{'type': 'attrib', 'value': 'red', 'tag': 'h1'}, {'type': 'text', 'value': 'Headline', 'tag': 'h1'}],
             [{'type': 'attrib', 'value': '', 'tag': 'h1'}, {'type': 'text', 'value': 'Different', 'tag': 'h1'}]] 
        ) 

class TemplateExtractionTestCaseAlgorithm2(TemplateExtractionTestCaseAlgorithm1):
    algorithm = 2

    def test_texthole3(self):
        self.assertExtracts(
            ['<h1>Headline</h1><p>Para</p><p>Final</p>', '<h1>Different</h1><p>Para</p><p>Diff</p>'],
            [[{'tag': 'h1', 'type': 'text', 'value': 'Headline'},
              {'tag': 'p', 'type': 'text', 'value': 'Final'}],
             [{'tag': 'h1', 'type': 'text', 'value': 'Different'},
              {'tag': 'p', 'type': 'text', 'value': 'Diff'}]]
        )

    def test_multitaghole1(self):
        self.assertExtracts(
            ['<div><p>Yes</p><p>No</p></div>', '<div><p>Yes</p><p>No</p><p>Maybe</p></div>'],
            [[{'tag': None, 'type': 'multitag', 'value': '<p>Yes</p><p>No</p>'}],
             [{'tag': None, 'type': 'multitag', 'value': '<p>Yes</p><p>No</p><p>Maybe</p>'}]]
        )

    def test_multitaghole2(self):
        self.assertExtracts(
            ['<div>Text <p>Yes</p><p>No</p></div>', '<div>Text <p>Yes</p><p>No</p><p>Maybe</p></div>'],
            [[{'tag': None, 'type': 'multitag', 'value': '<p>Yes</p><p>No</p>'}],
             [{'tag': None, 'type': 'multitag', 'value': '<p>Yes</p><p>No</p><p>Maybe</p>'}]]
        )

    def test_multitaghole3(self):
        self.assertExtracts(
            ['<div><p>Yes</p><p>No</p> Tail</div>',
             '<div><p>Yes</p><p>No</p><p>Maybe</p> Tail</div>'],
            [[{'tag': None, 'type': 'multitag', 'value': '<p>Yes</p><p>No</p> Tail'}],
             [{'tag': None, 'type': 'multitag', 'value': '<p>Yes</p><p>No</p><p>Maybe</p> Tail'}]]
        )

    def test_multitaghole5(self):
        self.assertExtracts(
            ['<div><p>Yes</p><p>No</p></div>', '<div><p>Yes</p><p>Bar</p><p>Maybe</p></div>'],
            [[{'tag': None, 'type': 'multitag', 'value': '<p>Yes</p><p>No</p>'}],
             [{'tag': None, 'type': 'multitag', 'value': '<p>Yes</p><p>Bar</p><p>Maybe</p>'}]]
        )

    def test_multitaghole6(self):
        self.assertExtracts(
            ['<div><p>Yes</p><p>No</p></div>', '<div><p>Yes</p><p id="test">No</p><p>Maybe</p></div>'],
            [[{'tag': None, 'type': 'multitag', 'value': '<p>Yes</p><p>No</p>'}],
             [{'tag': None, 'type': 'multitag', 'value': '<p>Yes</p><p id="test">No</p><p>Maybe</p>'}]]
        )

    def test_same_level1(self):
        self.assertExtracts(
            ['<h1>Man seen</h1><p>By John Smith</p><p>A man was seen today.</p>',
             '<h1>Bird seen</h1><p>By John Smith</p><p>A bird was seen yesterday.</p>'],
            [[{'tag': 'h1', 'type': 'text', 'value': 'Man seen'},
              {'tag': 'p', 'type': 'text', 'value': 'A man was seen today.'}],
             [{'tag': 'h1', 'type': 'text', 'value': 'Bird seen'},
              {'tag': 'p', 'type': 'text', 'value': 'A bird was seen yesterday.'}]]
        )

    def test_same_level2(self):
        self.assertExtracts(
            ['<p>By John Smith</p><h1>Man seen</h1><p>A man was seen today.</p>',
             '<p>By John Smith</p><h1>Bird seen</h1><p>A bird was seen yesterday.</p>'],
            [[{'tag': 'h1', 'type': 'text', 'value': 'Man seen'},
              {'tag': 'p', 'type': 'text', 'value': 'A man was seen today.'}],
             [{'tag': 'h1', 'type': 'text', 'value': 'Bird seen'},
              {'tag': 'p', 'type': 'text', 'value': 'A bird was seen yesterday.'}]]
        )

    def test_same_level3(self):
        self.assertExtracts(
            ['<p>By John Smith</p><h1>Man seen</h1><p>A man was seen today.</p><p>The end.</p>',
             '<p>By John Smith</p><h1>Bird seen</h1><p>A bird was seen yesterday.</p><p>The end.</p>'],
            [[{'tag': 'h1', 'type': 'text', 'value': 'Man seen'},
              {'tag': 'p', 'type': 'text', 'value': 'A man was seen today.'}],
             [{'tag': 'h1', 'type': 'text', 'value': 'Bird seen'},
              {'tag': 'p', 'type': 'text', 'value': 'A bird was seen yesterday.'}]]
        )

    def test_confusing1(self):
        self.assertExtracts(
            ['<ul>\n\t\t<li></li>\n\t\t<li></li>\n\t\t<li class="current"></li>\n\t\t<li></li>\n\t</ul>',
             '<ul>\n\t\t<li class="current"></li>\n\t\t<li></li>\n\t\t<li></li>\n\t\t<li></li>\n\t</ul>',
             '<ul>\n\t\t<li></li>\n\t\t<li class="current"></li>\n\t\t<li></li>\n\t\t<li></li>\n\t</ul>'],
            [[{'tag': 'li', 'type': 'attrib', 'value': ''},
              {'tag': 'li', 'type': 'attrib', 'value': ''},
              {'tag': 'li', 'type': 'attrib', 'value': 'current'}],
             [{'tag': 'li', 'type': 'attrib', 'value': 'current'},
              {'tag': 'li', 'type': 'attrib', 'value': ''},
              {'tag': 'li', 'type': 'attrib', 'value': ''}],
             [{'tag': 'li', 'type': 'attrib', 'value': ''},
              {'tag': 'li', 'type': 'attrib', 'value': 'current'},
              {'tag': 'li', 'type': 'attrib', 'value': ''}]]
        )

    def test_confusing2(self):
        self.assertExtracts(
            ['<a>Test</a><hr><a>Foo</a> | <a>Bar</a>',
              '<b>bold:</b> <a>link1</a><input><a>link2</a>'],
            [[{'tag': None, 'type': 'multitag', 'value': '<a>Test</a><hr/><a>Foo</a> | <a>Bar</a>'}],
             [{'tag': None, 'type': 'multitag', 'value': '<b>bold:</b> <a>link1</a><input/><a>link2</a>'}]]
        )

    def test_mixed1(self):
        self.assertExtracts(
            ['<h1>Headline</h1><p>This thing</p><br/><div id="footer">Copyright 2006</div>',
             '<h1>Headline 2</h1><p id="first">This thing</p><br/><div id="footer">Copyright 2007</div>'],
            [[{'tag': 'h1', 'type': 'text', 'value': 'Headline'},
              {'tag': 'p', 'type': 'attrib', 'value': ''},
              {'tag': 'div', 'type': 'text', 'value': 'Copyright 2006'}],
             [{'tag': 'h1', 'type': 'text', 'value': 'Headline 2'},
              {'tag': 'p', 'type': 'attrib', 'value': 'first'},
              {'tag': 'div', 'type': 'text', 'value': 'Copyright 2007'}]]
        )

if __name__ == "__main__":
    unittest.main()
