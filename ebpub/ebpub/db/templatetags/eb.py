from ebpub.db.models import NewsItem, SchemaField
from ebpub.db.utils import populate_attributes_if_needed
from ebpub.utils.bunch import bunch, bunchlong, stride
from ebpub.metros.allmetros import METRO_LIST, get_metro
from django import template
from django.conf import settings
from django.template.defaultfilters import stringfilter
from django.template.loader import select_template
from django.conf import settings
import datetime

register = template.Library()

register.filter('bunch', bunch)
register.filter('bunchlong', bunchlong)
register.filter('stride', stride)

def METRO_NAME():
    return get_metro()['metro_name']
register.simple_tag(METRO_NAME)

def SHORT_NAME():
    return settings.SHORT_NAME
register.simple_tag(SHORT_NAME)

def STATE_ABBREV():
    return get_metro()['state']
register.simple_tag(STATE_ABBREV)

def EB_SUBDOMAIN():
    return '%s.%s' % (settings.SHORT_NAME, settings.EB_DOMAIN)
register.simple_tag(EB_SUBDOMAIN)

def isdigit(value):
    return value.isdigit()
isdigit = stringfilter(isdigit)
register.filter('isdigit', isdigit)

def lessthan(value, arg):
    return int(value) < int(arg)
register.filter('lessthan', lessthan)

def greaterthan(value, arg):
    return int(value) > int(arg)
register.filter('greaterthan', greaterthan)

def schema_plural_name(schema, value):
    if isinstance(value, (list, tuple)):
        value = len(value)
    return (value == 1) and schema.name or schema.plural_name
register.simple_tag(schema_plural_name)

def safe_id_sort(value, arg):
    """
    Like Django's built-in "dictsort", but sorts second by the ID attribute, to
    ensure sorts always end up the same.
    """
    var_resolve = template.Variable(arg).resolve
    decorated = [(var_resolve(item), item.id, item) for item in value]
    decorated.sort()
    return [item[2] for item in decorated]
safe_id_sort.is_safe = False
register.filter('safe_id_sort', safe_id_sort)

def safe_id_sort_reversed(value, arg):
    var_resolve = template.Variable(arg).resolve
    decorated = [(var_resolve(item), item.id, item) for item in value]
    decorated.sort()
    decorated.reverse()
    return [item[2] for item in decorated]
safe_id_sort_reversed.is_safe = False
register.filter('safe_id_sort_reversed', safe_id_sort_reversed)

def friendlydate(value):
    try: # Convert to a datetime.date, if it's a datetime.datetime.
        value = value.date()
    except AttributeError:
        pass
    today = datetime.date.today()
    if value == today:
        return 'today'
    elif value == today - datetime.timedelta(1):
        return 'yesterday'
    elif today - value <= datetime.timedelta(6):
        return value.strftime('%A')
    return '%s %s' % (value.strftime('%B'), value.day)
register.filter('friendlydate', friendlydate)

class GetMetroListNode(template.Node):
    def render(self, context):
        context['METRO_LIST'] = METRO_LIST
        return ''

def do_get_metro_list(parser, token):
    # {% get_metro_list %}
    return GetMetroListNode()
register.tag('get_metro_list', do_get_metro_list)

class GetMetroNode(template.Node):
    def render(self, context):
        context['METRO'] = get_metro()
        return ''

def do_get_metro(parser, token):
    # {% get_metro %}
    return GetMetroNode()
register.tag('get_metro', do_get_metro)

class GetNewsItemNode(template.Node):
    def __init__(self, newsitem_variable, context_var):
        self.variable = template.Variable(newsitem_variable)
        self.context_var = context_var

    def render(self, context):
        newsitem_id = self.variable.resolve(context)
        try:
            context[self.context_var] = NewsItem.objects.select_related().get(id=newsitem_id)
        except NewsItem.DoesNotExist:
            pass
        return ''

def do_get_newsitem(parser, token):
    # {% get_newsitem [id_or_var_containing_id] as [context_var] %}
    bits = token.split_contents()
    if len(bits) != 4:
        raise template.TemplateSyntaxError('%r tag requires 3 arguments' % bits[0])
    return GetNewsItemNode(bits[1], bits[3])
register.tag('get_newsitem', do_get_newsitem)

class GetNewerNewsItemNode(template.Node):
    def __init__(self, newsitem_variable, newsitem_list_variable, context_var):
        self.newsitem_var = template.Variable(newsitem_variable)
        self.newsitem_list_var = template.Variable(newsitem_list_variable)
        self.context_var = context_var

    def render(self, context):
        newsitem = self.newsitem_var.resolve(context)
        newsitem_list = self.newsitem_list_var.resolve(context)
        if newsitem_list and newsitem_list[0].item_date > newsitem.item_date:
            context[self.context_var] = newsitem_list[0]
        else:
            context[self.context_var] = None
        return ''

