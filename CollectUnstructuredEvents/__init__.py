import asyncio
import datetime
import json
import time
from tempfile import mkdtemp

import cloudinary
import os
import sys
import logging

sys.path.append('/home/site/myenv/lib/python3.7/site-packages')
sys.path.append("../")

from typing import List
from azure.storage.blob import ContainerClient
from azure.storage.queue import QueueService
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

queue_client = QueueService(connection_string=connection_string, is_emulated=True)


def parse_events(events: List[UnstructuredEvent], classifier, extractor):
    for unstructured_event in events:
        try:
            yield parse_event(unstructured_event, classifier, extractor, uploader)
        except Exception as e:
            print(e)
            continue


def download_model(tempdir) -> str:
    model_dir = os.path.join(tempdir, "model")
    model_path = os.path.join(model_dir, "export.pkl")
    os.mkdir(model_dir)
    with open(model_path, "wb") as f:
        model_service.download_blob(model_blob).readinto(f)
    return model_dir


def get_tg_code():
    logging.info("Telegram code needs to be input. Put it into tgcode queue")
    while True:
        messages = queue_client.get_messages("tgcode", num_messages=1)
        if len(messages) == 0:
            time.sleep(10)
        else:
            content = messages[0].content
            queue_client.delete_message('tgcode', messages[0].id, messages[0].pop_receipt)
            return content


async def get_unstructured_events():
    extractor = NamedEntityExtractor()
    logging.info("Start downloading model")
    tempdir = mkdtemp()
    model_file_path = download_model(tempdir)
    try:
        logging.info("Model was downloaded to %s" % model_file_path)
        classifier = TypeClassifier(model_file_path)

        today = datetime.datetime.now()
        blob_name = "%s_%s_%s" % (today.year, today.month, today.day)

        logging.info("Start getting VK events")
        vk_blob_name = blob_name + "\\vk.json"
        existing_blobs = service.list_blobs(vk_blob_name)
        if len(list(existing_blobs)) == 0:
            vk_events = list(VkEventFetcher("/home/site/myenv").fetch_events())
            logging.info("Finish getting VK events")
            logging.info("Start parsing VK events")
            vk_parsed_events = list(parse_events(vk_events, classifier, extractor))
            content = json.dumps([e.to_json() for e in vk_parsed_events if e], ensure_ascii=False, indent=4)
            service.upload_blob(vk_blob_name, content)
            logging.info("Finish parsing VK events")

        tg_blob_name = blob_name + "\\tg.json"
        existing_blobs = service.list_blobs(tg_blob_name)
        if len(list(existing_blobs)) == 0:
            logging.info("Start getting TG events")
            tg_events = []
            async for event in TelegramEventFetcher("/home/site/myenv").fetch_events(code_callback=get_tg_code):
                tg_events.append(event)
            logging.info("Finished getting TG events")
            logging.info("Start parsing TG events")
            tg_parsed_events = list(parse_events(tg_events, classifier, extractor))
            content = json.dumps([e.to_json() for e in tg_parsed_events if e], ensure_ascii=False, indent=4)
            service.upload_blob(tg_blob_name, content)
            logging.info("Finished parsing TG events")
    finally:
        os.remove(os.path.join(model_file_path, "export.pkl"))
        os.rmdir(model_file_path)
        os.rmdir(tempdir)


def main(msg) -> None:
    asyncio.run(get_unstructured_events())


if __name__ == "__main__":
    main(None)
