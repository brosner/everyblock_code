from PIL import Image
from aggdraw import Draw, Pen, Brush

def make_marker(radius, fill_color, stroke_color, stroke_width, opacity=1.0):
    """
    Creates a map marker and returns a PIL image.

    radius
        In pixels

    fill_color
        Any PIL-acceptable color representation, but standard hex
        string is best

    stroke_color
        See fill_color

    stroke_width
        In pixels

    opacity
        Float between 0.0 and 1.0
    """
    # Double all dimensions for drawing. We'll resize back to the original
    # radius for final output -- it makes for a higher-quality image, especially
    # around the edges
    radius, stroke_width = radius * 2, stroke_width * 2
    diameter = radius * 2
    im = Image.new('RGBA', (diameter, diameter))
    draw = Draw(im)
    # Move in from edges half the stroke width, so that the stroke is not
    # clipped.
    half_stroke_w = (stroke_width / 2 * 1.0) + 1
    min_x, min_y = half_stroke_w, half_stroke_w
    max_x = diameter - half_stroke_w
    max_y = max_x
    bbox = (min_x, min_y, max_x, max_y)
    # Translate opacity into aggdraw's reference (0-255)
    opacity = int(opacity * 255)
    draw.ellipse(bbox,
                 Pen(stroke_color, stroke_width, opacity),
                 Brush(fill_color, opacity))
    draw.flush()
    # The key here is to resize using the ANTIALIAS filter, which is very
    # high-quality
    im = im.resize((diameter / 2, diameter / 2), Image.ANTIALIAS)
    return im
