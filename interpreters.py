import re
import datetime
from event_models import *


month_mapping = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12
}

current_year = datetime.datetime.now().year

day_regex_tutby = re.compile(r"(?P<day>\d+)\s*(?P<month>\w+),\s*(?P<week_day>\w+)")
date_time_regex_citydog = re.compile(r"(?P<day>\d+)\s*(?P<month>[^\W\d_]+)\s*\|\s*(?P<hour>\d+):(?P<minute>\d+)", re.U)
date_regex_citydog = re.compile(r"(\d+)\s*([^\W\d_]+)*\s*(\d{4})*", re.U)

class DateInterpreter:
    def _get_date(self, date_string):
        match = self.date_time_regex.match(date_string)
        if match:
            day, month, hour, minute = match.groups()
            day = datetime.datetime(current_year, month_mapping[month], int(day), int(hour), int(minute))
            return day
        elif '-' in date_string:
            start_date, end_date = date_string.split('-')
            start_day, start_month, start_year = self._parse_date(start_date.strip())
            end_day, end_month, end_year = self._parse_date(end_date.strip())
            if not start_month:
                start_month = end_month
                start_year = end_year
            if not start_year:
                start_year = datetime.datetime.now().year
                end_year = start_year
            start_day = datetime.date(int(start_year), month_mapping[start_month], int(start_day))
            end_day = datetime.date(int(end_year), month_mapping[end_month], int(end_day))
            return DateRange(start_day, end_day)
        elif 'c' in date_string:
            start_date = date_string.split('c')[1].strip()
            start_day, start_month, start_year = self._parse_date(start_date)
            if not start_year:
                start_year = current_year
            start_day = datetime.date(int(start_year), month_mapping[start_month], int(start_day))
            return DateRange(start_day, None)
        elif ',' in date_string:
            parsed_dates = [self._parse_date(d.strip()) for d in date_string.split(',')]
            for d in parsed_dates:
                if not d[1]:
                    d[1] = parsed_dates[-1][1]
                if not d[2]:
                    d[2] = current_year
            parsed_dates = [datetime.date(int(d[2]), month_mapping[d[1]], int(d[0])) for d in parsed_dates]
            return parsed_dates
        else:
            raise Exception("Unknown date format: %s" % date_string)

    pass

    def _parse_date(self, date_string):
        match = self.date_regex.match(date_string)
        if not match:
            raise Exception("Date is in unknown format: %s" % date_string)
        day, month, year = match.groups()
        return [day, month, year]


class CostInterpreter:
    pass
