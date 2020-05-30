import json
import datetime
import os
import asyncio
import cloudinary

from markup import NamedEntityExtractor
from scrappers import VkEventFetcher, TelegramEventFetcher, UnstructuredEvent, parse_event
from classifier import TypeClassifier
from cloudinary import uploader
from configuration import cloudinary_config
from typing import List


cloudinary.config(
  cloud_name=cloudinary_config['cloud_name'],
  api_key=cloudinary_config['api_key'],
  api_secret=cloudinary_config['api_secret']
)


def parse_events(events: List[UnstructuredEvent], classifier, extractor):
    for unstructured_event in events:
        try:
            event = parse_event(unstructured_event, classifier, extractor, uploader)
            yield event
        except Exception as e:
            print(e)
            continue


async def get_unstructured_events(folder):
    extractor = NamedEntityExtractor()
    classifier = TypeClassifier("C:\\Projects\\Research\\Events\\data\\model")

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
