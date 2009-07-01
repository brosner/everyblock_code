"""
Django URL resolvers that take into account the value of get_metro().

TODO: Currently, get_metro() is called and calculated each time through the
URL patterns, which could be inefficient. Look for a better way of doing this.
"""

from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import RegexURLPattern
from ebpub.metros.allmetros import get_metro

class MulticityRegexURLPattern(RegexURLPattern):
    def resolve(self, path):
        if not get_metro()['multiple_cities']:
            return None
        return RegexURLPattern.resolve(self, path)

class SinglecityRegexURLPattern(RegexURLPattern):
    def resolve(self, path):
        if get_metro()['multiple_cities']:
            return None
        return RegexURLPattern.resolve(self, path)

def metro_patterns(multi, single):
    pattern_list = []
    for t in multi:
        pattern_list.append(url(MulticityRegexURLPattern, *t))
    for t in single:
        pattern_list.append(url(SinglecityRegexURLPattern, *t))
    return pattern_list

def url(klass, regex, view, kwargs=None, name=None, prefix=''):
    if type(view) == list:
        # For include(...) processing.
        return RegexURLResolver(regex, view[0], kwargs)
    else:
        if isinstance(view, basestring):
            if not view:
                raise ImproperlyConfigured('Empty URL pattern view name not permitted (for pattern %r)' % regex)
            if prefix:
                view = prefix + '.' + view
        return klass(regex, view, kwargs, name)
