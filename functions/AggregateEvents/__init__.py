import azure.functions as func
import datetime
import json
import sys
import logging
import os

sys.path.append("../")

from azure.core.exceptions import ResourceNotFoundError
from typing import List
from azure.storage.blob import ContainerClient
from duplicate_detector import DuplicateEventsRemover
from models import Event, EventDateRange


container_name = "raweventdata"
connection_string = os.environ['AzureWebJobsStorage']
service = ContainerClient.from_connection_string(connection_string, container_name)


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


def load_events(blob_name) -> List[Event]:
    try:
        text = service.download_blob(blob_name).readall()
        return [Event.from_json(e) for e in json.loads(text)]
    except ResourceNotFoundError:
        return None


def save_events(events: List[Event], blob_name):
    text = json.dumps([e.to_json() for e in events], ensure_ascii=False, indent=4)
    service.upload_blob(blob_name, text)


def remove_duplicates():
    today = datetime.datetime.now()
    blob_folder = "%s_%s_%s" % (today.year, today.month, today.day)
    events = []
    for events_source in ["tutby", "citydog", "relax", "tg", "vk"]:
        events_from_source = load_events("%s\\%s.json" % (blob_folder, events_source))
        if not events_from_source:
            logging.info("Events from %s were not found" % events_source)
            return
        events.extend(events_from_source)

    events = filter_events(events)
    duplicate_detector = DuplicateEventsRemover()
    events = duplicate_detector.remove_duplicated_events(events)
    events_blob = "%s\\events.json" % blob_folder
    save_events(events, "%s\\events.json" % blob_folder)
    return events_blob


def main(mytimer: func.TimerRequest, msg: func.Out[str]) -> None:
    events_blob = remove_duplicates()
    if not events_blob:
        return
    msg.set(events_blob)
