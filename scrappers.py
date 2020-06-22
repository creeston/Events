import requests
import bs4
import vk_api
import re
import demoji
import traceback
import sys
import os

demoji.download_codes()

from interpreters import DateInterpreter, TagMapper
from telethon import TelegramClient
from configuration import tg_credentials, vk_credentials
from time import sleep
from datetime import datetime
from models import Event, EventDateRange, Place, event_type_mapping
from markup import MarkupCurrency
from typing import Optional, List, Tuple


space_re = re.compile(r"\s+")
dot_re = re.compile(r"\.+")
punctuation_characters = ['.', ',', ':', '!', '?', ';', '/']
specials = ['•', "►"]
hashtag_re = re.compile(r"(#\w+)")
splash_url = os.environ['SPLASH_URL'] + "/render.html"


class ScrapHelper:
    RE_COMBINE_WHITESPACE = re.compile(r"\s+")
    RE_HYPHENS = re.compile(r"[\-‒–—―]")

    @staticmethod
    def get_parsed(url: str):
        response = requests.get(url)
        return bs4.BeautifulSoup(response.content, 'lxml')

    @staticmethod
    def get_parsed_js(url):
        response = requests.post(splash_url, json={
            'url': url
        })
        return bs4.BeautifulSoup(response.content, 'lxml')

    @staticmethod
    def get_all_text(element: bs4.element.PageElement):
        if type(element) == bs4.element.NavigableString:
            return str(element).strip()
        if type(element) == bs4.element.Comment:
            return ""
        text = element.find_all(text=True)
        result = []
        for t in text:
            if str(t) == '\n':
                continue
            result.append(str(t))
        return "\n".join(result)

    @staticmethod
    def get_string(element):
        element_string = element.text
        br = element.find("br")
        if br:
            parts = [t.strip() for t in element.find_all(text=True) if len(t.strip()) > 0]
            return " ".join(parts)
        return re.sub(r'\s+', ' ', element_string).strip()

    @staticmethod
    def preprocess(string):
        string = string.lower()
        string = re.sub(ScrapHelper.RE_HYPHENS, "", string)
        string = re.sub(ScrapHelper.RE_COMBINE_WHITESPACE, " ", string)
        return string


