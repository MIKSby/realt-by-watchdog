import os
import time
from typing import Optional

import requests
import sentry_sdk
from bs4 import BeautifulSoup, Tag
from dotenv import load_dotenv
from requests import Response
from user_agent import generate_user_agent

load_dotenv()

sentry_sdk.init(os.getenv('SENTRY_URL'), traces_sample_rate=1.0)


class TelegramApi:
    def __init__(self, token: str) -> None:
        self.tg_api_url = f'https://api.telegram.org/bot{token}/'

    def get_updates(self) -> Response:
        return requests.get(url=f'{self.tg_api_url}getUpdates')

    def send_message(self, chat_id: str, text: str) -> Response:
        return requests.post(url=f'{self.tg_api_url}sendMessage',
                             data={'chat_id': chat_id, 'text': text})


class RealtWatchDog:
    def __init__(self, url, tg_token):
        self.state: Optional[str] = None
        self.default_parser = 'html.parser'
        self.url = url
        self._tg_token = tg_token
        self._alarm_message = os.getenv('ALARM_MESSAGE')

    def get_content(self):
        while True:
            try:
                response = requests.get(self.url, headers={'User-Agent': generate_user_agent()})
                if response.ok:
                    return response.text
            except Exception as exc:
                sentry_sdk.capture_exception(exc)
            time.sleep(200)

    def soup(self, content):
        return BeautifulSoup(content, self.default_parser)

    def start(self):
        self.state = self.extract()
        time.sleep(30)
        while True:
            if self.is_new_available():
                self.tg_alarm()
                self.sentry_alarm()
            time.sleep(60 * 60)

    def tg_alarm(self):
        tg = TelegramApi(self._tg_token)
        tg.send_message(chat_id=os.getenv('TG_CHAT_ID'), text=os.getenv('ALARM_MESSAGE'))

    def extract(self):
        content = self.get_content()
        soup = self.soup(content)
        tag: Tag = soup.findAll('div', {'class': 'info-mini-block'})[1]
        return tag.text.split('Опубликовано')[1]

    def is_new_available(self) -> bool:
        return self.state != self.extract()

    def sentry_alarm(self):
        sentry_sdk.capture_message(self._alarm_message)


if __name__ == '__main__':
    dog = RealtWatchDog(
        os.getenv('TARGET_URL'),  # example: https://realt.by/rent/flat-for-long/object/1111111/
        os.getenv('TG_TOKEN'),
    )
    dog.start()
