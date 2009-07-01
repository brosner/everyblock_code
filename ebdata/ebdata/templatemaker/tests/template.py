import unittest
from ebdata.templatemaker import Template, NoMatch
from ebdata.templatemaker.brain import Brain
from ebdata.templatemaker.hole import Hole

class TemplatemakerTestCase(unittest.TestCase):
    def create_the_long_way(self, *inputs):
        """
        "Helper method that returns a Template with the given inputs.
        """
        t = Template()
        for i in inputs:
            t.learn(i)
        return t

    def create_the_short_way(self, *inputs):
        t = Template()
        t.learn(*inputs)
        return t

    def assertCreated(self, expected, *inputs):
        """
        Asserts that a Template with the given inputs would be
        rendered as_text('!') to the expected string.
        """
        t1 = self.create_the_long_way(*inputs)
        t2 = self.create_the_short_way(*inputs)
        self.assertEqual(t1.as_text('!'), expected)
        self.assertEqual(t2.as_text('!'), expected)

class TemplatemakerExtractTestCase(unittest.TestCase):
    """
    This class' tests assume that self.setUp() creates self.template.
    """
    def assertExtracts(self, text, expected):
        """
        Asserts that self.template.extract(text) returns expected.
        """
        self.assertEqual(self.template.extract(text), expected)

    def assertNoMatch(self, text):
        """
        Asserts that self.template.extract(text) raises NoMatch.
        """
        self.assertRaises(NoMatch, self.template.extract, text)

class Creation(TemplatemakerTestCase):
    def test_noop1(self):
        self.assertCreated('<title>123</title>', '<title>123</title>')

    def test_noop2(self):
        self.assertCreated('<title>123</title>', '<title>123</title>', '<title>123</title>')

    def test_noop3(self):
        self.assertCreated('<title>123</title>', '<title>123</title>', '<title>123</title>', '<title>123</title>')

    def test_one_char_start1(self):
        self.assertCreated('!2345', '12345', '_2345')

    def test_one_char_start2(self):
        self.assertCreated('!2345', '12345', '12345', '_2345')

    def test_one_char_start3(self):
        self.assertCreated('!2345', '12345', '_2345', '^2345')

    def test_one_char_end1(self):
        self.assertCreated('1234!', '12345', '1234_')

    def test_one_char_end2(self):
        self.assertCreated('1234!', '12345', '12345', '1234_')

    def test_one_char_end3(self):
        self.assertCreated('1234!', '12345', '1234_', '1234^')

    def test_one_char_middle1(self):
        self.assertCreated('12!45', '12345', '12_45')

    def test_one_char_middle2(self):
        self.assertCreated('12!45', '12345', '12345', '12_45')

    def test_one_char_middle3(self):
        self.assertCreated('12!45', '12345', '12_45', '12^45')

    def test_one_char_middle4(self):
        self.assertCreated('12!45', '12345', '1245')

    def test_multi_char_start1(self):
        self.assertCreated('!345', '12345', '_2345', '1_345')

    def test_multi_char_start2(self):
        self.assertCreated('!345', '12345', '1_345', '_2345')

    def test_multi_char_start3(self):
        self.assertCreated('!45', '12345', '_2345', '1_345', '12_45')

    def test_multi_char_start4(self):
        self.assertCreated('!5', '12345', '_2345', '1_345', '12_45', '123_5')

    def test_multi_char_end1(self):
        self.assertCreated('1234!', '12345', '1234_')

    def test_multi_char_end2(self):
        self.assertCreated('123!', '12345', '1234_', '123_5')

    def test_multi_char_end3(self):
        self.assertCreated('12!', '12345', '1234_', '123_5', '12_45')

    def test_multi_char_end4(self):
        self.assertCreated('1!', '12345', '1234_', '123_5', '12_45', '1_345')

    def test_empty(self):
        self.assertCreated('', '', '')

    def test_no_similarities1(self):
        self.assertCreated('!', 'a', 'b')

    def test_no_similarities2(self):
        self.assertCreated('!', 'ab', 'ba', 'ac', 'bc')

    def test_no_similarities3(self):
        self.assertCreated('!', 'abc', 'ab_', 'a_c', '_bc')

    def test_left_weight1(self):
        self.assertCreated('!a!', 'ab', 'ba') # NOT '!b!'

    def test_left_weight2(self):
        self.assertCreated('a!b!', 'abc', 'acb')

    def test_multihole1(self):
        self.assertCreated('!2!', '123', '_23', '12_')

    def test_multihole2(self):
        self.assertCreated('!2!4!', '12345', '_2_4_')

    def test_multihole3(self):
        self.assertCreated('!2!4!', '12345', '_2345', '12_45', '1234_')

    def test_multihole4(self):
        self.assertCreated('!2!456!8', '12345678', '_2_456_8')

    def test_multihole5(self):
        self.assertCreated('!2!456!8', '12345678', '_2345678', '12_45678', '123456_8')

    def test_multihole6(self):
        self.assertCreated('!e! there', 'hello there', 'goodbye there')