class TutByScrapper:
    old_page_categories = {
        "concert": "https://afisha.tut.by/concert/",
        "party": "https://afisha.tut.by/party/",
        "theatre": "https://afisha.tut.by/theatre/",
        "other": "https://afisha.tut.by/other/"
    }
    new_page_categories = {
        "exhibition": "https://afisha.tut.by/exhibition/"
    }
    listed_events = []

    def __init__(self, logger):
        self.logger = logger
        self.mapper = TagMapper(logger)
        self.currency_markup = MarkupCurrency()

    def list_events(self):
        self.listed_events = []
        for category, events_page_url in self.old_page_categories.items():
            for event in self._list_events_from_old_page(events_page_url, category):
                yield event

        for category, events_page_url in self.new_page_categories.items():
            for event in self._list_events_from_new_page(events_page_url, category):
                yield event

    def _list_events_from_old_page(self, events_page_url: str, category: str) -> List[Event]:
        for event_element in self._get_event_elements(events_page_url):
            try:
                title, page_url = self._parse_old_title_element(event_element)
                if page_url in self.listed_events:
                    continue

                description, places_and_dates, poster_url, tut_by_tags, raw_dates = self._parse_event_page(page_url)
                age = self._get_age_restriction_from_tags(tut_by_tags)
                unified_tags = self._get_unified_tags(tut_by_tags, category)
                raw_costs = self._get_cost_from_description(description)
                for place, dates in places_and_dates:
                    yield Event(title, description, place, dates, page_url,
                                poster=poster_url, raw_tags=unified_tags, age_restriction=age, raw_dates=raw_dates,
                                raw_costs=raw_costs)
                self.listed_events.append(page_url)
            except str as e:
                self.logger.log_error(e)
                traceback.print_exc(file=sys.stdout)
                continue

    def _get_cost_from_description(self, description) -> Optional[List[str]]:
        money_tags = [description[s:e] for t, s, e in self.currency_markup.markup(description) if t == "MONEY"]
        if len(money_tags) > 0:
            return list(set(money_tags))
        return None

    def _get_unified_tags(self, tut_by_tags, category) -> List[str]:
        unified_tags = []
        unified_tags.extend(self.mapper.map_tut(category))
        for tag in tut_by_tags:
            unified_tags.extend(self.mapper.map_tut(tag))
        return unified_tags

    def _list_events_from_new_page(self, events_page_url, category):
        for event_element in self._get_event_elements_from_new_page(events_page_url):
            try:
                page_url = self._parse_media_element(event_element)
                if page_url in self.listed_events:
                    continue

                title = self._get_new_event_title(event_element)
                description, places_and_dates, poster_url, tut_by_tags, raw_dates = self._parse_event_page(page_url)
                age = self._get_age_restriction_from_tags(tut_by_tags)
                unified_tags = self._get_unified_tags(tut_by_tags, category)
                raw_costs = self._get_cost_from_description(description)
                for place, dates in places_and_dates:
                    yield Event(title, description, place, dates, page_url,
                                raw_tags=unified_tags, poster=poster_url, age_restriction=age, raw_dates=raw_dates,
                                raw_costs=raw_costs)
                self.listed_events.append(page_url)
            except Exception as e:
                self.logger.log_error(e)
                traceback.print_exc(file=sys.stdout)
                continue

    @staticmethod
    def _parse_old_title_element(event_element):
        title_and_time = event_element.find('div', {'class': 'event-item-i js-film-list__li'})
        title_element = title_and_time \
            .find('div', {'class': 'item-header'}) \
            .find('div', {'class': 'item-header-i'})
        event_title, event_link = TutByScrapper._get_title(title_element)
        return event_title, event_link

    @staticmethod
    def _get_event_elements_from_new_page(page_url):
        events_page = ScrapHelper.get_parsed(page_url)
        events_block = events_page.find("div", {"id": "events-block"})
        for event_element in events_block.find_all("li", {"class": "lists__li"}):
            yield event_element

    @staticmethod
    def _get_event_elements(events_page_url: str):
        events_page = ScrapHelper.get_parsed(events_page_url)
        events_block = events_page.find('div', {'id': 'schedule-table'})
        for event_element in events_block.find_all('div', {'class': [
            'b-afisha-event js-film-info',
            'b-afisha-event-title'
        ]}):
            if type(event_element) == bs4.element.NavigableString:
                continue
            if event_element.attrs['class'][0] == 'b-afisha-event-title':
                continue
            yield event_element

    @staticmethod
    def _parse_media_element(event_element):
        media_element = event_element.find("a", {"class": "media"})
        event_url = media_element.attrs['href']
        return event_url

    @staticmethod
    def _get_new_event_title(event_element):
        name_element = event_element.find("a", {"class": "name"})
        return ScrapHelper.get_string(name_element)

    @staticmethod
    def _get_tags(event_page: bs4.element.PageElement):
        tags_element = event_page.find("div", {"class": "sub_title m-margin-bottom tag-place"})
        if not tags_element:
            return []

        tag_elements = tags_element.find_all("a", {"class": "tag"})
        tags = []
        for tag_element in tag_elements:
            tags.append(re.sub(r"\s+", " ", tag_element.text.strip().lower()))
        return tags

    @staticmethod
    def _get_title(title_element):
        titles = title_element.find_all('a')
        event_title = ""
        event_link = ""
        for title in titles:
            event_title = title.find('span')
            if not event_title:
                continue
            event_title = event_title.contents[0]
            event_link = title['href']
            break
        return event_title, event_link

    @staticmethod
    def _parse_event_page(event_page_url: str):
        event_page = ScrapHelper.get_parsed(event_page_url)
        description = TutByScrapper._get_event_description(event_page)
        occurrences = list(TutByScrapper._parse_occurrences(event_page))
        occurrences_by_places = {}
        for place, date in occurrences:
            if place.name not in occurrences_by_places:
                occurrences_by_places[place.name] = (place, [])
            occurrences_by_places[place.name][1].append(date)

        places_and_dates = list(occurrences_by_places.values())
        raw_dates = list(TutByScrapper._get_raw_dates(event_page))
        poster_url = TutByScrapper._get_image(event_page)
        tut_by_tags = TutByScrapper._get_tags(event_page)
        return description, places_and_dates, poster_url, tut_by_tags, raw_dates

    @staticmethod
    def _get_raw_dates(event_page):
        schedule_element = event_page.find("div", {"class": "b-event__tickets js-cut_wrapper"})
        if not schedule_element:
            return None
        occurrences = schedule_element.find_all("div", {"class": "b-shedule-day_event"})
        prev_date = None
        for occurrence in occurrences:
            times_element = occurrence.find("ul", {"class": "b-list b-shedule-list"})
            day_element = occurrence.find("div", {"class": "b-shedule-day_item"})
            if not times_element:
                date = TutByScrapper._get_broad_date(day_element)
                day_range = date[0]
                week_schedule = date[1]
                yield "%s. %s" % (day_range, week_schedule)
            else:
                date, times = TutByScrapper._get_exact_raw_date(day_element, times_element)
                if not date:
                    date = prev_date
                prev_date = date
                for time in times:
                    yield "%s в %s" % (date.replace("\xa0", " "), time)

    @staticmethod
    def _parse_occurrences(event_page: bs4.element.PageElement):
        schedule_element = event_page.find("div", {"class": "b-event__tickets js-cut_wrapper"})
        if not schedule_element:
            return None
        occurrences = schedule_element.find_all("div", {"class": "b-shedule-day_event"})
        prev_date = None
        for occurrence in occurrences:
            times_element = occurrence.find("ul", {"class": "b-list b-shedule-list"})
            day_element = occurrence.find("div", {"class": "b-shedule-day_item"})
            place = TutByScrapper._get_place_from_occurrence(occurrence)
            if not times_element:
                date_range, time_range = TutByScrapper._get_broad_date(day_element)
                date_range = DateInterpreter.parse_tutby_date_range(date_range)
                week_schedule = DateInterpreter.parse_tutby_week_time_schedule(time_range)
                date_range = EventDateRange(*date_range, week_schedule)
                yield place, date_range
            else:
                date, times = TutByScrapper._get_exact_date(day_element, times_element)
                if not date and not prev_date:
                    continue
                if not date:
                    date = prev_date
                prev_date = date
                if not times or len(times) == 0:
                    yield place, DateInterpreter.get_date(*date)
                else:
                    for time in times:
                        yield place, DateInterpreter.get_datetime(*date, *time)

    @staticmethod
    def _get_exact_raw_date(day_element, times_element):
        day_string = list(day_element.children)[0].strip()
        if day_string:
            date = day_string
        else:
            date = None
        times_elements = times_element.find_all("li", {"class": "lists__li"})
        times = []
        for time_element in times_elements:
            times.append(time_element.text.strip())
        return [date, times]

    @staticmethod
    def _get_exact_date(day_element: bs4.element.PageElement, times_element: bs4.element.PageElement):
        day_string = list(day_element.children)[0].strip()
        if day_string:
            date = DateInterpreter.parse_day_month(day_string)
        else:
            date = None
        times_elements = times_element.find_all("li", {"class": "lists__li"})
        times = []
        for time_element in times_elements:
            hour, minute = time_element.text.strip().split(':')
            times.append((int(hour), int(minute)))

        return date, times

    @staticmethod
    def _get_broad_date(day_element: bs4.element.PageElement):
        values = list(day_element.children)[0].split(',')
        if len(values) != 2:
            raise Exception("Date string cannot be read")
        date_range, time_range = values
        return [date_range.strip(), time_range.strip()]

    @staticmethod
    def _get_place_from_occurrence(occurrence_element: bs4.element.PageElement):
        place_element = occurrence_element.find("a", {"class": "b-shedule-place"})
        items = list(place_element.children)
        place_name = str(items[0]).strip()
        place_address = items[1].text.strip()
        place_url = place_element.attrs['href']
        return Place(place_name, place_address, place_url)

    @staticmethod
    def _get_place_new(event_page):
        schedule_element = event_page.find("div", {"class": "b-event__tickets js-cut_wrapper"})
        if not schedule_element:
            return None
        place_elements = event_page.find_all("a", {"class": "b-shedule-place"})
        for place_element in place_elements:
            items = list(place_element.children)
            place_name = str(items[0]).strip()
            place_address = items[1].text.strip()
            place_url = place_element.attrs['href']
            yield Place(place_name, place_address, place_url)

    @staticmethod
    def _get_new_schedule(event_page):
        schedule_element = event_page.find("div", {"class": "b-event__tickets js-cut_wrapper"})
        if not schedule_element:
            return None
        schedules = schedule_element.find_all("div", {"class": "b-shedule-day_item"})
        for schedule in schedules:
            date_range, time_range = TutByScrapper._get_broad_date(schedule)
            yield date_range, time_range

    @staticmethod
    def _get_event_description(event_page: bs4.element.PageElement):
        description_element = event_page.find('div', {'id': 'event-description'})
        result = []
        for element in description_element.children:
            if type(element) == bs4.element.Tag:
                if element.name in ('script', 'link'):
                    continue
                if 'rel' in element.attrs:
                    continue
                if 'class' in element.attrs:
                    if len(
                            {'b-page-share', 'note', 'b-prmplace-media', 'b-subscription'} & set(element.attrs['class'])
                    ) > 0:
                        continue

            text = ScrapHelper.get_all_text(element)
            if not text:
                continue
            result.append(text)
        return "\n".join(result).replace("О событии", "").strip()

    @staticmethod
    def _get_image(event_page):
        img_element = event_page.find("img", {"class": "main_image"})
        return img_element.attrs['src']

    @staticmethod
    def _get_age_restriction_from_tags(tags):
        age = None
        tag_id = -1
        for i, tag in enumerate(tags):
            if re.match(r"\d{1,2}\+", tag):
                tag_id = i
                break
        if tag_id != -1:
            age = tags[tag_id]
            del tags[tag_id]
        return age


