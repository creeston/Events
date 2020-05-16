import datetime

from models import EventDateRange
from interpreters import DateInterpreter, try_parse_date_string
from markup import TypeMarkup, MarkupCurrency, PullEntityMarkup, filter_tags, markup_event
from duplicate_detector import DuplicateEventsRemover


markup_event({"text": 'Каждый четверг в 19:00 пр. Дзержинского 9 офис 1015 (первый этаж, вход со двора).'})


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


type_markup = TypeMarkup()
test_cases = [
    ("Мастер-класс по бачате!", "Мастер-класс"),
    ("Приглашаем на лекцию от знаменитого Н.", "лекцию"),
    ("О завтрашней интеллектуальной игре от клуба Умничек никто не слышал.", "интеллектуальной игре"),
    ("Организаторы модного показа заявляют, что всё будет фэшнбл", "модного показа"),
    ("Во время своего литературного вечера писатель Вася Пупкин представит свою поэму Пупок", "литературного вечера")
]
for text, expected_event in test_cases:
    matches = type_markup.markup(text)
    assert len(matches) == 1
    event_type, start, end = matches[0]
    assert text[start:end] == expected_event


currency_markup = MarkupCurrency()
test_cases = [
    ("36,00 — 196,00 руб.", ["196,00 руб."]),
    ("Взрослым - 12 byn, студентам - вход свободный", ["12 byn", "свободный"]),
    ("Я смог отжаться лишь 2 раза.", [])
]

for text, expected_currencies in test_cases:
    matches = currency_markup.markup(text)
    assert len(matches) == len(expected_currencies)
    for match, expected_currency in zip(matches, expected_currencies):
        event_type, start, end = match
        assert text[start:end] == expected_currency

pull_markup = PullEntityMarkup()
text = "2 декабря случилось раньше чем 2 декабря"
result = pull_markup.markup(text)
assert result[0][1] != result[1][1]
assert text[result[0][1]:result[0][2]] == text[result[1][1]:result[1][2]] == "2 декабря"

tags = [
    ("DATE", 1, 10),
    ("DATE", 2, 10),
    ("DATE", 3, 5),
    ("DATE", 11, 20)
]
tags = filter_tags(tags)
assert len(tags) == 2
assert tags[0] == ("DATE", 1, 10)
assert tags[1] == ("DATE", 11, 20)


# Remove duplicates
detector = DuplicateEventsRemover()
events = [
    {"title": "Состоится концерт группы The Feedback", "dates": [{"year": 2020, "month": 1, "day": 18}]},
    {"title": "Приходите на концерт группы The Feedback", "dates": [{"year": 2020, "month": 1, "day": 18}]},
    {"title": "Концерт группы The Feedback", "dates": [{"year": 2020, "month": 1, "day": 18}]}
]

filtered_events = detector.remove_duplicated_events(events)
assert len(filtered_events) == 1
