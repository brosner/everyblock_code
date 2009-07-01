"""
Coarse-graining data, AKA "binning".

We implement two methods of binning data, equal-size and equal-weight.
There are others, including zero-centered, mean-centered, and
median-centered.

Note that while we intend for the bins to be expose an interchangeable
interface---that is, each method of binning exposes the same interface
and the method of finding which bin a particular value is in is the
same---the semantics of determining a bin differs slightly by
implementation, and by intent.

The reason is that the high and low boundaries of equal-weight bins
break on the values of the actual data used to create the bins, and
therefore are always values found in the data, while the boundaries of
equal-size bins break on computed values determined by the initial data,
and therefore might not be found in the data. This has two implications::

    1. Adjacent equal-weight bins may be disjunct, that is, for example,
       the high value of a bin may not be equal to or very nearly equal
       to the low value of the next bin. This implies that only values
       found in the binned data should be used to determine a bin, and
       not an arbitrary value.
    2. You can determine a bin for an arbitrary value with equal-size
       bins, provided the value is between the lowest and highest
       boundary.
"""

from __future__ import division

class Bin(object):
    def __init__(self, min, max, data, last=False):
        # min and max may, for example in the case of equal-size, be
        # different than the min/max of the list of data values
        self.min = min
        self.max = max
        self.data = list(data)
        self.last = last

    def __contains__(self, x):
        if x in self.data or \
           (self.last and self.min <= x <= self.max) or \
           (not self.last and self.min <= x < self.max):
            return True
        return False

    def add(self, value):
        self.data.append(value)

    def __str__(self):
        return "(%s, %s)" % (self.min, self.max)

    def __repr__(self):
        return "<Bin %s>" % self.__str__()
    
class Bins(object):
    def __init__(self, values, n=4):
        self.n = n
        self.bins = []
        self.bin_data(values)

    def bin_data(self, values):
        raise NotImplementedError()

    def bin_value(self, value):
        for bin in self.bins:
            if value in bin:
                bin.add(value)

    def __len__(self):
        return len(self.bins)

    def which_bin(self, value):
        for i, bin in enumerate(self.bins):
            if value in bin:
                return i
        return None

    def __str__(self):
        return "[%s]" % ", ".join([str(b) for b in self.bins])

    def __repr__(self):
        return "<Bins %s>" % self.__str__()

class EqualSize(Bins):
    """
    Creates bins of equal interval between min and max.

    >>> values = [10, 13, 17, 32, 35, 40, 60, 64, 67]
    >>> bins = EqualSize(values, 3)
    >>> bins
    <Bins [(10.0, 29.0), (29.0, 48.0), (48.0, 67.0)]>
    >>> bins.which_bin(10.0)
    0
    >>> bins.which_bin(15)
    0
    >>> bins.which_bin(29.0)
    1
    >>> bins.which_bin(30)
    1
    >>> bins.which_bin(48.0)
    2
    >>> bins.which_bin(55)
    2
    >>> bins.which_bin(67.0)
    2
    >>> bins.which_bin(0)
    >>> bins.which_bin(67.1)
    """
    def bin_data(self, values):
        min_val = min(values)
        max_val = max(values)
        interval = (max_val - min_val) / self.n
        for i in xrange(self.n):
            last = i == self.n-1
            b1, b2 = (min_val + (interval * i)), (min_val + (interval * (i+1)))
            bin = Bin(b1, b2, [], last)
            self.bins.append(bin)
        for v in values:
            self.bin_value(v)

class EqualWeight(Bins):
    """
    Creates bins of roughly equal count of values.

    >>> values = [10, 13, 17, 32, 35, 40, 60, 64, 67]
    >>> bins = EqualWeight(values, 3)
    >>> bins
    <Bins [(10, 17), (32, 40), (60, 67)]>
    >>> bins.which_bin(10)
    0
    >>> bins.which_bin(15)
    0
    >>> bins.which_bin(17)
    0
    >>> bins.which_bin(32)
    1
    >>> bins.which_bin(36)
    1
    >>> bins.which_bin(40)
    1
    >>> bins.which_bin(60)
    2
    >>> bins.which_bin(63)
    2
    >>> bins.which_bin(67)
    2
    >>> bins.which_bin(0)
    >>> bins.which_bin(18)
    >>> bins.which_bin(41)
    >>> bins.which_bin(68)
    """
    def bin_data(self, values):
        values = sorted(list(values))
        num_vals = len(values)
        for i in xrange(self.n):
            lo, hi = int(i/self.n*num_vals), int((i+1)/self.n*num_vals-1)
            b1, b2 = values[lo], values[hi]
            last = i == self.n-1
            bin = Bin(b1, b2, values[lo:hi+1], last)
            self.bins.append(bin)

    def in_bin(self, bin, value):
        return bin[0] <= value <= bin[1]

if __name__ == "__main__":
    import doctest
    doctest.testmod()
