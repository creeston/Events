import vk_api
import re
from nltk.stem import PorterStemmer
import urlextract


class TextPreprocessor:
    def __init__(self):
        self.stemmer = PorterStemmer()
        self.url_extractor = urlextract.URLExtract()
        self.tag_regex = re.compile(r"<[^>]*>")
        self.email_regex = re.compile(r"[^\s]+@[^\s]+")
        self.number_regex = re.compile(r'\d+(?:\.\d*(?:[eE]\d+))?')
        self.dollar_regex = re.compile(r"[$]+")
        self.spaces_regex = re.compile(r"\s+")
        self.link_regex = re.compile(r"(\[(club|id)\d+\|([^\]]+)\])")
        self.hashtag_regex = re.compile(r"#[^\s]+")
        self.special_chars = [
            "❤", "❓", "@", "✅", "🤘", "•", "🤔", "❄", "⏰"
        ]
        self.emoji_regex = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                           "]+", flags=re.UNICODE)


    def preprocess_text(self, text):
        text = text.lower()
        text = self.remove_emoji(text)
        text = self.remove_special_characters(text)
        text = self.remove_group_links(text)
        text = self.remove_html_tags(text)
        text = self.replace_urls(text)
        text = self.replace_emails(text)
        text = self.replace_numbers(text)
        text = self.replace_tags(text)
        text = self.spaces_regex.sub(' ', text)
        return text.strip()

    def replace_tags(self, text):
        return self.hashtag_regex.sub(" hashtag ", text)

    def remove_html_tags(self, text):
        text = self.tag_regex.sub(" ", text).split(" ")
        text = filter(len, text)
        text = ' '.join(text)
        return text

    def remove_emoji(self, text):
        return self.emoji_regex.sub(r'', text)

    def replace_urls(self, text):
        urls = list(set(self.url_extractor.find_urls(text)))
        urls.sort(key=lambda u: len(u), reverse=True)
        for url in urls:
            text = text.replace(url, " httpaddr ")
        return text

    def replace_emails(self, text):
        return self.email_regex.sub(" emailaddr ", text)

    def replace_numbers(self, text):
        return self.number_regex.sub(" number ", text)

    def replace_dollar_signs(self, text):
        return self.dollar_regex.sub(" dollar ", text)

    def remove_group_links(self, text: str):
        matches = self.link_regex.findall(text)
        if not matches:
            return text
        for match in matches:
            text = text.replace(match[0], match[2])
        return text

    def remove_special_characters(self, text):
        for char in self.special_chars:
            text = text.replace(str(char), "")
        text = text.replace("\n", " ")
        return text

    def stem_words(self, text):
        text = [self.stemmer.stem(token) for token in text.split(" ")]
        text = " ".join(text)
        return text


def download_data():
    vk_session = vk_api.VkApi('+375445822205', '680029ABCr4.')
    vk_session.auth()
    api = vk_session.get_api()
    groups = [57422635, 47596848, 8788887, 27385815, 23439904]
    preprocessor = TextPreprocessor()
    with open("data/raw", "w+", encoding="utf-8") as f:
        for group_id in groups:
            for offset in range(10):
                response = api.wall.get(owner_id=-group_id, count=100, filter='owner', offset=offset * 100)
                posts = response['items']
                for post in posts:
                    text = post['text']
                    text = preprocessor.preprocess_text(text)
                    if not text or len(text.split(' ')) < 8:
                        continue
                    f.write("%s\n" % text)
            print("group %s was processed" % group_id)


lines = list(set(open('data/raw', encoding="utf-8").readlines()))

events = []
not_events = []
for line in lines[::-1]:
    print(line)
    response = input("event: ")
    if response == "1":
        events.append(line)
    elif response == "2":
        break
    else:
        not_events.append(line)
    del lines[-1]

open('data/raw', 'w', encoding="utf-8").writelines(lines)
open("events", "a", encoding="utf-8").writelines(events)
open("data/not_events", "a", encoding="utf-8").writelines(not_events)
