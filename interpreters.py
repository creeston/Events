import re
import json
import regex

from models import *

hyphens = r"[\-‒–—―—]"
hyphens_regex = re.compile(r"[\-‒–—―]")

relax_day_month_regex = re.compile(r"(\d+)\s*(\w+)", re.U)

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

# 2019 года
# 2019 г.
# group[1] -> year
optional_year_re = r"(\s*(\d{4})\s*(года|г\.|г)*)*"


def get_optional_year(groups):
    if len(groups) > 0 and groups[1]:
        return int(groups[1])
    else:
        return current_year


# 13 мая
# group[0] -> day, group[2] -> month
day_month_re = r"(\d{1,2})(-го)*\s*(%s)" % "|".join([v.lower() for v in month_mapping.keys()])


def get_day_month(groups):
    day = int(groups[0])
    month = month_mapping[groups[2]]
    return {"day": day, "month": month}


# 13 мая
# 13
# group[0] -> day, group[2] -> month
day_optional_month_re = r"(\d{1,2})(-го)*\s*(%s)*" % "|".join([v.lower() for v in month_mapping.keys()])


def get_day_optional_month(groups):
    day = int(groups[0])
    if len(groups) > 2 and groups[2]:
        month = month_mapping[groups[2]]
    else:
        month = None
    return {"day": day, "month": month}


day_optional_month_optional_year = day_optional_month_re + optional_year_re


def get_day_optional_month_optional_year(groups):
    day_month = get_day_optional_month(groups[:3])
    year = get_optional_year(groups[3:])
    day_month["year"] = year
    return day_month


# 13 мая
# 13 мая 2020
# 13 мая 2019 года
# 13 мая 2019 г.
# group[0] -> day, group[2] -> month, group[4] -> year
day_month_optional_year = day_month_re + optional_year_re
day_month_year_regex = regex.compile(day_month_optional_year, re.U)


def get_day_month_year(groups):
    day_month = get_day_month(groups[:3])
    year = get_optional_year(groups[3:])
    day_month["year"] = year
    return day_month


# 19.03.2020
# group[0] -> day, group[1] -> month, group[2] -> year
date_re = r"(\d{1,2})\s?\.\s?(\d{1,2})\s?\.\s?(\d{2,4})(\s*(г|г\.|года|))*"
date_regex = regex.compile(date_re)


def get_date(groups):
    day = int(groups[0])
    month = int(groups[1])
    year = int(groups[2])
    return {"day": day, "month": month, "year": year}


# до 12 апреля
# group[0] -> preposition, group[1] -> day, group[3] -> month, group[5] -> year
day_month_year_until = regex.compile(r"(до|по)\s*" + day_month_optional_year)


def get_day_month_year_until(groups):
    date = get_day_month_year(groups[1:])
    return {"start": None, "end": date}


# до конца апреля
# group[0] -> preposition, group[1] -> goal, group[2] -> month
literal_month_until = regex.compile(r"(до )*(конца|середины)\s+(\p{L}+)")


def get_literal_month_until(groups):
    goal = groups[1]
    month = month_mapping[groups[2]]
    return {"start": None, "end": {"goal": goal, "month": month}}


# до 01.11.2019
# group[0] -> preposition, group[1] -> day, group[2] -> month, group[3] -> year
date_until = regex.compile(r"(до|по)\s*" + date_re)


def get_date_until(groups):
    date = get_date(groups[1:])
    return {"start": None, "end": date}


# с 12 по 13 апреля
# с 12 апреля до 14 апреля 2020 гю
# с 13 апреля 2019 по 15 апреля 2021
# group[0] -> day, group[2] -> month, group[4] -> year, group[7] -> day, group[9] -> month, group[11] -> year
from_day_to_day_month = regex.compile(r"с\s*" + day_optional_month_optional_year +
                                      r"\s*(по|до)\s*" + day_month_optional_year)


def get_from_day_to_day(groups):
    start = get_day_optional_month_optional_year(groups[:6])
    end = get_day_month_year(groups[7:])
    return {"start": start, "end": end}


# 12-13 апреля
# group[0] -> day, group[2] -> month, group[4] -> year, group[6] -> delimiter,
# group[7] -> day, group[9] -> month, group[11] -> year
day_hyphen_day_month = regex.compile(day_optional_month_optional_year + r"\s*(" + hyphens + r"|,)\s*" +
                                     day_month_optional_year)


def get_day_hyphen_day(groups):
    start = get_day_optional_month_optional_year(groups[:6])
    delimiter = groups[6]
    end = get_day_month_year(groups[7:])
    if delimiter == ",":
        return [start, end]
    else:
        return {"start": start, "end": end}


# 12.02.20-14.03.20
# group[0] -> day, group[1] -> month, group[2] -> year, group[5] -> day, group[6] -> month, group[7] -> year
date_hyphen_date = regex.compile(date_re + r"\s*" + hyphens + r"\s*" + date_re)


