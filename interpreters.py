import re
import datetime
import json
from event_models import *

hyphens = "[\-‒–—―—]"

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
    'пн': 0,
    'вт': 1,
    'ср': 2,
    'чт': 3,
    'пт': 4,
    'сб': 5,
    'вс': 6
}

day_month_regex = re.compile(r"(\d+)\s*(\w+)", re.U)

date_time_regex_citydog = re.compile(r"(\d+)\s*(\w+)\s*\|\s*(\d+):(\d+)", re.U)
date_regex_citydog = re.compile(r"(\d+)\s*([^\W\d_]+)*\s*(\d{4})*", re.U)
date_range_without_end_citydog_regex = re.compile(r"[сc]\s+(\d{1,2})\s+(\w+)", re.U)
date_range_citydog_regex = re.compile(r"(\d{1,2})\s+(\w+)*\s*(\d{4})*\s*[-—]\s*(\d{1,2})\s+(\w+)\s*(\d{4})*", re.U)

tut_by_range_regex = re.compile(r"с (\d{1,2}) (\w+) по (\d{1,2}) (\w+)", re.U)
tut_by_week_range = re.compile(r"(\w{2})–(\w{2})\s+(\d{2}):(\d{2})—(\d{2}):(\d{2})", re.U)

time_range_regex = re.compile(r"((\d{2}):(\d{2})\s*" + hyphens + r"\s*(\d{2}):(\d{2}))|(выходн)")
day_code_relax_regex = re.compile(r"(%s)\." % "|".join([v.lower() for v in weekday_mapping.keys()]))
day_month_relax_regex = re.compile(r"(\d{1,2})(\s+(%s))?" % "|".join([v.lower() for v in month_mapping.keys()]))
hyphens_regex = re.compile(r"[\-‒–—―]")

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
            return tomorrow.day, tomorrow.month
        match = date_range_citydog_regex.match(date_string)
        if match:
            # 2 апреля — 4 апреля
            return DateInterpreter._parse_range(match)
        match = day_month_regex.findall(date_string)
        if len(match) > 0:
            # сб, 29 февраля
            day, month = match[0]
            return int(day.strip()), month_mapping[month]

        return None

    @staticmethod
    def parse_relax_schedule(schedule_string):
        schedule_string = schedule_string.replace("10500", "10:00")
        time_ranges = []
        for match in time_range_regex.finditer(schedule_string):
            time_range, start_hour, start_minute, end_hour, end_minute, weekend = match.groups()
            span = match.span()
            if not weekend:
                time_ranges.append(([(start_hour, start_minute), (end_hour, end_minute)], span))
            else:
                time_ranges.append((None, span))
        for time_range, span in reversed(time_ranges):
            start, end = span
            schedule_string = schedule_string[:start] + "TIME_RANGE" + schedule_string[end:]

        if any(c.isdigit() for c in schedule_string):
            return DateInterpreter._get_date_relax_schedule(schedule_string, time_ranges)
        return DateInterpreter._get_week_relax_schedule(schedule_string, time_ranges)

    @staticmethod
    def _get_week_relax_schedule(schedule_string, time_ranges):
        schedule = [None] * len(weekday_mapping)
        week_days = []
        for match in day_code_relax_regex.finditer(schedule_string):
            day_code = match.groups()[0]
            span = match.span()
            week_days.append((day_code, span))
        if len(week_days) == 0:
            schedule[0:-1] = time_ranges[0][0]
            return schedule

        i = 0
        time_range_id = 0
        while i < len(week_days):
            start = week_days[i][1][1]
            if i + 1 < len(week_days):
                end = week_days[i + 1][1][0]
                separation = schedule_string[start:end]
            else:
                separation = schedule_string[start:]
            if separation in hyphens:
                start_day = weekday_mapping[week_days[i][0]]
                end_day = weekday_mapping[week_days[i + 1][0]]
                for day in range(start_day, end_day + 1):
                    schedule[day] = time_ranges[time_range_id][0]
                i += 2
                time_range_id += 1
            else:
                day = weekday_mapping[week_days[i][0]]
                schedule[day] = time_ranges[time_range_id][0]
                i += 1
                if separation != ",":
                    time_range_id += 1
        return schedule

    @staticmethod
    def _get_date_relax_schedule(schedule_string, time_ranges):
        schedule_string = schedule_string.replace("и", ",")
        dates = []
        date_matches = []
        for match in day_month_relax_regex.finditer(schedule_string):
            day, _, month = match.groups()
            span = match.span()
            date_matches.append((day, month, span))

        i = 0
        time_range_id = 0
        current_enumeration = []
        while i < len(date_matches):
            start = date_matches[i][2][1]
            if i + 1 < len(date_matches):
                end = date_matches[i + 1][2][0]
                separation = schedule_string[start:end]
            else:
                separation = schedule_string[start:]
            separation = separation.strip()
            if separation in hyphens:
                start_day, start_month = date_matches[i][0:2]
                end_day, end_month = date_matches[i + 1][0:2]
                if not start_month:
                    start_month = end_month
                dates.append(EventDateRange(
                    DateInterpreter.get_day(int(start_day), start_month),
                    DateInterpreter.get_day(int(end_day), end_month), [time_ranges[time_range_id][0]] * 7))
                i += 2
                time_range_id += 1
            elif separation == ",":
                if not current_enumeration:
                    current_enumeration = [
                        date_matches[i][:2],
                        date_matches[i + 1][:2],
                    ]
                else:
                    current_enumeration.append(date_matches[i + 1][:2])
                i += 1
            else:
                if current_enumeration:
                    month = current_enumeration[-1][1]
                    start_time, end_time = time_ranges[time_range_id][0]
                    for day, m in current_enumeration:
                        dates.append(EventDateRange(
                            DateInterpreter.get_date(day, month, *start_time),
                            DateInterpreter.get_date(day, month, *end_time)
                        ))
                    current_enumeration = None
                else:
                    day, month = date_matches[i][:2]
                    if time_range_id == len(time_ranges):
                        print("")
                    start_time, end_time = time_ranges[time_range_id][0]
                    dates.append(EventDateRange(
                        DateInterpreter.get_date(day, month, *start_time),
                        DateInterpreter.get_date(day, month, *end_time)
                    ))
                time_range_id += 1
                i += 1
        return dates

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
            return [DateInterpreter.get_date(day, month, hour, minute)]
        match = date_range_without_end_citydog_regex.match(date_string)
        # с 12 марта
        if match:
            day, month = match.groups()
            day = int(day)
            month = month_mapping[month]
            return [EventDateRange(datetime.date(current_year, month, day), None, None)]
        match = date_range_citydog_regex.match(date_string)
        # 12 февраля - 30 апреля
        if match:
            return [DateInterpreter._parse_range(match)]

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
        week_string = week_string.lower()
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
        if type(month) == str:
            month = month_mapping[month]
        return datetime.datetime(current_year, month, int(day), int(hour), int(minute))

    @staticmethod
    def get_day(day, month):
        if type(month) == str:
            month = month_mapping[month]
        if day == None:
            print("")
        if month == None:
            print("")
        return datetime.date(current_year, month, day)


