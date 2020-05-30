import json
from typing import List

from sql_storage import EventRepository
from models import group_by_dates, Event
from duplicate_detector import DuplicateEventsRemover


def load_events(folder) -> List[Event]:
    with open("%s\\events.json" % folder, "r", encoding="utf-8") as f:
        events = json.load(f)
    events = [Event.from_json(e) for e in events]
    return events


def save_to_storage(folder):
    repository = EventRepository()
    duplicate_remover = DuplicateEventsRemover()
    events = load_events(folder)
    events_by_date = group_by_dates(events)

    for date, events in events_by_date.items():
        events_to_save = []
        ids_to_remove = []
        existing_events = list(repository.list_events_by_date(date))
        duplicate_list = duplicate_remover.detect_duplicates(existing_events + events)
        for duplicates in duplicate_list:
            if len(duplicates) == 1:
                unique_event = duplicates[0]
            else:
                if any([not e.timestamp for e in duplicates]):
                    unique_event = max(duplicates, key=lambda e: len(e.to_str()))
                else:
                    unique_event = max(duplicates, key=lambda e: e.timestamp)

                duplicates = [d for d in duplicates if d != unique_event]
                ids_to_remove.extend([e.event_id for e in duplicates if e.event_id])

            if not unique_event.event_id:
                events_to_save.append(unique_event)
        repository.save_events(events_to_save)
        repository.remove_events(ids_to_remove)


if __name__ == "__main__":
    save_to_storage("C:\\Projects\\Research\\Events\\data\\event_data\\raw_data\\2020_5_29")
