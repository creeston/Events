from typing import List
import datetime


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
        return {
            "year": dt.year,
            "month": dt.month,
            "day": dt.day
        }


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


class EventDateRange:
    def __init__(self, start_day, end_date, week_schedule=None):
        self.start_day = start_day
        self.end_day = end_date
        self.week_schedule = week_schedule

    def __str__(self):
        return "from %s to %s" % (self.start_day, self.end_day)

    def to_json(self):
        return {
            "start": date_to_json(self.start_day),
            "end":  date_to_json(self.end_day),
            "schedule": self.week_schedule
        }


class Event:
    def __init__(self, title: str, short_description: str, poster: str, description: str, place: EventPlace,
                 event_tags: List[str], event_dates, source: str,
                 registration_info=None, info=None, age_restriction=None, cost=None, raw_dates=None):
        self.title = title
        self.short_description = short_description
        self.poster = poster
        self.description = description
        self.place = place
        self.event_tags = list(set(event_tags))
        self.event_dates = event_dates
        self.source = source
        self.registration_info = registration_info
        # number or url
        self.info = info
        self.age_restriction = age_restriction
        self.cost = cost

        self.raw_dates = raw_dates

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
            "raw_dates": self.raw_dates
        }

        for d in self.event_dates:
            if type(d) == EventDateRange:
                result["dates"].append(d.to_json())
            else:
                result["dates"].append(date_time_to_json(d))

        return result

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
