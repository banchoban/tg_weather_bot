import json
import asyncio

from decouple import config
from datetime import datetime  # TODO timezones

from helpers.requester import make_request
from weather_processor import get_current_weather

API_ACCESS_TOKEN = config('TG_TOKEN')
API_REQUEST_TPL = 'https://api.telegram.org/bot{}/{}'  # URL format: (API token, method name)
TODAY_DATE = datetime.utcnow().date()

subscribers_list = [337886033]


async def make_weather_mailing():  # TODO
    while True:
        if datetime.utcnow().date() > TODAY_DATE:  # if we have next day TODO make it better
            for user in subscribers_list:
                pass  # TODO send weather data

            await asyncio.sleep(24 * 3600)  # one day
        else:
            await asyncio.sleep(3600)  # one hour


async def get_updates():
    """Getting list of updates from tg"""
    updates_offset = 0

    while True:
        api_url = f'{API_REQUEST_TPL.format(API_ACCESS_TOKEN, "getUpdates")}?offset={updates_offset}'

        response = await make_request(url=api_url)
        update = json.loads(response)

        if update['result']:
            updates_offset = update['result'][-1]['update_id']
            await process_update(update['result'][-1])

        await asyncio.sleep(2.0)


async def process_update(json_data: dict):
    if 'location' in json_data['message']:

        weather_data = await get_current_weather(json_data['message']['location'])
        await send_message(chat_id=json_data['message']['chat']['id'], text=json.dumps(weather_data))
    else:
        await send_message(chat_id=json_data['message']['chat']['id'], text='Sorry, i didn\'t find geo data in your message. Try to send it again.')


async def send_message(chat_id: int, text: str, data=None):  # TODO do we need to send files in messages?
    api_url = API_REQUEST_TPL.format(API_ACCESS_TOKEN, 'sendMessage')
    data = {'chat_id': chat_id, 'text': text}

    await make_request(url=api_url, payload=data)


def run_bot():
    ioloop = asyncio.get_event_loop()
    tasks = [ioloop.create_task(get_updates())]
    wait_tasks = asyncio.wait(tasks)
    ioloop.run_until_complete(wait_tasks)
    ioloop.close()


if __name__ == '__main__':
    run_bot()
