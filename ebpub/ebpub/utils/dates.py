import datetime
import time

def daterange(d1, d2):
    "Iterator that returns every date between d1 and d2, inclusive."
    current = d1
    while current <= d2:
        yield current
        current += datetime.timedelta(days=1)

def parse_date(value, format, return_datetime=False):
    """
    Equivalent to time.strptime, but it returns a datetime.date or
    datetime.datetime object instead of a struct_time object.

    Returns None if the value evaluates to False.
    """
    # See http://docs.python.org/lib/node85.html
    idx = return_datetime and 7 or 3
    func = return_datetime and datetime.datetime or datetime.date
    if value:
        return func(*time.strptime(value, format)[:idx])
    return None

def parse_time(value, format):
    """
    Equivalent to time.strptime, but it returns a datetime.time object.
    """
    return datetime.time(*time.strptime(value, format)[3:6])
