import json
import re
from typing import List, Optional

import regex
import copy
import datetime

from pullenti_wrapper.langs import (set_langs, RU)
from pullenti_wrapper.processor import (Processor, DATE, ORGANIZATION, MONEY, ADDRESS)
from difflib import get_close_matches, SequenceMatcher
from itertools import groupby
from natasha import (AddressExtractor, OrganisationExtractor, DatesExtractor)
from deeppavlov import configs, build_model
from interpreters import try_parse_date_string, hyphens
from duplicate_detector import DuplicateEventsRemover
from models import Event, Place, datetime_from_json, EventDateRange


punct_re = re.compile(r"[.,;!?]")
current_year = datetime.datetime.now().year


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
        start_index = lower_text.find(" %s " % entity)
        if start_index < 0:
            start_index = max(lower_text.find(" \"%s\" " % entity),
                              lower_text.find(" “%s” " % entity),
                              lower_text.find(" «%s» " % entity),
                              lower_text.find(" (%s) " % entity))
            if start_index >= 0:
                start_index += 1
        if start_index < 0:
            if not cutoff:
                continue
            match = find_entity(text, entity, cutoff)
            if not match:
                continue
            start_index = lower_text.find(" %s " % match)
            end = start_index + len(match)
        else:
            end = start_index + len(entity)
        result.append((tag, start_index, end))

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
        self.address_place_dict = load_json("C:\\Projects\\Research\\Events\\data\\keywords\\places.json")
        places = [places for address, places in self.address_place_dict.items()]
        self.places = list(set([p for sublist in places for p in sublist]))

    def markup(self, text: str):
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


class MarkupRegister:
    register = ["необходима регистрация", "регистрация", "с регистрацией", "по регистрации"]

    def markup(self, text):
        return markup_by_list(self.register, text, "REGISTER", 0.9)


class MarkupCurrency:
    currency = [r"б\.?\s*р\.?", "byn", r"руб\.?", "рублей", r"р[^\w]"]
    free = ["свободный", "бесплатно", "free"]
    currency_value = r"(\d+)([.,](\d{2}))?"
    currency_regex = currency_value + r"(\s*(" + "|".join(currency) + "))"
    currency_re = re.compile(currency_regex)
    currency_range_re = re.compile(currency_value + r"\s*" + hyphens + r"\s*" + currency_regex)

    def markup(self, text):
        result = []
        for match in self.currency_range_re.finditer(text):
            result.append(("MONEY", *match.span()))
        for match in self.currency_re.finditer(text):
            start, end = match.span()
            if len([s for t, s, e in result if s <= start <= e]) > 0:
                continue
            result.append(("MONEY", *match.span()))
        free_results = markup_by_list(self.free, text, "FREE", 0.8)
        result.extend([(t, s, e) for t, s, e in free_results])
        return result

    @staticmethod
    def get_currency(groups):
        value = 0
        whole_part = groups[0]
        fract_part = groups[2]
        if whole_part:
            value += int(whole_part)
        if fract_part:
            value += int(fract_part) / 100
        return value

    def parse_currency(self, currency_string) -> Optional[List[int]]:
        match = self.currency_re.fullmatch(currency_string)
        if match:
            return [self.get_currency(match.groups())]
        match = self.currency_range_re.fullmatch(currency_string)
        if match:
            groups = match.groups()
            return [self.get_currency(groups[:3]), self.get_currency(groups[3:])]
        return None


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


