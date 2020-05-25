import json
import datetime
from typing import List

from azure.storage.table import TableService
from models import group_by_dates


class EventRepository:
    events_by_date_table = "eventsByDate"
    event_duplicates_table = "eventDuplicates"

    def __init__(self, connection_string=None):
        if not connection_string:
            connection_string = "AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;DefaultEndpointsProtocol=http;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
            self.table_client = TableService(connection_string=connection_string)

    def list_events_by_date(self, dt: datetime.date) -> List[dict]:
        pk = self._date_to_pk(dt)
        for event in self.table_client.query_entities(self.events_by_date_table, filter="PartitionKey eq '%s'" % (pk,)):
            if 'place' in event:
                event['place'] = json.loads(event['place'])
            if 'dates' in event:
                event['dates'] = json.loads(event['dates'])
            if 'raw_dates' in event:
                event['raw_dates'] = event['raw_dates'].split('\n')
            if 'tags' in event:
                event['tags'] = event['tags'].split(',')
            if 'type' in event:
                event['type'] = event['type'].split(',')
            if 'cost' in event:
                event['cost'] = event['cost'].split(',')
            yield event

    def remove_rows(self, dt, row_keys):
        pk = self._date_to_pk(dt)
        for key in row_keys:
            self.table_client.delete_entity(self.events_by_date_table, pk, key)

    def save_events_by_date(self, events: List[dict], dt: datetime.date, table_name=events_by_date_table):
        partition_keys = set()
        for event in events:
            if 'PartitionKey' not in event:
                if dt:
                    event['PartitionKey'] = self._date_to_pk(dt)
                else:
                    event['PartitionKey'] = str(datetime.date.today().year)

            if 'RowKey' not in event:
                full_text = event['title'] + "\n" + event['short_description'] + "\n" + event['description']
                event['RowKey'] = str(hash(full_text))

            event['place'] = json.dumps(event['place'], ensure_ascii=False)
            event['dates'] = json.dumps(event['dates'])
            event['tags'] = ",".join(event['tags'])
            if 'type' in event:
                event['type'] = ",".join(event['type'])
            if "raw_dates" in event:
                event['raw_dates'] = "\n".join(event['raw_dates'])
            if 'cost' in event and event['cost']:
                event['cost'] = ",".join(str(c) for c in event['cost'])
            else:
                event['cost'] = None
            self.table_client.insert_or_replace_entity(table_name, event)
            partition_keys.add(event['PartitionKey'])

        for pk in partition_keys:
            self.table_client.insert_or_replace_entity(table_name, {"PartitionKey": "PARTITIONS", "RowKey": pk})

    def save_events_json(self, events: List[dict]):
        grouped_events = group_by_dates(events)
        for dt, events in grouped_events.items():
            self.save_events_by_date(events, dt)

    @staticmethod
    def _date_to_pk(dt: datetime.date):
        return "%d_%d_%d" % (dt.year, dt.month, dt.day)
