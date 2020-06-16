import logging
import azure.functions as func
import os

from trainers import labels, ClassifierTrainer
from common import Logger
from tempfile import mkdtemp


def load_data(training_data):
    raw_data = []
    for entity in training_data:
        text = entity['Text']
        event_labels = entity['Labels'].split(',')
        label_ids = [labels.index(label) for label in event_labels if label in labels]
        raw_data.append((text, label_ids))
    return raw_data


def download_model(tempdir,
                   itos_blob: func.InputStream,
                   weight_blob: func.InputStream,
                   enc_weight_blob: func.InputStream):
    itos_path = os.path.join(tempdir, "itos.pkl")
    weight_path = os.path.join(tempdir, "lm_5_ep_lr2-3_5_stlr.pth")
    enc_weight_path = os.path.join(tempdir, "lm_5_ep_lr2-3_5_stlr_enc.pth")

    with open(itos_path, "wb") as f:
        f.write(itos_blob.read())
    with open(weight_path, "wb") as f:
        f.write(weight_blob.read())
    with open(enc_weight_path, "wb") as f:
        f.write(enc_weight_blob.read())
    return itos_path, weight_path, enc_weight_path


def main(msg,
         itos: func.InputStream, encweight: func.InputStream, weight: func.InputStream,
         data) -> None:
    trainer = ClassifierTrainer(Logger())
    logging.info("Start loading data for training")
    data = load_data(data)
    logging.info("Start downloading base model")
    tempdir = mkdtemp()
    export_path = None
    itos_file, weight_file, enc_weight_file = download_model(tempdir, itos, weight, encweight)
    try:
        weights_pretrained = os.path.join(tempdir, 'lm_5_ep_lr2-3_5_stlr')
        itos_pretrained = os.path.join(tempdir, 'itos')
        pretrained_data = (weights_pretrained, itos_pretrained)
        logging.info("Start training")
        result, export_path = trainer.train_classifier_model(data, pretrained_data, tempdir)
        logging.info("Training finished " + str(result))
    finally:
        os.remove(itos_file)
        os.remove(weight_file)
        os.remove(enc_weight_file)
        if export_path:
            os.remove(export_path)
        os.rmdir(tempdir)


if __name__ == "__main__":
    main(None, None, None, None, None)
