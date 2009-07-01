from django import forms
from django.conf import settings
from django.core.mail import send_mail
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from ebinternal.feedback.models import Category, Feedback, Response, CannedResponse
import datetime
import re

class CategoryForm(forms.Form):
    category = forms.ModelChoiceField(Category.objects.order_by('name'))

def save_feedback(request):
    # Meant to be called as an Ajax request; no response.
    if not request.POST.get('message', '').strip():
        raise Http404
    page_url = request.META.get('HTTP_REFERER', '').replace('\n', '').strip()
    m = re.search(r'^http://(.*?)\.', page_url)
    city = m and m.group(1) or ''
    ip_address = request.META.get('HTTP_X_FORWARDED_FOR', '') or request.META.get('REMOTE_ADDR', '')
    uncategorized, _ = Category.objects.get_or_create(name='Uncategorized')
    f = Feedback.objects.create(
        city=city,
        page_url=page_url,
        message=request.POST['message'],
        ip_address=ip_address[:255],
        email=request.POST.get('email', '').strip(),
        date_received=datetime.datetime.now(),
        assigned_to='',
        date_responded=None,
        responder='',
        is_awesome=False,
        is_ignored=False,
        category=uncategorized,
    )
    anon_note = f.email and 'S' or 'Anonymous s'
    subject = '%site feedback: %s %s' % (anon_note, f.city or 'Unknown city', f.page_url)
    message = u'Referrer: %s\nIP address: %s\nE-mail: %s\nReply here: %s\n\n%s' % \
        (f.page_url, f.ip_address, f.email, f.url(), f.message)
    send_mail(subject, message, settings.EB_FROM_EMAIL, [settings.EB_NOTIFICATION_EMAIL], fail_silently=True)
    return HttpResponse('')

def feedback_list(request):
    open_list = Feedback.objects.select_related().filter(date_responded__isnull=True).order_by('-date_received')
    closed_list = Feedback.objects.select_related().filter(date_responded__isnull=False).order_by('-date_received')[:30]
    return render_to_response('feedback/feedback_list.html', {
        'open_list': open_list,
        'closed_list': closed_list,
        'category_form': CategoryForm(auto_id=False),
    })

def feedback_detail(request, feedback_id):
    f = get_object_or_404(Feedback.objects.select_related(), id=feedback_id)
    remote_user = request.META.get('REMOTE_USER', '')
    if request.method == 'POST':
        if request.POST.get('claim', False):
            f.assigned_to = remote_user
            f.save()
            return HttpResponseRedirect(request.path)
        response_text = request.POST.get('response', '').strip()
        if response_text:
            f.date_responded = datetime.datetime.now()
            f.responder = remote_user
            if response_text:
                if not f.email.strip():
                    raise Http404('No e-mail address to send to')
                # Note that we send the message before creating the Response
                # object, in case the e-mail sending fails.
                subject = 'Response to your site feedback'
                message = u'%s\n\n\n---- You wrote: ----\n\n%s' % (response_text, f.message)
                send_mail(subject, message, settings.EB_FROM_EMAIL, [f.email], fail_silently=False)
                response = Response.objects.create(
                    feedback=f,
                    date_sent=f.date_responded,
                    to_email=f.email,
                    from_email=f.responder,
                    message=response_text,
                )
            f.save()
            return HttpResponseRedirect('../')
    staff_first_name, staff_full_name = settings.EB_STAFF[remote_user]
    return render_to_response('feedback/feedback_detail.html', {
        'feedback': f,
        'response_list': f.response_set.order_by('date_sent'),
        'canned_response_list': CannedResponse.objects.order_by('name'),
        'category_form': CategoryForm(auto_id=False),
        'staff_first_name': staff_first_name,
        'staff_full_name': staff_full_name,
    })

def feedback_ignore(request):
    f_id = request.POST.get('feedback_id')
    if not f_id.isdigit():
        raise Http404
    remote_user = request.META.get('REMOTE_USER', '')
    Feedback.objects.filter(id=f_id).update(date_responded=datetime.datetime.now(), responder=remote_user, is_ignored=True)
    return HttpResponse('')

def feedback_change_category(request):
    f_id = request.POST.get('feedback_id')
    c_id = request.POST.get('category_id')
    if not c_id.isdigit() or not f_id.isdigit():
        raise Http404
    Feedback.objects.filter(id=f_id).update(category=c_id)
    return HttpResponse('')
