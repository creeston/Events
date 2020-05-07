from difflib import SequenceMatcher
import datetime


class DuplicateDetector:
    def remove_duplicated_events(self, events):
        events_by_dates = self._group_events_by_dates(events)
        unique_events = self._filter_events(events_by_dates)
        return unique_events

    @staticmethod
    def _group_events_by_dates(events):
        events_by_dates = {}
        for event in events:
            date = event['dates'][0]
            if 'start' in date:
                date = date['start']
            if date:
                if "hour" in date:
                    dt = datetime.datetime(year=date['year'], month=date['month'], day=date['day'], hour=date['hour'],
                                           minute=date['minute'])
                else:
                    dt = datetime.date(year=date['year'], month=date['month'], day=date['day'])
            else:
                dt = datetime.date(year=datetime.MINYEAR, month=1, day=1)

            if dt not in events_by_dates:
                events_by_dates[dt] = []
            events_by_dates[dt].append(event)
        return events_by_dates

    @staticmethod
    def _filter_events(events_by_dates):
        filtered_events = []
        for dt, grouped_events in events_by_dates.items():
            initial_len = len(grouped_events)
            if initial_len > 1:
                grouped_events = DuplicateDetector._remove_duplicated(grouped_events)
            filtered_events.extend(grouped_events)
        return filtered_events

    @staticmethod
    def _remove_duplicated(evs):
        removed_idx = set()
        unique_events = []
        for i, current_event in enumerate(evs):
            if i in removed_idx:
                continue

            duplicates = [current_event]
            for j, event in enumerate(evs[i + 1:]):
                if j in removed_idx:
                    continue
                res = DuplicateDetector._similar(current_event['description'], event['description'])
                if res > 0.6:
                    duplicates.append(event)
                    removed_idx.add(j)

            unique_event = max(duplicates, key=lambda e: len(e['description']))
            unique_events.append(unique_event)

        return unique_events

    def _remove_duplicated_texts(self, evs):
        removed_idx = set()
        unique_events = []
        for i, current_text in enumerate(evs):
            if i in removed_idx:
                continue

            duplicates = [current_text]
            for j, text in enumerate(evs[i + 1:]):
                if j in removed_idx:
                    continue
                res = self._similar(current_text, text)
                if res > 0.6:
                    duplicates.append(text)
                    removed_idx.add(j)

            unique_event = max(duplicates, key=lambda e: len(e))
            unique_events.append(unique_event)

    @staticmethod
    def _similar(a, b):
        return SequenceMatcher(None, a, b).ratio()
