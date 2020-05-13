from difflib import SequenceMatcher
from models import Event, group_by_dates


class DuplicateEventsRemover:
    def remove_duplicated_events(self, events):
        events_by_dates = group_by_dates(events)
        filtered_events = []
        for dt, grouped_events in events_by_dates.items():
            initial_len = len(grouped_events)
            if initial_len > 1:
                duplicates_list = self.detect_duplicates(grouped_events)
                unique_events = []
                for duplicates in duplicates_list:
                    unique_event = max(duplicates, key=lambda e: len(e['title'] + e['description']))
                    unique_events.append(unique_event)
            else:
                unique_events = grouped_events

            filtered_events.extend(unique_events)
        return filtered_events

    @staticmethod
    def _get_place_name(event):
        if 'place' not in event:
            return None
        if 'name' not in event['place']:
            return None
        return event['place']['name']

    def detect_duplicates(self, events):
        removed_idx = set()
        duplicates_list = []
        for i, current_event in enumerate(events):
            if i in removed_idx:
                continue

            duplicates = [current_event]
            for j, event in enumerate(events[i + 1:]):
                j += (i + 1)
                if j in removed_idx:
                    continue
                res = self._similar(
                    current_event['title'] + " " + current_event['description'],
                    event['title'] + " " + event['description'])
                if res > 0.55:
                    duplicates.append(event)
                    removed_idx.add(j)
                elif self._get_place_name(current_event) == self._get_place_name(event):
                    res = self._similar(current_event['title'], event['title'])
                    if res > 0.7:
                        duplicates.append(event)
                        removed_idx.add(j)

            duplicates_list.append(duplicates)
        return duplicates_list

    @staticmethod
    def _similar(a, b):
        return SequenceMatcher(None, a, b).ratio()
