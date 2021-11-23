# This is main module of project, used for interaction with telegram api
# TODO logging

import json
import asyncio

from decouple import config
from datetime import datetime  # TODO timezones

from helpers.requester import make_request
from weather_processor import get_current_weather

API_ACCESS_TOKEN = config('TG_TOKEN')
API_REQUEST_TPL = 'https://api.telegram.org/bot{}/{}'  # URL format: (API token, method name)
TODAY_DATE = datetime.utcnow().date()

updates_queue = list()
# TODO user's db

'''
async def make_weather_mailing():  # TODO
    while True:
        if datetime.utcnow().date() > TODAY_DATE:  # if we have next day TODO make it better
            for user in subscribers_list:
                pass  # TODO send weather data

            await asyncio.sleep(24 * 3600)  # one day
        else:
            await asyncio.sleep(3600)  # one hour
'''


async def get_updates():
    """Getting list of updates from tg"""
    updates_offset = 0

    while True:
        api_url = f'{API_REQUEST_TPL.format(API_ACCESS_TOKEN, "getUpdates")}?offset={updates_offset}'

        response = await make_request(url=api_url)
        update = json.loads(response)

        if update['result']:
            updates_offset = update['result'][-1]['update_id'] + 1
            updates_queue.extend(update['result'])

        await asyncio.sleep(2.0)


async def process_updates():
    """Processing updates, received from tg"""
    while True:
        if not updates_queue:
            await asyncio.sleep(3.0)
            continue

        json_data = updates_queue[0]
        updates_queue.remove(json_data)

        if 'location' in json_data['message']:  # reading place coords to get actual weather data

            weather_data = await get_current_weather(json_data['message']['location'])
            weather_info = f'Current weather data for <b>{weather_data["city"]}</b>\n' \
                           f'<b>Weather:</b> {weather_data["weather"]} {weather_data["icon"]}\n' \
                           f'<b>Temperature:</b> {weather_data["temp"]} \xb0C. <b>Feels like:</b> {weather_data["feels_like"]} \xb0C.\n' \
                           f'<b>Pressure:</b> {weather_data["pressure"]} P. <b>Humidity:</b> {weather_data["humidity"]} %.\n' \
                           f'<b>Visibility:</b> {weather_data["visibility"]} km. <b>Wind:</b> {weather_data["wind_speed"]} m/s.\n' \
                           f'<b>Sunrise:</b> {datetime.fromtimestamp(weather_data["sunrise"]).time()}. <b>Sunset:</b> {datetime.fromtimestamp(weather_data["sunset"]).time()}.'

            await send_message(chat_id=json_data['message']['chat']['id'], text=weather_info)
        else:
            await send_message(chat_id=json_data['message']['chat']['id'], text='Sorry, i didn\'t find geo data in your message. Try to send it again.')


async def send_message(chat_id: int, text: str, data=None):  # TODO do we need to send files in messages?
    """Sending message to tg user"""
    api_url = API_REQUEST_TPL.format(API_ACCESS_TOKEN, 'sendMessage')
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}

    await make_request(url=api_url, payload=data)


def run_bot():
    """Run tasks for receiving and processing updates"""
    ioloop = asyncio.get_event_loop()
    tasks = [ioloop.create_task(get_updates()), ioloop.create_task(process_updates())]
    wait_tasks = asyncio.wait(tasks)
    ioloop.run_until_complete(wait_tasks)
    ioloop.close()


if __name__ == '__main__':
    try:
        run_bot()
    except KeyboardInterrupt:
        print('Closed')
