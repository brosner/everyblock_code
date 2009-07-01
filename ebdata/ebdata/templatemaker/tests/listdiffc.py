"""
These tests are identical to the ones in listdiff.py but use the C version of
longest_common_substring instead of the pure Python version.
"""

from ebdata.templatemaker.listdiffc import longest_common_subsequence as longest_common_substring
from listdiff import LongestCommonSubstring
import unittest

class LongestCommonSubstringC(LongestCommonSubstring):
    def LCS(self, seq1, seq2):
        return longest_common_substring(seq1, seq2)

del LongestCommonSubstring

if __name__ == "__main__":
    unittest.main()
