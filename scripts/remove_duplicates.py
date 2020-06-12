import datetime
import json

from typing import List
from duplicate_detector import DuplicateEventsRemover
from models import Event, EventDateRange


def load_events(filename) -> List[Event]:
    with open(filename, "r", encoding="utf-8") as f:
        return [Event.from_json(e) for e in json.load(f)]


def save_json(filename, events: List[Event]):
    with open(filename, "w+", encoding="utf-8") as f:
        return json.dump([e.to_json() for e in events], f, ensure_ascii=False, indent=4)


def filter_events(events: List[Event]) -> List[Event]:
    filtered = []
    for event in events:
        should_skip = False
        # if event has both date range and singular date - take only singular dates
        if any(type(d) == EventDateRange for d in event.event_dates) and \
                any(type(d) == datetime.datetime for d in event.event_dates):
            event.event_dates = [d for d in event.event_dates if type(d) == datetime.datetime]

        for d in event.event_dates:
            if type(d) == EventDateRange:
                if d.end is None:
                    should_skip = True
                    break
        if not should_skip:
            filtered.append(event)
    return filtered


def remove_duplicates(folder):
    tut = load_events("%s\\tutby.json" % folder)
    cd = load_events("%s\\citydog.json" % folder)
    relax = load_events("%s\\relax.json" % folder)
    vk = load_events("%s\\tg.json" % folder)
    tg = load_events("%s\\vk.json" % folder)

    events = filter_events(tut + cd + relax + vk + tg)
    duplicate_detector = DuplicateEventsRemover()
    events, duplicates = duplicate_detector.remove_duplicated_events(events)
    save_json("%s\\events.json" % folder, events)
    with open("%s\\duplicates.json" % folder, "w+", encoding="utf-8") as f:
        return json.dump([[e.description for e in group] for group in duplicates if len(set([e.description for e in group])) != 1 ], f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    remove_duplicates("C:\\Projects\\Research\\Events\\data\\event_data\\raw_data\\2020_5_29")
