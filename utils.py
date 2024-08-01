from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

from dateutil import parser
from django.utils.module_loading import import_string


class DateRangeIterator:
    def __init__(self, start_date, end_date, delta=1, tz_name="UTC"):
        self.tz_name = tz_name
        self.start = self.ensure_utc_datetime(start_date)
        self.end = self.ensure_utc_datetime(end_date)
        self.current = self.start
        self.delta = delta

    def __iter__(self):
        return self

    def __next__(self):
        if self.current > self.end:
            raise StopIteration
        else:
            result = self.current
            self.current += timedelta(days=self.delta)
            return result

    def ensure_utc_datetime(self, timestamp):
        if isinstance(timestamp, date) and not isinstance(timestamp, datetime):
            timestamp = datetime.combine(timestamp, datetime.min.time())
        if isinstance(timestamp, str):
            timestamp = parser.parse(timestamp)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=ZoneInfo(self.tz_name))
        return timestamp.astimezone(ZoneInfo("UTC"))


class LazyImport:
    def __init__(self, module_name):
        self.module_name = module_name
        self.module = None

    def __getattr__(self, name):
        if self.module is None:
            print(f'Importing module {self.module_name}')
            self.module = import_string(self.module_name)
        return getattr(self.module, name)
