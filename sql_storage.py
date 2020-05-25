import datetime
import pyodbc

from typing import List
from configuration import sql_server
from models import Event, EventDateRange, Place


class EventRepository:
    events_by_date_table = "eventsByDate"
    event_duplicates_table = "eventDuplicates"

    sql_insert_event = "EXECUTE [CreateEvent] ?, ?, ?, ?, ?, ?, ?"
    sql_set_date = 'EXECUTE [dbo].SetEventDate ?, ?'
    sql_set_date_range = 'EXECUTE [dbo].SetEventDateRange ?, ?, ?'
    sql_set_type = "EXECUTE [dbo].SetEventType ?, ?"
    sql_list_event_types = "EXECUTE [dbo].ListEventTypes"
    sql_list_event_by_date = "EXECUTE [dbo].ListEventsByDate ?"
    sql_delete_event = "[dbo].[DeleteEvent] ?"
    sql_create_place = "[dbo].[CreatePlace] ?, ?, ?"
    sql_exclude_event = "[dbo].[ExcludeEvent] ?, ?"

    def __init__(self):
        self.connection = pyodbc.connect(
            'DRIVER={ODBC Driver 17 for SQL Server};SERVER=' + sql_server['server']
            + ';DATABASE=' + sql_server['database']
            + ';UID=' + sql_server['username']
            + ';PWD=' + sql_server['password'])

        self.cursor = self.connection.cursor()

    def __enter__(self):
        return self

    def __exit__(self, type_param, value, traceback):
        self.cursor.close()
        self.connection.close()

    def save_events(self, events: List[Event]):
        type_mapping, _ = self.load_type_mapping()
        for event in events:
            place_id = self.insert_place(event.place)
            event_id = self.insert_event(event, place_id)
            self.set_event_attributes(event_id, event.event_dates, event.event_tags, type_mapping)
            self.connection.commit()

    def remove_events(self, event_ids: List[int]):
        for event_id in event_ids:
            self.cursor.execute(self.sql_delete_event, event_id)
        self.connection.commit()

    def insert_event(self, event, place_id):
        cost = ""
        if type(event.cost) == list and event.cost is not None:
            cost = " ".join([str(int(c)) for c in event.cost])

        values = (event.title, event.poster, event.description, event.short_description, event.source, cost, place_id)
        self.cursor.execute(self.sql_insert_event, values)
        event_id = self.cursor.fetchval()
        return event_id

    def exclude_event(self, event_id, username):
        self.cursor.execute(self.sql_exclude_event, (event_id, username))
        self.connection.commit()

    def insert_place(self, place: Place):
        values = (place.name, place.address, place.url)
        self.cursor.execute(self.sql_create_place, values)
        place_id = self.cursor.fetchval()
        return place_id

    def list_events_by_date(self, date) -> List[Event]:
        self.cursor.execute(self.sql_list_event_by_date, date)
        events = []
        query_result = self.cursor.fetchall()
        for event_id, title, poster, short, desc, source, cost, dates, start_dates, end_dates, \
                place_name, place_address, place_url, types in query_result:

            if types:
                types = [t for t in types.split(' ')]
            else:
                types = []

            events_dates = []
            if dates:
                for date in dates.split(','):
                    events_dates.append(datetime.datetime.fromisoformat(date))
            if start_dates:
                for start_date, end_date in zip(start_dates.split(','), end_dates.split(',')):
                    if start_date and start_date != 'null':
                        start_date = datetime.datetime.fromisoformat(start_date)
                    else:
                        start_date = None
                    if end_date and end_date != 'null':
                        end_date = datetime.datetime.fromisoformat(end_date)
                    else:
                        end_date = None
                    events_dates.append(EventDateRange(start_day=start_date, end_day=end_date))
            if cost:
                cost = [int(c) for c in cost.split(' ')]

            place = Place(place_name, place_address, place_url)
            event = Event(title, desc, place, events_dates, source,
                          short_description=short, poster=poster, event_tags=types, cost=cost, event_id=event_id)
            events.append(event)
        return events

    def load_type_mapping(self):
        self.cursor.execute(self.sql_list_event_types)
        type_to_id = {}
        id_to_type = []
        for type_id, type_name in self.cursor.fetchall():
            type_to_id[type_name] = type_id
            id_to_type.append(type_name)
        return type_to_id, id_to_type

    def set_event_attributes(self, event_id, dates, types, type_mapping):
        for event_type in types:
            if event_type in type_mapping:
                self.cursor.execute(self.sql_set_type, (type_mapping[event_type], event_id))

        for date in dates:
            if type(date) == EventDateRange:
                self.cursor.execute(self.sql_set_date_range, (date.start, date.end, event_id))
            else:
                self.cursor.execute(self.sql_set_date, (date, event_id))
