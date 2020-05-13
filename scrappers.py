import requests
import bs4
import vk_api
import re
import demoji

from time import sleep
from models import *
from interpreters import DateInterpreter, TagMapper
from telethon import TelegramClient
from configuration import tg_credentials, vk_credentials
from translators import GoogleTranslator

space_re = re.compile(r"\s+")
dot_re = re.compile(r"\.+")
puncts = ['.', ',', ':', '!', '?', ';', '/']
specials = ['•', "►"]
hashtag_re = re.compile(r"(#\w+)")


class ScrapHelper:
    RE_COMBINE_WHITESPACE = re.compile(r"\s+")
    RE_HYPHENS = re.compile(r"[\-‒–—―]")

    @staticmethod
    def get_parsed(url):
        response = requests.get(url)
        return bs4.BeautifulSoup(response.content, 'lxml')

    @staticmethod
    def get_parsed_js(url):
        response = requests.post('http://192.168.99.100:8050/render.html', json={
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
    categories = {
        "concert": "https://afisha.tut.by/concert/",
        "party": "https://afisha.tut.by/party/",
        "theatre": "https://afisha.tut.by/theatre/",
        "other": "https://afisha.tut.by/other/"
    }
    new_page_categories = {
        "exhibition": "https://afisha.tut.by/exhibition/"
    }
    listed_events = []
    mapper = TagMapper()

    def list_events(self):
        print("List tutby")
        self.listed_events = []
        for category, link in self.categories.items():
            print(link)
            for event in self._list_events_from_old_page(link, category):
                yield event
        for category, link in self.new_page_categories.items():
            print(link)
            for event in self._list_events_from_new_page(link, category):
                yield event

    def _list_events_from_new_page(self, page_url, category):
        for event_element in self._get_event_elements_from_new_page(page_url):
            event_url = self._parse_media_element(event_element)
            if event_url in self.listed_events:
                continue

            event_title = self._get_new_event_title(event_element)
            description, occurrences, image_url, tags, raw_occurrences = self._parse_event_page(event_url)
            age = self._get_age_restriction(tags)
            unified_tags = []
            unified_tags.extend(self.mapper.map_tut(category))
            for tag in tags:
                unified_tags.extend(self.mapper.map_tut(tag))

            for place_name, place_and_dates in occurrences.items():
                place = place_and_dates[0][0]
                dates = [d[1] for d in place_and_dates]
                yield Event(event_title, "", image_url, description, place, unified_tags, dates, event_url,
                            age_restriction=age, raw_dates=raw_occurrences)
            self.listed_events.append(event_url)

    def _list_events_from_old_page(self, page_url, category):
        for event_element in self._get_event_elements(page_url):
            try:
                event_title, event_link = self._parse_old_title_element(event_element)
                if event_link in self.listed_events:
                    continue

                description, occurrences, image_url, tags, raw_occurrences = self._parse_event_page(event_link)
                age = self._get_age_restriction(tags)
                unified_tags = []
                unified_tags.extend(self.mapper.map_tut(category))
                for tag in tags:
                    unified_tags.extend(self.mapper.map_tut(tag))
                for place_name, places_and_dates in occurrences.items():
                    place = places_and_dates[0][0]
                    dates = [d[1] for d in places_and_dates]
                    yield Event(event_title, "", image_url, description, place, unified_tags, dates, event_link,
                                age_restriction=age, raw_dates=raw_occurrences)
                self.listed_events.append(event_link)
            except Exception as e:
                print(e)
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
    def _get_event_elements(page_url):
        events_page = ScrapHelper.get_parsed(page_url)
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
    def _parse_event_page(event_link):
        event_page = ScrapHelper.get_parsed(event_link)
        description = TutByScrapper._get_event_description(event_page).replace("О событии", "").strip()
        occurrences = list(TutByScrapper._parse_occurrences(event_page))
        occurrences_by_places = {}
        for place, date in occurrences:
            if place.place_name not in occurrences_by_places:
                occurrences_by_places[place.place_name] = []
            occurrences_by_places[place.place_name].append((place, date))

        raw_occurrences = list(TutByScrapper._get_raw_occurrences(event_page))
        image_url = TutByScrapper._get_image(event_page)
        tags = TutByScrapper._get_tags(event_page)
        return description, occurrences_by_places, image_url, tags, raw_occurrences

    @staticmethod
    def _get_raw_occurrences(event_page):
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
    def _parse_occurrences(event_page):
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
                date = TutByScrapper._get_broad_date(day_element)
                day_range = DateInterpreter.parse_tutby_date_range(date[0])
                week_schedule = DateInterpreter.parse_tutby_week_time_schedule(date[1])
                date_range = EventDateRange(*day_range, week_schedule)
                yield place, date_range
            else:
                date, times = TutByScrapper._get_exact_date(day_element, times_element)
                if not date:
                    date = prev_date
                prev_date = date
                for time in times:
                    yield place, DateInterpreter.get_date(*date, *time)

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
    def _get_exact_date(day_element, times_element):
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

        return [date, times]

    @staticmethod
    def _get_broad_date(day_element):
        values = list(day_element.children)[0].split(',')
        if len(values) != 2:
            raise Exception("Date string cannot be read")
        date_range, time_range = values
        return [date_range.strip(), time_range.strip()]

    @staticmethod
    def _get_place_from_occurrence(occurrence_element):
        place_element = occurrence_element.find("a", {"class": "b-shedule-place"})
        items = list(place_element.children)
        place_name = str(items[0]).strip()
        place_address = items[1].text.strip()
        place_url = place_element.attrs['href']
        return EventPlace(place_name, place_address, place_url)

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
            yield EventPlace(place_name, place_address, place_url)

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
    def _get_event_description(event_page):
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
        return "\n".join(result)

    @staticmethod
    def _get_image(event_page):
        img_element = event_page.find("img", {"class": "main_image"})
        return img_element.attrs['src']

    @staticmethod
    def _get_age_restriction(tags):
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
    mapper = TagMapper()

    def list_events(self):
        print("List events from citydog.by")
        self.listed_events = []
        for event in self.list_afisha_events():
            yield event
        for event in self.list_vedy_events():
            yield event

    def list_vedy_events(self):
        print(self.vedy_page)
        events_page = ScrapHelper.get_parsed_js(self.vedy_page)
        events_block = events_page.find('div', {'class': 'vedy-contentCol'}).find("div")
        for event_element in events_block.find_all("div", {"class": "vedyMain-item"}):
            event_type = self._get_vedy_category(event_element)
            image_url = self._get_image_url(event_element, "vedyMain-itemImg")
            labels = self._get_vedy_labels(event_element)
            info_element = event_element.find("div", {"class": "vedyMain-itemInfo"})
            event_title, event_link = self._get_title(info_element)
            if event_link in self.listed_events:
                continue
            short_description = self._get_short_description(info_element)
            header_element, description_element = self._get_full_vedy_info_element(event_link)
            date_string = self._get_vedy_date(header_element)
            dates = DateInterpreter.parse_citydog_date(date_string)
            date_string = date_string.replace("   |   ", " в ")
            places = self._get_places(header_element)
            if len(places) > 0:
                place = places[0]
            else:
                place = EventPlace("", "", "")
            event_source, event_cost, register_link = self._get_event_additional_info(header_element)
            full_description = self._get_full_description(description_element)
            tags = self._get_vedy_tags(description_element)
            tags.extend(labels)
            unified_tags = []
            unified_tags.extend(self.mapper.map_cd(event_type))
            for tag in tags:
                unified_tags.extend(self.mapper.map_cd(tag))
            yield Event(event_title, short_description, image_url, full_description,
                        place, unified_tags, dates, event_link,
                        cost=event_cost, info=event_source, registration_info=register_link, raw_dates=[date_string])

            self.listed_events.append(event_link)

    def list_afisha_events(self):
        print(self.afisha_page)
        events_page = ScrapHelper.get_parsed(self.afisha_page)
        events_block = events_page.find('div', {'class': 'afishaMain-items'})
        for event_element in events_block.children:
            if type(event_element) == bs4.element.NavigableString:
                continue

            event_type = self._get_category(event_element)
            image_url = self._get_image_url(event_element, "afishaMain-itemImg")
            info_element = event_element.find("div", {"class": "afishaMain-itemInfo"})
            event_title, event_link = self._get_title(info_element)
            if event_link in self.listed_events:
                continue
            date_string = self._get_date(info_element, "afishaMain-itemDate")
            date = DateInterpreter.parse_citydog_date(date_string)
            if type(date) != list:
                date = [date]
            date_string = date_string.replace("   |   ", " в ")
            short_description = self._get_short_description(info_element)
            event_page, event_info_element = self._get_full_event_info_element(event_link)
            places = self._get_places(event_info_element)
            event_source, event_cost, registration = self._get_event_additional_info(event_info_element)
            full_description = self._get_full_description(event_page)
            occurrences = self._get_occurrences(event_page)
            raw_occurrences = list(self._get_raw_occurrences(event_page))
            raw_occurrences.append(date_string)
            unified_tags = []
            unified_tags.extend(self.mapper.map_cd(event_type))
            if len(occurrences) > 0:
                for place_names, dates in occurrences.items():
                    place = dates[0]
                    dates = dates[1:]
                    yield Event(event_title, short_description, image_url, full_description, place, unified_tags,
                                dates, event_link, cost=event_cost, registration_info=registration, info=event_source,
                                raw_dates=raw_occurrences)
            else:
                for place in places:
                    yield Event(event_title, short_description, image_url, full_description, place, unified_tags,
                                date, event_link, cost=event_cost, registration_info=registration, info=event_source,
                                raw_dates=raw_occurrences)

            self.listed_events.append(event_link)

    @staticmethod
    def _get_vedy_date(header_element: bs4.element.PageElement):
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
    def _get_vedy_labels(event_element: bs4.element.PageElement):
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
    def _get_vedy_tags(description_element: bs4.element.PageElement):
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
    def _get_full_vedy_info_element(vedy_page_url: str):
        header_element = None
        description_element = None
        while not description_element and not header_element:
            sleep(1)
            event_page = ScrapHelper.get_parsed_js(vedy_page_url)
            header_element = event_page.find("div", {"class": "vedyPage-header"})
            description_element = event_page.find("div", {"class": "_vedyPage-Description"})
        return header_element, description_element

    @staticmethod
    def _get_short_description(info_element: bs4.element.PageElement):
        return info_element.find("p").text.strip()

    @staticmethod
    def _get_title(info_element: bs4.element.PageElement):
        title_element = info_element.find("h3").find("a")
        title = title_element.text
        event_link = title_element.attrs['href']
        return title, event_link

    @staticmethod
    def _get_category(event_element: bs4.element.PageElement):
        return event_element.attrs['class'][1].strip().lower()

    @staticmethod
    def _get_vedy_category(event_element: bs4.element.PageElement):
        return event_element.attrs['class'][2].strip().lower()

    @staticmethod
    def _get_image_url(event_element: bs4.element.PageElement, class_name):
        image_element = event_element.find("div", {"class": class_name})
        image_url = image_element.find("img").attrs['src']
        return image_url

    @staticmethod
    def _get_date(info_element: bs4.element.PageElement, class_name: str):
        date_element = info_element.find("div", {"class": class_name})
        return date_element.text.strip()

    @staticmethod
    def _get_event_additional_info(event_info_element: bs4.element.PageElement):
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
    def _get_full_description(event_page: bs4.element.PageElement):
        full_description_element = event_page.find("div", {"class": "afishaPost-Description-text"})
        return full_description_element.text.strip()

    @staticmethod
    def _get_places(event_info_element: bs4.element.PageElement):
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
            places.append(EventPlace(place_name, place_address, None))
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
                    if place.place_name not in occurrences_by_place:
                        occurrences_by_place[place.place_name] = [place]
                    sessions = CityDogScrapper._get_sessions(place_element)
                    for time in sessions:
                        time = DateInterpreter.parse_hour_minute(time)
                        date = DateInterpreter.get_date(*day, *time)
                        if type(date) == list:
                            occurrences_by_place[place.place_name].extend(date)
                        else:
                            occurrences_by_place[place.place_name].append(date)
        return occurrences_by_place

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
        place = EventPlace(place_name, place_address, None)
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
    mapper = TagMapper()

    def list_events(self):
        print("List events from Relax")
        self.listed_events = []
        for event_types, url in self.pages:
            print(url)
            schedule_element = None
            while not schedule_element:
                events_page = self._open_events_page(url)
                schedule_element = events_page.find("div", {"id": "append-shcedule"})
            for event in self._list_events(schedule_element, event_types):
                yield event

    def _list_events(self, schedule_element, event_types):
        day_schedules = schedule_element.find_all("div", {"class": "schedule__list"})
        for day_schedule_element in day_schedules:
            event_elements = self._get_events(day_schedule_element)
            for event_element in event_elements:
                event_title, event_link = self._get_title_and_link(event_element)
                if event_link in self.listed_events:
                    continue
                event_page = ScrapHelper.get_parsed(event_link)
                event_image_url = event_page.find("img", {"class": "b-afisha-event__image"}).attrs['src']
                event_full_info = event_page.find("div", {"class": "b-afisha-layout-theater_full"})
                event_cost, event_genre, event_info_number, working_hours, registration_info, age_restriction \
                    = self._get_metadata(event_full_info)
                occurrences = self._get_occurrences(event_full_info)
                raw_occurrences = list(self._get_raw_occurrences(event_full_info))
                description = self._get_description(event_full_info)
                tags = []
                if event_genre:
                    tags.extend(event_genre)
                tags.extend(self._get_tags_from_title(event_title))
                tags.extend(event_types[1:])

                for place_name, dates in occurrences.items():
                    place = dates[0]
                    dates = dates[1:]
                    if working_hours:
                        raw_occurrences.append(working_hours)
                        schedule = DateInterpreter.parse_relax_schedule(working_hours)
                        if not schedule:
                            continue
                        if type(schedule[0]) == EventDateRange:
                            dates = schedule
                        elif type(dates[0]) == EventDateRange and len(dates) == 1:
                            dates[0].week_schedule = schedule

                    unified_tags = []
                    unified_tags.extend(self.mapper.map_relax(event_types[0]))
                    for tag in tags:
                        unified_tags.extend(self.mapper.map_relax(tag))

                    yield Event(event_title, "", event_image_url, description, place, unified_tags, dates, event_link,
                                cost=event_cost, registration_info=registration_info,
                                info=event_info_number, age_restriction=age_restriction, raw_dates=raw_occurrences)

                self.listed_events.append(event_link)

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
            occurrences_by_place[place.place_name] = [place]
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
                schedule_place = EventPlace(place_name, None, None)
                if schedule_place.place_name not in occurrences_by_place:
                    occurrences_by_place[schedule_place.place_name] = [schedule_place]
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
                    date = DateInterpreter.get_date(*date, *time)
            else:
                if type(date) != EventDateRange:
                    date = DateInterpreter.get_day(*date)
            if type(date) == list:
                occurrences_by_place[schedule_place.place_name].extend(date)
            else:
                occurrences_by_place[schedule_place.place_name].append(date)
        return occurrences_by_place

    @staticmethod
    def _get_title_and_link(event_element: bs4.element.PageElement):
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
        return EventPlace(place_name, None, place_link)

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

        return EventPlace(place_name, place_address, place_link)

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

    @staticmethod
    def _get_metadata(event_info_element: bs4.element.PageElement):
        event_cost = None
        event_genre = None
        event_info_number = None
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
                    event_info_number = value
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
                    raise Exception("Metadata is unknown: %s" % key)
        return event_cost, event_genre, event_info_number, working_hours, registration_info, age_restriction


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
    lines = [l.strip() for l in lines if len(l.strip()) > 0]
    normal_lines = []
    for l in lines:
        words = [w for w in l.split(' ') if len(w) > 0]
        if l[-1] in puncts:
            normal_lines.append(l + ' ')
        elif "http" in words[-1]:
            normal_lines.append(l + ' . ')
        else:
            normal_lines.append(l + '. ')
    text = "".join(normal_lines)
    text = space_re.sub(" ", text)
    return text.strip()


class TelegramEventFetcher:
    api_id = tg_credentials['api_id']
    api_hash = tg_credentials['api_hash']
    channels = [-1001149046377]

    time_emoji = '🕰'
    place_emoji = '🏛'

    bold_re = re.compile(r"(\*\*([^*]*)\*\*)")
    italic_re = re.compile(r"(__([^_]*)__)")

    translator = GoogleTranslator()

    async def fetch_events(self):
        async with TelegramClient('anon', self.api_id, self.api_hash) as client:
            for channel_name in self.channels:
                channel = await client.get_entity(channel_name)
                messages = await client.get_messages(channel, limit=2000)
                for m in messages:
                    raw_text = m.text
                    if not raw_text:
                        continue
                    text = m.message

                    text = text.replace(self.time_emoji, "<TIME>")
                    text = text.replace(self.place_emoji, "<PLACE>")

                    if detect_lang(text) == "by":
                        continue
                        text = self.translator.translate_from_bel(text)
                        raw_text = self.translator.translate_from_bel(raw_text)

                    title = None
                    times = []
                    place = None

                    for value, inner_value in self.bold_re.findall(raw_text):
                        title = inner_value.replace('\n', ' ').strip()
                        break

                    lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 0]

                    for i, l in enumerate(lines):
                        if "<TIME>" in l:
                            start_index = l.find("<TIME>")
                            time = l[start_index + len("<TIME>"):].strip()
                            times.append(time)
                        elif "<PLACE>" in l:
                            start_index = l.find("<PLACE>")
                            place = l[start_index + len("<PLACE>"):].strip()
                    if not title:
                        title = lines[0]
                    if not place:
                        continue

                    text = text.replace("<TIME>", "").replace("<PLACE>", "")

                    if title:
                        start = text.find(title)
                        end = start + len(title)
                        title = (start, end)
                    if len(times) > 0:
                        time_tags = []
                        for time in times:
                            start = text.find(time)
                            end = start + len(time)
                            time_tags.append((start, end))
                    if place:
                        start = text.find(place)
                        end = start + len(place)
                        place = (start, end)

                    yield {"title": title, "dates": time_tags, "place": place, "text": text}


class VkEventFetcher:
    phone_num = vk_credentials["phone_num"]
    password = vk_credentials["password"]
    vk_communities = [57422635, 47596848, 8788887]
    club_re = re.compile(r"(\[club\d+\|([^\]]+)\])")

    stop_words = ["победитель", "выиграй", "выигрывай"]

    def fetch_events(self):
        vk_session = vk_api.VkApi(self.phone_num, self.password)
        vk_session.auth()
        api = vk_session.get_api()
        for group_id in self.vk_communities:
            for offset in range(10):
                response = api.wall.get(owner_id=-group_id, count=100, filter='owner', offset=offset * 100)
                posts = response['items']
                for post in posts:
                    text = post['text']
                    if not text or len(text.split(' ')) < 8:
                        continue
                    if any(s in text.lower() for s in self.stop_words):
                        continue
                    yield {"text": self.clean_text(text), "place": None, "date": None}

    def clean_text(self, text):
        for match in self.club_re.finditer(text):
            value, group_name = match.groups()
            text = text.replace(value, group_name)
        return clean_text(text)