class ExtractNoHoles(TemplatemakerExtractTestCase):
    def setUp(self):
        self.template = Template(Brain(['hello']))

    def test_extracts_nothing(self):
        self.assertExtracts('hello', ())

    def test_no_match_empty(self):
        self.assertNoMatch('')

    def test_no_match_case_sensitive1(self):
        self.assertNoMatch('Hello')

    def test_no_match_case_sensitive2(self):
        self.assertNoMatch('HELLO')

    def test_no_match_invalid(self):
        self.assertNoMatch('goodbye')

    def test_no_match_spaces1(self):
        self.assertNoMatch('hello ')

    def test_no_match_spaces2(self):
        self.assertNoMatch(' hello')

    def test_no_match_spaces3(self):
        self.assertNoMatch(' hello ')

class ExtractOneHole(TemplatemakerExtractTestCase):
    def setUp(self):
        self.template = Template(Brain(['Hello, ', Hole(), '. How are you?']))

    def test_one_word(self):
        self.assertExtracts('Hello, Picasso. How are you?', ('Picasso',))

    def test_two_words(self):
        self.assertExtracts('Hello, Michael Jordan. How are you?', ('Michael Jordan',))

    def test_three_words(self):
        self.assertExtracts('Hello, Frank Lloyd Wright. How are you?', ('Frank Lloyd Wright',))

    def test_period(self):
        self.assertExtracts('Hello, Richard J. Daley. How are you?', ('Richard J. Daley',))

    def test_empty_value(self):
        self.assertExtracts('Hello, . How are you?', ('',))

    def test_no_match_empty(self):
        self.assertNoMatch('')

    def test_no_match_case_sensitive(self):
        self.assertNoMatch('hello, friend. how are you?')

    def test_no_match_invalid(self):
        self.assertNoMatch('foo')

    def test_no_match_slightly_off1(self):
        self.assertNoMatch('Hello, friend.')

    def test_no_match_slightly_off2(self):
        self.assertNoMatch('Hello. How are you?')

    def test_no_match_slightly_off3(self):
        self.assertNoMatch('Hello friend. How are you?') # No comma

class ExtractTwoHoles(TemplatemakerExtractTestCase):
    def setUp(self):
        self.template = Template(Brain(['<p>', Hole(), ' and ', Hole(), '</p>']))

    def test_basic1(self):
        self.assertExtracts('<p>this and that</p>', ('this', 'that'))

    def test_basic2(self):
        self.assertExtracts('<p>foo and bar</p>', ('foo', 'bar'))

    def test_multiple_ands(self):
        self.assertExtracts('<p>and and and</p>', ('and', 'and'))

    def test_spaces1(self):
        self.assertExtracts('<p> this  and  that </p>', (' this ', ' that '))

    def test_spaces2(self):
        self.assertExtracts('<p>  and  </p>', (' ', ' '))

    def test_dots(self):
        self.assertExtracts('<p>. and .</p>', ('.', '.'))

    def test_question_marks(self):
        self.assertExtracts('<p>? and ?</p>', ('?', '?'))

    def test_empty_values(self):
        self.assertExtracts('<p> and </p>', ('', ''))

    def test_one_empty_value_first(self):
        self.assertExtracts('<p> and that</p>', ('', 'that'))

    def test_one_empty_value_second(self):
        self.assertExtracts('<p>this and </p>', ('this', ''))

    def test_no_match_empty(self):
        self.assertNoMatch('')

    def test_no_match_case_sensitive(self):
        self.assertNoMatch('<P>this and that</P>')

    def test_no_match_invalid(self):
        self.assertNoMatch('foo')

    def test_no_match_slightly_off1(self):
        self.assertNoMatch('this and that')

    def test_no_match_slightly_off2(self):
        self.assertNoMatch('<p></p>')

    def test_no_match_slightly_off3(self):
        self.assertNoMatch('<p>and</p>')