def get_date_hyphen_date(groups):
    start = get_date(groups[:5])
    end = get_date(groups[5:])
    return {"start": start, "end": end}


# 12 апреля, четверг
# 15 февраля (суббота)
# group[0] -> day, group[2] -> month
weekday_after = regex.compile(day_month_re + r"\s*(,\s*\p{L}+|\s*\(\p{L}+\))")

# четверг 12 апреля
# четверг, 13 мая
# group[0] -> day, group[2] -> month
weekday_before = regex.compile(r"\p{L}+[,\s]+" + day_month_re)

# 12:32
# 20.30
# 3 часа
# 12 часов
# group[0] -> hour, group[1] -> minute, group[3] -> hour
time_regex = r"[\sв]*(\d{1,2})[:.-](\d{1,2})(\s*мск)*|(\d{1,2})\s*(часов|часа)"
time_re = regex.compile(time_regex)


def get_time(groups):
    if not groups[0]:
        hour = int(groups[3])
        minute = 0
    else:
        hour, minute = int(groups[0]), int(groups[1])
    return {"hour": hour, "minute": minute}


# 10:00 до 14:00
# с 10:00 до 16:00
time_range_re = regex.compile(r"[с]?\s*(" + time_regex + r")\s*(до|" + hyphens + r")\s*(" + time_regex + ")\s*(\p{L}+)?")


def get_time_range(groups):
    start_time = get_time(groups[1:6])
    end_time = get_time(groups[8:])
    return {"start_time": start_time, "end_time": end_time}


# вторник в 18:30
week_day_time_re = regex.compile("(\p{L}+)\s+" + time_regex)


def get_week_day_time(groups):
    weekday = groups[0]
    time = get_time(groups[1:])
    time["week_day"] = weekday
    return time


# 12 апреля в 17:20
# group[0] -> day, group[2] -> month, group[4] -> year, group[6] -> delimiter,
# group[7] -> hour, group[8] -> minute, group[10] -> hour
day_month_time = regex.compile(day_month_optional_year + r"[\s,]*(в|с)*\s*" + time_regex)


def get_day_month_time(groups):
    date = get_day_month_year(groups[:5])
    time = get_time(groups[7:])
    date['hour'] = time['hour']
    date['minute'] = time['minute']
    return date


# 29.02.2020 в 14.00
# group[0] -> day, group[1] -> month, group[2] -> year, group[5] -> delimiter,
# group[6] -> hour, group[7] -> minute, group[9] -> hour
date_time_re = regex.compile(date_re + r"[\s,]*(в|с)*\s*" + time_regex)


def get_date_time(groups):
    date = get_date(groups[:4])
    time = get_time(groups[6:])
    date['hour'] = time['hour']
    date['minute'] = time['minute']
    return date


# до 22:30, 23 мая
# group[0] -> delimiter, group[1] -> hour, group[2] -> minute, group[4] -> hour,
# group[6] -> day, group[8] -> month, group[10] -> year
time_before_date = regex.compile("(в|с|до)*" + time_regex + r"[\s,]+" + day_month_optional_year)


def get_time_before_date(groups):
    delimiter = groups[0]
    time = get_time(groups[1:5])
    date = get_day_month_year(groups[5:])
    date['hour'] = time['hour']
    date['minute'] = time['minute']
    if delimiter == "до":
        date['delim'] = "UNTIL"
    return date


# четверг 13 августа в 18:20
# group[0] -> day, group[2] -> month, group[4] -> year, group[6] -> delimiter,
# group[7] -> hour, group[8] -> minute, group[10] -> hour
weekday_before_date_time = regex.compile(r"\p{L}+[,\s]+" + day_month_optional_year + r"[\s,]+(в|с)*\s*" + time_regex)

regexes = [
    (day_month_year_regex, get_day_month_year),
    (day_month_year_until, get_day_month_year_until),
    (from_day_to_day_month, get_from_day_to_day),
    (day_hyphen_day_month, get_day_hyphen_day),
    (date_regex, get_date),
    (weekday_after, get_day_month),
    (weekday_before, get_day_month),
    (time_re, get_time),
    (time_range_re, get_time_range),
    (day_month_time, get_day_month_time),
    (weekday_before_date_time, get_day_month_time),
    (week_day_time_re, get_week_day_time),
    (time_before_date, get_time_before_date),
    (date_time_re, get_date_time),
    (date_hyphen_date, get_date_hyphen_date),
    (date_until, get_date_until),
    (literal_month_until, get_literal_month_until)
]


