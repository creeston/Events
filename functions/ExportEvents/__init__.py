import logging
import azure.functions as func
import json
import os

from typing import List
from azure.storage.blob import ContainerClient
from sql_storage import EventRepository
from models import group_by_dates, Event
from duplicate_detector import DuplicateEventsRemover

connection_string = os.environ['AzureWebJobsStorage']
container_name = "raweventdata"
service = ContainerClient.from_connection_string(connection_string, container_name)


def load_events(blob_name) -> List[Event]:
    text = service.download_blob(blob_name).readall()
    return [Event.from_json(e) for e in json.loads(text)]


def save_to_storage(blob_name):
    repository = EventRepository()
    duplicate_remover = DuplicateEventsRemover()
    events = load_events(blob_name)
    logging.info("%d events has to be saved" % len(events))
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
        logging.info("%d events saved" % len(events_to_save))


def main(msg: func.QueueMessage) -> None:
    blob_name = msg.get_body()
    save_to_storage(blob_name)
    logging.info('Python queue trigger function processed a queue item: %s',
                 msg.get_body().decode('utf-8'))


if __name__ == "__main__":
    main(func.QueueMessage(body="2020_5_29/events.json"))

