from scrappers import RelaxScrapper, TutByScrapper, CityDogScrapper
import json


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


write_events_to_file("data/event_data/relax.json", RelaxScrapper().list_events())
write_events_to_file("data/event_data/citydog.json", CityDogScrapper().list_events())
write_events_to_file("data/event_data/tutby.json", TutByScrapper().list_events())
