import datetime
from difflib import SequenceMatcher


class DuplicateEventsRemover:
    def remove_duplicated_events(self, events):
        events_by_dates = self._group_by_dates(events)
        filtered_events = []
        for dt, grouped_events in events_by_dates.items():
            initial_len = len(grouped_events)
            if initial_len > 1:
                grouped_events = self._remove_duplicates(grouped_events)
            filtered_events.extend(grouped_events)
        return filtered_events

    @staticmethod
    def _get_place_name(event):
        if 'place' not in event:
            return None
        if 'name' not in event['place']:
            return None
        return event['place']['name']

    def _remove_duplicates(self, events):
        removed_idx = set()
        unique_events = []
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

            unique_event = max(duplicates, key=lambda e: len(e['title'] + e['description']))
            unique_events.append(unique_event)
        return unique_events

    @staticmethod
    def _similar(a, b):
        return SequenceMatcher(None, a, b).ratio()

    @staticmethod
    def _group_by_dates(events):
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