class CityDogScrapper:
    afisha_page = "https://citydog.by/afisha/"
    vedy_page = "https://citydog.by/vedy/#events"
    listed_events = []

    def __init__(self, logger):
        self.logger = logger
        self.mapper = TagMapper(logger)

    def list_events(self):
        self.listed_events = []
        for event in self.list_afisha_events():
            yield event
        for event in self.list_vedy_events():
            yield event

    def list_vedy_events(self):
        events_page = ScrapHelper.get_parsed_js(self.vedy_page)
        events_block = events_page.find('div', {'class': 'vedy-contentCol'}).find("div")
        for event_element in events_block.find_all("div", {"class": "vedyMain-item"}):
            try:
                category = self._get_vedy_category(event_element)
                poster_url = self._get_poster_url(event_element, "vedyMain-itemImg")
                labels = self._get_vedy_labels(event_element)
                info_element = event_element.find("div", {"class": "vedyMain-itemInfo"})
                title, page_url = self._get_title(info_element)
                if page_url in self.listed_events:
                    continue
                short_description = self._get_short_description(info_element)
                header_element, description_element = self._get_full_vedy_info_element(page_url)
                date_string = self._get_vedy_date(header_element)
                dates = DateInterpreter.parse_citydog_date(date_string)
                date_string = date_string.replace("   |   ", " в ")
                places = self._get_places(header_element)
                if len(places) > 0:
                    place = places[0]
                else:
                    place = Place(None, None, None)
                event_source, raw_cost, register_url = self._get_event_additional_info(header_element)
                if raw_cost:
                    raw_cost = [raw_cost]
                description = self._get_full_description(description_element)
                cd_tags = self._get_vedy_tags(description_element)
                cd_tags.extend(labels)
                unified_tags = self._get_unified_tags(cd_tags, category)
                yield Event(title, description, place, dates, page_url,
                            poster=poster_url, raw_tags=unified_tags, short_description=short_description,
                            raw_costs=raw_cost, registration_info=register_url, raw_dates=[date_string])

                self.listed_events.append(page_url)
            except Exception as e:
                self.logger.log_error(e)
                continue

    def _get_unified_tags(self, cd_tags, category) -> List[str]:
        unified_tags = []
        unified_tags.extend(self.mapper.map_cd(category))
        for tag in cd_tags:
            unified_tags.extend(self.mapper.map_cd(tag))
        return unified_tags

    def list_afisha_events(self):
        events_page = ScrapHelper.get_parsed(self.afisha_page)
        events_block = events_page.find('div', {'class': 'afishaMain-items'})
        for event_element in events_block.children:
            try:
                if type(event_element) == bs4.element.NavigableString:
                    continue
                category = self._get_category(event_element)
                poster_url = self._get_poster_url(event_element, "afishaMain-itemImg")
                info_element = event_element.find("div", {"class": "afishaMain-itemInfo"})
                title, page_url = self._get_title(info_element)
                if page_url in self.listed_events:
                    continue

                short_description = self._get_short_description(info_element)
                event_page, event_info_element = self._get_full_event_info_element(page_url)
                event_source, raw_cost, registration_url = self._get_event_additional_info(event_info_element)
                if raw_cost:
                    raw_cost = [raw_cost]
                description = self._get_full_description(event_page)
                unified_tags = self._get_unified_tags([], category)
                places_and_dates = self._get_occurrences(event_page)
                if len(places_and_dates) > 0:
                    raw_dates = list(self._get_raw_occurrences(event_page))
                    for place, dates in places_and_dates:
                        yield Event(title, description, place, dates, page_url,
                                    raw_tags=unified_tags, short_description=short_description, poster=poster_url,
                                    raw_costs=raw_cost, registration_info=registration_url, raw_dates=raw_dates)
                else:
                    date_string = self._get_date_string(info_element, "afishaMain-itemDate")
                    date = DateInterpreter.parse_citydog_date(date_string)
                    date_string = date_string.replace("   |   ", " в ")
                    raw_dates = [date_string]
                    places = self._get_places(event_info_element)
                    for place in places:
                        yield Event(title, description, place, date, page_url,
                                    raw_tags=unified_tags, short_description=short_description, poster=poster_url,
                                    raw_costs=raw_cost, registration_info=registration_url, raw_dates=raw_dates)

                self.listed_events.append(page_url)
            except Exception as e:
                self.logger.log_error(e)
                continue

    @staticmethod
    def _get_vedy_date(header_element: bs4.element.PageElement) -> str:
        event_info_element = header_element.find("div", {"class": "vedyPage-eventInfoWrapper"})
        date_element = event_info_element.find("h3")
        result = []
        for element in date_element.children:
            if type(element) == bs4.element.NavigableString:
                result.append(str(element))
            elif element.name == 'br':
                result.append('\n')
        return "".join(result)

    @staticmethod
    def _get_vedy_labels(event_element: bs4.element.PageElement) -> List[str]:
        labels_element = event_element.find("div", {"class": "labels"})
        if not labels_element:
            return []
        labels = []
        for label_element in labels_element.find_all("i"):
            if "ng-hide" in label_element.attrs['class']:
                continue
            label = label_element.attrs['class'][1]
            labels.append(label)
        return labels

    @staticmethod
    def _get_vedy_tags(description_element: bs4.element.PageElement) -> List[str]:
        result = []
        tags_element = description_element.find("div", {"class": "vedyPage-tags"})
        for tag_element in tags_element.find_all("div", {"class": "vedyPage-tag"}):
            result.append(tag_element.text.strip().lower())
        return result

    @staticmethod
    def _get_full_event_info_element(event_page_url: str):
        event_info_element = None
        event_page = None
        while not event_info_element:
            sleep(1)
            event_page = ScrapHelper.get_parsed(event_page_url)
            event_info_element = event_page.find("div", {"class": "afishaPost-eventInfoBody"})
        return event_page, event_info_element

    @staticmethod
    def _get_full_vedy_info_element(vedy_page_url: str) -> Tuple[bs4.element.PageElement, bs4.element.PageElement]:
        header_element = None
        description_element = None
        while not description_element and not header_element:
            sleep(1)
            event_page = ScrapHelper.get_parsed_js(vedy_page_url)
            header_element = event_page.find("div", {"class": "vedyPage-header"})
            description_element = event_page.find("div", {"class": "_vedyPage-Description"})
        return header_element, description_element

    @staticmethod
    def _get_short_description(info_element: bs4.element.PageElement) -> str:
        return info_element.find("p").text.strip()

    @staticmethod
    def _get_title(info_element: bs4.element.PageElement) -> Tuple[str, str]:
        title_element = info_element.find("h3").find("a")
        title = title_element.text
        event_link = title_element.attrs['href']
        return title, event_link

    @staticmethod
    def _get_category(event_element: bs4.element.PageElement):
        return event_element.attrs['class'][1].strip().lower()

    @staticmethod
    def _get_vedy_category(event_element: bs4.element.PageElement) -> str:
        return event_element.attrs['class'][2].strip().lower()

    @staticmethod
    def _get_poster_url(event_element: bs4.element.PageElement, class_name) -> str:
        image_element = event_element.find("div", {"class": class_name})
        image_url = image_element.find("img").attrs['src']
        return image_url

    @staticmethod
    def _get_date_string(info_element: bs4.element.PageElement, class_name: str) -> str:
        date_element = info_element.find("div", {"class": class_name})
        return date_element.text.strip()

    @staticmethod
    def _get_event_additional_info(event_info_element: bs4.element.PageElement) -> Tuple[str, str, str]:
        additional_info_element = event_info_element.find("div", {"class": "additional_info"})
        event_source = None
        event_cost = None
        register_link = None
        for additional_info in additional_info_element.children:
            if type(additional_info) == bs4.element.NavigableString:
                continue
            elements = list(additional_info.children)
            if len(elements) < 2:
                continue
            if "справк" in elements[0].text.lower():
                event_source = additional_info.find('a').attrs['href']
            elif "вход" in elements[0].text.lower():
                event_cost = elements[1].strip()
            elif "регистр" in elements[0].text.lower():
                register_link = elements[2].attrs['href']
        return event_source, event_cost, register_link

    @staticmethod
    def _get_full_description(event_page: bs4.element.PageElement) -> str:
        full_description_element = event_page.find("div", {"class": "afishaPost-Description-text"})
        return full_description_element.text.strip()

    @staticmethod
    def _get_places(event_info_element: bs4.element.PageElement) -> List[Place]:
        places = []
        place_elements = event_info_element.find_all("div", {"class": "place"})
        for place_element in place_elements:
            place_name_element = place_element.find("a", {"class": "address_link", "itemprop": "name"})
            if not place_name_element:
                place_name_element = place_element.find("span", {"class": "place-name"})
            place_name = place_name_element.text
            place_address_element = place_element.find("p", {"class": "place-address"})
            if not place_address_element:
                place_address_element = place_element.find("div", {"class": "address"})
            place_address = place_address_element.text.strip()
            places.append(Place(place_name, place_address, None))
        return places

    @staticmethod
    def _get_occurrences(event_page: bs4.BeautifulSoup):
        schedule_element = event_page.find("div", {"class": "afishaPost-Raspisanie"})
        occurrences_by_place = {}
        if schedule_element:
            for day_element in schedule_element.find_all("div", {"class": "day"}):
                day_string = CityDogScrapper._get_day_string(day_element)
                day = DateInterpreter.parse_day_month(day_string)
                for place_element in day_element.find_all("div", {"class": "place"}):
                    place = CityDogScrapper._get_place(place_element)
                    if place.name not in occurrences_by_place:
                        occurrences_by_place[place.name] = (place, [])
                    sessions = CityDogScrapper._get_sessions(place_element)
                    for time in sessions:
                        time = DateInterpreter.parse_hour_minute(time)
                        date = DateInterpreter.get_datetime(*day, *time)
                        if type(date) == list:
                            occurrences_by_place[place.name][1].extend(date)
                        else:
                            occurrences_by_place[place.name][1].append(date)
        return list(occurrences_by_place.values())

    @staticmethod
    def _get_raw_occurrences(event_page: bs4.BeautifulSoup):
        schedule_element = event_page.find("div", {"class": "afishaPost-Raspisanie"})
        if schedule_element:
            for day_element in schedule_element.find_all("div", {"class": "day"}):
                day_string = CityDogScrapper._get_day_string(day_element)
                for place_element in day_element.find_all("div", {"class": "place"}):
                    sessions = CityDogScrapper._get_sessions(place_element)
                    times = []
                    for time in sessions:
                        time = DateInterpreter.parse_hour_minute(time)
                        times.append("%d:%d" % (time[0], time[1]))
                    yield "%s в %s" % (day_string, ",".join(times))

    @staticmethod
    def _get_day_string(day_element):
        day_string = day_element.find("h5")
        day_string = day_string.text.split(',')[0].strip()
        return day_string

    @staticmethod
    def _get_place(place_element):
        place_name_element = place_element.find("div", {"class": "place-name"})
        place_name = str(list(place_name_element.children)[0])
        place_address = place_name_element.find("span").text
        place = Place(place_name, place_address, None)
        return place

    @staticmethod
    def _get_sessions(place_element):
        sessions = []
        for session_element in place_element.find_all("div", {"class": "session"}):
            session_span = session_element.find("span")
            if not session_span:
                break
            time_string = session_span.text
            sessions.append(time_string)
        return sessions


