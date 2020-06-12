import datetime
import json
import azure.functions as func
import sys
import os

sys.path.append("../")

from typing import List
from azure.storage.blob import ContainerClient
from common import Logger
from markup import MarkupCurrency
from models import Event
from scrappers import post_process_event, RelaxScrapper, CityDogScrapper, TutByScrapper

container_name = "raweventdata"
connection_string = os.environ['AzureWebJobsStorage']
service = ContainerClient.from_connection_string(connection_string, container_name)


def write_events_to_blob(blob_name, events: List[Event], currency_markup: MarkupCurrency,
                         timestamp: datetime.datetime,
                         logger: Logger):
    first_read = False
    logger.log_info("Write events to %s" % blob_name)
    content = ["[\n"]
    for event in events:
        event = post_process_event(event, logger, currency_markup, timestamp)
        if first_read:
            content.append(",\n")
        else:
            first_read = True
        content.append(json.dumps(event.to_json(), ensure_ascii=False, indent=4))
    content.append('\n]')
    content = "".join(content)
    service.upload_blob(blob_name, content)


def get_structured_events():
    currency_markup = MarkupCurrency()
    timestamp = datetime.datetime.now()
    today = datetime.datetime.now()
    blob_name = "%s_%s_%s" % (today.year, today.month, today.day)

    logger = Logger()
    scrappers = {
        "relax": RelaxScrapper(logger),
        "citydog": CityDogScrapper(logger),
        "tutby": TutByScrapper(logger)
    }

    for source, scrapper in scrappers.items():
        print(source)
        events = scrapper.list_events()
        write_events_to_blob(blob_name + "\\%s.json" % source, events, currency_markup, timestamp, logger)

    return blob_name


def main(msg) -> None:
    get_structured_events()


if __name__ == "__main__":
    main(None)
