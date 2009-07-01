from __future__ import division
import math

def normalize(min_val, max_val):
    """
    Maps a value to a range between 0.0 and 1.0.

    >>> n = normalize(5, 45)
    >>> n(25)
    0.5
    >>> L = [23, 34, 23, 38, 35, 17, 15, 25, 19, 10]
    >>> ['%.3f' % n(i) for i in L] # doctest: +NORMALIZE_WHITESPACE
    ['0.450', '0.725', '0.450', '0.825', '0.750', '0.300', '0.250', '0.500',
    '0.350', '0.125']
    >>> n(5)
    0.0
    >>> n(45)
    1.0
    >>> n(4)
    0.0
    >>> n(46)
    1.0
    """
    def f(value, clip=True):
        if min_val == max_val:
            return 0.0
        if clip:
            if value <= min_val:
                return 0.0
            elif value >= max_val:
                return 1.0
        return (value - min_val) * (1.0 / (max_val - min_val))

    return f

def mean(values):
    if len(values) == 0:
        return 0.0
    return sum(values) / len(values)

def sliding_window(values, N):
    """
    Generator of a slice of a list of values of length N, that starts
    at the beginning and slides along yielding ranges until it runs
    out of room.

    Example, with N == 3:
    
    ['a', 'b', 'c', 'd', 'e']
      ^    ^    ^             -> ['a', 'b', 'c']
           ^    ^    ^        -> ['b', 'c', 'd']
                ^    ^    ^   -> ['c', 'd', 'e']
    """
    i, j = 0, N-1
    len_values = len(values)
    while (j < len_values):
        yield values[i:j]
        i += 1
        j += 1
    
def moving_function(values, N, f):
    return [f(v) for v in sliding_window(values, N)]

def moving_average(values, N):
    """
    Calculates the N-moving average of a list of data points.
    
    Assumes `values' is sorted.
    """
    return moving_function(values, N, mean)

def moving_sum(values, N):
    return moving_function(values, N, sum)

def variance(values):
    """
    Calculates the variance, or the mean deviation of a list of values
    from the mean.
    """
    if len(values) == 0:
        return 0.0
    mean_ = mean(values)
    return sum(math.pow(X - mean_, 2) for X in values) / len(values)

def stddev(values):
    """
    Calculates the standard deviation of a list of values.

    Standard deviation is the square root of the variance.
    """
    return math.sqrt(variance(values))

def percent_within_stddev(values, N=1):
    """
    Calculates the percentage of values that lie within N standard
    deviations of the mean.

    The 68-95-99.7 rule (aka three sigma rule, or empirical rule),
    tells us that almost all values in a normal distribution lie
    within 3 standard deviations of the mean.
    """
    mean_ = mean(values)
    stddev_ = stddev(values)
    num_within = len([v for v in values
                      if (v - stddev_ * N) <= mean_ and (v + stddev_ * N) >= mean_])
    return num_within / len(values)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