class NamedEntityExtractor:
    def __init__(self):
        self.markupers = [
            PlaceMarkup(),
            MarkupCurrency(),
            PullEntityMarkup(),
            NatashaMarkup(),
            DeepPavlovMarkup(),
            MarkupRegister()
        ]
        self.structured_data_extractor = DataExtractor()

    def extract_entities_from_event(self, event_text: str, timestamp: datetime.datetime) -> Optional[Event]:
        markups = list(self.get_event_markup(event_text))
        if len(markups) == 0:
            return None

        event = self.structured_data_extractor.get_structured_data_from_markups(markups, event_text, timestamp)
        return event

    def get_event_markup(self, e: str):
        markups = self.markup_event_text(e)
        if len(markups) == 0:
            return
        for tag, start, end in markups:
            value = e[start:end]
            value = self._fix_paranthesis(value)
            value = self._fix_quotes(value)
            value = value.strip()
            if tag == "TIME" or tag == "DATE":
                date_obj, date_string = try_parse_date_string(value)
                if date_string:
                    rest_value = value.replace(date_string, "").strip()
                    if len(rest_value) > 0 and try_parse_date_string(rest_value)[1] is None:
                        yield "FAC", rest_value
                    elif len(rest_value) > 0:
                        yield "DATE", rest_value
                    yield "TIME", date_string
                    continue
            yield tag, value

    def markup_event_text(self, text: str):
        result = []

        for markup in self.markupers:
            result.extend(markup.markup(text))

        result = sorted(result, key=lambda p: p[1])
        return result

    def _fix_paranthesis(self, text):
        text = self.fix_paired_chars(text, '(', ')')
        return text

    def _fix_quotes(self, text):
        text = self.fix_paired_chars(text, "«", "»")
        count = len([c for c in text if c == '"'])
        if count % 2 == 0:
            return text
        text = text + '"'
        return text.replace('""', '')

    @staticmethod
    def fix_paired_chars(text, open_char, close_char):
        open_count = len([c for c in text if c == open_char])
        close_count = len([c for c in text if c == close_char])
        if open_count == close_count:
            return text

        if open_count - close_count == 1:
            text = text + close_char
        if close_count - open_count == 1:
            text = text.replace(close_char, "").replace(open_char, "")
        return text.replace(open_char + close_char, "")


