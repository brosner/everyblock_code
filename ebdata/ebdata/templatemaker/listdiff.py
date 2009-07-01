from hole import Hole

def listdiff(list1, list2):
    """
    Given two lists, returns a "diff" list, with Hole instances inserted
    as necessary.
    """
    hole = Hole()

    # Special case.
    if list1 == list2 == []:
        return []

    best_size, offset1, offset2 = longest_common_substring(list1, list2)

    result = []

    if best_size == 0:
        result.append(hole)
    if offset1 > 0 and offset2 > 0:
        # There's leftover stuff on the left side of BOTH lists.
        result.extend(listdiff(list1[:offset1], list2[:offset2]))
    elif offset1 > 0 or offset2 > 0:
        # There's leftover stuff on the left side of ONLY ONE of the lists.
        result.append(hole)
    if best_size > 0:
        result.extend(list1[offset1:offset1+best_size])
        if (offset1 + best_size < len(list1)) and (offset2 + best_size < len(list2)):
            # There's leftover stuff on the right side of BOTH lists.
            result.extend(listdiff(list1[offset1+best_size:], list2[offset2+best_size:]))
        elif (offset1 + best_size < len(list1)) or (offset2 + best_size < len(list2)):
            # There's leftover stuff on the right side of ONLY ONE of the lists.
            result.append(hole)
    return result

# NOTE: This is a "longest common substring" algorithm, not a
# "longest common subsequence" algorithm. The difference is that longest common
# subsequence does not require the bits to be contiguous.
#
# The longest common subsequence of "foolish" and "fools" is "fools".
# The longest common substring of "foolish" and "fools" is "fool".
try:
    from listdiffc import longest_common_subsequence as longest_common_substring
except ImportError:
    def longest_common_substring(seq1, seq2):
        """
        Given two sequences, calculates the longest common substring and returns
        a tuple of:
            (LCS length, LCS offset in seq1, LCS offset in seq2)
        """
        best_size, offset1, offset2 = half_longest_match(seq1, seq2)
        best_size, offset2, offset1 = half_longest_match(seq2, seq1, best_size, offset2, offset1)
        return best_size, offset1, offset2

    def half_longest_match(seq1, seq2, best_size=0, offset1=-1, offset2=-1):
        """
        Implements "one half" of the longest common substring algorithm.
        """
        len1 = len(seq1)
        len2 = len(seq2)
        i = 0 # seq2 index
        current_size = 0
        while i < len2:
            if best_size >= len2 - i:
                break # Short circuit
            j = i
            k = 0
            while k < len1 and j < len2:
                if seq1[k] == seq2[j]:
                    current_size += 1
                    if current_size >= best_size:
                        new_offset1 = k - current_size + 1
                        new_offset2 = j - current_size + 1
                        if current_size > best_size or (new_offset1 <= offset1 and new_offset2 <= offset2):
                            offset1 = new_offset1
                            offset2 = new_offset2
                        best_size = current_size
                else:
                    current_size = 0
                j += 1
                k += 1
            i += 1
            current_size = 0
        return best_size, offset1, offset2
