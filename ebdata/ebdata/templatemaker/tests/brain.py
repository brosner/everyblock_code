from ebdata.templatemaker.brain import Brain
from ebdata.templatemaker.hole import Hole, OrHole, IgnoreHole
import unittest

class BrainTestCase(unittest.TestCase):
    def assertAsText(self, brain, marker, expected):
        """
        Asserts that Brain(brain).as_text(marker) == expected.
        """
        b = Brain(brain)
        if marker is not None:
            self.assertEqual(b.as_text(marker), expected)
        else:
            self.assertEqual(b.as_text(), expected)

    def assertNumHoles(self, brain, expected):
        """
        Asserts that Brain(brain).num_holes() == expected.
        """
        b = Brain(brain)
        self.assertEqual(b.num_holes(), expected)

    def assertRegex(self, brain, expected):
        """
        Asserts that Brain(brain).match_regex() == expected.
        """
        b = Brain(brain)
        self.assertEqual(b.match_regex(), expected)

    def test_as_text_empty1(self):
        self.assertAsText([], None, '')

    def test_as_text_empty2(self):
        self.assertAsText([], 'marker', '')

    def test_as_text1(self):
        self.assertAsText(['1', Hole(), '2', Hole(), '3'], None, '1{{ HOLE }}2{{ HOLE }}3')

    def test_as_text2(self):
        self.assertAsText(['1', Hole(), '2', Hole(), '3'], '!', '1!2!3')

    def test_num_holes_empty(self):
        self.assertNumHoles([], 0)

    def test_num_holes1(self):
        self.assertNumHoles(['a', 'b', 'c'], 0)

    def test_num_holes2(self):
        self.assertNumHoles(['a', Hole(), 'c'], 1)

    def test_num_holes3(self):
        self.assertNumHoles(['a', Hole(), 'c', Hole()], 2)

    def test_regex_empty(self):
        self.assertRegex([], '^(?s)$')

    def test_regex_noholes(self):
        self.assertRegex(['a', 'b', 'c'], '^(?s)abc$')

    def test_regex_special_chars(self):
        self.assertRegex(['^$?.*'], r'^(?s)\^\$\?\.\*$')

    def test_regex_holes1(self):
        self.assertRegex(['a', Hole(), 'b'], '^(?s)a(.*?)b$')

    def test_regex_holes2(self):
        self.assertRegex(['a', OrHole('b', 'c'), 'd', IgnoreHole()], '^(?s)a(b|c)d.*?$')

class BrainEmptyTestCase(unittest.TestCase):
    def assertConcise(self, brain, expected):
        """
        Asserts that Brain(brain).concise() == expected.
        """
        b = Brain(brain)
        self.assertEqual(b.concise(), expected)

    def test_empty(self):
        self.assertConcise([], [])

    def test_basic1(self):
        self.assertConcise(['a'], ['a'])

    def test_basic2(self):
        self.assertConcise(['a', 'b'], ['ab'])

    def test_basic3(self):
        self.assertConcise(['a', Hole(), 'b'], ['a', Hole(), 'b'])

    def test_basic4(self):
        self.assertConcise([Hole(), 'a', Hole(), 'b'], [Hole(), 'a', Hole(), 'b'])

    def test_basic5(self):
        self.assertConcise([Hole(), 'a', Hole(), 'b', Hole()],
            [Hole(), 'a', Hole(), 'b', Hole()])

    def test_basic6(self):
        self.assertConcise([Hole(), 'a', 'b', 'c', Hole(), 'd', 'e', 'f', Hole(), 'g'],
            [Hole(), 'abc', Hole(), 'def', Hole(), 'g'])

    def test_long_strings(self):
        self.assertConcise(['this is ', 'a test', Hole(), 'of the ', 'emergency ', 'broadcast system', Hole()],
            ['this is a test', Hole(), 'of the emergency broadcast system', Hole()])

class BrainSerialization(unittest.TestCase):
    def assertSerializes(self, brain):
        """
        Serializes and unserializes the given brain, asserting that a round
        trip works properly.
        """
        b = Brain(brain)
        self.assertEqual(b, Brain.from_serialized(b.serialize()))

    def test_empty(self):
        self.assertSerializes([])

    def test_integer(self):
        self.assertSerializes([1, 2, 3])

    def test_string(self):
        self.assertSerializes(['abc', 'd', 'e', 'fg hi jklmnop'])

    def test_hole1(self):
        self.assertSerializes([Hole()])

    def test_hole2(self):
        self.assertSerializes([Hole(), Hole(), Hole()])

    def test_hole_and_strings(self):
        self.assertSerializes([Hole(), 'abc', Hole(), 'def', Hole()])

    def test_format1(self):
        self.assertEqual(Brain([]).serialize(), 'gAJjZXZlcnlibG9jay50ZW1wbGF0ZW1ha2VyLmJyYWluCkJyYWluCnEBKYFxAn1xA2Iu\n')

    def test_format2(self):
        self.assertEqual(Brain([Hole(), 'abc', Hole()]).serialize(), 'gAJjZXZlcnlibG9jay50ZW1wbGF0ZW1ha2VyLmJyYWluCkJyYWluCnEBKYFxAihjZXZlcnlibG9j\nay50ZW1wbGF0ZW1ha2VyLmhvbGUKSG9sZQpxAymBcQR9cQViVQNhYmNxBmgDKYFxB31xCGJlfXEJ\nYi4=\n')

    def test_format_input1(self):
        self.assertEqual(Brain([]), Brain.from_serialized('gAJjZXZlcnlibG9jay50ZW1wbGF0ZW1ha2VyLmJyYWluCkJyYWluCnEBKYFxAn1xA2Iu\n'))

    def test_format_input2(self):
        self.assertEqual(Brain([Hole(), 'abc', Hole()]), Brain.from_serialized('gAJjZXZlcnlibG9jay50ZW1wbGF0ZW1ha2VyLmJyYWluCkJyYWluCnEBKYFxAihjZXZlcnlibG9j\nay50ZW1wbGF0ZW1ha2VyLmhvbGUKSG9sZQpxAymBcQR9cQViVQNhYmNxBmgDKYFxB31xCGJlfXEJ\nYi4=\n'))

if __name__ == "__main__":
    unittest.main()
