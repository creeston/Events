from difflib import SequenceMatcher
from typing import List
from models import group_by_dates, Event


class DuplicateEventsRemover:
    def remove_duplicated_events(self, events: List[Event]):
        duplicate_groups = []
        events_by_dates = group_by_dates(events)
        filtered_events = []
        for dt, grouped_events in events_by_dates.items():
            initial_len = len(grouped_events)
            if initial_len > 1:
                duplicates_list = self.detect_duplicates(grouped_events)
                unique_events = []
                for duplicates in duplicates_list:
                    if len(duplicates) > 1:
                        duplicate_groups.append(duplicates)
                    unique_event = max(duplicates, key=lambda e: len(e.to_str()))
                    unique_events.append(unique_event)
            else:
                unique_events = grouped_events

            filtered_events.extend(unique_events)
        return filtered_events, duplicate_groups

    def remove_duplicate_strings(self, strings):
        if len(strings) < 2:
            return strings

        removed_idx = set()
        duplicates_list = []
        for i, current_string in enumerate(strings):
            if i in removed_idx:
                continue

            duplicates = [current_string]
            for j, string in enumerate(strings[i + 1:]):
                j += (i + 1)
                if j in removed_idx:
                    continue

                res = self._similar(current_string, string)
                if res > 0.6:
                    duplicates.append(string)
                    removed_idx.add(j)

            duplicates_list.append(duplicates)
        return [max(duplicates, key=lambda d: len(d)) for duplicates in duplicates_list]

    @staticmethod
    def _get_place_name(event: Event):
        if not event.place:
            return None
        return event.place.name

    def detect_duplicates(self, events: List[Event]) -> List[List[Event]]:
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
                current_text, event_text = current_event.to_str(), event.to_str()
                if len(current_text) == 0 or len(event_text) == 0:
                    continue

                res = self._similar(current_text, event_text)
                if res > 0.55:
                    duplicates.append(event)
                    removed_idx.add(j)
                elif self._get_place_name(current_event) == self._get_place_name(event) and \
                        current_event.title and event.title:
                    res = self._similar(current_event.title, event.title)
                    if res > 0.7:
                        duplicates.append(event)
                        removed_idx.add(j)

            duplicates_list.append(duplicates)
        return duplicates_list

    @staticmethod
    def _similar(a, b):
        return SequenceMatcher(None, a, b).ratio()
