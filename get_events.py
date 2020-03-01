from scrappers import RelaxScrapper, TutByScrapper, CityDogScrapper
import json
from classify import EventTagClassifier, TextPreprocessor, load_json, EventNotEventClassifier
from random import shuffle
from event_fetchers import TelegramEventFetcher, VkEventFetcher


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


#write_events_to_file("data/relax.json", RelaxScrapper().list_events())
#write_events_to_file("data/citydog.json", CityDogScrapper().list_events())
#write_events_to_file("data/tutby.json", TutByScrapper().list_events())

preprocessor = TextPreprocessor()
preprocessor.load_vocab("training\\vocab")
type_classifier = EventTagClassifier(preprocessor)
type_classifier.load_model("training\\type_classifier")

tag_classifier = EventTagClassifier(preprocessor)
type_classifier.load_model("training\\tag_classifier")

is_event_classifier = EventNotEventClassifier(preprocessor)
is_event_classifier.load_model("training\\is_event_classifier")


raw_events = []
events = VkEventFetcher().fetch_events()
for event in events:
    is_event = is_event_classifier.is_event(event)
    if not is_event:
        raw_events.append(preprocessor.preprocess_text(event) + "\n")

open("data\\raw_events", "a", encoding="utf-8").writelines(raw_events)

