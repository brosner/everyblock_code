import re

def regex_tagger(regex, field_name, index=None, classes=[]):
    def tag_data(data):
        classes.extend(['locationdetected', 'field-%s' % index])
        pre = '<a href="#" class="%s" field="%s-input">' % (' '.join(classes), field_name)
        post = '</a>'
        return re.sub(regex, lambda m: pre + m.group(0) + post, data)
    return tag_data

def lookup_tagger(field, index=None, classes=[]):
    from ebdata.nlp.places import phrase_tagger
    def tag_data(data):
        phrases = [p['name'] for p in field.lookup_set.values('name')]
        classes.extend(['locationdetected', 'field-%s' % index])
        pre = '<a href="#" class="%s" field="%s-input">' % (' '.join(classes), field.name)
        post = '</a>'
        tag_phrases = phrase_tagger(phrases, pre, post)
        return tag_phrases(data)
    return tag_data

class SFZoningAgendasExtractor(object):
    fields = (
        {'name': 'description', 'required': True},
        {'name': 'agenda_item', 'required': True, 'persist': True},
        {'name': 'case_number', 'required': True},
        {'name': 'action_requested', 'required': True},
        {'name': 'preliminary_recommendation', 'required': False},
    )

    def get_title(self, location, attrs):
        return '%s at %s' % (attrs['action_requested'].name, location)

    def get_description(self, location, attrs):
        return ''

    def extract_data(self, blob):
        from lxml.etree import tostring
        from lxml.html import document_fromstring
        from ebdata.textmining.treeutils import preprocess

        tree = document_fromstring(blob.html).xpath("//div[@id='contents']")[0]
        tree = preprocess(tree,
            drop_tags=('a', 'area', 'b', 'center', 'font', 'form', 'img', 'input', 'map', 'small', 'span', 'sub', 'sup', 'topic', 'u'),
            drop_trees=('applet', 'button', 'embed', 'iframe', 'object', 'select', 'textarea'),
            drop_attrs=('background', 'border', 'cellpadding', 'cellspacing', 'class', 'clear', 'id', 'rel', 'style', 'target'))
        html = tostring(tree, method='html')
        # Remove non breaking spaces (&nbsp; and &#160;) so tagging regexes
        # can be less complicated
        return html.replace('&nbsp;', ' ').replace('&#160;', ' ')

    def tag_data(self, data):
        data = self.tag_addresses(data)
        for f in self.fields:
            tagger = getattr(self, 'tag_%s' % f['name'], None)
            if tagger is None:
                continue
            data = tagger(data)
        return data

    def tag_addresses(self, data):
        regex = r'(?i)(\d+[\b|\s+\-\s+][\d\w\s]+\b)(STREET|AVENUE|BOULEVARD|DRIVE)'
        tag_data = regex_tagger(regex, 'location', 1, classes=['location'])
        return tag_data(data)

    def get_date(self, blob):
        """
        Return the date to be used for a NewsItem.
        """
        from ebpub.utils.dates import parse_date
        # Dates are generally in a format like January 15, 2008, and sometimes
        # followed by other text. Pull out the date part so we can parse it.
        date_match = re.search(r'(\w+\s*\d{1,2}\s*,\s*\d{4})', blob.title)
        if date_match is None:
            return ''
        else:
            date_string = date_match.group(1)
            return parse_date(date_string, '%B %d, %Y')

    def tag_agenda_item(self, data):
        from ebpub.db.models import SchemaField
        field = SchemaField.objects.get(schema__slug='zoning-minutes', name='agenda_item')
        tag_phrases = lookup_tagger(field, 0)
        return tag_phrases(data)

    def tag_case_number(self, data):
        regex = r'(\d{4}\.[\w\d]{4,})'
        tag_data = regex_tagger(regex, 'case_number', 1)
        return tag_data(data)

    def tag_action_requested(self, data):
        from ebpub.db.models import SchemaField
        field = SchemaField.objects.get(schema__slug='zoning-minutes', name='action_requested')
        tag_phrases = lookup_tagger(field, 0)
        return tag_phrases(data)

    def tag_preliminary_recommendation(self, data):
        regex = r'(?i)(Preliminary Recommendation:\s*)([\w\s]+)(\n*<)' # still not working all the time
        pre = '<a href="#" class="locationdetected" field="preliminary_recommendation-input">'
        post = '</a>'
        def _temp2(match):
            return match.group(1) + pre + match.group(2) + post + match.group(3)
        return re.sub(regex, _temp2, data)

class SFZoningMinutesExtractor(SFZoningAgendasExtractor):
    fields = (
        {'name': 'description', 'required': True},
        {'name': 'agenda_item', 'required': True, 'persist': True},
        {'name': 'case_number', 'required': True},
        {'name': 'action_requested', 'required': True},
        {'name': 'preliminary_recommendation', 'required': False},
        {'name': 'action', 'required': False},
    )

    def tag_action(self, data):
        regex = r'(?i)(ACTION:\s*)([\w\s]+)(\n*<)'
        pre = '<a href="#" class="locationdetected" field="action-input">'
        post = '</a>'
        def _temp2(match):
            return match.group(1) + pre + match.group(2) + post + match.group(3)
        return re.sub(regex, _temp2, data)
