import json
import os

from scrappers import RelaxScrapper, TutByScrapper, CityDogScrapper
from datetime import datetime


def write_events_to_file(filename, events):
    first_read = False
    with open(filename, "w+", encoding="utf-8") as f:
        f.write("[\n")
        for event in events:
            if first_read:
                f.write(",\n")
            else:
                first_read = True
            f.write(json.dumps(event.to_json(), ensure_ascii=False, indent=4))
        f.write('\n]')


today = datetime.now()
folder_name = "data/event_data/raw_data/%s_%s_%s_%s/" % (today.year, today.month, today.day, today.hour)
if not os.path.exists(folder_name):
    os.mkdir(folder_name)

write_events_to_file(folder_name + "relax.json", RelaxScrapper().list_events())
write_events_to_file(folder_name + "citydog.json", CityDogScrapper().list_events())
write_events_to_file(folder_name + "tutby.json", TutByScrapper().list_events())
