from django import template

register = template.Library()

def raw(parser, token):
    # Whatever is between {% raw %} and {% endraw %} will be preserved as
    # raw, unrendered template code.
    # If 'silent' is passed in -- {% raw silent %} -- then the resulting output
    # will not contain the {% raw %} and {% endraw %} tags themselves.
    # Otherwise, the output will include an {% endraw %} at the start and
    # {% raw %} at the end, so that other parts of the page aren't vulnerable
    # to Django template escaping injection.
    silent = 'silent' in token.contents
    if silent:
        text = []
    else:
        text = ['{% endraw %}']
    parse_until = 'endraw'
    tag_mapping = {
        template.TOKEN_TEXT: ('', ''),
        template.TOKEN_VAR: ('{{', '}}'),
        template.TOKEN_BLOCK: ('{%', '%}'),
        template.TOKEN_COMMENT: ('{#', '#}'),
    }
    # By the time this template tag is called, the template system has already
    # lexed the template into tokens. Here, we loop over the tokens until
    # {% endraw %} and parse them to TextNodes. We have to add the start and
    # end bits (e.g. "{{" for variables) because those have already been
    # stripped off in a previous part of the template-parsing process.
    while parser.tokens:
        token = parser.next_token()
        if token.token_type == template.TOKEN_BLOCK and token.contents == parse_until:
            if not silent:
                text.append('{% raw silent %}')
            return template.TextNode(u''.join(text))
        start, end = tag_mapping[token.token_type]
        text.append(u'%s%s%s' % (start, token.contents, end))
    parser.unclosed_block_tag(parse_until)
raw = register.tag(raw)
