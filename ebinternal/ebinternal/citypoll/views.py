from django.db.models import Count
from django.http import Http404, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.utils import simplejson as json
from ebinternal.citypoll.models import Vote, City
import datetime

def save_feedback(request):
    # Meant to be called as an Ajax request; no response.
    if request.META.get('CONTENT_TYPE') == 'application/json':
        data = json.loads(request.raw_post_data)
        city_text = data['city'].strip()
        email = data['email'].strip().lower()
    else:
        if not (request.POST.get('city') and request.POST.get('email')):
            raise Http404('City or email is missing')
        city_text = request.POST['city'].strip()
        email = request.POST['email'].strip().lower()

    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '') or request.META.get('REMOTE_ADDR', '')

    # Ignore duplicate feedbacks.
    try:
        v = Vote.objects.get(city_text=city_text, email=email)
    except Vote.DoesNotExist:
        v = Vote.objects.create(
            city=None,
            city_text=city_text,
            email=email,
            notes=request.POST.get('notes', '').strip(),
            ip_address=ip_address,
            date_received=datetime.datetime.now(),
        )
    return HttpResponse('')

def city_vote_list(request):
    c_list = City.objects.annotate(votes=Count('vote')).order_by('-votes')
    return render_to_response('citypoll/vote_list.html', {
        'city_list': c_list,
    })

def city_detail(request, city_id):
    c = get_object_or_404(City, id=city_id)
    return render_to_response('citypoll/city_detail.html', {
        'city': c,
        'vote_list': c.vote_set.order_by('-date_received'),
    })
