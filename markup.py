import json
import re
from scrappers import TelegramEventFetcher, VkEventFetcher
from pullenti_wrapper.langs import (set_langs, RU)
from pullenti_wrapper.processor import (Processor, DATE, ORGANIZATION, MONEY, ADDRESS)
from difflib import get_close_matches, SequenceMatcher
from itertools import groupby
from natasha import (AddressExtractor, OrganisationExtractor, DatesExtractor)
from deeppavlov import configs, build_model


punct_re = re.compile(r"[.,;!?]")


def load_json(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def find_all(a_str, sub):
    start = 0
    while True:
        start = a_str.find(sub, start)
        if start == -1:
            return
        yield start
        start += len(sub)


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


def get_n_grams(n, text):
    tokens = text.split(' ')
    for i in range(len(tokens) - n + 1):
        n_gram = " ".join(tokens[i:i + n])
        yield n_gram


def find_entity(text, entity, cutoff=0.8):
    place_grams = len(entity.split(' '))
    matches = []
    for n in range(1, place_grams * 2):
        grams = list(get_n_grams(n, text))
        for gram in grams:
            rate = similar(entity, gram)
            if rate > cutoff:
                matches.append((gram, rate))
    if not matches:
        return None
    match = max(matches, key=lambda p: p[1])[0]
    return match


def markup_by_list(entities, text, tag, cutoff=None):
    entities = [e.lower() for e in entities]
    lower_text = " " + punct_re.sub(" ", text.lower()) + " "
    result = []

    for entity in entities:
        start = lower_text.find(" %s " % entity)
        if start < 0:
            if not cutoff:
                continue
            match = find_entity(text, entity, cutoff)
            if not match:
                continue
            start = lower_text.find(" %s " % match)
            end = start + len(match)
        else:
            end = start + len(entity)
        result.append((tag, start, end))

    filtered_result = []
    for start, matches in groupby(result, key=lambda m: m[1]):
        matches = list(matches)
        if len(matches) == 1:
            filtered_result.append(matches[0])
        else:
            max_result = max(matches, key=lambda m: m[2] - m[1])
            filtered_result.append(max_result)

    result = []
    for end, matches in groupby(filtered_result, key=lambda m: m[2]):
        matches = list(matches)
        if len(matches) == 1:
            result.append(matches[0])
        else:
            max_result = max(matches, key=lambda m: m[2] - m[1])
            result.append(max_result)

    return result


class PlaceMarkup:
    def __init__(self):
        self.places = [t.lower() for t in load_json("C:\\Projects\\Research\\Events\\data\\keywords\\places.json")]

    def markup(self, text):
        return markup_by_list(self.places, text, "PLACE")


class TypeMarkup:
    def __init__(self):
        self.types = [t.lower() for t in load_json("data/keywords/event_types.json")]

    def markup(self, text):
        return markup_by_list(self.types, text, "EVENT", 0.75)


class TypeDetector:
    def __init__(self):
        self.types = [t.lower() for t in load_json("data/keywords/event_types.json")]

    def markup(self, text):
        entities = [e.lower() for e in self.types]
        lower_text = " " + punct_re.sub(" ", text.lower()) + " "
        result = []
        words = [w.strip() for w in lower_text.split(' ') if len(w.strip()) > 0]
        pair_words = []
        for i in range(len(words) - 1):
            pair_words.append("%s %s" % (words[i], words[i + 1]))

        for event_type in entities:
            start = lower_text.find(" %s " % event_type)
            if start < 0:
                matches = get_close_matches(event_type, pair_words, n=1, cutoff=0.75)
                if len(matches) == 0:
                    matches = get_close_matches(event_type, words, n=1, cutoff=0.8)
                    if len(matches) == 0:
                        continue

            result.append(event_type)

        return result


class MarkupCurrency:
    currency = [r"б\.?\s*р\.?", "byn", r"руб\.?", "рублей", r"р[^\w]"]
    free = ["свободный", "бесплатно", "free"]
    currency_re = re.compile(r"((\d+([.,]\d{2})?)\s*(" + "|".join(currency) + "))")

    def markup(self, text):
        result = []
        for match in self.currency_re.finditer(text):
            result.append(("MONEY", *match.span()))
        free_results = markup_by_list(self.free, text, "FREE", 0.8)
        result.extend([(t, s, e) for t, s, e in free_results])
        return result


class DeepPavlovMarkup:
    exclude_categories = ["WORK_OF_ART", "PERSON", "PRODUCT", "NORP", "LANGUAGE", "ORDINAL", "GPE",
                          "CARDINAL", "LAW", "QUANTITY"]

    def __init__(self):
        self.model = build_model(configs.ner.ner_ontonotes_bert_mult, download=True)

    def markup(self, text):
        try:
            result = self.model([text])
        except:
            return []
        tokens = result[0][0]
        tags = result[1][0]

        markups = []
        current_markup = []
        current_tag = None
        for token, tag in zip(tokens, tags):
            if tag == 'O':
                continue
            if tag[0] == 'B':
                if (current_tag == 'FAC' or current_tag == 'GPE') and tag[2:] in ['QUANTITY', 'CARDINAL', 'TIME']:
                    current_tag = 'FAC'
                    current_markup.append(token)
                    continue
                if len(current_markup) > 0:
                    markups.append((current_tag, list(current_markup)))
                    current_tag, current_markup = None, []
                current_markup.append(token)
                current_tag = tag[2:]
            if tag[0] == 'I':
                current_markup.append(token)
        if len(current_markup) > 0:
            markups.append((current_tag, list(current_markup)))

        markup_spans = []
        shift = 0
        for tag, tokens in markups:
            spans = []
            current_text = text[shift:]
            for token in tokens:
                start = current_text.index(token)
                end = start + len(token)
                if len(spans) > 0:
                    last_span = spans[-1]
                    start += last_span[1]
                    end += last_span[1]

                spans.append((start, end))
                current_text = text[shift:][end:]
            start = spans[0][0] + shift
            end = spans[-1][1] + shift
            shift = end
            markup_spans.append((tag, start, end))
        return [m for m in markup_spans if m[0] not in self.exclude_categories]


class PullEntityMarkup:
    def __init__(self):
        set_langs([RU])
        self.processor = Processor([ORGANIZATION, DATE, ADDRESS, MONEY])

    def markup(self, text):
        result = self.processor(text)
        spans = []
        already_found = {}
        for match in result.walk():
            start, stop = match.span
            label = match.referent.label
            if label in ["STREET", "PERSONPROPERTY"]:
                continue
            value = result.text[start:stop]
            if value in already_found:
                true_start = already_found[value][0]
                del already_found[value][0]
                if len(already_found) == 0:
                    del already_found[value]
            else:
                true_starts = list(find_all(text, value))
                if len(true_starts) == 1:
                    true_start = true_starts[0]
                elif len(true_starts) > 1:
                    true_start = true_starts[0]
                    del true_starts[0]
                    already_found[value] = true_starts
                else:
                    true_start = text.find(value)

            true_end = true_start + len(value)
            spans.append((label, true_start, true_end))
        return spans


class NatashaMarkup:
    def __init__(self):
        self.address = AddressExtractor()
        self.org = OrganisationExtractor()
        self.dates = DatesExtractor()

    def markup(self, text):
        result = []
        matches = self.address(text)
        for match in matches:
            start, end = match.span
            result.append(("ADDRESS", start, end))

        matches = self.org(text)
        for match in matches:
            start, end = match.span
            result.append(("ORGANIZATION", start, end))

        matches = self.dates(text)
        for match in matches:
            start, end = match.span
            result.append(("DATE", start, end))
        return result


async def get_events():
    vk_fetcher = VkEventFetcher()
    for event in vk_fetcher.fetch_events():
        yield event

    tg_fetcher = TelegramEventFetcher()
    async for event in tg_fetcher.fetch_events():
        yield event


def filter_tags(tags):
    tags_filtered = []
    while len(tags) > 0:
        max_tag = max(tags, key=lambda t: t[2] - t[1])
        tags_filtered.append(max_tag)
        tags = [t for t in tags if not (t[1] >= max_tag[1] and t[2] <= max_tag[2])]
    return tags_filtered


markups = [
    PlaceMarkup(),
    MarkupCurrency(),
    PullEntityMarkup(),
    NatashaMarkup(),
    DeepPavlovMarkup()
]


def markup_event(event):
    text = event["text"]
    result = []

    for markup in markups:
        result.extend(markup.markup(text))

    result = sorted(result, key=lambda p: p[1])
    return result

    other_tags = [tag for tag in result if tag[0] in ["FREE", "MONEY", "PERSON", "TITLE"]]
    date_tags = [tag for tag in result if "DATE" in tag[0]]#filter_tags([tag for tag in result if "DATE" in tag[0]])
    address_tags = [tag for tag in result if "ADDRESS" in tag[0]]#filter_tags([tag for tag in result if "ADDRESS" in tag[0]])
    org_tags = [tag for tag in result if "ORG" in tag[0]]#filter_tags([tag for tag in result if "ORG" in tag[0]])
    place_tags = [tag for tag in result if "PLACE" in tag[0]]


    result = []
    result.extend(place_tags)
    result.extend(org_tags)
    result.extend(address_tags)
    result.extend(date_tags)
    result.extend(other_tags)
    #result = sorted(filter_tags(result), key=lambda p: p[1])
    result = sorted(result, key=lambda p: p[1])
    return result


def get_span(text, match):
    start = text.find(match)
    end = start + len(match)
    return start, end


def markup_afisha_events():
    labels_file = open("labeled_afisha_text", "w+", encoding="utf-8")
    events = load_json("data/event_data/afisha_events.json")
    for event in events:
        text_labels = []
        text = event["description"]
        title = event["title"]

        # try to mark subject, knowing the title of the event
        title_match = find_entity(text, title, cutoff=0.8)
        if title_match:
            text_labels.append(("SUBJECT", *get_span(text, title_match)))
        else:
            # put title to the beginning of the text and mark it as SUBJECT
            text_labels.append(("SUBJECT", 0, len(title)))
            if title[-1] == ".":
                text = "%s %s" % (title, text)
            else:
                text = "%s. %s" % (title, text)

        # try to mark place, knowing the title of the event
        place = event["place"]["name"]
        place_match = find_entity(text, place, cutoff=0.5)
        if place_match:
            text_labels.append(("PLACE", *get_span(text, place_match)))
        else:
            # put place to the end of the text
            start = len(text) + 1
            text_labels.append(("PLACE", start, start + len(place)))
            text = "%s %s" % (text, place)

        for markup in markups:
            try:
                text_labels.extend(markup.markup(text))
            except Exception as e:
                print(e)
                continue

        other_tags = [tag for tag in text_labels if tag[0] in ["FREE", "MONEY", "PERSON", "SUBJECT", "EVENT"]]
        date_tags = filter_tags([tag for tag in text_labels if "DATE" in tag[0]])
        address_tags = filter_tags([tag for tag in text_labels if "ADDRESS" in tag[0]])
        org_tags = filter_tags([tag for tag in text_labels if "ORG" in tag[0]])
        place_tags = [tag for tag in text_labels if "PLACE" in tag[0]]

        text_labels = []
        text_labels.extend(place_tags)
        text_labels.extend(org_tags)
        text_labels.extend(address_tags)
        text_labels.extend(date_tags)
        text_labels.extend(other_tags)
        text_labels = sorted(filter_tags(text_labels), key=lambda p: p[1])

        if all([l[0] != "DATE" for l in text_labels]) == 0:
            # put own dates
            if "raw_dates" not in event:
                continue

            dates = event["raw_dates"]
            for date in dates:
                start = len(text) + 1
                text_labels.append(("DATE", start, start + len(date)))
                text = "%s %s" % (text, date)

        labeled_text = {"text": text, "labels": []}
        for label, start, end in text_labels:
            labeled_text["labels"].append([start, end, label])
            print("[%s]\t%s" % (label, text[start:end]))
        print()
        j = json.dumps(labeled_text, ensure_ascii=False)
        labels_file.write(j + "\n")


if __name__ == "__main__":
    markup_afisha_events()
