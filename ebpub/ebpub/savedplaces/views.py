from django import http
from django.utils import simplejson
from ebpub.db.views import parse_pid
from ebpub.savedplaces.models import SavedPlace
from ebpub.streets.models import Block

def ajax_save_place(request):
    """
    Creates a SavedPlace for request.POST['pid'] and request.user.
    """
    if request.method != 'POST':
        raise http.Http404()
    if 'pid' not in request.POST:
        raise http.Http404('Missing pid')
    if not request.user:
        raise http.Http404('Not logged in')

    place, block_radius, xy_radius = parse_pid(request.POST['pid'])
    kwargs = {'user_id': request.user.id}
    if isinstance(place, Block):
        block, location = place, None
        kwargs['block__id'] = place.id
    else:
        block, location = None, place
        kwargs['location__id'] = place.id

    # Validate that the SavedPlace hasn't already been created for this user,
    # to avoid duplicates.
    try:
        sp = SavedPlace.objects.get(**kwargs)
    except SavedPlace.DoesNotExist:
        pass
    else:
        return http.HttpResponse('0') # Already exists.

    SavedPlace.objects.create(
        user_id=request.user.id,
        block=block,
        location=location,
        nickname=request.POST.get('nickname', '').strip(),
    )
    return http.HttpResponse('1')

def ajax_remove_place(request):
    """
    Removes the SavedPlace for request.POST['pid'] and request.user.
    """
    if request.method != 'POST':
        raise http.Http404()
    if 'pid' not in request.POST:
        raise http.Http404('Missing pid')
    if not request.user:
        raise http.Http404('Not logged in')

    place, block_radius, xy_radius = parse_pid(request.POST['pid'])
    kwargs = {'user_id': request.user.id}
    if isinstance(place, Block):
        block, location = place, None
        kwargs['block__id'] = place.id
    else:
        block, location = None, place
        kwargs['location__id'] = place.id

    SavedPlace.objects.filter(**kwargs).delete()
    return http.HttpResponse('1')

def json_saved_places(request):
    """
    Returns JSON of SavedPlaces for request.user, or an empty list
    if the user isn't logged in.
    """
    if not request.user:
        result = []
    else:
        result = [{'name': sp.place.pretty_name, 'url': sp.place.url()} for sp in SavedPlace.objects.filter(user_id=request.user.id)]
    return http.HttpResponse(simplejson.dumps(result), mimetype='application/javascript')
