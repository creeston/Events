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

weekday_mapping = {
    'ПН': 0,
    'ВТ': 1,
    'СР': 2,
    'ЧТ': 3,
    'ПТ': 4,
    'СБ': 5,
    'ВС': 6
}

day_month_regex = re.compile(r"(\d+)\s*(\w+)", re.U)

date_time_regex_citydog = re.compile(r"(\d+)\s*(\w+)\s*\|\s*(\d+):(\d+)", re.U)
date_regex_citydog = re.compile(r"(\d+)\s*([^\W\d_]+)*\s*(\d{4})*", re.U)
date_range_without_end_citydog_regex = re.compile(r"[сc]\s+(\d{1,2})\s+(\w+)", re.U)
date_range_citydog_regex = re.compile(r"(\d{1,2})\s+(\w+)*\s*(\d{4})*\s*[-—]\s*(\d{1,2})\s+(\w+)\s*(\d{4})*", re.U)

tut_by_range_regex = re.compile(r"с (\d{1,2}) (\w+) по (\d{1,2}) (\w+)", re.U)
tut_by_week_range = re.compile(r"(\w{2})–(\w{2})\s+(\d{2}):(\d{2})—(\d{2}):(\d{2})", re.U)

current_year = datetime.datetime.now().year
today = datetime.datetime.now()
tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)


class DateInterpreter:
    @staticmethod
    def parse_day_month(date_string):
        date_string = date_string.replace(u"\xa0", " ").strip()
        day_string, month_string = date_string.split(" ")
        day = int(day_string.strip())
        month = month_mapping[month_string.strip()]
        return day, month

    @staticmethod
    def parse_hour_minute(time_string):
        if not time_string:
            return None
        hour, minute = time_string.split(":")
        return int(hour.strip()), int(minute.strip())

    @staticmethod
    def parse_relax_date(date_string):
        if 'сегодня' in date_string:
            # вт, сегодня
            return today.day, today.month
        if 'завтра' in date_string:
            # ср, завтра
            return tomorrow.day, tomorrow.month,
        match = day_month_regex.findall(date_string)
        if len(match) > 0:
            # сб, 29 февраля
            day, month = match[0]
            return int(day.strip()), month_mapping[month]
        match = date_range_citydog_regex.match(date_string)
        if match:
            # 2 апреля — 4 апреля
            return DateInterpreter._parse_range(match)
        return None


    @staticmethod
    def parse_citydog_date(date_string):
        match = date_time_regex_citydog.match(date_string)
        # 12 апреля    |    23:00
        if match:
            day, month, hour, minute = match.groups()
            day = int(day)
            month = month_mapping[month]
            hour = int(hour)
            minute = int(minute)
            return DateInterpreter.get_date(day, month, hour, minute)
        match = date_range_without_end_citydog_regex.match(date_string)
        # с 12 марта
        if match:
            day, month = match.groups()
            day = int(day)
            month = month_mapping[month]
            return EventDateRange(datetime.date(current_year, month, day), None, None)
        match = date_range_citydog_regex.match(date_string)
        # 12 февраля - 30 апреля
        if match:
            return DateInterpreter._parse_range(match)

        # 12, 13 апреля
        values = date_string.split(',')
        last_day, last_month = DateInterpreter.parse_day_month(values[-1])
        dates = [datetime.date(current_year, last_month, int(day)) for day in values[:-1]]
        dates.append(datetime.date(current_year, last_month, last_day))
        return dates

    @staticmethod
    def _parse_range(match):
        start_day, start_month, start_year, end_day, end_month, end_year = match.groups()
        if not start_year:
            start_year = current_year
        if not end_year:
            end_year = current_year
        if not start_month:
            start_month = end_month
        start_date = datetime.date(int(start_year), month_mapping[start_month], int(start_day))
        end_date = datetime.date(int(end_year), month_mapping[end_month], int(end_day))
        return EventDateRange(start_date, end_date, None)

    @staticmethod
    def parse_tutby_date_range(date_range):
        date_range = date_range.lower()
        if 'постоянная' in date_range:
            return None, None
        match = tut_by_range_regex.match(date_range)
        if not match:
            raise Exception("unknown date range format")
        start_day, start_month, end_day, end_month = match.groups()
        return datetime.date(current_year, month_mapping[start_month.strip()], int(start_day.strip())), \
               datetime.date(current_year, month_mapping[end_month.strip()], int(end_day.strip()))

    @staticmethod
    def parse_tutby_week_time_schedule(week_string):
        week_schedule = [None] * len(weekday_mapping)
        for match in tut_by_week_range.findall(week_string):
            start_day, end_day, start_hour, start_minute, end_hour, end_minute = match
            start_day = weekday_mapping[start_day]
            end_day = weekday_mapping[end_day]
            start_time = (int(start_hour), int(start_minute))
            end_time = (int(end_hour), int(end_minute))
            for day in range(start_day, end_day + 1):
                week_schedule[day] = (start_time, end_time)
        return week_schedule

    @staticmethod
    def get_date(day, month, hour, minute):
        return datetime.datetime(current_year, month, day, hour, minute)

    @staticmethod
    def get_day(day, month):
        return datetime.date(current_year, month, day)

class CostInterpreter:
    pass
