from django.shortcuts import render_to_response
from django.template.context import RequestContext

def eb_render(request, *args, **kwargs):
    """
    Replacement for render_to_response that uses RequestContext and sets an
    extra template variable, TEMPLATE_NAME.
    """
    kwargs['context_instance'] = RequestContext(request)
    return render_to_response(*args, **kwargs)
