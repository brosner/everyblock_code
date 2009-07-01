from ebdata.templatemaker.hole import Hole
from ebdata.templatemaker.listdiff import listdiff, longest_common_substring
import unittest

class LongestCommonSubstring(unittest.TestCase):
    def LCS(self, seq1, seq2):
        return longest_common_substring(seq1, seq2)

    def assertLCS(self, seq1, seq2, expected_length, expected_offset1, expected_offset2):
        best_size, offset1, offset2 = self.LCS(seq1, seq2)
        self.assertEqual(best_size, expected_length)
        self.assertEqual(offset1, expected_offset1)
        self.assertEqual(offset2, expected_offset2)

    def test_both_empty(self):
        self.assertLCS([], [], 0, -1, -1)

    def test_l1_empty(self):
        self.assertLCS([], ['a'], 0, -1, -1)

    def test_l2_empty(self):
        self.assertLCS(['a'], [], 0, -1, -1)

    def test_equal1(self):
        self.assertLCS(['a'], ['a'], 1, 0, 0)

    def test_equal2(self):
        self.assertLCS(['a', 'b', 'c'], ['a', 'b', 'c'], 3, 0, 0)

    def test_common1(self):
        self.assertLCS(['a', 'b', 'c'], ['b', 'c', 'a'], 2, 1, 0)

    def test_common2(self):
        self.assertLCS(['b', 'c', 'a'], ['a', 'b', 'c'], 2, 0, 1)

    def test_common3(self):
        self.assertLCS(['a', 'b', 'c', 'd'], ['a'], 1, 0, 0)

    def test_common4(self):
        self.assertLCS(['a', 'b', 'c', 'd'], ['b'], 1, 1, 0)

    def test_common5(self):
        self.assertLCS(['a', 'b', 'c', 'd'], ['c'], 1, 2, 0)

    def test_common6(self):
        self.assertLCS(['a', 'b', 'c', 'd'], ['d'], 1, 3, 0)

    def test_common7(self):
        self.assertLCS(['a', 'b', 'c', 'd'], ['c', 'd'], 2, 2, 0)

    def test_common8(self):
        self.assertLCS(['a', 'b', 'c', 'd'], ['f', 'c', 'd'], 2, 2, 1)

    def test_common9(self):
        self.assertLCS(['a'], ['a', 'b', 'c', 'd'], 1, 0, 0)

    def test_common10(self):
        self.assertLCS(['b'], ['a', 'b', 'c', 'd'], 1, 0, 1)

    def test_common11(self):
        self.assertLCS(['c'], ['a', 'b', 'c', 'd'], 1, 0, 2)

    def test_common12(self):
        self.assertLCS(['d'], ['a', 'b', 'c', 'd'], 1, 0, 3)

    def test_common13(self):
        self.assertLCS(['c', 'd'], ['a', 'b', 'c', 'd'], 2, 0, 2)

    def test_common14(self):
        self.assertLCS(['f', 'c', 'd'], ['a', 'b', 'c', 'd'], 2, 1, 2)

    def test_common15(self):
        self.assertLCS(['1', '2', '!', '4', '5'], ['1', '2', '3', '4', '5'], 2, 0, 0)

    def test_common16(self):
        self.assertLCS(['1', '2', '4', '5'], ['1', '2', '3', '4', '5'], 2, 0, 0)

    def test_common17(self):
        self.assertLCS(['1', '2', '3', '4', '5'], ['1', '2', '4', '5'], 2, 0, 0)

    def test_hole1(self):
        self.assertLCS([Hole()], [Hole()], 1, 0, 0)

    def test_hole2(self):
        self.assertLCS([Hole(), Hole()], [Hole(), Hole()], 2, 0, 0)

    def test_hole3(self):
        self.assertLCS([Hole(), 'a'], [Hole(), 'b'], 1, 0, 0)

    def test_hole4(self):
        self.assertLCS(['a', Hole(), 'b'], ['a', Hole(), 'b'], 3, 0, 0)

    def test_hole5(self):
        self.assertLCS(['b', Hole(), 'c'], ['a', Hole(), 'c'], 2, 1, 1)

    def test_hole6(self):
        self.assertLCS(['a', Hole(), 'b'], ['c', Hole(), 'd'], 1, 1, 1)

    def test_earliest1(self):
        "The LCS should be the earliest index in both strings."
        self.assertLCS(['b', 'a', 'c'], ['a', 'd', 'a'], 1, 1, 0)

    def test_earliest2(self):
        "The LCS should be the earliest index in both strings."
        self.assertLCS(['a', 'd', 'a'], ['b', 'a', 'c'], 1, 0, 1)

