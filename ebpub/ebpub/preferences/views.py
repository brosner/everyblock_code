from django import http
from ebpub.db.models import Schema
from ebpub.preferences.models import HiddenSchema

def ajax_save_hidden_schema(request):
    """
    Creates a HiddenSchema for request.POST['schema'] and request.user.
    """
    if request.method != 'POST':
        raise http.Http404()
    if 'schema' not in request.POST:
        raise http.Http404('Missing schema')
    if not request.user:
        raise http.Http404('Not logged in')

    # Validate that the HiddenSchema hasn't already been created for this user,
    # to avoid duplicates.
    try:
        schema = Schema.public_objects.get(slug=request.POST['schema'])
        sp = HiddenSchema.objects.get(user_id=request.user.id, schema=schema)
    except Schema.DoesNotExist:
        return http.HttpResponse('0') # Schema doesn't exist.
    except HiddenSchema.DoesNotExist:
        pass
    else:
        return http.HttpResponse('0') # Already exists.

    HiddenSchema.objects.create(user_id=request.user.id, schema=schema)
    return http.HttpResponse('1')

def ajax_remove_hidden_schema(request):
    """
    Removes the HiddenSchema for request.POST['schema'] and request.user.
    """
    if request.method != 'POST':
        raise http.Http404()
    if 'schema' not in request.POST:
        raise http.Http404('Missing schema')
    if not request.user:
        raise http.Http404('Not logged in')

    try:
        hidden_schema = HiddenSchema.objects.filter(user_id=request.user.id, schema__slug=request.POST['schema'])
    except HiddenSchema.DoesNotExist:
        # The schema didn't exist. This is a no-op.
        return http.HttpResponse('0')
    hidden_schema.delete()
    return http.HttpResponse('1')
