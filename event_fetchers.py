from telethon import TelegramClient
import vk_api
from configuration import tg_credentials, vk_credentials
from translators import GoogleTranslator
import re
import demoji


space_re = re.compile(r"\s+")
dot_re = re.compile(r"\.+")
puncts = ['.', ',', ':', '!', '?', ';', '/']
specials = ['•', "►"]
hashtag_re = re.compile(r"(#\w+)")


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