class DataExtractor:
    open_quote_chars = ['"', "“", "«"]
    close_quote_chars = ['"', '»', '”']
    quote_chars = list(set(open_quote_chars + close_quote_chars))
    quotated_text_re = regex.compile(r'([' +
                                     "".join(open_quote_chars) + r']([^' +
                                     "".join(close_quote_chars) + r']*)[' +
                                     "".join(close_quote_chars) + r'])')
    open_bracket_chars = ['(', '[']
    close_bracket_chars = [')', ']']

    def __init__(self):
        self.duplicate_detector = DuplicateEventsRemover()
        self.currency_markup = MarkupCurrency()

    def get_structured_data_from_markups(self, text_markup: List, text: str, timestamp: datetime.datetime):
        if timestamp:
            default_year = timestamp.year
        else:
            default_year = current_year

        dates, raw_dates = self.get_dates(text_markup)
        address, places = self.get_place(text_markup)
        if address:
            address = self._remove_trailing_comma(address)
        if places:
            places = [self._remove_trailing_comma(p) for p in places]
            places = [re.split(r"[!]", p) for p in places]
            places = [p.strip() for sublist in places for p in sublist if len(p.strip()) > 2]
            places = [p for p in places if not try_parse_date_string(p)[0]
                      and "минут" not in p
                      and "час" not in p
                      and "начал" not in p]
            places = self.duplicate_detector.remove_duplicate_strings(places)

        place = Place(name=",".join(places), address=address)
        title = self.get_title(text)
        cost, is_free, is_register = self.get_metadata(text_markup)
        if len(cost) > 0:
            for c in [v for tag, v in text_markup if tag == "MONEY"]:
                for i in range(len(places)):
                    places[i] = places[i].replace(c, "")

        event_dates = []
        for date in dates:
            if "start_time" in date and 'day' in date:
                if 'year' not in date or not date['year']:
                    date['year'] = default_year
                start_date = copy.deepcopy(date)
                del start_date['start_time']
                start_date['hour'] = date['start_time']['hour']
                start_date['minute'] = date['start_time']['minute']
                end_date = None
                if 'end_time' in date:
                    end_date = copy.deepcopy(date)
                    del start_date['end_time']
                    del end_date['end_time']
                    del end_date['start_time']
                    end_date['hour'] = date['end_time']['hour']
                    end_date['minute'] = date['end_time']['minute']
                    end_date = datetime_from_json(end_date)

                start_date = datetime_from_json(start_date)
                event_dates.append(EventDateRange(start_day=start_date, end_day=end_date))
            if "day" in date:
                if 'year' not in date or not date['year']:
                    date['year'] = default_year
                date = datetime_from_json(date)
                if not date:
                    continue
            elif "start" in date:
                start, end = None, None
                if date['start']:
                    if 'year' not in date['start'] or not date['start']['year']:
                        date['start']['year'] = default_year
                    start = datetime_from_json(date['start'])
                if date['end']:
                    if 'year' not in date['end'] or not date['end']['year']:
                        date['end']['year'] = default_year
                    end = datetime_from_json(date['end'])
                event_dates.append(EventDateRange(start_day=start, end_day=end))

        tags = []
        if is_free:
            tags.append("free")
        if is_register:
            tags.append("register")

        return Event(title, text, place, event_dates, "", cost=cost, raw_dates=raw_dates, event_tags=tags)

    def get_dates(self, markups):
        dates = []
        raw_dates = []
        for t, value in [m for m in markups if m[0] in ["DATE", "DATERANGE", "TIME"]]:
            value = value.lower().replace('г. г.', "г.")
            match, value = try_parse_date_string(value)
            if not match:
                continue

            dates.append(match)
            raw_dates.append(value)

        unique_dates = []
        self.get_unique_dates(dates, unique_dates)
        raw_dates = list(set(raw_dates))
        return unique_dates, raw_dates

    def get_unique_dates(self, dates, unique_list):
        ranges = [d for d in dates if "start" in d]
        for date_range in ranges:
            start, end = date_range['start'], date_range['end']
            if start:
                existing = [d for d in unique_list if d['start'] == start]
                if len(existing) == 0:
                    unique_list.append(date_range)
            elif end:
                existing = [d for d in unique_list if d['end'] == end]
                if len(existing) == 0:
                    unique_list.append(date_range)

        dates = [d for d in dates if "start" not in d]
        time_without_date = None
        date_without_time = None
        for date in dates:
            if type(date) == list:
                self.get_unique_dates(date, unique_list)
            elif "day" in date:
                existing = [d for d in unique_list if "day" in d
                            and d["day"] == date['day']
                            and d['month'] == date['month']]
                if len(existing) == 0:
                    ranges = [[d["start"], d["end"]] for d in unique_list if "start" in d]
                    ranges = [d for sublist in ranges for d in sublist if d]
                    existing = [d for d in ranges if
                                "day" in d and d["day"] == date['day'] and d['month'] == date['month']]

                if len(existing) == 0:
                    unique_list.append(date)
                    if "hour" not in date:
                        if time_without_date:
                            if "hour" in time_without_date:
                                date["hour"] = time_without_date["hour"]
                                date["minute"] = time_without_date["minute"]
                            else:
                                date["start_time"] = time_without_date["start_time"]
                                date["end_time"] = time_without_date["end_time"]
                            time_without_date = None
                        else:
                            date_without_time = date
                elif "hour" in date:
                    existing[0]['hour'] = date['hour']
                    existing[0]['minute'] = date['minute']
            elif "hour" in date:
                if date_without_time:
                    date_without_time["hour"] = date["hour"]
                    date_without_time["minute"] = date["minute"]
                    date_without_time = None
                else:
                    time_without_date = date
            elif "start_time" in date:
                if date_without_time:
                    date_without_time["start_time"] = date["start_time"]
                    date_without_time["end_time"] = date["end_time"]
                    date_without_time = None
                else:
                    time_without_date = date

    def get_best_address(self, candidates):
        common_string = candidates[0]
        for i in range(len(candidates) - 1):
            common_string = self._get_common_substring(common_string, candidates[i + 1])
        candidates = [c for c in candidates if c.startswith(common_string)]
        if len(candidates) == 0:
            return None
        return max(candidates, key=lambda l: len(l))

    def get_place(self, markups):
        fac_max_len = 80
        address = None
        place_candidates = []
        address_tags = list(set([v for t, v in markups if t == "ADDRESS"]))
        fac_tags = list(set([v for t, v in markups if t == "FAC" and len(v) <= fac_max_len]))
        place_tags = list(set(v for t, v in markups if t == "PLACE"))

        if len(address_tags) == 1:
            address = address_tags[0]
        elif len(address_tags) > 1:
            address = self.get_best_address(address_tags)
        elif len(address_tags) == 0:
            address_candidates = [candidate for candidate in fac_tags if any(c.isdigit() for c in candidate)]
            if len(address_candidates) > 0:
                address = address_candidates[0]

        if len(place_tags) > 0:
            return address, place_tags

        # try to extract place from "fac" tags
        if not address:
            return None, []

        for value in fac_tags:
            common_part = self._get_common_substring(value, address)
            if common_part != address:
                if len(value) >= 5 and len(common_part) < 3:
                    place_candidates.append(value)
            else:
                rest = value.replace(common_part, "").replace("()", "").strip()
                rest = self._remove_trailing_comma(rest)
                if len(rest) > 2 and value.startswith(rest):
                    place_candidates.append(rest)

        return address, place_candidates

    def get_title(self, text):
        tokens = text.split(" ")
        possible_title = []

        trailing_bracket_token_id = None
        for token_id, token in enumerate(tokens):
            for char in token:
                if char in self.open_bracket_chars:
                    trailing_bracket_token_id = token_id
                if char in self.close_bracket_chars:
                    trailing_bracket_token_id = None
            possible_title.append(token)
            if sum([len(t) for t in possible_title]) > 80:
                break
        if trailing_bracket_token_id:
            possible_title = possible_title[:trailing_bracket_token_id]
        possible_title = " ".join(possible_title)

        candidates = self.quotated_text_re.findall(possible_title)
        if len(candidates) > 0:
            quoted_text = candidates[-1][0]
            index_of_quoted = possible_title.index(quoted_text)
            return possible_title[:(index_of_quoted + len(quoted_text))] + "."

        sentences = possible_title.split("!")
        if len(sentences) > 1:
            return sentences[0] + "!"

        sentences = possible_title.split("?")
        if len(sentences) > 1:
            return sentences[0] + "?"

        sentences = regex.split(r"([\p{Ll}\d]\.)\s*(\p{Lu})", possible_title)
        if len(sentences) > 1:
            combined_sentences = []
            i = 0
            while i < len(sentences):
                if i == 0:
                    combined_sentences.append(sentences[0] + sentences[1])
                    i += 2
                elif i == len(sentences) - 2:
                    combined_sentences.append(sentences[i] + sentences[i + 1])
                    break
                else:
                    combined_sentences.append(sentences[i] + sentences[i + 1] + sentences[i + 2])
                    i += 3

            return "".join(combined_sentences[:-1]) + ".."

        return possible_title + "..."

    def get_metadata(self, markups):
        is_free = len([m for m in markups if m[0] == "FREE"]) > 0
        is_register = len([m for m in markups if m[0] == "REGISTER"]) > 0
        cost = [self.currency_markup.parse_currency(v) for tag, v in markups if tag == "MONEY"]
        cost = [c for c in cost if c and len(c) > 0]
        cost = [c for sublist in cost for c in sublist if sublist]
        return sorted(list(set(cost))), is_free, is_register

    @staticmethod
    def _get_common_substring(s1, s2):
        match = SequenceMatcher(None, s1, s2).find_longest_match(0, len(s1), 0, len(s2))
        return s1[match.a: match.a + match.size]

    @staticmethod
    def _remove_trailing_comma(string):
        string = string.strip()
        chars = [',', '!', '.', ':', ';', '?', '-']
        while len(string) > 0 and string[-1] in chars:
            string = string[:-1]
        while len(string) > 0 and string[0] in chars:
            string = string[1:]
        return string
