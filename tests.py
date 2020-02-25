from event_models import EventDateRange
from interpreters import DateInterpreter
import datetime

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
