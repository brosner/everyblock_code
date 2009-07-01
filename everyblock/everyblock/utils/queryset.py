def batch(qs, size=1000):
    total = qs.count()
    for start in range(0, total, size):
        end = min(start + size, total)
        yield (start, end, total, qs[start:end])
