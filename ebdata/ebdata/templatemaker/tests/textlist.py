from ebdata.templatemaker.textlist import html_to_paragraph_list
from ebdata.textmining.treeutils import make_tree
import unittest

class AutoTextMetaclass(type):
    """
    Metaclass that adds a test method for every pair in TEST_DATA.
    """
    def __new__(cls, name, bases, attrs):
        TEST_DATA = (
            # input, expected output
            ('hello', ['hello']),
            ('hello\nthere', ['hello there']),
            ('hello\r\nthere', ['hello there']),

            ('<p>First</p><p>Second</p>', ['First', 'Second']),
            ('<p>First<p>Second</p>', ['First', 'Second']),
            ('First<p>Second</p>', ['First', 'Second']),
            ('First<p>Second', ['First', 'Second']),
            ('<p>First</p>Second', ['First', 'Second']),
            ('First</p>Second', ['First', 'Second']),
            ('First</p>Second</p>', ['First', 'Second']),
            ('First<p></p>Second', ['First', 'Second']),
            ('<p></p>First<p></p>Second', ['First', 'Second']),
            ('</p>First</p>Second', ['First', 'Second']),

            ('hello<br>there', ['hello', 'there']),
            ('hello<br>\nthere', ['hello', 'there']),
            ('hello<br><br>there', ['hello', 'there']),
            ('hello<br><br><br>there', ['hello', 'there']),
            ('hello<br><br><br><br>there', ['hello', 'there']),

            ('<p>hello<br>there</p>', ['hello', 'there']),
            ('<p>hello</p><br><p>there</p>', ['hello', 'there']),
            ('hello<br><p>there</p>', ['hello', 'there']),
            ('hello<br><p>there</p>', ['hello', 'there']),
        )
        def make_test_func(html, expected):
            return lambda self: self.assertConverts(html, expected)
        for i, (html, expected) in enumerate(TEST_DATA):
            func = make_test_func(html, expected)
            func.__doc__ = repr(html)
            attrs['test_%03d' % i] = func # Use '%03d' to make tests run in order, because unittest uses string ordering.
        return type.__new__(cls, name, bases, attrs)

class LocationTestCase(unittest.TestCase):
    __metaclass__ = AutoTextMetaclass

    def assertConverts(self, html, expected):
        self.assertEqual(html_to_paragraph_list(make_tree(html)), expected)

if __name__ == "__main__":
    unittest.main()
