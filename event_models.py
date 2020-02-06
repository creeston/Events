from typing import List
import datetime


class EventPlace:
    def __init__(self, place_name, place_address, place_url):
        self.place_name = place_name
        self.place_address = place_address
        self.place_url = place_url

    def __str__(self):
        return self.place_name


class DateRange:
    def __init__(self, start_day, end_date):
        self.start_day = start_day
        self.end_day = end_date

    def __str__(self):
        return "from %s to %s" % (self.start_day, self.end_day)


class TutByEvent:
    def __init__(self, title: str, place: EventPlace, date: str,
                 times: List[datetime.time], description: str,
                 tags: List[str], category: str, link: str, is_free: bool, image_url: str):
        self.title = title
        self.place = place
        self.times = times
        self.description = description
        self.tags = tags
        self.link = link
        self.date = date
        self.category = category
        self.is_free = is_free
        self.image_url = image_url

    def __str__(self):
        result = [
            self.image_url,
            "%s - %s (%s)" % (self.place, self.title, self.category),
            self.date]
        if self.tags:
            result.append("(%s)" % ",".join(self.tags))
        if self.description:
            result.append("\n".join([str(t) for t in self.description if t]).strip())
        for time in self.times:
            result.append(str(time))
        result.append(self.link)
        if self.is_free:
            result.append("<FREE>")
        return "\n".join(result)


class CityDogScheduleElement:
    def __init__(self, place, date: str, time: str):
        self.place = place
        self.date = date

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
