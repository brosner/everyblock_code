from ebdata.templatemaker.articletext import is_punctuated
import os.path
import unittest

class AutoTestMetaclass(type):
    """
    Metaclass that adds a test method for every pair in TEST_DATA.
    """
    def __new__(cls, name, bases, attrs):
        def make_test_func(input_value, expected):
            return lambda self: self.assertAutotest(input_value, expected)
        for i, (html, expected) in enumerate(attrs['TEST_DATA']):
            func = make_test_func(html, expected)
            func.__doc__ = repr(html)
            attrs['test_%03d' % i] = func # Use '%03d' to make tests run in order, because unittest uses string ordering.
        return type.__new__(cls, name, bases, attrs)

class PunctuatedTestCase(unittest.TestCase):
    __metaclass__ = AutoTestMetaclass

    TEST_DATA = (
        (u'This is a sentence.', True),
        (u'This is a sentence?', True),
        (u'This is a sentence!', True),
        (u'This is a sentence.  ', True),
        (u'This is a sentence?  ', True),
        (u'This is a sentence!  ', True),
        (u'Not a sentence', False),
        (u'Not. A! Sentence? Correct', False),
        (u'"This is a quoted sentence."', True),
        (u'"This is a quoted sentence." ', True),
        (u'"This is a quoted sentence. " ', True),
        (u'"This is a quoted sentence?"', True),
        (u'"This is a quoted sentence?" ', True),
        (u'"This is a quoted sentence ?" ', True),
        (u'"This is a quoted sentence!"', True),
        (u'"This is a quoted sentence!" ', True),
        (u'"This is a quoted sentence! " ', True),
        (u'This is a sentence (yeah).', True),
        (u'This is a sentence. (Yeah.)', True),
        (u'This is a sentence. (Yeah?)', True),
        (u'This is a sentence. (Yeah!)', True),
        (u'This is a sentence. ("Quoted.")', True),
        (u'This is a sentence. ("Quoted?")', True),
        (u'This is a sentence. ("Quoted!")', True),
        (u'This is a sentence. (\'Single-quoted.\')', True),
        (u'This is a sentence. (\'Single-quoted?\')', True),
        (u'This is a sentence. (\'Single-quoted!\')', True),
        (u'This is a sentence. ("\'Double-quoted.\'")', True),
        (u'This is a sentence. ("\'Double-quoted?\'")', True),
        (u'This is a sentence. ("\'Double-quoted!\'")', True),
        (u'This is a sentence. (\'"Double-quoted."\')', True),
        (u'This is a sentence. (\'"Double-quoted?"\')', True),
        (u'This is a sentence. (\'"Double-quoted!"\')', True),
        (u'He "said, \'It\'s going to reveal what else she has done\'."', True),
        (u'He \u201csaid, \u2018It\u2019s going to reveal what else she has done\u2019.\u201d', True),
    )

    def assertAutotest(self, sentence, expected):
        self.assertEqual(bool(is_punctuated(sentence)), expected)

if __name__ == "__main__":
    unittest.main()
