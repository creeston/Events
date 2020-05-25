import json
from typing import List

from duplicate_detector import DuplicateEventsRemover
from models import Event


def load_events(filename) -> List[Event]:
    with open(filename, "r", encoding="utf-8") as f:
        return [Event.from_json(e) for e in json.load(f)]


def save_json(filename, events: List[Event]):
    with open(filename, "w+", encoding="utf-8") as f:
        return json.dump([e.to_json() for e in events], f, ensure_ascii=False, indent=4)


def remove_duplicates(folder):
    tut = load_events("%s\\tutby.json" % folder)
    cd = load_events("%s\\citydog.json" % folder)
    relax = load_events("%s\\relax.json" % folder)
    vk = load_events("%s\\tg.json" % folder)
    tg = load_events("%s\\vk.json" % folder)

    events = tut + cd + relax + vk + tg

    duplicate_detector = DuplicateEventsRemover()
    events = duplicate_detector.remove_duplicated_events(events)
    save_json("%s\\events.json" % folder, events)


if __name__ == "__main__":
    remove_duplicates("C:\\Projects\\Research\\Events\\data\\event_data\\raw_data\\2020_5_22")
