import json


if __name__ == "__main__":
    from markup import NamedEntityExtractor

    extractor = NamedEntityExtractor()
    with open("C:\\Projects\\Research\\Events\\data\\event_data\\vk_tg_events.json", "r", encoding="utf-8") as f:
        events = [e for e in json.load(f)]

    for e in events:
        data = extractor.extract_entities_from_event(e['text'])
        if not data:
            continue
        print(e['text'])
        for k, v in data.items():
            print("[%s]: %s" % (k, v))
        print()


#
#     from scrappers import TelegramEventFetcher, VkEventFetcher
#     from markup import markup_event
#     from classifier import TypeClassifier
#     from interpreters import DateInterpreter, try_parse_date_string, time_re, time_range_re
#
#     import datetime
#     import json
#     import os
#     import sys
#

#

#
#     sys.exit()
#
#
#     today = datetime.datetime.now()
#     folder_name = "C:\\Projects\\Research\\Events\\data\\event_data\\raw_data\\%s_%s_%s_%s" % (today.year, today.month, today.day, today.hour)
#     if not os.path.exists(folder_name):
#         os.mkdir(folder_name)
#
#
#     classifier = TypeClassifier("C:\\Projects\\Research\\Events\\data\\model")
#
#     seen = set()
#     for event in VkEventFetcher().fetch_events():
#         event_types = classifier.predict_type(event["text"])
#         if len(event_types) == 0:
#             continue
#
#         markups = markup_event(event)
#         if len(markups) == 0:
#             continue
#
#         if "DATE" not in [t for t, s, e in markups]:
#             continue
#
#         dates = []
#
#         try:
#             for t, s, e in [m for m in markups if m[0] == "DATE" or m[0] == "DATERANGE"]:
#                 value = event['text'][s:e].lower().replace('г. г.', "г.")
#                 match = try_parse_date_string(value)
#                 if not match:
#                     continue
#                 if "start" in match and match["start"]:
#                     if "month" not in match['start'] or not match['start']['month']:
#                         match['start']['month'] = match['end']['month']
#                 dates.append(match)
#         except Exception as e:
#             print(event)
#             print(e)
#             continue
#
#         if len(dates) == 0:
#             continue
#
#         print(event)
#         print(event_types)
#         for d in dates:
#             print(d)
#
#         seen = set()
#         for tag, start, end in markups:
#             if tag == "DATE" or tag == "DATERANGE":
#                 continue
#
#             value = event['text'][start:end]
#             if value not in seen:
#                 print("[%s]: %s" % (tag, event['text'][start:end]))
#                 seen.add(value)
#         print()
