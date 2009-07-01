import sys
import time
import threading

lock = threading.RLock()

class ProgressBar(object):
    """
    12% [====                ]

    >>> pbar = ProgressBar(0, 99)
    >>> pbar(0)
    >>> pbar(1) # &c.
    """
    def __init__(self, min_val, max_val, width=40, stdout=None):
        self.min_val = min_val
        self.max_val = max_val
        self.width = width
        self.current = min_val
        self.char = '='
        if stdout is None:
            stdout = sys.stdout
        self.stdout = stdout

    def _percent_complete(self):
        return float(self.current - self.min_val) / (self.max_val - self.min_val)

    def bar(self):
        num_hash_marks = int(round(self.width * self._percent_complete()))
        bar = '[' + num_hash_marks * self.char + (self.width - num_hash_marks) * ' ' + ']'
        return '%3.f%% %s' % (self._percent_complete() * 100, bar)

    def __str__(self):
        return self.bar()

    def __call__(self, current):
        lock.acquire()
        try:
            self.current = current
            self.stdout.write('\r')
            self.stdout.write(str(self))
            self.stdout.flush()
        finally:
            lock.release()

class TimedProgressBar(ProgressBar):
    """
    ETA 00:06:28 12% [====                ]

    >>> pbar = TimedProgressBar(0, 99)
    >>> pbar.start()
    >>> pbar(0)
    >>> pbar(1) # &c.
    """
    def __init__(self, min_val, max_val, show_rate=True, width=40, stdout=None):
        ProgressBar.__init__(self, min_val, max_val, width, stdout)
        self.show_rate = True
        self.start_time = None
        self.last_time = None
        self.eta = (0, 0, 0) # (hours, minutes, seconds) est. remaining

    def start(self):
        self.start_time = self.last_time = time.time()

    def __str__(self):
        if self.show_rate:
            rate = ' (%.1f/sec)' % self.rate
        else:
            rate = ''
        return 'ETA %02d:%02d:%02d %s%s' % (self.eta[0], self.eta[1], self.eta[2],
                                            ProgressBar.__str__(self), rate)

    def __call__(self, current):
        if self.start_time is None:
            raise RuntimeError('must call .start()')
        lock.acquire()
        try:
            self.last_time = time.time()
            elapsed = self.last_time - self.start_time
            rate = (self.current - self.min_val) / elapsed
            self.rate = rate
            eta_seconds = (self.max_val - self.current) * rate
            hours = eta_seconds / 3600
            minutes = (eta_seconds % 3600) / 60
            seconds = eta_seconds % 60
            self.eta = (hours, minutes, seconds)
            ProgressBar.__call__(self, current)
        finally:
            lock.release()

if __name__ == '__main__':
    import random
    pb = TimedProgressBar(0, 99)
    pb.start()
    for i in xrange(100):
        time.sleep(1 + random.random()/2)
        pb(i)
