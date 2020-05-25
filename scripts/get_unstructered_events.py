import json
import datetime
import os
import asyncio
import cloudinary

from markup import NamedEntityExtractor
from scrappers import VkEventFetcher, TelegramEventFetcher
from classifier import TypeClassifier
from models import EventDateRange
from cloudinary import uploader
from configuration import classifier_model, cloudinary_config


cloudinary.config(
  cloud_name=cloudinary_config['cloud_name'],
  api_key=cloudinary_config['api_key'],
  api_secret=cloudinary_config['api_secret']
)


def parse_events(events, classifier, extractor):
    for event_json in events:
        try:
            event_types = classifier.predict_type(event_json["text"])
            if len(event_types) == 0:
                continue

            event = extractor.extract_entities_from_event(event_json['text'])
            if not event or not event.event_dates:
                continue

            dates = []
            for d in event.event_dates:
                if type(d) == EventDateRange:
                    if (d.start_day and d.start_day.year < 2019) or (d.end_day and d.end_day.year < 2019):
                        continue
                else:
                    if d.year < 2019:
                        continue
                dates.append(d)

            if len(dates) == 0:
                continue

            if "url" in event_json and event_json['url']:
                event.source = event_json['url']
            if "timestamp" in event_json and event_json['timestamp']:
                event.timestamp = event_json['timestamp']
            if "title" in event_json and event_json['title']:
                event.title = event_json['title']
            if 'poster' in event_json and event_json['poster']:
                event.poster = event_json['poster']
            if 'poster_bytes' in event_json and event_json['poster_bytes']:
                upload_result = uploader.upload_image(event_json['poster_bytes'])
                event.poster = upload_result.url

            event.event_dates = dates
            event.event_tags = event_types

            yield event
        except Exception as e:
            print(e)
            continue


async def get_unstructured_events(folder):
    extractor = NamedEntityExtractor()
    classifier = TypeClassifier(classifier_model)

    today = datetime.datetime.now()
    folder_name = "%s\\%s_%s_%s" % (folder, today.year, today.month, today.day)
    if not os.path.exists(folder_name):
        os.mkdir(folder_name)

    tg_events = []
    async for event in TelegramEventFetcher().fetch_events():
        tg_events.append(event)

    with open(folder_name + "\\tg.json", "w", encoding="utf-8") as f:
        tg_parsed_events = list(parse_events(tg_events, classifier, extractor))
        json.dump([e.to_json() for e in tg_parsed_events], f, ensure_ascii=False, indent=4)

    vk_events = list(VkEventFetcher().fetch_events())
    with open(folder_name + "\\vk.json", "w", encoding="utf-8") as f:
        vk_parsed_events = list(parse_events(vk_events, classifier, extractor))
        json.dump([e.to_json() for e in vk_parsed_events], f, ensure_ascii=False, indent=4)

    return folder_name


if __name__ == "__main__":
    asyncio.run(get_unstructured_events("C:\\Projects\\Research\\Events\\data\\event_data\\raw_data"))