class ListdiffTestCase(unittest.TestCase):
    def assertListdiff(self, l1, l2, expected):
        self.assertEqual(listdiff(l1, l2), expected)

    def test_both_empty(self):
        self.assertListdiff([], [], [])

    def test_l1_empty(self):
        self.assertListdiff(
            [],
            ['a'],
            [Hole()],
        )

    def test_l2_empty(self):
        self.assertListdiff(
            ['a'],
            [],
            [Hole()],
        )

    def test_equal1(self):
        self.assertListdiff(
            ['a'],
            ['a'],
            ['a'],
        )

    def test_equal2(self):
        self.assertListdiff(
            ['a', 'b'],
            ['a', 'b'],
            ['a', 'b'],
        )

    def test_equal3(self):
        self.assertListdiff(
            ['a', 'b', 'c'],
            ['a', 'b', 'c'],
            ['a', 'b', 'c'],
        )

    def test_hole1(self):
        self.assertListdiff(
            ['Hello', ' ', 'John'],
            ['Hello', ' ', 'Fran'],
            ['Hello', ' ', Hole()],
        )

    def test_hole2(self):
        self.assertListdiff(
            ['Hello', ' ', 'John'],
            ['Goodbye', ' ', 'Fran'],
            [Hole(), ' ', Hole()],
        )

    def test_hole3(self):
        self.assertListdiff(
            ['a', 'b', 'c', 'd', 'e', 'f'],
            ['a', '_', 'c', '_', 'e', '_'],
            ['a', Hole(), 'c', Hole(), 'e', Hole()],
        )

    def test_hole4(self):
        self.assertListdiff(
            ['a', 'b', 'c', 'd', 'e', 'f'],
            ['_', 'b', '_', 'd', '_', 'f'],
            [Hole(), 'b', Hole(), 'd', Hole(), 'f'],
        )

    def test_hole5(self):
        self.assertListdiff(
            ['this', ' ', 'and', ' ', 'that'],
            ['foo', ' ', 'and', ' ', 'bar'],
            [Hole(), ' ', 'and', ' ', Hole()],
        )

    def test_hole6(self):
        self.assertListdiff(
            ['1', '2', '3', '4', '5'],
            ['1', '2', '4', '5'],
            ['1', '2', Hole(), '4', '5'],
        )

    def test_hole7(self):
        self.assertListdiff(
            ['1', '2', '4', '5'],
            ['1', '2', '3', '4', '5'],
            ['1', '2', Hole(), '4', '5'],
        )

    def test_hole8(self):
        self.assertListdiff(
            ['3', '4', '5'],
            ['4', '5'],
            [Hole(), '4', '5'],
        )

    def test_hole9(self):
        self.assertListdiff(
            ['4', '5'],
            ['5'],
            [Hole(), '5'],
        )

    def test_hole_input1(self):
        self.assertListdiff(
            [Hole()],
            [Hole()],
            [Hole()],
        )

    def test_hole_input2(self):
        self.assertListdiff(
            [],
            [Hole()],
            [Hole()],
        )

    def test_hole_input3(self):
        self.assertListdiff(
            [Hole()],
            [],
            [Hole()],
        )

    def test_hole_input4(self):
        self.assertListdiff(
            [Hole(), 'hello'],
            [Hole(), 'hello'],
            [Hole(), 'hello'],
        )

    def test_hole_input5(self):
        self.assertListdiff(
            [Hole(), 'person 1'],
            [Hole(), 'person 2'],
            [Hole(), Hole()],
        )

    def test_hole_input6(self):
        self.assertListdiff(
            [Hole(), 'person 1', ' test'],
            [Hole(), 'person 2', ' test'],
            [Hole(), Hole(), ' test'],
        )

    def test_hole_input7(self):
        self.assertListdiff(
            ['foo', Hole(), 'person 1 test'],
            ['foo', Hole(), 'person 2 test'],
            ['foo', Hole(), Hole()],
        )

if __name__ == "__main__":
    unittest.main()