class RelaxScrapper:
    pages = [
        (["concert"], "https://afisha.relax.by/conserts/minsk/"),
        (["party"], "https://afisha.relax.by/clubs/minsk/"),
        (["expo"],  "https://afisha.relax.by/expo/minsk/"),
        (["event"], "https://afisha.relax.by/event/minsk/"),
        (["sport"], "https://afisha.relax.by/sport/minsk/"),
    ]

    # for education for exclude "courses" genre
    pages.extend([
        (["education", genre], "https://afisha.relax.by/education/minsk/#?options%5B101%5D=" + str(genre_id))
        for genre_id, genre in [
            (1923, "интенсив"),
            (1783, "конференция"),
            (2263, "кулинарный мастер-класс"),
            (634, "лекция"),
            (635, "мастер-класс"),
            (2513, "митап"),
            (636, "семинар"),
            (637, "тренинг"),
            (2283, "форум")]])

    listed_events = []

    def __init__(self, logger):
        self.logger = logger
        self.mapper = TagMapper(logger)

    def list_events(self):
        self.listed_events = []
        for event_categories, url in self.pages:
            schedule_element = None
            while not schedule_element:
                events_page = self._open_events_page(url)
                schedule_element = events_page.find("div", {"id": "append-shcedule"})
            for event in self._list_events(schedule_element, event_categories):
                yield event

    @staticmethod
    def _get_poster_url(event_page: bs4.element.PageElement) -> Optional[str]:
        poster_element = event_page.find("img", {"class": "b-afisha-event__image"})
        if poster_element:
            return poster_element.attrs['src']
        return None

    def _get_relax_tags(self, genre, title, event_categories) -> List[str]:
        tags = []
        if genre:
            tags.extend(genre)
        tags.extend(self._get_tags_from_title(title))
        tags.extend(event_categories[1:])
        return tags

    def _list_events(self, schedule_element: Optional[bs4.element.PageElement], event_categories: List[str]):
        day_schedules = schedule_element.find_all("div", {"class": "schedule__list"})
        for day_schedule_element in day_schedules:
            event_elements = self._get_events(day_schedule_element)
            for event_element in event_elements:
                title, page_url = self._get_title_and_link(event_element)
                if page_url in self.listed_events:
                    continue
                event_page = ScrapHelper.get_parsed(page_url)
                poster_url = self._get_poster_url(event_page)
                event_full_info = event_page.find("div", {"class": "b-afisha-layout-theater_full"})
                raw_cost, genre, working_hours, registration_info, age_restriction = self._get_metadata(event_full_info)
                if raw_cost:
                    raw_cost = [raw_cost]
                places_and_dates = self._get_occurrences(event_full_info)
                raw_dates = list(self._get_raw_occurrences(event_full_info))
                description = self._get_description(event_full_info)
                relax_tags = self._get_relax_tags(genre, title, event_categories)
                unified_tags = self._get_unified_tags(relax_tags, event_categories)
                for place, dates in places_and_dates:
                    if working_hours:
                        raw_dates.append(working_hours)
                        schedule = DateInterpreter.parse_relax_schedule(working_hours)
                        if not schedule:
                            continue
                        if type(schedule[0]) == EventDateRange:
                            dates = schedule
                        elif type(dates[0]) == EventDateRange and len(dates) == 1:
                            dates[0].week_schedule = schedule

                    yield Event(title, description, place, dates, page_url,
                                raw_costs=raw_cost, poster=poster_url, registration_info=registration_info,
                                raw_tags=unified_tags, age_restriction=age_restriction, raw_dates=raw_dates)

                self.listed_events.append(page_url)

    @staticmethod
    def _open_events_page(url):
        if "options" in url:
            events_page = ScrapHelper.get_parsed_js(url)
        else:
            events_page = ScrapHelper.get_parsed(url)
        return events_page

    @staticmethod
    def _get_tags_from_title(title):
        title = ScrapHelper.preprocess(title)
        if "мастер класс" in title:
            return ["мастер-класс"]
        return []

    def _get_unified_tags(self, relax_tags, event_categories) -> List[str]:
        unified_tags = []
        unified_tags.extend(self.mapper.map_relax(event_categories[0]))
        for tag in relax_tags:
            unified_tags.extend(self.mapper.map_relax(tag))

        return unified_tags

    @staticmethod
    def _get_raw_occurrences(event_full_info: bs4.element.PageElement):
        times_element = event_full_info.find("div", {"class": "schedule"})
        if not times_element:
            times_element = event_full_info.find("div", {"id": "theatre-table"})
        for date_time_element in times_element.find_all("div", {"class": "schedule__item"}):
            schedule_day = date_time_element.find("div", {"class": "schedule__day"})
            schedule_time = date_time_element.find("div", {"class": "schedule__seance"})
            time_string = None
            if schedule_time:
                time_string = ScrapHelper.get_string(schedule_time)
            day_string = ScrapHelper.get_string(schedule_day)
            if time_string:
                day_string += " в " + time_string
            yield day_string

    @staticmethod
    def _get_occurrences(event_full_info: bs4.element.PageElement):
        occurrences_by_place = {}
        times_element = event_full_info.find("div", {"class": "schedule"})
        place = RelaxScrapper._get_place(event_full_info)
        if place:
            occurrences_by_place[place.name] = (place, [])
        if not times_element:
            times_element = event_full_info.find("div", {"id": "theatre-table"})
        prev_date = None
        for date_time_element in times_element.find_all("div", {"class": "schedule__item"}):
            schedule_day = date_time_element.find("div", {"class": "schedule__day"})
            schedule_time = date_time_element.find("div", {"class": "schedule__seance"})
            schedule_place_element = date_time_element.find("div", {"class": "schedule__place"})
            place_name = None
            if schedule_place_element:
                place_name = ScrapHelper.get_string(schedule_place_element)

            if place_name:
                schedule_place = Place(place_name, None, None)
                if schedule_place.name not in occurrences_by_place:
                    occurrences_by_place[schedule_place.name] = (schedule_place, [])
            else:
                schedule_place = place

            time_string = None
            if schedule_time:
                time_string = ScrapHelper.get_string(schedule_time)
            day_string = ScrapHelper.get_string(schedule_day)
            date = DateInterpreter.parse_relax_date(day_string)
            time = DateInterpreter.parse_hour_minute(time_string)
            if date:
                prev_date = date
            else:
                date = prev_date
            if time:
                if type(date) == EventDateRange:
                    date.week_schedule = [time] * 7
                else:
                    date = DateInterpreter.get_datetime(*date, *time)
            else:
                if type(date) != EventDateRange:
                    date = DateInterpreter.get_date(*date)
            if type(date) == list:
                occurrences_by_place[schedule_place.name][1].extend(date)
            else:
                occurrences_by_place[schedule_place.name][1].append(date)
        return list(occurrences_by_place.values())

    @staticmethod
    def _get_title_and_link(event_element: bs4.element.PageElement) -> Tuple[str, str]:
        title_element = event_element.find("div", {"class": "schedule__event"}).find("a")
        event_title = ScrapHelper.get_string(title_element)
        event_link = title_element.attrs['href']
        return event_title, event_link

    @staticmethod
    def _get_events(day_schedule_element: bs4.element.PageElement):
        for event_element in day_schedule_element.find("div").find_all("div", {"class": "schedule__item"}):
            if 'schedule__item--ads' in event_element.attrs['class']:
                continue
            yield event_element

    @staticmethod
    def _get_date_string(day_schedule_element: bs4.element.PageElement):
        date_title = day_schedule_element.find("h5")
        return ScrapHelper.get_string(date_title)

    @staticmethod
    def _get_short_place(event_element: bs4.element.PageElement):
        place_element = event_element.find("a", {"class": "schedule__place-link link"})
        if not place_element:
            return None
        place_name = ScrapHelper.get_string(place_element)
        place_link = place_element.attrs['href']
        return Place(place_name, None, place_link)

    @staticmethod
    def _get_place(event_info_element: bs4.element.PageElement):
        place_element = event_info_element.find("div", {"class": "b-afisha_about-place_dscr"})
        if not place_element:
            return None
        place_link = place_element.find('a')
        place_name = ScrapHelper.get_string(place_link)
        place_link = place_link.attrs['href']
        place_address_element = place_element.find("p")
        place_address = None
        if place_address_element:
            place_address = place_address_element.find("a")
            if not place_address:
                place_address = place_address_element.find("span")
            place_address = ScrapHelper.get_string(place_address)

        return Place(place_name, place_address, place_link)

    @staticmethod
    def _get_description(event_info_element: bs4.element.PageElement):
        description_element = event_info_element.find('div', {"class": "b-afisha_cinema_description_text"})
        text = description_element.find_all(text=True)
        result = []
        for t in text:
            if str(t) == '\n':
                continue
            result.append(str(t))
        return "\n".join(result)

    def _get_metadata(self, event_info_element: bs4.element.PageElement) -> \
            Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
        event_cost = None
        event_genre = None
        working_hours = None
        registration_info = None
        age_restriction = None
        event_metadata_element = event_info_element.find("div", {"class": "b-afisha_cinema_description"})
        if event_metadata_element:
            event_metadata_table = event_metadata_element.find("table")
            for metadata_element in event_metadata_table.find_all("tr"):
                key_element, value_element = list(metadata_element.find_all("td"))
                key = ScrapHelper.get_string(key_element)
                value = ScrapHelper.get_string(value_element)
                if 'стоимость' in key.lower() or 'вход' in key.lower():
                    event_cost = value
                elif 'жанр' in key.lower():
                    event_genre = [v.strip().lower() for v in value.split(',')]
                elif 'инфолиния' in key.lower():
                    pass
                elif 'возрастное' in key.lower():
                    age_restriction = value.strip()
                elif 'дата' == key.lower():
                    continue
                elif 'точки продаж' == key.lower():
                    continue
                elif 'время работы' == key.lower():
                    working_hours = value
                elif 'регистрация' == key.lower():
                    registration_info = value
                elif 'внимание' in key.lower():
                    continue
                else:
                    self.logger.log_error("Relax metadata is unknown: %s" % key)
        return event_cost, event_genre, working_hours, registration_info, age_restriction


