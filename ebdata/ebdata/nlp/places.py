import re
from ebpub.db.models import Location
from ebpub.streets.models import Place, Misspelling

def phrase_tagger(phrases, pre='<span>', post='</span>'):
    # Sort the phrases and then reverse them so, for example, Lake View East
    # will come before Lake View in the regex, and will match more greedily.
    # Use the decorate-sort-undecorate pattern and then list.reverse() to
    # avoid the overhead of calling a custom comparison function.
    decorated = [(len(p), p) for p in phrases]
    decorated.sort()
    decorated.reverse()
    phrases = [i[1] for i in decorated]
    # use a closure here to cache the value for phrases
    def tag_phrases(text):
        """
        Returns text with any matches from phrases wrapped with pre and post.
        """
        # If no phrases were provided, just return the text we received.
        if len(phrases) == 0:
            return text

        def _re_handle_match(m):
            output = (m.group(1) or '') + m.group(2) + (m.group(3) or '')
            if m.group(1) and m.group(3):
                return output
            return pre + output + post
        phrases_re = '|'.join([r'\b%s\b' % re.escape(p) for p in phrases])

        # In addition to identifying every phrase, this regex grabs the "pre"
        # and "post" before the phrase, optionally. Then the _re_handle_match()
        # function checks whether the "pre" and "post" were provided. If both
        # were found, that means this phrase was already tagged (perhaps by
        # tag_addresses(), and thus the new tags aren't inserted. Note that
        # this assumes that each tagging of the text (whether it's
        # tag_addresses(), place_tagger() or location_tagger()) uses a
        # consistent "pre" and "post".
        return re.sub('(?i)(%s[^<]*)?(%s)([^<]*%s)?' % \
            (re.escape(pre), phrases_re, re.escape(post)), _re_handle_match, text)

    return tag_phrases

def place_tagger(pre='<addr>', post='</addr>'):
    phrases = [p['pretty_name'] for p in Place.objects.values('pretty_name').order_by('-pretty_name')]
    return phrase_tagger(phrases, pre, post)

def location_tagger(pre='<addr>', post='</addr>'):
    location_qs = Location.objects.values('name').order_by('-name').exclude(location_type__slug__in=('boroughs', 'cities'))
    locations = [p['name'] for p in location_qs]
    misspellings = [m['incorrect'] for m in Misspelling.objects.values('incorrect').order_by('-incorrect')]
    return phrase_tagger(locations + misspellings, pre, post)
