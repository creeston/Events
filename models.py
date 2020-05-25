from typing import List, Optional
from datetime import timezone, datetime, MINYEAR


def date_time_to_json(dt) -> dict:
    return {
            "year": dt.year,
            "month": dt.month,
            "day": dt.day,
            "hour": dt.hour,
            "minute": dt.minute
    }


def datetime_from_json(j) -> Optional[datetime]:
    try:
        if 'year' not in j or not j['year']:
            j['year'] = datetime.now().year

        if "minute" in j:
            return datetime(year=int(j['year']), month=int(j['month']), day=int(j['day']),
                            hour=int(j['hour']), minute=int(j['minute']))
        else:
            return date_from_json(j)
    except ValueError:
        return None
    except TypeError:
        return None


def date_from_json(j) -> datetime:
    return datetime(year=int(j['year']), month=int(j['month']), day=int(j['day']))


def date_to_json(dt: datetime.date) -> Optional[dict]:
    if not dt:
        return None
    return {
        "year": dt.year,
        "month": dt.month,
        "day": dt.day,
    }


class Place:
    def __init__(self, name: str, address: str, url: str = None):
        self.name = name
        self.address = address
        self.url = url

    def __str__(self):
        return "%s (%s)" % (self.name, self.address)

    def to_json(self):
        return {
            "name": self.name,
            "address": self.address,
            "url": self.url
        }

    @staticmethod
    def from_json(j):
        return Place(j['name'], j['address'], j['url'])


class EventDateRange:
    def __init__(self, start_day: Optional[datetime], end_day: datetime, week_schedule=None):
        self.start = start_day
        self.end = end_day
        self.schedule = week_schedule

    def __str__(self):
        return "from %s to %s" % (self.start, self.end)

    def to_json(self):
        return {
            "start": date_to_json(self.start),
            "end":  date_to_json(self.end),
            "schedule": self.schedule
        }

    @staticmethod
    def from_json(j):
        start, end = None, None
        if "start" in j and j['start']:
            start = date_from_json(j['start'])
        if "end" in j and j["end"]:
            end = date_from_json(j['end'])
        return EventDateRange(start_day=start, end_day=end,
                              week_schedule=j['schedule'])


