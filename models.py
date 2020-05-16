from typing import List
import datetime


def group_by_dates(events):
    events_by_dates = {}
    for event in events:
        event_model = Event.from_json(event)
        dt = event_model.get_first_date()
        if dt not in events_by_dates:
            events_by_dates[dt] = []
        events_by_dates[dt].append(event)
    return events_by_dates


def date_time_to_json(dt):
    if type(dt) == datetime.datetime:
        return {
            "year": dt.year,
            "month": dt.month,
            "day": dt.day,
            "hour": dt.hour,
            "minute": dt.minute
        }
    else:
        return date_to_json(dt)


def datetime_from_json(j):
    if "minute" in j:
        return datetime.datetime(year=int(j['year']), month=int(j['month']), day=int(j['day']),
                                 hour=int(j['hour']), minute=int(j['minute']))
    else:
        return date_from_json(j)


def date_from_json(j):
    return datetime.date(year=int(j['year']), month=int(j['month']), day=int(j['day']))


def date_to_json(dt: datetime.date):
    if not dt:
        return None
    return {
        "year": dt.year,
        "month": dt.month,
        "day": dt.day,
    }


class EventPlace:
    def __init__(self, place_name, place_address, place_url):
        self.place_name = place_name
        self.place_address = place_address
        self.place_url = place_url

    def __str__(self):
        return self.place_name

    def to_json(self):
        return {
            "name": self.place_name,
            "address": self.place_address,
            "url": self.place_url
        }

    @staticmethod
    def from_json(j):
        return EventPlace(j['name'], j['address'], j['url'])


class EventDateRange:
    def __init__(self, start_day, end_day, week_schedule=None):
        self.start_day = start_day
        self.end_day = end_day
        self.week_schedule = week_schedule

    def __str__(self):
        return "from %s to %s" % (self.start_day, self.end_day)

    def to_json(self):
        return {
            "start": date_to_json(self.start_day),
            "end":  date_to_json(self.end_day),
            "schedule": self.week_schedule
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
    def __init__(self, title: str, short_description: str, poster: str, description: str, place: EventPlace,
                 event_tags: List[str], event_dates, source: str, event_types=None,
                 registration_info=None, info=None, age_restriction=None, cost=None, raw_dates=None):
        self.title = title
        self.short_description = short_description
        self.poster = poster
        self.description = description
        self.place = place
        if event_tags:
            self.event_tags = list(set(event_tags))
        self.event_dates = event_dates
        self.source = source
        self.registration_info = registration_info
        # number or url
        self.info = info
        self.age_restriction = age_restriction
        self.cost = cost

        self.raw_dates = raw_dates

    def get_first_date(self):
        for d in self.event_dates:
            if type(d) == EventDateRange:
                return d.start_day
            elif type(d) == datetime.date or type(d) == datetime.datetime:
                return d
        return datetime.date(year=datetime.MINYEAR, month=1, day=1)

    @staticmethod
    def from_json(j):
        reg_info, cost, age, info, raw_dates = None, None, None, None, None
        if 'registration_info' in j:
            reg_info = j['registration_info']
        if 'cost' in j:
            cost = j['cost']
        if 'age' in j:
            age = j['age']
        if 'info' in j:
            info = j['info']
        if 'raw_dates' in j:
            raw_dates = j['raw_dates']

        dates = []
        for d in j['dates']:
            if "start" in d:
                dates.append(EventDateRange.from_json(d))
            else:
                dates.append(datetime_from_json(d))
        title, short, description, poster, place, tags, url = None, None, None, None, None, None, None
        if 'title' in j:
            title = j['title']
        if 'short_description' in j:
            short = j['short_description']
        if 'poster' in j:
            poster = j['poster']
        if 'description' in j:
            description = j['description']
        if 'place' in j:
            place = EventPlace.from_json(j['place'])
        if 'tags' in j:
            tags = j['tags']
        if 'url' in j:
            url = j['url']

        return Event(title, short, poster, description, place, tags, dates, url, None,
                     reg_info, info, age, cost, raw_dates)

    def to_json(self):
        result = {
            "title": self.title,
            "short_description": self.short_description,
            "description": self.description,
            "poster": self.poster,
            "url": self.source,
            "place": self.place.to_json(),
            "tags": self.event_tags,
            "age": self.age_restriction,
            "registration": self.registration_info,
            "info": self.info,
            "cost": self.cost,
            "dates": [],
            "raw_dates": self.raw_dates,
        }

        for d in self.event_dates:
            if type(d) == EventDateRange:
                result["dates"].append(d.to_json())
            else:
                result["dates"].append(date_time_to_json(d))

        return result

    def to_str(self):
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


class CityDogScheduleElement:
    def __init__(self, place, date: str, time: str):
        self.place = place
        self.date = date
        self.time = time

    def __str__(self):
        return "%s - %s" % (str(self.place), self.date)


class CityDogEvent:
    def __init__(self, title: str, short_description: str, full_description: str,
                 cost: str, source: str, schedule: List[CityDogScheduleElement],
                 event_date, places: List[EventPlace], event_type: str, url: str, image_url: str, tags: List[str],
                 register_link=None):
        self.title = title
        self.short_description = short_description
        self.full_description = full_description
        self.cost = cost
        self.source = source
        self.event_date = event_date
        self.schedule = schedule
        self.event_type = event_type
        self.places = places
        self.url = url
        self.image_url = image_url
        self.tags = tags
        self.register_link = register_link

    def __str__(self):
        result = [
            "%s (%s)" % (self.title, self.event_type),
            self.short_description,
            "%s - %s" % (", ".join(str(p) for p in self.places), self.event_date),
            self.cost,
            "%s <- %s" % (self.url, self.source),
            self.full_description
        ]

        if self.register_link:
            result.append("Регистрация: %s" % self.register_link)
        result.extend([str(s) for s in self.schedule])
        result.extend([str(s) for s in self.tags])

        return "\n".join(result)


class RelaxEvent:
    def __init__(self, title: str, full_description: str,
                 cost: str, schedule: List[str],
                 event_date, place: EventPlace, event_type: str,
                 url: str, image_url: str, tags: List[str],
                 working_hours, registration_info, event_info_number):
        self.title = title
        self.full_description = full_description
        self.cost = cost
        self.event_date = event_date
        self.schedule = schedule
        self.event_type = event_type
        self.place = place
        self.url = url
        self.image_url = image_url
        self.tags = tags
        self.working_hours = working_hours
        self.registration_info = registration_info
        self.event_info_number = event_info_number

    def __str__(self):
        result = [
            "%s (%s)" % (self.title, self.event_type),
            "%s - %s" % (self.place, self.event_date),
            self.url,
            self.full_description
        ]

        if self.cost:
            result.append(self.cost)

        result.extend([str(s) for s in self.schedule])
        result.extend([str(s) for s in self.tags])

        return "\n".join(result)
