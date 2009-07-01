from django import template
import re

register = template.Library()

class FullLinksNode(template.Node):
    """
    Converts all <a href>s within {% full_links %} / {% end_full_links %} to
    use fully qualified URLs -- i.e., to start with 'http://'. Doesn't touch
    the ones that already start with 'http://'.
    """
    def __init__(self, nodelist, domain_var):
        self.nodelist = nodelist
        self.domain_var = template.Variable(domain_var)

    def render(self, context):
        domain = self.domain_var.resolve(context)
        output = self.nodelist.render(context)
        output = re.sub(r'(?i)(<a.*?\bhref=")/', r'\1http://%s/' % domain, output)
        return output

def do_full_links(parser, token):
    # {% full_links [domain] %} ... {% end_full_links %}
    args = token.contents.split()
    if len(args) != 2:
        raise template.TemplateSyntaxError("%r tag requires exactly one argument." % args[0])
    nodelist = parser.parse(('end_full_links',))
    parser.delete_first_token()
    return FullLinksNode(nodelist, args[1])
register.tag('full_links', do_full_links)