def detect_lang(text):
    by_letters = ['і', 'ў', 'шч']
    for by_letter in by_letters:
        if by_letter in text:
            return "by"
    return "ru"


def clean_text(text):
    text = text.replace('❗', '!')
    text = demoji.replace(text, ' ')
    for hashtag in hashtag_re.findall(text):
        text = text.replace(hashtag, " ")
    for c in specials:
        text = text.replace(c, ' ')

    lines = text.split('\n')
    lines = [line.strip() for line in lines if len(line.strip()) > 0]
    normal_lines = []
    for line in lines:
        words = [w for w in line.split(' ') if len(w) > 0]
        if line[-1] in punctuation_characters:
            normal_lines.append(line + ' ')
        elif "http" in words[-1]:
            normal_lines.append(line + ' . ')
        else:
            normal_lines.append(line + '. ')
    text = "".join(normal_lines)
    text = space_re.sub(" ", text)
    return text.strip()


class UnstructuredEvent:
    def __init__(self, text: str, url: str, timestamp: datetime,
                 title: str = None, poster_bytes: list = None, poster: str = None):
        self.title = title
        self.text = text
        self.url = url
        self.poster_bytes = poster_bytes
        self.timestamp = timestamp
        self.poster = poster


class TelegramEventFetcher:
    api_id = tg_credentials['api_id']
    api_hash = tg_credentials['api_hash']
    channels = [-1001149046377]

    bold_re = re.compile(r"(\*\*([^*]*)\*\*)")
    italic_re = re.compile(r"(__([^_]*)__)")

    def __init__(self, session_folder):
        self.session_file = os.path.join(session_folder, 'get_events')

    async def fetch_events(self, code_callback=None):
        client = TelegramClient(None, self.api_id, self.api_hash)
        await client.start(vk_credentials["phone_num"], code_callback=code_callback)
        try:
            for channel_id in self.channels:
                channel = await client.get_entity(channel_id)
                channel_name = channel.username
                messages = await client.get_messages(channel, limit=200)
                for m in messages:
                    raw_text = m.raw_text
                    if not raw_text:
                        continue

                    title = None
                    for value, inner_value in self.bold_re.findall(m.text):
                        title = inner_value.replace('\n', ' ').strip()
                        break

                    text = clean_text(raw_text)
                    url = "https://t.me/%s/%s" % (channel_name, m.id)
                    image_bytes = None
                    if 'MessageMediaPhoto' in str(type(m.media)):
                        image_bytes = await client.download_media(m, file=bytes, thumb=-1)

                    yield UnstructuredEvent(text, url, m.date, title=title, poster_bytes=image_bytes)
        finally:
            await client.log_out()


