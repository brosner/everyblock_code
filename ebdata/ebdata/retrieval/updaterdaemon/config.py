"""
Sample config file for the updaterdaemon
"""

def hourly(*minutes):
    def handle(dt):
        return dt.minute in minutes
    return handle

def multiple_hourly(*hour_minutes):
    # hour_minutes is a list of tuples in the format (hour, minute)
    hour_minutes = set(hour_minutes)
    def handle(dt):
        return (dt.hour, dt.minute) in hour_minutes
    return handle

def daily(hour, minute):
    def handle(dt):
        return dt.hour == hour and dt.minute == minute
    return handle

def weekly(weekday, hour, minute):
    # weekday -- 0=Monday, 6=Sunday
    def handle(dt):
        return dt.weekday() == weekday and dt.hour == hour and dt.minute == minute
    return handle

TASKS = (
    # time_callback, function_to_run, params_for_function, settings_file_name
    #
    # Example:
    # (daily(12, 0), run_some_function, {'kwargs': 'foo'}, {'DJANGO_SETTINGS_MODULE': 'foo.settings'})
)
