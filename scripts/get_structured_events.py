import json
import os
from typing import List

from models import Event
from scrappers import RelaxScrapper, TutByScrapper, CityDogScrapper, post_process_event
from datetime import datetime
from markup import MarkupCurrency


class Logger:
    def log_error(self, message):
        print("Error: %s" % message)

    def log_info(self, message):
        print("Info: %s" % message)


def write_events_to_file(filename, events: List[Event], currency_markup: MarkupCurrency, timestamp: datetime.date,
                         logger: Logger):
    first_read = False
    logger.log_info("Write events to %s" % filename)
    with open(filename, "w+", encoding="utf-8") as f:
        f.write("[\n")
        for event in events:
            event = post_process_event(event, logger, currency_markup, timestamp)
            if first_read:
                f.write(",\n")
            else:
                first_read = True
            f.write(json.dumps(event.to_json(), ensure_ascii=False, indent=4))
        f.write('\n]')


def get_structured_events(folder):
    currency_markup = MarkupCurrency()
    timestamp = datetime.now()

    today = datetime.now()
    folder_name = "%s\\%s_%s_%s" % (folder, today.year, today.month, today.day)
    if not os.path.exists(folder_name):
        os.mkdir(folder_name)

    logger = Logger()
    write_events_to_file(folder_name + "\\relax.json", RelaxScrapper(logger).list_events(), currency_markup, timestamp, logger)
    write_events_to_file(folder_name + "\\citydog.json", CityDogScrapper(logger).list_events(), currency_markup, timestamp, logger)
    write_events_to_file(folder_name + "\\tutby.json", TutByScrapper(logger).list_events(), currency_markup, timestamp, logger)

    return folder_name


if __name__ == "__main__":
    get_structured_events("C:\\Projects\\Research\\Events\\data\\event_data\\raw_data")
