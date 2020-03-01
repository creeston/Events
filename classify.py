import json
from nltk.stem import PorterStemmer
import urlextract
from nltk.corpus import stopwords
import re
from collections import Counter
import numpy as np
import pickle
from sklearn import svm


def load_json(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


class TextPreprocessor:
    def __init__(self):
        self.stemmer = PorterStemmer()
        self.url_extractor = urlextract.URLExtract()
        self.tag_regex = re.compile(r"<[^>]*>")
        self.email_regex = re.compile(r"[^\s]+@[^\s]+")
        self.number_regex = re.compile(r'\d+(?:\.\d*(?:[eE]\d+))?')
        self.dollar_regex = re.compile(r"[$]+")
        self.spaces_regex = re.compile(r"\s+")
        self.special_chars = [
            "<", "[", "^", ">", "+", "?", "!", "'", ".", ",", ":",
            "*", "%", "#", "_", "=", "-", "&", '/', '\\', '(', ')', ";", "\"", "«", "»", "|", "•", "—", "–", "●", "►",
        ]
        self.stop_words = set(stopwords.words('russian'))
        self.mapping = {}
        self.places = load_json("data\\places.json")
        self.emoji_regex = re.compile(
            "["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "]+", flags=re.UNICODE)

    def preprocess_text(self, text):
        text = text.lower()
        text = self.remove_html_tags(text)
        text = self.replace_urls(text)
        text = self.replace_emails(text)
        text = self.replace_numbers(text)
        text = self.replace_places(text)
        text = self.replace_dollar_signs(text)
        text = self.remove_special_characters(text)
        text = self.remove_characters_not_in_range(text)
        text = self.stem_words(text)
        text = self.remove_stop_words(text)
        text = self.spaces_regex.sub(' ', text)
        return text.strip()

    @staticmethod
    def remove_characters_not_in_range(text):
        return "".join([c for c in text if ord(c) in range(65536)])

    def remove_html_tags(self, text):
        text = self.tag_regex.sub(" ", text).split(" ")
        text = filter(len, text)
        text = ' '.join(text)
        return text

    def replace_urls(self, text):
        urls = list(set(self.url_extractor.find_urls(text)))
        urls.sort(key=lambda u: len(u), reverse=True)
        for url in urls:
            text = text.replace(url, " httpaddr ")
        return text

    def replace_emails(self, text):
        return self.email_regex.sub(" emailaddr ", text)

    def replace_places(self, text):
        for place in self.places:
            text = text.replace(" %s " % place, " place ")
        return text

    def replace_numbers(self, text):
        return self.number_regex.sub(" number ", text)

    def replace_dollar_signs(self, text):
        return self.dollar_regex.sub(" dollar ", text)

    def remove_special_characters(self, text):
        for char in self.special_chars:
            text = text.replace(str(char), " ")
        return self.emoji_regex.sub(" ", text)

    def remove_stop_words(self, text):
        for word in self.stop_words:
            text = text.replace(" %s " % word, " ")
        return text

    def stem_words(self, text):
        text = [self.stemmer.stem(token) for token in text.split(" ")]
        text = " ".join(text)
        return text

    def load_vocab(self, vocab_path):
        with open(vocab_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                index, word = line.split('\t')
                self.mapping[word] = int(index)

    def create_vocab(self, vocab_path, texts):
        vocab = []
        for text in texts:
            text = self.preprocess_text(text)
            words = text.split(' ')
            word_counts = Counter(words)
            vocab.append(word_counts)

        vocab = sum(vocab, Counter())
        most_common = vocab.most_common(2000)
        vocab = []
        for (k, v) in most_common:
            vocab.append(k)

        vocab = [(index + 1, word) for index, word in enumerate(sorted(vocab))]
        with open(vocab_path, 'w+', encoding="utf-8") as f:
            for index, word in vocab:
                f.write("%s\t%s\n" % (index, word))
                self.mapping[word] = index

    def convert_text_to_feature_vector(self, text):
        text = self.preprocess_text(text)
        words = text.split(' ')
        feature_vector = np.zeros(len(self.mapping))
        for word in words:
            if word in self.mapping:
                feature_vector[self.mapping[word] - 1] = 1
        return feature_vector


class EventTagClassifier:
    def __init__(self, preprocessor):
        self.preprocessor = preprocessor
        self.classifiers = []
        self.tag_data = []
        self.tag_mapping = {}

    def detect_tags(self, text):
        text = self.preprocessor.preprocess_text(text)
        vector = self.preprocessor.convert_text_to_feature_vector(text)
        result = []
        for i, clf in enumerate(self.classifiers):
            prediction = clf.predict([vector])
            if prediction[0] == 1:
                result.append(self.tag_data[i])
        return result

    def train(self, train_set_path):
        tags = load_json(train_set_path)
        self._create_tag_mapping(tags)
        x, y = self._create_train_data(tags)
        self.classifiers = []
        for tag, tag_id in self.tag_mapping.items():
            y_train = []
            for v in y:
                y_train.append(v[tag_id])
            y_train = np.array(y_train)
            clf = svm.SVC(kernel='linear')
            clf.fit(x, y_train)
            self.classifiers.append(clf)

    def save_model(self, path):
        pickle.dump(self, open(path, 'wb'))

    def load_model(self, path):
        model = pickle.load(open(path, 'rb'))
        self.classifiers = model.classifiers
        self.tag_data = model.tag_data
        self.tag_mapping = model.tag_mapping

    def _create_train_data(self, train_data):
        x, y = [], []
        for text, tag in train_data:
            feature_vector = self.preprocessor.convert_text_to_feature_vector(text)
            tag_vector = self.convert_tags_to_vector(tag)
            x.append(feature_vector)
            y.append(tag_vector)
        return np.array(x), np.array(y)

    def _create_tag_mapping(self, tags):
        self.tag_data = [t[1] for t in tags]
        self.tag_data = sorted(list(set([t.lower() for tt in self.tag_data for t in tt])))
        self.tag_mapping = {}
        for i, t in enumerate(self.tag_data):
            self.tag_mapping[t] = i

    def convert_tags_to_vector(self, tag_list):
        v = np.zeros(len(self.tag_mapping))
        for t in tag_list:
            t = t.lower()
            v[self.tag_mapping[t]] = 1
        return v


class EventNotEventClassifier:
    def __init__(self, preprocessor):
        self.preprocessor = preprocessor
        self.clf = None

    def is_event(self, event_text):
        vector = self.preprocessor.convert_text_to_feature_vector(event_text)
        prediction = self.clf.predict([vector])
        return prediction[0] == 1

    def train(self):
        events = list(set(open('data/events', encoding="utf-8").readlines()))
        not_events = list(set(open('data/not_events', encoding="utf-8").readlines()))
        event_vectors = [self.preprocessor.convert_text_to_feature_vector(event) for event in events]
        not_event_vectors = [self.preprocessor.convert_text_to_feature_vector(not_event) for not_event in not_events]

        y_train_events = np.zeros(len(event_vectors))
        y_train_events.fill(1)
        y_train_not_events = np.zeros(len(not_event_vectors))

        x_train = np.concatenate((event_vectors, not_event_vectors))
        y_train = np.concatenate((y_train_events, y_train_not_events))

        # parameters = {'kernel': ('linear', 'rbf'), 'C': [0.1, 0.5, 1, 1.5]}
        # svc = svm.SVC()
        # clf = GridSearchCV(svc, parameters)
        self.clf = svm.SVC(kernel='rbf', C=1.5, gamma='scale')
        self.clf.fit(x_train, y_train)

    def save_model(self, path):
        pickle.dump(self.clf, open(path, 'wb'))

    def load_model(self, path):
        self.clf = pickle.load(open(path, 'rb'))
