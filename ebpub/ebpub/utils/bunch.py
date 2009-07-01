import math

# From http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/425044
def bunch(lst, size):
    size = int(size)
    return [lst[i:i+size] for i in range(0, len(lst), size)]

def bunchlong(lst, size):
    size = float(int(size))
    return bunch(lst, int(math.ceil(len(lst) / size)))

def stride(lst, size):
    """
    >>> stride([1, 2, 3, 4, 5, 6], 2)
    [[1, 3, 5], [2, 4, 6]]
    >>> stride([1, 2, 3, 4, 5], 2)
    [[1, 3, 5], [2, 4]]
    >>> stride([1, 2, 3, 4, 5], 1)
    [[1, 2, 3, 4, 5]]
    >>> stride([1, 2, 3, 4, 5, 6], 3)
    [[1, 4], [2, 5], [3, 6]]
    >>> stride([1, 2, 3, 4, 5, 6, 7], 3)
    [[1, 4, 7], [2, 5], [3, 6]]
    """
    size = int(size)
    return [lst[i::size] for i in range(size)]

if __name__ == "__main__":
    import doctest
    doctest.testmod()
