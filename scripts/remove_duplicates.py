import json
from duplicate_detector import DuplicateEventsRemover


def load_json(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filename, obj):
    with open(filename, "w+", encoding="utf-8") as f:
        return json.dump(obj, f, ensure_ascii=False, indent=4)


folder = "C:\\Projects\\Research\\Events\\data\\event_data\\raw_data\\2020_5_13_23"
tut = load_json("%s\\tutby.json" % folder)
cd = load_json("%s\\citydog.json" % folder)
relax = load_json("%s\\relax.json" % folder)

events = []
events.extend(tut)
events.extend(cd)
events.extend(relax)

duplicate_detector = DuplicateEventsRemover()
events = duplicate_detector.remove_duplicated_events(events)

save_json("%s\\events.json" % folder, events)