class VkEventFetcher:
    phone_num = vk_credentials["phone_num"]
    password = vk_credentials["password"]
    vk_communities = [57422635, 47596848, 8788887]
    club_re = re.compile(r"(\[club\d+\|([^\]]+)\])")

    stop_words = ["победитель", "выиграй", "выигрывай", "выигрывай"]

    def __init__(self, config_storage_folder):
        self.config_path = os.path.join(config_storage_folder, "vk_config.v2.json")

    def fetch_events(self) -> List[UnstructuredEvent]:
        vk_session = vk_api.VkApi(self.phone_num, self.password, config_filename=self.config_path)
        vk_session.auth()
        api = vk_session.get_api()
        for group_id in self.vk_communities:
            for offset in range(2):
                response = api.wall.get(owner_id=-group_id, count=100, filter='owner', offset=offset * 100)
                posts = response['items']
                for post in posts:
                    text = post['text']
                    post_id = post['id']
                    poster = None
                    if 'attachments' in post:
                        photo_attachments = [a for a in post['attachments'] if a['type'] == 'photo']
                        if len(photo_attachments) > 0:
                            attachment = photo_attachments[0]['photo']
                            image = max(attachment['sizes'], key=lambda p: p['height'])
                            poster = image['url']

                    url = "https://vk.com/wall-%s_%s" % (group_id, post_id)
                    timestamp = datetime.fromtimestamp(post['date'])
                    if not text or len(text.split(' ')) < 8:
                        continue
                    if any(s in text.lower() for s in self.stop_words):
                        continue

                    text = self.clean_text(text)
                    yield UnstructuredEvent(text, url, timestamp, poster=poster)

    def clean_text(self, text):
        for match in self.club_re.finditer(text):
            value, group_name = match.groups()
            text = text.replace(value, group_name)
        return clean_text(text)


