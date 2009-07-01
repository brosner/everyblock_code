from ebdata.templatemaker.hole import Hole, OrHole, RegexHole, IgnoreHole
import unittest

class HoleEquality(unittest.TestCase):
    def test_equal_hole(self):
        self.assertEqual(Hole(), Hole())

    def test_nonequal_hole(self):
        self.assertNotEqual(Hole(), OrHole())

    def test_equal_orhole(self):
        self.assertEqual(OrHole('a', 'b'), OrHole('a', 'b'))

    def test_nonequal_orhole1(self):
        self.assertNotEqual(OrHole('a'), OrHole('a', 'b'))

    def test_nonequal_orhole2(self):
        self.assertNotEqual(OrHole('a'), OrHole('b'))

    def test_equal_regexhole1(self):
        self.assertEqual(RegexHole('\d\d', False), RegexHole('\d\d', False))

    def test_equal_regexhole2(self):
        self.assertEqual(RegexHole('(\d\d)', True), RegexHole('(\d\d)', True))

    def test_nonequal_regexhole1(self):
        self.assertNotEqual(RegexHole('\d\d', False), RegexHole('\d', False))

    def test_nonequal_regexhole2(self):
        self.assertNotEqual(RegexHole('\d', False), IgnoreHole())

    def test_nonequal_regexhole3(self):
        self.assertNotEqual(RegexHole('\d', False), Hole())

    def test_nonequal_regexhole4(self):
        self.assertNotEqual(RegexHole('\d\d', False), RegexHole('\d\d', True))

    def test_nonequal_regexhole5(self):
        self.assertNotEqual(RegexHole('\d\d', False), RegexHole('(\d\d)', False))

    def test_equal_ignorehole(self):
        self.assertEqual(IgnoreHole(), IgnoreHole())

    def test_nonequal_ignorehole1(self):
        self.assertNotEqual(IgnoreHole(), Hole())

    def test_nonequal_ignorehole2(self):
        self.assertNotEqual(IgnoreHole(), OrHole('a'))

class HoleRepr(unittest.TestCase):
    def test_hole(self):
        self.assertEqual(repr(Hole()), '<Hole>')

    def test_orhole(self):
        self.assertEqual(repr(OrHole(1, 2, 3, 4)), '<OrHole: (1, 2, 3, 4)>')

    def test_regexhole(self):
        self.assertEqual(repr(RegexHole('\d\d-\d\d', False)), '<RegexHole: \d\d-\d\d>')

    def test_ignorehole(self):
        self.assertEqual(repr(IgnoreHole()), '<IgnoreHole>')

class Regexes(unittest.TestCase):
    def test_hole(self):
        self.assertEqual(Hole().regex(), '(.*?)')

    def test_orhole1(self):
        self.assertEqual(OrHole('a', 'b').regex(), '(a|b)')

    def test_orhole2(self):
        self.assertEqual(OrHole('?', '.').regex(), '(\?|\.)')

    def test_regexhole(self):
        self.assertEqual(RegexHole('\d\d-\d\d', False).regex(), '\d\d-\d\d')

    def test_ignorehole(self):
        self.assertEqual(IgnoreHole().regex(), '.*?')

class HoleCapture(unittest.TestCase):
    def test_hole(self):
        self.assertEqual(Hole().capture, True)

    def test_orhole(self):
        self.assertEqual(OrHole('a', 'b').capture, True)

    def test_regexhole1(self):
        self.assertEqual(RegexHole('\d\d-\d\d', False).capture, False)

    def test_regexhole2(self):
        self.assertEqual(RegexHole('(\d\d-\d\d)', True).capture, True)

    def test_regexhole3(self):
        self.assertEqual(RegexHole('(\d\d-\d\d)', False).capture, False)

    def test_ignorehole(self):
        self.assertEqual(IgnoreHole().capture, False)

if __name__ == "__main__":
    unittest.main()
