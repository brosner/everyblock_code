"""
Map marker clustering

We need to know:

    + List of points (in lat/lng)

    + List of map resolutions

    + Size of buffer, and how to translate it into lat/lng
"""

import math
from bunch import Bunch # relative import

def euclidean_distance(a, b):
    """
    Calculates the Euclidean distance between two points.

    Assumes (x, y) pairs.
    """
    return math.hypot(a[0] - b[0], a[1] - b[1])

def buffer_cluster(objects, radius, dist_fn=euclidean_distance):
    """
    Clusters objects into bunches within a buffer by a given radius.

    Differs from k-means clustering in that the number of bunches is
    not known before the program is run or given as an argument: a
    "natural" number of bunches is returned, depending on whether a
    point falls within a buffer. The number of bunches is inversely
    proportional to the size of the buffer: the larger the buffer,
    the fewer number of bunches (but the larger the number of points
    contained in each bunch).

    Similar to k-means clustering in that it calculates a new center
    point for each bunch on each iteration, eventually arriving at
    a steady state.

    I'm just calling it 'buffer clustering': this may be called
    something else for real and there may be a better implementation,
    but I don't know better!

    ``objects`` is a dict with keys for ID some domain object, and 
    the values being 2-tuples representing their points on a 
    coordinate system.
    """
    bunches = []
    buffer = radius
    for key, point in objects.iteritems():
        bunched = False
        for bunch in bunches:
            if dist_fn(point, bunch.center) <= buffer:
                bunch.add_obj(key, point)
                bunched = True
                break
        if not bunched:
            bunches.append(Bunch(key, point))
    return bunches