class ExtractWithHoleAtStart(TemplatemakerExtractTestCase):
    def setUp(self):
        self.template = Template(Brain([Hole(), ' and bar']))

    def test_basic(self):
        self.assertExtracts('foo and bar', ('foo',))

    def test_and(self):
        self.assertExtracts('and and bar', ('and',))

    def test_empty_value(self):
        self.assertExtracts(' and bar', ('',))

    def test_space_value(self):
        self.assertExtracts('  and bar', (' ',))

    def test_large(self):
        self.assertExtracts('This and that and this and that and bar', ('This and that and this and that',))

    def test_no_match_empty(self):
        self.assertNoMatch('')

    def test_no_match_case_sensitive(self):
        self.assertNoMatch('foo AND BAR')

    def test_no_match_invalid(self):
        self.assertNoMatch('foo')

    def test_no_match_slightly_off1(self):
        self.assertNoMatch('foo and bar.')

    def test_no_match_slightly_off2(self):
        self.assertNoMatch('and bar')

    def test_no_match_slightly_off3(self):
        self.assertNoMatch('and bar ')

class ExtractWithHoleAtEnd(TemplatemakerExtractTestCase):
    def setUp(self):
        self.template = Template(Brain(['foo and ', Hole()]))

    def test_basic(self):
        self.assertExtracts('foo and bar', ('bar',))

    def test_and(self):
        self.assertExtracts('foo and and', ('and',))

    def test_empty_value(self):
        self.assertExtracts('foo and ', ('',))

    def test_space_value(self):
        self.assertExtracts('foo and  ', (' ',))

    def test_period(self):
        self.assertExtracts('foo and bar.', ('bar.',))

    def test_large(self):
        self.assertExtracts('foo and this and that and this and that', ('this and that and this and that',))

    def test_no_match_empty(self):
        self.assertNoMatch('')

    def test_no_match_case_sensitive(self):
        self.assertNoMatch('FOO AND bar')

    def test_no_match_invalid(self):
        self.assertNoMatch('foo')

    def test_no_match_slightly_off1(self):
        self.assertNoMatch('foo and')

    def test_no_match_slightly_off2(self):
        self.assertNoMatch(' foo and')

class Initialization(unittest.TestCase):
    def test_string(self):
        t = Template(brain='Y2NvcHlfcmVnCl9yZWNvbnN0cnVjdG9yCnAxCihjZXZlcnlibG9jay50ZW1wbGF0ZW1ha2VyLmJy\nYWluCkJyYWluCnAyCmNfX2J1aWx0aW5fXwpsaXN0CnAzCihscDQKZzEKKGNldmVyeWJsb2NrLnRl\nbXBsYXRlbWFrZXIuaG9sZQpIb2xlCnA1CmNfX2J1aWx0aW5fXwpvYmplY3QKcDYKTnRScDcKYVMn\nYWJjJwpwOAphZzEKKGc1Cmc2Ck50UnA5CmF0UnAxMAou\n')
        self.assertEqual(t.brain, [Hole(), 'abc', Hole()])

    def test_brain(self):
        t = Template(brain=[Hole(), 'abc', Hole()])
        self.assertEqual(t.brain, [Hole(), 'abc', Hole()])

    def test_none(self):
        t = Template(brain=None)
        self.assertEqual(t.brain, None)

if __name__ == "__main__":
    unittest.main()
