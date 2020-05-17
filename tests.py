import datetime

from models import EventDateRange
from interpreters import DateInterpreter
from markup import TypeMarkup, MarkupCurrency, PullEntityMarkup, filter_tags, markup_event


markup_event({"text": 'Каждый четверг в 19:00 пр. Дзержинского 9 офис 1015 (первый этаж, вход со двора).'})

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


