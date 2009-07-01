class Bunch(object):
    """
    A bunch is a list of objects which knows its center point,
    determined as the average of its objects' points. It's a useful
    data structure for clustering.
    """
    __slots__ = ["objects", "center", "points"]

    def __init__(self, obj, point):
        self.objects = []
        self.points = []
        self.center = (0, 0)
        self.add_obj(obj, point)

    def add_obj(self, obj, point):
        self.objects.append(obj)
        self.points.append(point)
        self.update_center(point)

    def update_center(self, point):
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        self.center = (sum(xs) * 1.0 / len(self.objects), sum(ys) * 1.0 / len(self.objects))

    def x(self):
        return self.center[0]
    x = property(x)

    def y(self):
        return self.center[1]
    y = property(y)
        
    def __repr__(self):
        objs = list.__repr__(self.objects[:3])
        if len(self.objects) > 3:
            objs = objs[:-1] + ", ...]"
        return u"<Bunch: %s, center: (%.3f, %.3f)>" % (objs, self.x, self.y)
