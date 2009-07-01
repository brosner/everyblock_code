class Color(object):
    def __init__(self, r, g, b):
        for x in [r, g, b]:
            if not isinstance(x, int):
                raise RuntimeError, 'expected int got %s (%s)' % (type(x), x)
        self.r = r
        self.g = g
        self.b = b

    @classmethod
    def from_hex(cls, color_hex):
        """
        Parses a hex color code, like "#cc00ff"

        >>> Color.from_hex('#cc6699')
        <Color r(204), g(102), b(153)>
        >>> Color.from_hex('33ddee')
        <Color r(51), g(221), b(238)>
        >>> Color.from_hex('#c69')
        <Color r(204), g(102), b(153)>
        >>> Color.from_hex('c69')
        <Color r(204), g(102), b(153)>
        """
        if color_hex.startswith('#'):
            color_hex = color_hex[1:]
        if len(color_hex) == 3:
            # Shortcut hex: 'c69' -> 'cc6699'
            color_hex = ''.join((color_hex[i] * 2 for i in xrange(3)))
        r, g, b = map(lambda x: int(x, 16),
                      (color_hex[i*2:(i*2)+2] for i in xrange(3)))
        return cls(r, g, b)

    def to_hex(self):
        """
        >>> Color(r=204, g=102, b=153).to_hex()
        'cc6699'
        >>> Color(r=0, g=0, b=255).to_hex()
        '0000ff'
        """
        return '%02x%02x%02x' % (self.r, self.g, self.b)

    def __str__(self):
        return self.to_hex()

    def __repr__(self):
        return '<Color r(%s), g(%s), b(%s)>' % (self.r, self.g, self.b)

class ColorSpread(object):
    """
    Generates intermediate color values between two endpoints.

    Moves linearly in the color space.

    >>> spread = ColorSpread(Color.from_hex('#ff3399'), Color.from_hex('#33ff99'), 2)
    >>> for color in spread:
    ...     str(color)
    'ff3399'
    '999999'
    '33ff99'
    """
    def __init__(self, start, end, steps):
        self.start = start
        self.end = end
        self.steps = steps

    def __iter__(self):
        for i in xrange(self.steps + 1):
            if i == self.steps:
                yield self.end
                break
            color_parts = {}
            for comp in ['r', 'g', 'b']:
                start = getattr(self.start, comp)
                delta = getattr(self.end, comp) - start
                inc = int(1.0 * delta / self.steps)
                color_parts[comp] = start + (i * inc)
            yield Color(**color_parts)

def color_spread(start_hex, end_hex, steps):
    for color in ColorSpread(Color.from_hex(start_hex), Color.from_hex(end_hex), steps):
        yield color

if __name__ == '__main__':
    import doctest
    doctest.testmod()