def try_parse_date_string(date_string):
    date_string = date_string.lower()
    matches = [(reg[0].fullmatch(date_string), reg[1]) for reg in regexes]
    matches = [m for m in matches if m[0]]

    if len(matches) == 0:
        not_full_matches = [(reg[0].match(date_string), reg[1]) for reg in regexes]
        not_full_matches = [m for m in not_full_matches if m[0]]

        if len(not_full_matches) == 0:
            return None, None
        else:
            matches = not_full_matches

    if len(matches) == 1:
        match, reg = matches[0]
    else:
        match, reg = max(matches, key=lambda m: m[0].span()[1] - m[0].span()[0])
    groups = match.groups()
    return reg(groups), date_string[match.span()[0]:match.span()[1]]


# citydog
date_time_regex_citydog = re.compile(r"(\d+)\s*(\w+)\s*\|\s*(\d+):(\d+)", re.U)
date_regex_citydog = re.compile(r"(\d+)\s*([^\W\d_]+)*\s*(\d{4})*", re.U)
date_range_without_end_citydog_regex = re.compile(r"[сc]\s+(\d{1,2})\s+(\w+)", re.U)
date_range_citydog_regex = re.compile(r"(\d{1,2})\s+(\w+)*\s*(\d{4})*\s*[-—]\s*(\d{1,2})\s+(\w+)\s*(\d{4})*", re.U)

# tutby
tut_by_range_regex = re.compile(r"с (\d{1,2}) (\w+) по (\d{1,2}) (\w+)", re.U)
tut_by_week_range = re.compile(r"(\w{2})–(\w{2})\s+(\d{2}):(\d{2})—(\d{2}):(\d{2})", re.U)

# relax
day_code_relax_regex = re.compile(r"(%s)\." % "|".join([v.lower() for v in weekday_mapping.keys()]))
day_month_relax_regex = re.compile(r"(\d{1,2})(\s+(%s))?" % "|".join([v.lower() for v in month_mapping.keys()]))
time_range_regex = re.compile(r"((\d{2}):(\d{2})\s*" + hyphens + r"\s*(\d{2}):(\d{2}))|(выходн)")


current_year = datetime.datetime.now().year
today = datetime.datetime.now()
tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)


class DateInterpreter:
    @staticmethod
    def parse_day_month(date_string):
        date_string = date_string.replace(u"\xa0", " ").strip()
        values = date_string.split(" ")
        if len(values) > 2:
            print(values)
        if len(values) == 1:
            return int(values[0]), None
        day_string, month_string = values
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
        match = relax_day_month_regex.findall(date_string)
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

        try:
            if any(c.isdigit() for c in schedule_string):
                return DateInterpreter._get_date_relax_schedule(schedule_string, time_ranges)
            return DateInterpreter._get_week_relax_schedule(schedule_string, time_ranges)
        except Exception as e:
            print(e)

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
        # 3 мая\nДедлайн: 01.07
        date_string = date_string.split('\n')[0]

        # 12 апреля    |    23:00
        match = date_time_regex_citydog.match(date_string)
        if match:
            day, month, hour, minute = match.groups()
            day = int(day)
            month = month_mapping[month]
            hour = int(hour)
            minute = int(minute)
            return [DateInterpreter.get_date(day, month, hour, minute)]

        # с 12 марта
        match = date_range_without_end_citydog_regex.match(date_string)
        if match:
            day, month = match.groups()
            day = int(day)
            month = month_mapping[month]
            return [EventDateRange(datetime.date(current_year, month, day), None, None)]

        # 12 февраля - 30 апреля
        match = date_range_citydog_regex.match(date_string)
        if match:
            return [DateInterpreter._parse_range(match)]

        # 12, 13 апреля
        # 9 мая, 13 июня
        values = [v.strip() for v in date_string.split(',')]
        dates = []
        for value in reversed(values):
            day, month = DateInterpreter.parse_day_month(value)
            if not month:
                month = dates[-1].month
            dates.append(datetime.date(current_year, month, int(day)))

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
            start_day = int(weekday_mapping[start_day])
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
        return datetime.date(current_year, month, day)


class TagMapper:
    mapping_file = "C:\\Projects\\Research\\Events\\data\\tags\\mapping.json"

    def __init__(self):
        self.mapping = self._load_mapping(self.mapping_file)

    @staticmethod
    def _load_mapping(filename):
        with open(filename, "r", encoding="utf") as f:
            return json.load(f)

    def map_tut(self, value):
        return self._get_mapped(value, self.mapping["tutby"])

    def map_relax(self, value):
        return self._get_mapped(value, self.mapping["relax"])

    def map_cd(self, value):
        return self._get_mapped(value, self.mapping["cd"])

    @staticmethod
    def _get_mapped(value, mapping):
        if value in mapping["tag"]:
            mapped = mapping["tag"][value]
        elif value in mapping["type"]:
            mapped = mapping["type"][value]
        else:
            print("Unknown tag: %s" % value)
            return [value.title()]
        return mapped.split(',')
