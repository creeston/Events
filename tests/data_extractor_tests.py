from deepdiff import DeepDiff
from markup import DataExtractor

extractor = DataExtractor()

data = extractor.get_structured_data_from_markups([
    ("TIME", "10 февраля в 20:00"),
    ("TIME", "10 февраля"),
    ("TIME", "20:00"),
    ("FAC", "Корпус (пр. Машерова, 9)"),
    ("ADDRESS", "пр. Машерова, 9"),
    ("ADDRESS", "пр. Машерова, 9"),
    ("DATE", "античных времен до наших дней"),
    ("FREE", "свободный")
], "")
diff = DeepDiff(data, {"dates": [{"day": 10, "month": 2, "year": 2020, "hour": 20, "minute": 0}],
                       "place": ['Корпус'], "address": "пр. Машерова, 9",
                       "is_free": True, "cost": [], "title": "..."}, ignore_order=True)
assert not diff


data = extractor.get_structured_data_from_markups([
    ("DATE", "Privacy Day"),
    ("ORG", "Human Constanta"),
    ("TIME", "1 февраля"),
    ("TIME", "10:00-19:00"),
    ("ADDRESS", "ул.Фабрициуса 4"),
    ("FAC", "Imaguru Startup HUB, ул.Фабрициуса 4"),
    ("DATE", "этого года"),
    ("ORGANIZATION", "Инфобез"),
    ("FREE", "бесплатное")
], "Human Constanta")
diff = DeepDiff(data, {
    "dates": [{
        "day": 1, "month": 2, "year": 2020,
        "start_time": {"hour": 10, "minute": 0},
        "end_time": {"hour": 19, "minute": 0}}],
    "place": ['Imaguru Startup HUB'], "address": "ул.Фабрициуса 4",
    "is_free": True, "cost": [], "title": "Human Constanta..."}, ignore_order=True)

assert not diff

data = extractor.get_structured_data_from_markups([
    ("TIME", "7 марта в 17:00"),
    ("TIME", "10:00-19:00"),
    ("FAC", '"Ступени"'),
    ("FAC", 'парк Горького'),
    ("ADDRESS", "ул. Фрунзе, 2"),
    ("FAC", 'Фрунзе, 2'),
], "")
diff = DeepDiff(data, {"dates": [{"day": 7, "month": 3, "year": 2020, "hour": 17, "minute": 0}],
                       "place": ['парк Горького', '"Ступени"'], "address": "ул. Фрунзе, 2",
                       "is_free": False, "cost": [], "title": "..."}, ignore_order=True)
assert not diff

address = extractor.get_best_address([
    "ул. Хоружей 613",
    "ул. Хоружей 613-3",
    "два ул. Хоружей 613",
])

assert address == "ул. Хоружей 613-3"


unique_dates = []
extractor.get_unique_dates([
    {"day": 12, "month": 10},
    {"day": 12, "month": 10, "hour": 5, "minute": 40},
    {"minute": 40, "hour": 5},
    [{"day": 12, "month": 10}, {"day": 14, "month": 10}],
], unique_dates)

assert len(unique_dates) == 2 \
       and unique_dates[0] == {"day": 12, "month": 10, "minute": 40, "hour": 5} \
       and unique_dates[1] == {"day": 14, "month": 10}


unique_dates = []
extractor.get_unique_dates([
    {"day": 12, "month": 10},
    {"day": 12, "month": 10, "hour": 5, "minute": 40},
    {"minute": 40, "hour": 5},
    {"start": {"day": 12, "month": 10}, "end": {"day": 14, "month": 10}}
], unique_dates)

assert len(unique_dates) == 1 \
       and unique_dates[0] == {"start": {"day": 12, "month": 10, "minute": 40, "hour": 5},
                               "end": {"day": 14, "month": 10}}

unique_dates = []
extractor.get_unique_dates([
    {"day": 12, "month": 10},
    {"minute": 40, "hour": 5},
], unique_dates)
assert len(unique_dates) == 1 and unique_dates[0] == {"day": 12, "month": 10, "minute": 40, "hour": 5}

unique_dates = []
extractor.get_unique_dates([
    {"minute": 40, "hour": 5},
    {"day": 12, "month": 10},
], unique_dates)
assert len(unique_dates) == 1 and unique_dates[0] == {"day": 12, "month": 10, "minute": 40, "hour": 5}
