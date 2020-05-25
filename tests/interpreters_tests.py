import datetime
from interpreters import time_re, time_range_re, try_parse_date_string, weekday_after, DateInterpreter
from models import EventDateRange

#assert try_parse_date_string("Бачата для начинающих \"с нуля\". 19:00 - 23:00")[0]

assert time_re.fullmatch("18:00")
assert time_range_re.fullmatch("18:00 до 19:30")
assert time_range_re.fullmatch("с 18:00 до 19:30")
assert time_range_re.fullmatch("23:20 до 5:30 утра")
assert time_range_re.fullmatch("18:00- 19:30")

assert weekday_after.fullmatch("15 февраля (суббота)")


result = try_parse_date_string("с 18:00 до 23:00")[0]
assert result['start_time']['hour'] == 18
assert result['start_time']['minute'] == 0
assert result['end_time']['hour'] == 23
assert result['end_time']['minute'] == 0


# Test date parser
date_strings = [
    "13 мая",
    "21.30",
    "субботу 18 апреля, с 13:00",
    "15 апреля в 10:00",
    "до 22 апреля",
    "3 апреля",
    "20:00",
    "20-32",
    "субботу 28 марта в 21.00",
    "28 марта",
    "27 марта",
    "19.03.2020",
    "19. 03.2020",
    "19.04.20",
    "19. 04.20",
    "19.04.20",
    "с 16 по 20 марта",
    "16-20 марта",
    "12 марта в 18:15",
    "12.03.2020",
    "5 марта в 18:15",
    "7 марта 2020 года",
    "27 февраля в 19:00",
    "четверг 20 февраля в 19.00",
    "10 февраля в 18:20",
    "28-31 января",
    "21 декабря, суббота",
    "18 декабря в 17:00",
    "с 21 декабря 2019 года по 6 января 2020 года",
    "21 декабря 2019 года",
    "10 декабря в 18:15",
    "14-15 декабря",
    "15 декабря с 12:00",
    "13-16 ноября",
    "по 15 января",
    "до 10 декабря",
    "30 ноября в 11:00",
    "с 1 по 10 декабря",
    "21 мая, в 19.00",
    "12 мая 2020 года в 19:00",
    "12 мая 2020 года",
    "8 мая, пятница",
    "10 мая с 12:00",
    "19 апреля в 18:00",
    "18 апреля 2020 года",
    "7 апреля в 19:00",
    "по 10 мая 2020 года",
    "10 мая 2020 года",
    "с 22 января по 26 июля 2020 г.",
    "26 июля 2020 г. г.",
    "26 июля 2020 г.",
    "17 марта 2020 года в 19.00",
    "17 марта 2020 года",
    "до 7 июня",
    "с 1 февраля по 11 мая",
    "по 31 марта",
    "четверг 19 марта",
    "по 12 апреля",
    "28 марта в 19:00",
    "17 марта 2020, 19:15",
    "17 марта 2020",
    "12 марта в 19.00",
    "18 – 21 марта",
    "12 марта - 26 апреля 2020 г.",
    "26 апреля 2020 г.",
    "11 марта в 18.00",
    "8 марта с 12.00",
    "С 12 марта по 26 апреля",
    "10 марта в 19:00",
    "9 марта 2020 года",
    "3 марта в 19:00",
    "29 февраля 2020 года",
    "29 февраля 2020 года с 10:00",
    "четверг 27 февраля",
    "с 28 февраля по 29 марта 2020 года",
    "29 марта 2020 года",
    "23 февраля с 14.00",
    "22 февраля 2020 года",
]

for date_string in date_strings:
    assert try_parse_date_string(date_string)[0]


result = DateInterpreter.parse_relax_date("вт, 19 января 2038")
assert result[0] == 19 and result[1] == 1


result = DateInterpreter.parse_relax_schedule("вт.-чт.: 12:00 — 20:00. пт.,сб.,вс.: 12:00 — 18:00. пн.: выходные")
assert not result[0]
for day in (1, 2, 3):
    assert result[day][0] == ('12', '00')
    assert result[day][1] == ('20', '00')
for day in (4, 5, 6):
    assert result[day][0] == ('12', '00')
    assert result[day][1] == ('18', '00')

result = DateInterpreter.parse_relax_schedule(
    "23-24 марта: 10:00 — 18:00. 25 апреля: 10:00 — 16:00. 26 и 27 апреля: 10:00 - 17:30")
assert len(result) == 4
assert all([type(r) == EventDateRange for r in result])
assert result[0].start_day == datetime.date(2020, 3, 23)
assert result[0].end_day == datetime.date(2020, 3, 24)
for d in result[0].week_schedule:
    assert d[0] == ('10', '00')
    assert d[1] == ('18', '00')

assert result[1].start_day == datetime.datetime(2020, 4, 25, 10, 0)
assert result[1].end_day == datetime.datetime(2020, 4, 25, 16, 0)
assert result[2].start_day == datetime.datetime(2020, 4, 26, 10, 0)
assert result[2].end_day == datetime.datetime(2020, 4, 26, 17, 30)
assert result[3].start_day == datetime.datetime(2020, 4, 27, 10, 0)
assert result[3].end_day == datetime.datetime(2020, 4, 27, 17, 30)