class TagMapper:
    tut_tag_mapping_file = "data/tut_tag_mapping.json"
    tut_type_mapping_file = "data/tut_type_mapping.json"
    relax_tag_mapping_file = "data/relax_tag_mapping.json"
    relax_type_mapping_file = "data/relax_type_mapping.json"
    cd_tag_mapping_file = "data/cd_tag_mapping.json"
    cd_type_mapping_file = "data/cd_type_mapping.json"

    def __init__(self):
        self.relax_mapping = {
            "tags": self._load_mapping(self.relax_tag_mapping_file),
            "types": self._load_mapping(self.relax_type_mapping_file),
        }
        self.tut_mapping = {
            "tags": self._load_mapping(self.tut_tag_mapping_file),
            "types": self._load_mapping(self.tut_type_mapping_file),
        }
        self.cd_mapping = {
            "tags": self._load_mapping(self.cd_tag_mapping_file),
            "types": self._load_mapping(self.cd_type_mapping_file),
        }

    @staticmethod
    def _load_mapping(filename):
        with open(filename, "r", encoding="utf") as f:
            return json.load(f)

    def map_tut(self, value):
        return self._get_mapped(value, self.tut_mapping)

    def map_relax(self, value):
        return self._get_mapped(value, self.relax_mapping)

    def map_cd(self, value):
        return self._get_mapped(value, self.cd_mapping)

    @staticmethod
    def _get_mapped(value, mapping):
        if value in mapping["tags"]:
            mapped = mapping["tags"][value]
        elif value in mapping["types"]:
            mapped = mapping["types"][value]
        else:
            raise Exception("Mapping was not found for %s" % value)
        return mapped.split(',')

