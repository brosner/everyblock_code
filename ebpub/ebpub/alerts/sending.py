from django.conf import settings
from django.core.mail import SMTPConnection, EmailMultiAlternatives
from django.template.loader import render_to_string
from ebpub.alerts.models import EmailAlert
from ebpub.db.models import NewsItem
from ebpub.db.utils import populate_attributes_if_needed
from ebpub.db.views import make_search_buffer
from ebpub.streets.models import Block
import datetime

class NoNews(Exception):
    pass

def email_text_for_place(alert, place, place_name, place_url, newsitem_list, date, frequency):
    """
    Returns a tuple of (text, html) for the given args. `text` is the text-only
    e-mail, and `html` is the HTML version.
    """
    domain = '%s.%s' % (settings.SHORT_NAME, settings.EB_DOMAIN)
    context = {
        'place': place,
        'is_block': isinstance(place, Block),
        'block_radius': isinstance(place, Block) and alert.radius or None,
        'domain': domain,
        'email_address': alert.user.email,
        'place_name': place_name,
        'place_url': place_url,
        'newsitem_list': newsitem_list,
        'date': date,
        'frequency': frequency,
        'unsubscribe_url': alert.unsubscribe_url(),
    }
    return render_to_string('alerts/email.txt', context), render_to_string('alerts/email.html', context)

def email_for_subscription(alert, start_date, frequency):
    """
    Returns a (place_name, text, html) tuple for the given EmailAlert
    object and date.
    """
    start_datetime = datetime.datetime(start_date.year, start_date.month, start_date.day)
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    end_datetime = datetime.datetime.combine(yesterday, datetime.time(23, 59, 59, 9999)) # the end of yesterday
    # Order by schema__id to group schemas together.
    qs = NewsItem.objects.select_related().filter(schema__is_public=True, pub_date__range=(start_datetime, end_datetime)).order_by('-schema__importance', 'schema__id')
    if alert.include_new_schemas:
        if alert.schemas:
            qs = qs.exclude(schema__id__in=alert.schemas.split(','))
    else:
        if alert.schemas:
            qs = qs.filter(schema__id__in=alert.schemas.split(','))
    if alert.block:
        place_name, place_url = alert.block.pretty_name, alert.block.url()
        place = alert.block
        search_buffer = make_search_buffer(alert.block.location.centroid, alert.radius)
        qs = qs.filter(location__bboverlaps=search_buffer)
    elif alert.location:
        place_name, place_url = alert.location.name, alert.location.url()
        place = alert.location
        qs = qs.filter(newsitemlocation__location__id=alert.location.id)
    ni_list = list(qs)
    if not ni_list:
        raise NoNews
    schemas_used = set([ni.schema for ni in ni_list])
    populate_attributes_if_needed(ni_list, list(schemas_used))
    text, html = email_text_for_place(alert, place, place_name, place_url, ni_list, start_date, frequency)
    return place_name, text, html

def send_all(frequency):
    """
    Sends an e-mail to all subscribers in the system with data with the given frequency.
    """
    conn = SMTPConnection() # Use default settings.
    count = 0
    start_date = datetime.date.today() - datetime.timedelta(days=frequency)
    for alert in EmailAlert.active_objects.filter(frequency=frequency):
        try:
            place_name, text_content, html_content = email_for_subscription(alert, start_date, frequency)
        except NoNews:
            continue
        subject = 'Update: %s' % place_name
        message = EmailMultiAlternatives(subject, text_content, settings.GENERIC_EMAIL_SENDER,
            [alert.user.email], connection=conn)
        message.attach_alternative(html_content, 'text/html')
        message.send()
        count += 1