class Event:
    def __init__(self, title: str, description: str, place: Place, event_dates: List, source_url: str,
                 poster: str = None, short_description: str = None, event_tags: List[str] = None,
                 registration_info: str = None, age_restriction: str = None, cost: List[int] = None,
                 raw_dates=None, raw_cost: str = None, raw_tags: List[str] = None,
                 timestamp=None, event_id=None):
        self.title = title
        self.short_description = short_description
        self.poster = poster
        self.description = description
        self.place = place
        if event_tags:
            self.event_tags = list(set(event_tags))
        else:
            self.event_tags = []
        self.event_dates = event_dates
        self.source = source_url
        self.registration_info = registration_info
        self.age_restriction = age_restriction
        self.cost = cost
        self.raw_dates = raw_dates
        self.timestamp = timestamp
        self.raw_cost = raw_cost
        self.raw_tags = raw_tags
        self.event_id = event_id

    def get_first_date(self):
        for d in self.event_dates:
            if type(d) == EventDateRange:
                if d.start:
                    return d.start
                else:
                    return d.end
            elif type(d) == datetime.date or type(d) == datetime:
                return d
        return datetime(year=MINYEAR, month=1, day=1)

    @staticmethod
    def from_json(j):
        reg_info, cost, age, info, raw_dates = None, None, None, None, None
        title, short, description, poster, place, tags, url, timestamp = None, None, None, None, None, None, None, None
        raw_tags, raw_cost = None, None

        if 'registration_info' in j:
            reg_info = j['registration_info']
        if 'cost' in j:
            cost = j['cost']
        if 'age' in j:
            age = j['age']
        if 'raw_dates' in j:
            raw_dates = j['raw_dates']

        dates = []
        for d in j['dates']:
            if "start" in d:
                dates.append(EventDateRange.from_json(d))
            else:
                dates.append(datetime_from_json(d))

        if 'title' in j:
            title = j['title']
        if 'short_description' in j:
            short = j['short_description']
        if 'poster' in j:
            poster = j['poster']
        if 'description' in j:
            description = j['description']
        if 'place' in j:
            place = Place.from_json(j['place'])
        if 'tags' in j:
            tags = j['tags']
        if 'raw_tags' in j:
            raw_tags = j['raw_tags']
        if 'raw_cost' in j:
            raw_cost = j['raw_cost']
        if 'url' in j:
            url = j['url']
        if 'timestamp' in j:
            timestamp = datetime.fromtimestamp(j['timestamp'])

        return Event(title, description, place, dates, url, short_description=short, poster=poster,
                     registration_info=reg_info, age_restriction=age, cost=cost, raw_dates=raw_dates,
                     event_tags=tags, raw_tags=raw_tags, timestamp=timestamp, raw_cost=raw_cost)

    def to_json(self) -> dict:
        result = {
            "title": self.title,
            "short_description": self.short_description,
            "description": self.description,
            "poster": self.poster,
            "url": self.source,
            "tags": self.event_tags,
            "age": self.age_restriction,
            "registration": self.registration_info,
            "cost": self.cost,
            "raw_dates": self.raw_dates,
            "raw_tags": self.raw_tags,
            "raw_cost": self.raw_cost,
            "event_id": self.event_id
        }

        if self.timestamp:
            result['timestamp'] = self.timestamp.replace(tzinfo=timezone.utc).timestamp()

        if self.place:
            result['place'] = self.place.to_json()

        dates = []
        for d in self.event_dates:
            if type(d) == EventDateRange:
                dates.append(d.to_json())
            else:
                dates.append(date_time_to_json(d))
        result['dates'] = dates
        return result

    def to_str(self) -> str:
        result = [self.title]
        if self.short_description:
            result.append(self.short_description)
        if self.description:
            result.append(self.description)
        return "\n".join(result)

    def __str__(self):
        result = [
            self.poster,
            "%s - %s" % (self.place, self.title,)]
        if self.event_tags:
            result.append("(%s)" % ",".join(self.event_tags))
        if self.description:
            result.append(self.description)
        for time in self.event_dates:
            result.append(str(time))
        result.append(self.source)
        return "\n".join(result)


event_type_mapping = {
    "Бесплатно": "free",
    "Выставка": "exhibition",
    "Встреча": "lecture",
    "Вечеринка": "party",
    "Дегустация": "food",
    "Занятие": "training",
    "Интенсив": "training",
    "Игра": "game",
    "Квест": "game",
    "Концерт": "concert",
    "Квиз": "game",
    "Конкурс": "compete",
    "Конференция": "festival",
    "Лекция": "lecture",
    "Мастер-класс": "training",
    "Модный показ": "show",
    "Онлайн": "online",
    "Просмотр": "view",
    "Презентация": "lecture",
    "Разговорный клуб": "training",
    "Семинар": "training",
    "Стендап": "standup",
    "Спектакль": "theater",
    "Спортивное мероприятие": "sport",
    "Тренинг": "training",
    "Турнир": "compete",
    "Фестиваль": "festival",
    "Хакатон": "compete",
    "Шоу": "show",
    "Экскурсия": "tour",
    "Ярмарка": "market"
}


event_types = [
    "compete",
    "concert",
    "concert_programm",
    "exhibition",
    "festival",
    "food",
    "free",
    "game",
    "lecture",
    "market",
    "online",
    "open air",
    "party",
    "show",
    "sport",
    "standup",
    "theatre",
    "tour",
    "training",
    "view"
]


def group_by_dates(events: List[Event]) -> dict:
    events_by_dates = {}
    for event in events:
        dt = event.get_first_date()
        if dt not in events_by_dates:
            events_by_dates[dt] = []
        events_by_dates[dt].append(event)
    return events_by_dates
