import requests
import bs4
import re
from time import sleep
from event_models import *
from interpreters import DateInterpreter


class ScrapHelper:
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
        return re.sub(r'\s+', ' ', element_string).strip()


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

    def list_events(self):
        self.listed_events = []
        for category, link in self.categories.items():
            for event in self._list_events_from_old_page(link, category):
                yield event
        for category, link in self.new_page_categories.items():
            for event in self._list_events_from_new_page(link, category):
                yield event

    def _list_events_from_new_page(self, page_url, category):
        for event_element in self._get_event_elements_from_new_page(page_url):
            event_url, tags = self._parse_media_element(event_element)
            if event_url in self.listed_events:
                continue

            event_title = self._get_new_event_title(event_element)
            is_free = self._is_free_event(event_element)
            if is_free:
                tags.append("free")

            description, occurrences, image_url = self._parse_event_page(event_url)
            for place_name, place_and_dates in occurrences.items():
                place = place_and_dates[0][0]
                dates = [d[1] for d in place_and_dates]
                yield Event(event_title, "", image_url, description, place, category, tags, [], dates, event_url)
            self.listed_events.append(event_url)

    def _list_events_from_old_page(self, page_url, category):
        for event_element in self._get_event_elements(page_url):
            event_title, event_link, tags = self._parse_old_title_element(event_element)
            if event_link in self.listed_events:
                continue

            description, occurrences, image_url = self._parse_event_page(event_link)
            for place_name, places_and_dates in occurrences.items():
                place = places_and_dates[0][0]
                dates = [d[1] for d in places_and_dates]
                yield Event(event_title, "", image_url, description, place, category, tags, [], dates, event_link)
            self.listed_events.append(event_link)

    @staticmethod
    def _parse_old_title_element(event_element):
        title_and_time = event_element.find('div', {'class': 'event-item-i js-film-list__li'})
        title_element = title_and_time \
            .find('div', {'class': 'item-header'}) \
            .find('div', {'class': 'item-header-i'})
        tags = TutByScrapper._get_tags_old(title_element)
        event_title, event_link = TutByScrapper._get_title(title_element)
        event_label_element = title_and_time \
            .find('div', {'class': 'item-header'}) \
            .find('div', {'class': 'event-label'})

        if event_label_element:
            free_element = event_label_element.find("a", {"class": "free-event"})
            if free_element:
                tags.append("free")
        return event_title, event_link, tags

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
        tags = TutByScrapper._get_tags(media_element)
        return event_url, tags

    @staticmethod
    def _get_new_event_title(event_element):
        name_element = event_element.find("a", {"class": "name"})
        return ScrapHelper.get_string(name_element)

    @staticmethod
    def _get_tags(media_element: bs4.element.PageElement):
        tags_element = media_element.find("p")
        tags = []
        if tags_element:
            for child in tags_element.children:
                if type(child) == bs4.element.NavigableString:
                    tags.append(str(child))
        return tags

    @staticmethod
    def _is_free_event(event_element: bs4.element.PageElement):
        free_element = event_element.find("div", {"class": "txt"}).find("a", {"class": "free-event"})
        if free_element:
            return True
        return False

    @staticmethod
    def _get_tags_old(title_element):
        tags_element = title_element.find('p', {'class': 'tag-place'})
        tags = []
        if tags_element:
            tag_elements = tags_element.find_all('a')
            for tag_element in tag_elements:
                tag = tag_element.contents[0]
                tag = re.sub(r'\s+', ' ', tag).strip()
                tags.append(tag)
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
        description = TutByScrapper._get_event_description(event_page)
        occurrences = list(TutByScrapper._parse_occurrences(event_page))
        occurrences_by_places = {}
        for place, date in occurrences:
            if place.place_name not in occurrences_by_places:
                occurrences_by_places[place.place_name] = []
            occurrences_by_places[place.place_name].append((place, date))

        image_url = TutByScrapper._get_image(event_page)
        return description, occurrences_by_places, image_url

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
                yield place, EventDateRange(*day_range, week_schedule)
            else:
                date, times = TutByScrapper._get_exact_date(day_element, times_element)
                if not date:
                    date = prev_date
                prev_date = date
                for time in times:
                    yield place, DateInterpreter.get_date(*date, *time)

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


