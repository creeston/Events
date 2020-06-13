import re
import urlextract


class TextPreprocessor:
    def __init__(self):
        self.url_extractor = urlextract.URLExtract()
        self.url_extractor.update()
        self.tag_regex = re.compile(r"<[^>]*>")
        self.email_regex = re.compile(r"[^\s]+@[^\s]+")
        self.number_regex = re.compile(r'\d+(?:\.\d*(?:[eE]\d+))?')
        self.spaces_regex = re.compile(r"\s+")
        self.special_chars = [
            "<", "[", "]", "`", "^", ">", "+", "?", "!", "'", ".", ",", ":",
            "*", "%", "#", "_", "=", "-", "&", '/', '\\', '(', ')', ";", "\"", "«", "»", "|", "•", "—", "–", "●", "►",
            "\n",
            "@", "$"
        ]

    def preprocess_text(self, text):
        text = text.lower()
        text = text.replace('\\xa', ' ')
        text = self.remove_html_tags(text)
        text = self.replace_urls(text)
        text = self.remove_emails(text)
        # text = self.replace_numbers(text)
        text = self.remove_special_characters(text)
        text = text.lower().replace("ё", "е")
        text = re.sub(' +', ' ', text)
        text = re.sub('[^a-zA-Zа-яА-Я1-9]+', ' ', text)
        return text.strip()

    def remove_html_tags(self, text):
        text = self.tag_regex.sub(" ", text).split(" ")
        text = filter(len, text)
        text = ' '.join(text)
        return text

    def replace_urls(self, text):
        urls = list(set(self.url_extractor.find_urls(text)))
        urls.sort(key=lambda u: len(u), reverse=True)
        for url in urls:
            text = text.replace(url, "")
        return text

    def remove_emails(self, text):
        return self.email_regex.sub("", text)

    def replace_numbers(self, text):
        return self.number_regex.sub(" number ", text)

    def remove_special_characters(self, text):
        for char in self.special_chars:
            text = text.replace(str(char), " ")
        return text
