import fastai.text as ftext
import pandas as pd
import random

from sklearn.model_selection import train_test_split
from preprocess import TextPreprocessor


labels = [
    "compete",
    "concert",
    "concert_programm",
    "exhibition",
    "festival",
    "food",
    "free",
    "game",
    "lecture",
    "market",
    "online",
    "open air",
    "party",
    "show",
    "sport",
    "standup",
    "theatre",
    "tour",
    "training",
    "view"
]


class ClassifierTrainer:
    def __init__(self, logger):
        self.logger = logger
        self.preprocessor = TextPreprocessor()

    def train_classifier_model(self, raw_data, pretrained_model, output_path):
        df_train, df_val, df_test = self._prepare_train_data(raw_data)
        tokenizer = ftext.Tokenizer(lang='xx')
        data_lm = ftext.TextLMDataBunch.from_df(
            '',
            tokenizer=tokenizer,
            bs=16,
            train_df=df_train,
            valid_df=df_val,
            text_cols=0,
            label_delim=' ')

        self.logger.log_info("Start training language model")
        language_model_learner = self._create_language_model_learner(data_lm, pretrained_model)
        encoder_name = self._train_language_model(language_model_learner)

        self.logger.log_info("Start classifier")
        classifier_learner = self._create_classifier_learner(data_lm, df_train, df_val, tokenizer, encoder_name)
        self._train_classifier(classifier_learner)

        self.logger.log_info("Export model")
        classifier_learner.export(output_path)
        learner_new = ftext.load_learner(output_path)
        label_precision = self._evaluate_model(df_test, learner_new)
        return label_precision

    def _prepare_train_data(self, raw_data):
        preprocessed_data = [(self.preprocessor.preprocess_text(d[0]), d[1]) for d in raw_data]

        df_train = pd.DataFrame(columns=['Text', 'Label'])
        df_test = pd.DataFrame(columns=['Text', 'Label'])

        random.shuffle(preprocessed_data)
        data_texts = [d[0] for d in preprocessed_data]
        data_labels = [" ".join([str(label) for label in d[1]]) for d in preprocessed_data]

        df_train['Text'], df_test['Text'], df_train['Label'], df_test['Label'] = train_test_split(
            data_texts, data_labels, test_size=0.1, random_state=1)
        df_train, df_val = train_test_split(df_train, test_size=0.1, random_state=1)
        return df_train, df_val, df_test

    def _create_language_model_learner(self, data_lm, pretrained_model):
        # Hack for this specific model - lm_5_ep_lr2-3_5_stlr, as it was trained on older version of fast ai.
        # For new models you shouldn't override the config
        config = ftext.awd_lstm_lm_config.copy()
        config['n_hid'] = 1150

        learn_lm = ftext.language_model_learner(data_lm, ftext.AWD_LSTM,
                                                config=config, pretrained_fnames=pretrained_model, drop_mult=0.3)
        return learn_lm

    def _train_language_model(self, learn_lm):
        # comment to speed up testing
        # learn_lm.freeze()
        # learn_lm.fit_one_cycle(3, 1e-2, moms=(0.8, 0.7))

        # learn_lm.unfreeze()
        learn_lm.fit_one_cycle(5, 1e-3, moms=(0.8, 0.7))

        encoder_name = 'ft_enc_events'
        learn_lm.save_encoder(encoder_name)
        return encoder_name

    def _create_classifier_learner(self, data_lm, df_train, df_val, tokenizer, encoder_name):
        data_class = ftext.TextClasDataBunch.from_df('', vocab=data_lm.train_ds.vocab, bs=32, train_df=df_train,
                                                     valid_df=df_val, text_cols=0, label_cols=1, tokenizer=tokenizer,
                                                     label_delim=' ')
        config = ftext.awd_lstm_clas_config.copy()
        config['n_hid'] = 1150
        learn = ftext.text_classifier_learner(data_class, ftext.AWD_LSTM, config=config, drop_mult=0.5)
        learn.load_encoder(encoder_name)
        return learn

    def _train_classifier(self, learner):
        # comment to speed up
        # learner.freeze()

        # Train with best learning rate

        # learner.fit_one_cycle(2, 6e-01, moms=(0.8, 0.7))

        # Unfreeze some layers and train with lower learning rates

        # learner.freeze_to(-2)
        # learner.fit_one_cycle(3, slice(1e-2 / (2.6 ** 4), 1e-2), moms=(0.8, 0.7))

        # learner.freeze_to(-3)
        # learner.fit_one_cycle(2, slice(5e-3 / (2.6 ** 4), 5e-3), moms=(0.8, 0.7))

        learner.unfreeze()
        learner.fit_one_cycle(2, slice(1e-3 / (2.6 ** 4), 1e-3), moms=(0.8, 0.7))

    def _evaluate_model(self, df_test, learner):
        labels_results = {label: {"tp": 0, "fp": 0, "fn": 0} for label in labels}
        for row in df_test.iterrows():
            test_text = row[1]['Text']
            text_labels = [labels[int(label)] for label in row[1]['Label'].split(' ')]
            predicted_labels = self.predict(learner, test_text)
            for label in text_labels:
                if label in predicted_labels:
                    labels_results[label]["tp"] += 1
                else:
                    labels_results[label]["fn"] += 1

            for label in predicted_labels:
                if label not in text_labels:
                    labels_results[label]["fp"] += 1

        result = []
        for metric, stats in labels_results.items():
            result.append((metric,  stats['tp'] / (stats['tp'] + stats['fp'])))
        return result

    def predict(self, learner, text):
        # pytorch stores labels as strings, and they are sorted as strings as well: '0', '1', '10', '11'...
        # It means, that if model's result if 3, that actually means label '11'
        torch_labels = sorted([str(i) for i in range(20)])
        p = learner.predict(text)
        result = []
        for index, i in enumerate(p[1]):
            if int(i) == 1:
                true_label = int(torch_labels[index])
                result.append(labels[true_label])
        return result
