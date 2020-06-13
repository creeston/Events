import asyncio
import datetime
import json
import cloudinary
import azure.functions as func
import os
import sys
import logging

sys.path.append("../")

from typing import List
from azure.storage.blob import ContainerClient

from cloudinary import uploader
from classifier import TypeClassifier
from configuration import cloudinary_config
from markup import NamedEntityExtractor
from scrappers import UnstructuredEvent, parse_event, TelegramEventFetcher, VkEventFetcher

cloudinary.config(
  cloud_name=cloudinary_config['cloud_name'],
  api_key=cloudinary_config['api_key'],
  api_secret=cloudinary_config['api_secret']
)


connection_string = os.environ['AzureWebJobsStorage']
container_name = "raweventdata"
service = ContainerClient.from_connection_string(connection_string, container_name)
model_blob = "classifier/export.pkl"
model_service = ContainerClient.from_connection_string(connection_string, "model")


def parse_events(events: List[UnstructuredEvent], classifier, extractor):
    for unstructured_event in events:
        try:
            yield parse_event(unstructured_event, classifier, extractor, uploader)
        except Exception as e:
            print(e)
            continue


def download_model() -> str:
    model_path = "temp\\model\\export.pkl"
    model_dir = "temp\\model"
    if os.path.exists(model_dir):
        if os.path.exists(model_path):
            os.remove(model_path)
    else:
        if not os.path.exists("temp"):
            os.mkdir("temp")
        os.mkdir(model_dir)
    with open(model_path, "wb") as f:
        model_service.download_blob(model_blob).readinto(f)
    return model_dir


async def get_unstructured_events():
    extractor = NamedEntityExtractor()
    logging.info("Start downloading model")
    model_file_path = download_model()
    logging.info("Model was downloaded to %s" % model_file_path)
    classifier = TypeClassifier(model_file_path)

    today = datetime.datetime.now()
    blob_name = "%s_%s_%s" % (today.year, today.month, today.day)

    logging.info("Start getting VK events")

    vk_events = list(VkEventFetcher().fetch_events())

    logging.info("Finish getting VK events")
    logging.info("Start parsing VK events")

    vk_parsed_events = list(parse_events(vk_events, classifier, extractor))
    content = json.dumps([e.to_json() for e in vk_parsed_events if e], ensure_ascii=False, indent=4)
    service.upload_blob(blob_name + "\\vk.json", content)
    logging.info("Finish parsing VK events")

    logging.info("Start getting TG events")
    tg_events = []
    async for event in TelegramEventFetcher().fetch_events():
        tg_events.append(event)

    logging.info("Finished getting TG events")
    logging.info("Start parsing TG events")

    tg_parsed_events = list(parse_events(tg_events, classifier, extractor))
    content = json.dumps([e.to_json() for e in tg_parsed_events if e], ensure_ascii=False, indent=4)
    service.upload_blob(blob_name + "\\tg.json", content)

    logging.info("Finished parsing TG events")



def main(msg) -> None:
    asyncio.run(get_unstructured_events())


if __name__ == "__main__":
    main(None)