def post_process_event(event: Event, logger, currency_markup, timestamp: datetime) -> Event:
    if event.raw_costs and len(event.raw_costs) > 0 and not event.cost:
        costs = []
        for raw_cost in event.raw_costs:
            markup = currency_markup.markup(raw_cost)
            if len(markup) == 0:
                logger.log_error("Cost couldn't be parsed: %s" % raw_cost)
                continue

            money_tags = [m for m in markup if m[0] == "MONEY"]
            if len(money_tags) > 0:
                currencies = [currency_markup.parse_currency(raw_cost[s:e]) for _, s, e in money_tags]
                currencies = [c for c in currencies if c]
                if len(currencies) != 0:
                    costs.extend(sorted(list(set([c for sublist in currencies for c in sublist]))))
                else:
                    logger.log_error("Cost couldn't be parsed: %s" % raw_cost)

            if any(m[0] == "FREE" for m in markup) and "free" not in event.event_tags:
                event.event_tags.append("free")
        event.cost = costs

    if event.raw_tags and len(event.raw_tags) > 0:
        for raw_tag in event.raw_tags:
            if raw_tag in event_type_mapping:
                event.event_tags.append(event_type_mapping[raw_tag])

    event.timestamp = timestamp
    return event


def parse_event(unstructured_event: UnstructuredEvent, classifier, extractor, uploader) -> Optional[Event]:
    event_types = classifier.predict_type(unstructured_event.text)
    if len(event_types) == 0:
        return None

    event = extractor.extract_entities_from_event(unstructured_event.text, unstructured_event.timestamp)
    if not event or not event.event_dates or len(event.event_dates) == 0:
        return None

    event.source = unstructured_event.url
    event.timestamp = unstructured_event.timestamp
    if unstructured_event.title:
        event.title = unstructured_event.title
    if unstructured_event.poster:
        event.poster = unstructured_event.poster
    if unstructured_event.poster_bytes and len(unstructured_event.poster_bytes) > 0:
        upload_result = uploader.upload_image(unstructured_event.poster_bytes)
        event.poster = upload_result.url
    event.event_tags = event_types
    return event
