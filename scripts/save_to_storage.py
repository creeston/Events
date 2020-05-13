import json
import copy

from storage import EventRepository
from models import group_by_dates, Event
from classifier import TypeClassifier
from duplicate_detector import DuplicateEventsRemover

repository = EventRepository()
with open("C:\\Projects\\Research\\Events\\data\\event_data\\raw_data\\2020_5_13_23\\events.json", "r", encoding="utf-8") as f:
    events = json.load(f)

classifier = TypeClassifier("C:\\Projects\\Research\\Events\\data\\model")
duplicate_remover = DuplicateEventsRemover()
events_by_date = group_by_dates(events)

for date, events in events_by_date.items():
    if not date:
        print("Date is None for %d events" % (len(events)))
        continue

    events_to_save = []
    row_keys_to_remove = []
    existing_events = list(repository.list_events_by_date(date))
    duplicate_list = duplicate_remover.detect_duplicates(existing_events + events)
    for duplicates in duplicate_list:
        if len(duplicates) == 1:
            unique_event = duplicates[0]
        else:
            unique_event = max(duplicates, key=lambda e: len(e['title'] + e['description']))
            existing_row_keys = [e['RowKey'] for e in duplicates if 'RowKey' in e]
            existing_types = [e['type'] for e in duplicates if 'verified' in e and e['verified']]
            if len(existing_row_keys) > 0:
                unique_event['RowKey'] = existing_row_keys[0]
                row_keys_to_remove.extend(existing_row_keys[1:])
            if len(existing_types) > 0:
                unique_event['type'] = existing_types[0]

            duplicates_to_save = [copy.deepcopy(d) for d in duplicates]
            duplicates_hash = hash(" ".join([e['description'] for e in duplicates_to_save]))
            for d in duplicates_to_save:
                d['PartitionKey'] = "%s_%s_%s_%s" % (date.year, date.month, date.day, duplicates_hash)
            repository.save_events_by_date(duplicates_to_save, date, table_name=repository.event_duplicates_table)

        if 'type' not in unique_event or not unique_event['type']:
            unique_event['type'] = classifier.predict_event_type(Event.from_json(unique_event))
        events_to_save.append(unique_event)
    repository.save_events_by_date(events_to_save, date)
    repository.remove_rows(date, row_keys_to_remove)
