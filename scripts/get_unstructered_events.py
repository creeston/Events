from scrappers import TelegramEventFetcher, VkEventFetcher
from markup import markup_event
from classifier import TypeClassifier
from interpreters import DateInterpreter, try_parse_date_string, time_re, time_range_re

import datetime
import json
import os
import sys


def fix_paranthesis(text):
    text = fix_paired_chars(text, '(', ')')
    return text


def fix_quotes(text):
    text= fix_paired_chars(text, "«", "»")
    count = len([c for c in text if c == '"'])
    if count % 2 == 0:
        return text
    text = text + '"'
    return text.replace('""', '')


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


def write_events_to_file(filename, events):
    first_read = False
    with open(filename, "w+", encoding="utf-8") as f:
        f.write("[\n")
        for event in events:
            if first_read:
                f.write(",\n")
            else:
                first_read = True
            f.write(json.dumps(event.to_json(), ensure_ascii=False, indent=4))
        f.write('\n]')


with open("C:\\Projects\\Research\\Events\\data\\event_data\\vk_tg_events.json", "r", encoding="utf-8") as f:
    events = [e for e in json.load(f)]


for e in events:
    markups = markup_event(e)
    if len(markups) == 0:
        continue
    print(e['text'])
    seen = set()
    for tag, start, end in markups:
        value = e['text'][start:end]
        value = fix_paranthesis(value)
        value = fix_quotes(value)
        value = value.strip()
        if tag == "TIME" or tag == "DATE":
            date_obj, date_string = try_parse_date_string(value)
            if date_string:
                rest_value = value.replace(date_string, "").strip()
                if len(rest_value) > 0 and try_parse_date_string(rest_value)[1] is None:
                    print("[FAC]: %s" % rest_value)
                elif len(rest_value) > 0:
                    print("[DATE]: %s" % rest_value)
                print("[TIME]: %s" % date_string)
                continue
        if value in seen:
            continue
        print("[%s]: %s" % (tag, value))
        seen.add(value)
    print()

sys.exit()


today = datetime.datetime.now()
folder_name = "C:\\Projects\\Research\\Events\\data\\event_data\\raw_data\\%s_%s_%s_%s" % (today.year, today.month, today.day, today.hour)
if not os.path.exists(folder_name):
    os.mkdir(folder_name)


classifier = TypeClassifier("C:\\Projects\\Research\\Events\\data\\model")

seen = set()
for event in VkEventFetcher().fetch_events():
    event_types = classifier.predict_type(event["text"])
    if len(event_types) == 0:
        continue

    markups = markup_event(event)
    if len(markups) == 0:
        continue

    if "DATE" not in [t for t, s, e in markups]:
        continue

    dates = []

    try:
        for t, s, e in [m for m in markups if m[0] == "DATE" or m[0] == "DATERANGE"]:
            value = event['text'][s:e].lower().replace('г. г.', "г.")
            match = try_parse_date_string(value)
            if not match:
                continue
            if "start" in match and match["start"]:
                if "month" not in match['start'] or not match['start']['month']:
                    match['start']['month'] = match['end']['month']
            dates.append(match)
    except Exception as e:
        print(event)
        print(e)
        continue

    if len(dates) == 0:
        continue

    print(event)
    print(event_types)
    for d in dates:
        print(d)

    seen = set()
    for tag, start, end in markups:
        if tag == "DATE" or tag == "DATERANGE":
            continue

        value = event['text'][start:end]
        if value not in seen:
            print("[%s]: %s" % (tag, event['text'][start:end]))
            seen.add(value)
    print()