def do_get_newer_newsitem(parser, token):
    # {% get_more_recent_newsitem [newsitem] [comparison_list] as [context_var] %}
    bits = token.split_contents()
    if len(bits) != 5:
        raise template.TemplateSyntaxError('%r tag requires 4 arguments' % bits[0])
    return GetNewerNewsItemNode(bits[1], bits[2], bits[4])
register.tag('get_newer_newsitem', do_get_newer_newsitem)

class GetNewsItemListByAttributeNode(template.Node):
    def __init__(self, schema_id_variable, newsitem_id_variable, att_name, att_value_variable, context_var):
        self.schema_id_variable = template.Variable(schema_id_variable)
        self.newsitem_id_variable = template.Variable(newsitem_id_variable)
        self.att_name = att_name
        self.att_value_variable = template.Variable(att_value_variable)
        self.context_var = context_var

    def render(self, context):
        schema_id = self.schema_id_variable.resolve(context)
        newsitem_id = self.newsitem_id_variable.resolve(context)
        att_value = self.att_value_variable.resolve(context)
        sf = SchemaField.objects.select_related().get(schema__id=schema_id, name=self.att_name)
        ni_list = NewsItem.objects.select_related().filter(schema__id=schema_id).exclude(id=newsitem_id).by_attribute(sf, att_value).order_by('-item_date')
        populate_attributes_if_needed(ni_list, [sf.schema])

        # We're assigning directly to context.dicts[-1] so that the variable
        # gets set in the top-most context in the context stack. If we didn't
        # do this, the variable would only be available within the specific
        # {% block %} from which the template tag was called, because the
        # {% block %} implementation does a context.push() and context.pop().
        context.dicts[-1][self.context_var] = ni_list

        return ''

def do_get_newsitem_list_by_attribute(parser, token):
    # {% get_newsitem_list_by_attribute [schema_id] [newsitem_id_to_ignore] [att_name]=[value_or_var_containing_value] as [context_var] %}
    # {% get_newsitem_list_by_attribute schema.id newsitem.id business_id=attributes.business_id as other_licenses %}
    bits = token.split_contents()
    if len(bits) != 6:
        raise template.TemplateSyntaxError('%r tag requires 5 arguments' % bits[0])
    if bits[3].count('=') != 1:
        raise template.TemplateSyntaxError('%r tag third argument must contain 1 equal sign' % bits[0])
    att_name, att_value_variable = bits[3].split('=')
    return GetNewsItemListByAttributeNode(bits[1], bits[2], att_name, att_value_variable, bits[5])
register.tag('get_newsitem_list_by_attribute', do_get_newsitem_list_by_attribute)

class NewsItemListBySchemaNode(template.Node):
    def __init__(self, newsitem_list_variable, is_ungrouped):
        self.variable = template.Variable(newsitem_list_variable)
        self.is_ungrouped = is_ungrouped

    def render(self, context):
        ni_list = self.variable.resolve(context)

        # For convenience, the newsitem_list might just be a single newsitem,
        # in which case we turn it into a list.
        if isinstance(ni_list, NewsItem):
            ni_list = [ni_list]

        schema = ni_list[0].schema
        template_list = ['db/snippets/newsitem_list/%s.html' % schema.slug,
                         'db/snippets/newsitem_list.html']
        schema_template = select_template(template_list)
        return schema_template.render(template.Context({
            'is_grouped': not self.is_ungrouped,
            'schema': schema,
            'newsitem_list': ni_list,
            'num_newsitems': len(ni_list),
            'place': context.get('place'),
            'is_block': context.get('is_block'),
            'block_radius': context.get('block_radius'),
        }))

def do_newsitem_list_by_schema(parser, token):
    # {% newsitem_list_by_schema [newsitem_or_newsitem_list] [ungrouped?] %}
    bits = token.split_contents()
    if len(bits) not in (2, 3):
        raise template.TemplateSyntaxError('%r tag requires one or two arguments' % bits[0])
    if len(bits) == 3:
        if bits[2] != 'ungrouped':
            raise template.TemplateSyntaxError('Optional last argument to %r tag must be the string "ungrouped"' % bits[0])
        is_ungrouped = True
    else:
        is_ungrouped = False
    return NewsItemListBySchemaNode(bits[1], is_ungrouped)
register.tag('newsitem_list_by_schema', do_newsitem_list_by_schema)

def contains(value, arg):
    return arg in value
register.filter('contains', contains)