class CityDogScrapper:
    afisha_page = "https://citydog.by/afisha/"
    vedy_page = "https://citydog.by/vedy/#events"
    listed_events = []

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
            event_type = self._get_vedy_category(event_element)
            image_url = self._get_image_url(event_element, "vedyMain-itemImg")
            labels = self._get_vedy_labels(event_element)
            info_element = event_element.find("div", {"class": "vedyMain-itemInfo"})
            event_title, event_link = self._get_title(info_element)
            if event_link in self.listed_events:
                continue
            short_description = self._get_short_description(info_element)
            header_element, description_element = self._get_full_vedy_info_element(event_link)
            date = self._get_vedy_date(header_element)
            date = DateInterpreter.parse_citydog_date(date)
            if type(date) != list:
                date = [date]
            place = self._get_places(header_element)[0]
            event_source, event_cost, register_link = self._get_event_additional_info(header_element)
            full_description = self._get_full_description(description_element)
            tags = self._get_vedy_tags(description_element)
            tags.extend(labels)
            metadata = {"cost": event_cost, "reg": register_link, "source": event_source}
            yield Event(event_title, short_description, image_url, full_description,
                        place, event_type, tags, metadata, date, event_link)

            self.listed_events.append(event_link)

    def list_afisha_events(self):
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
            date = self._get_date(info_element, "afishaMain-itemDate")
            date = DateInterpreter.parse_citydog_date(date)
            if type(date) != list:
                date = [date]
            short_description = self._get_short_description(info_element)
            event_page, event_info_element = self._get_full_event_info_element(event_link)
            places = self._get_places(event_info_element)
            event_source, event_cost, registration = self._get_event_additional_info(event_info_element)
            full_description = self._get_full_description(event_page)
            occurrences = self._get_occurrences(event_page)
            metadata = {"cost": event_cost, "reg": registration, "source": event_source}
            if len(occurrences) > 0:
                for place_names, dates in occurrences.items():
                    place = dates[0]
                    dates = dates[1:]
                    yield Event(event_title, short_description, image_url, full_description, place, event_type, [],
                                metadata, dates, event_link)
            else:
                for place in places:
                    yield Event(event_title, short_description, image_url, full_description, place, event_type, [],
                                metadata, date, event_link)

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
            result.append(tag_element.text.strip())
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
        return event_element.attrs['class'][1]

    @staticmethod
    def _get_vedy_category(event_element: bs4.element.PageElement):
        return event_element.attrs['class'][2]

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
        ("concert", "https://afisha.relax.by/conserts/minsk/"),
        ("party", "https://afisha.relax.by/clubs/minsk/"),
        ("expo",  "https://afisha.relax.by/expo/minsk/"),
        ("event", "https://afisha.relax.by/event/minsk/"),
        ("sport", "https://afisha.relax.by/sport/minsk/"),
    ]

    # for education for exclude "courses" genre
    # 1923 - интенсив 1783 - конференция 2263 - кулинарный мастер класс 634 - лекция 635 - мастер класс 2513 - митап
    # 636 - семинар 2283 - форум
    pages.extend([
        ("education", "https://afisha.relax.by/education/minsk/#?options%5B101%5D=" + str(genre_id))
        for genre_id in [1923, 1783, 2263, 634, 635, 2513, 636, 637, 2283]])

    listed_events = []

    def list_events(self):
        self.listed_events = []
        for event_type, url in self.pages:
            schedule_element = None
            while not schedule_element:
                events_page = self._open_events_page(url)
                schedule_element = events_page.find("div", {"id": "append-shcedule"})
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
                    event_cost, event_genre, event_info_number, working_hours, registration_info \
                        = self._get_metadata(event_full_info)
                    occurrences = self._get_occurrences(event_full_info)
                    description = self._get_description(event_full_info)
                    tags = []
                    if event_genre:
                        tags.extend(event_genre)

                    metadata = {
                        "cost": event_cost,
                        "reg": registration_info,
                        "number": event_info_number,
                        "working":  working_hours
                    }

                    for place_name, dates in occurrences.items():
                        place = dates[0]
                        dates = dates[1:]
                        yield Event(event_title, "", event_image_url, description, place, event_type,
                                    tags, metadata, dates, event_link)

                    self.listed_events.append(event_link)

    @staticmethod
    def _open_events_page(url):
        if "options" in url:
            events_page = ScrapHelper.get_parsed_js(url)
        else:
            events_page = ScrapHelper.get_parsed(url)
        return events_page

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
                    event_genre = value.split(',')
                elif 'инфолиния' in key.lower():
                    event_info_number = value
                elif 'возрастное' in key.lower():
                    continue
                elif 'дата' == key.lower():
                    continue
                elif 'точки продаж' == key.lower():
                    continue
                elif 'время работы' == key.lower():
                    working_hours = value
                elif 'регистрация' == key.lower():
                    registration_info = value
                else:
                    raise Exception("Metadata is unknown: %s" % key)
        return event_cost, event_genre, event_info_number, working_hours, registration_info
