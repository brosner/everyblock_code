from django import template
import calendar

register = template.Library()

def days_in_month(value):
    # Given a datetime.date, returns the number of days in that month.
    return calendar.monthrange(value.year, value.month)[1]
register.filter('days_in_month', days_in_month)
