import logging
import azure.functions as func
import os
from azure.storage.blob import ContainerClient
from azure.cosmosdb.table.tableservice import TableService
from trainers import labels, ClassifierTrainer
from common import Logger

connection_string = os.environ['AzureWebJobsStorage']
service = TableService(connection_string=connection_string, is_emulated=True)

table = "eventClassificationTrainingData"
weights_blob = "ULMFit/lm_5_ep_lr2-3_5_stlr.pth"
enc_weights_blob = "ULMFit/lm_5_ep_lr2-3_5_stlr_enc.pth"
itos_blob = "ULMFit/itos.pkl"
model_service = ContainerClient.from_connection_string(connection_string, "model")


def load_data():
    raw_data = []
    for entity in service.query_entities(table):
        text = entity['Text']
        event_labels = entity['Labels'].split(',')
        label_ids = [labels.index(label) for label in event_labels if label in labels]
        raw_data.append((text, label_ids))
    return raw_data


def download_model() -> str:
    itos_path = "temp\\ULMFit\\itos.pkl"
    weight_path = "temp\\ULMFit\\lm_5_ep_lr2-3_5_stlr.pth"
    enc_weight_path = "temp\\ULMFit\\lm_5_ep_lr2-3_5_stlr_enc.pth"

    model_dir = "temp\\ULMFit"
    if os.path.exists(model_dir):
        if os.path.exists(itos_path):
            os.remove(itos_path)
        if os.path.exists(weight_path):
            os.remove(weight_path)
        if os.path.exists(enc_weight_path):
            os.remove(enc_weight_path)
    else:
        if not os.path.exists("temp"):
            os.mkdir("temp")
        os.mkdir(model_dir)

    with open(itos_path, "wb") as f:
        model_service.download_blob(itos_blob).readinto(f)
    with open(weight_path, "wb") as f:
        model_service.download_blob(weights_blob).readinto(f)
    with open(enc_weight_path, "wb") as f:
        model_service.download_blob(enc_weights_blob).readinto(f)
    return model_dir


def main(msg) -> None:
    trainer = ClassifierTrainer(Logger())
    logging.info("Start loading data for training")
    data = load_data()
    logging.info("Start downloading base model")
    model_path = download_model()
    weights_pretrained = os.path.abspath(model_path + '\\lm_5_ep_lr2-3_5_stlr')
    itos_pretrained = os.path.abspath(model_path + '\\itos')
    pretrained_data = (weights_pretrained, itos_pretrained)
    logging.info("Start training")
    train_model = os.path.abspath("trained_model")
    result = trainer.train_classifier_model(data, pretrained_data, train_model)
    logging.info("Training finished " + str(result))
