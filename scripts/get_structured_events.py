import json
import os
from typing import List

from models import Event, event_type_mapping
from scrappers import RelaxScrapper, TutByScrapper, CityDogScrapper
from datetime import datetime
from markup import MarkupCurrency


def write_events_to_file(filename, events: List[Event], currency_markup: MarkupCurrency, timestamp: datetime.date):
    first_read = False
    with open(filename, "w+", encoding="utf-8") as f:
        f.write("[\n")
        for event in events:
            if event.raw_cost:
                cost = event.raw_cost
                markup = currency_markup.markup(cost)
                money_tags = [m for m in markup if m[0] == "MONEY"]
                currencies = [currency_markup.parse_currency(cost[s:e]) for _, s, e in money_tags]
                currencies = sorted(list(set([c for sublist in currencies for c in sublist])))
                event.cost = currencies
                if any(m[0] == "FREE" for m in markup) and "free" not in event.event_tags:
                    event.event_tags.append("free")

            if event.raw_tags and len(event.raw_tags) > 0:
                for raw_tag in event.raw_tags:
                    if raw_tag in event_type_mapping:
                        event.event_tags.append(event_type_mapping[raw_tag])

            event.timestamp = timestamp
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

    write_events_to_file(folder_name + "\\relax.json", RelaxScrapper().list_events(), currency_markup, timestamp)
    write_events_to_file(folder_name + "\\citydog.json", CityDogScrapper().list_events(), currency_markup, timestamp)
    write_events_to_file(folder_name + "\\tutby.json", TutByScrapper().list_events(), currency_markup, timestamp)

    return folder_name


if __name__ == "__main__":
    get_structured_events("C:\\Projects\\Research\\Events\\data\\event_data\\raw_data")
