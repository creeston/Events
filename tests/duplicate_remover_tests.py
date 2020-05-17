from duplicate_detector import DuplicateEventsRemover


detector = DuplicateEventsRemover()
events = [
    {"title": "Состоится концерт группы The Feedback", "dates": [{"year": 2020, "month": 1, "day": 18}]},
    {"title": "Приходите на концерт группы The Feedback", "dates": [{"year": 2020, "month": 1, "day": 18}]},
    {"title": "Концерт группы The Feedback", "dates": [{"year": 2020, "month": 1, "day": 18}]}
]

filtered_events = detector.remove_duplicated_events(events)
assert len(filtered_events) == 1

strings = ['кинотеатре "Центральный"', 'Curry House', 'к/т «Центральный»']
filtered_string = detector.remove_duplicate_strings(strings)

assert len(filtered_string) == 2
