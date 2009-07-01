from django import forms
from django.core.paginator import Paginator, EmptyPage
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render_to_response
from ebwiki.wiki.models import Page
from difflib import unified_diff
import urllib

easy_diff = lambda x, y: '\n'.join(unified_diff(x.split('\n'), y.split('\n'), 'Old page', 'New page', lineterm=""))

class PageForm(forms.Form):
    headline = forms.CharField(max_length=80, widget=forms.TextInput(attrs={'size': 80}))
    content = forms.CharField(widget=forms.Textarea(attrs={'rows': 20, 'cols': 70}))
    change_message = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'size': 100}))
    minor_edit = forms.BooleanField(widget=forms.CheckboxInput, required=False)
    version = forms.IntegerField(widget=forms.HiddenInput)

def redirecter(request):
    "Redirects to a given URL without sending the 'Referer' header."
    try:
        url = request.GET['url']
    except KeyError:
        raise Http404
    if not url.startswith('http://') and not url.startswith('https://'):
        raise Http404
    return HttpResponse('<html><head><meta http-equiv="Refresh" content="0; URL=%s"></head><body>Redirecting...</body></html>' % urllib.unquote_plus(url))

def view_page(request, slug):
    try:
        page = Page.objects.order_by('-version').filter(slug=slug)[0]
    except IndexError:
        page = Page(slug=slug) # Temporarily construct Page object so we can call edit_url()
        return HttpResponseRedirect(page.edit_url())
    return render_to_response('wiki/view_page.html', {'page': page})

def view_version(request, slug, version):
    page = get_object_or_404(Page, slug=slug, version=version)
    return render_to_response('wiki/view_version.html', {'page': page})

def edit_page(request, slug):
    try:
        latest_page = Page.objects.order_by('-version').filter(slug=slug)[0]
    except IndexError:
        latest_page = None
    if request.method == 'POST':
        form = PageForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            if latest_page:
                if latest_page.headline == cd['headline'] and latest_page.content == cd['content']:
                    # If no changes were made, don't touch the database.
                    return HttpResponseRedirect(latest_page.url())
                if latest_page.version != int(cd['version']):
                    diff = easy_diff(Page.objects.get(slug=slug, version=cd['version']).content, cd['content'])
                    return render_to_response('wiki/edit_conflict.html', {'diff': diff, 'latest_page': latest_page})
            new_page = Page.objects.create_with_auto_version(slug, cd['headline'], cd['content'],
                cd['change_message'], request.META.get('REMOTE_USER', 'anonymous'), request.META['REMOTE_ADDR'],
                cd['minor_edit'])
            return HttpResponseRedirect(new_page.url())
    else:
        if latest_page is not None:
            form = PageForm({'headline': latest_page.headline, 'content': latest_page.content, 'version': latest_page.version})
        else:
            form = PageForm(initial={'change_message': 'Created page', 'version': 0})
    return render_to_response('wiki/edit_page.html', {'old_page': latest_page, 'slug': slug, 'form': form})

def history(request, slug):
    page_list = Page.objects.filter(slug=slug).order_by('-version')
    if not page_list:
        raise Http404("A history doesn't exist for the given slug.")
    return render_to_response('wiki/history.html', {'page_list': page_list, 'slug': slug})

def version_diff(request, slug, version1, version2):
    if int(version1) == 0:
        old_content = ''
    else:
        old_content = get_object_or_404(Page, slug=slug, version=version1).content
    page = get_object_or_404(Page, slug=slug, version=version2)
    diff = easy_diff(old_content, page.content)
    return render_to_response('wiki/version_diff.html', {'diff': diff, 'slug': slug, 'version1': version1, 'version2': version2, 'page': page})

def previous_version_diff(request, slug, version):
    return version_diff(request, slug, int(version)-1, version)

def latest_changes(request):
    p = Paginator(Page.objects.order_by('-change_date'), 30)
    try:
        page_num = int(request.GET.get('p', '1'))
    except ValueError:
        page_num = 1
    try:
        page = p.page(page_num)
    except EmptyPage:
        raise Http404('Invalid page')
    return render_to_response('wiki/latest_changes.html', {'result_page': page})

def list_orphans(request):
    orphans = Page.objects.find_orphans()
    return render_to_response('wiki/list_orphans.html', {'orphans': orphans})
