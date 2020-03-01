from telethon import TelegramClient
import vk_api
from configuration import tg_credentials, vk_credentials


class TelegramEventFetcher:
    api_id = tg_credentials['api_id']
    api_hash = tg_credentials['api_hash']
    channels = [-1001149046377]

    def fetch_events(self):
        client = TelegramClient('anon', self.api_id, self.api_hash)
        events = []

        async def main():
            for channel_name in self.channels:
                channel = await client.get_entity(channel_name)
                messages = await client.get_messages(channel, limit=1000)
                for m in messages:
                    text = m.message
                    if text and 'і' not in text:
                        events.append(text)

        with client:
            client.loop.run_until_complete(main())
        return events


class VkEventFetcher:
    phone_num = vk_credentials["phone_num"]
    password = vk_credentials["password"]
    vk_communities = [57422635, 47596848, 8788887]

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
                    yield text
