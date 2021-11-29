# This is main module of project, used for interaction with telegram api
# TODO exceptions

import json
import asyncio
import logging

from decouple import config
from datetime import datetime  # TODO timezones

from helpers.requester import make_request
from weather_processor import get_current_weather

API_ACCESS_TOKEN = config('TG_TOKEN')
API_REQUEST_TPL = 'https://api.telegram.org/bot{}/{}'  # URL format: (API token, method name)
# TODAY_DATE = datetime.utcnow().date()

logger = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

updates_queue = list()
users = dict()


async def send_start_message(user_id: int):
    current_weather__button = {'text': 'Current weather'}
    keyboard = [[current_weather__button]]

    if user_id not in users:  # TODO
        keyboard[0].append({'text': 'Register'})

    reply_markup = {'keyboard': keyboard}
    await send_message(chat_id=user_id, text='Hi! How can i help you?', reply_markup=json.dumps(reply_markup))

command_mapping = {'/start': send_start_message}

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
            logger.debug(f'Received {len(update["result"])} updates from Telegram')
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

        if json_data.get('message'):  # reading place coords to get actual weather data
            message = json_data['message']

            username = message["from"]["username"]
            user_id = message["from"]["id"]

            logger.debug(f'Received message from user {username}: {user_id}')

            if message['text'] in command_mapping:
                logger.debug(f'Received {message["text"]} command from user {user_id}: {username}')
                await command_mapping[message['text']](user_id=user_id)
                logger.debug(f'Command {message["text"]} for user {user_id}: {username} executed')
                continue

            if'location' in message:

                lat = message['location']['latitude']
                lon = message['location']['longitude']

                logger.debug(f'Getting weather data for user {username}: {user_id}. Coordinates: lat: {lat}, lon: {lon}')

                weather_data = await get_current_weather(lat=lat, lon=lon)
                weather_info = f'Current weather data for <b>{weather_data["city"]}</b>\n' \
                               f'<b>Weather:</b> {weather_data["weather"]} {weather_data["icon"]}\n' \
                               f'<b>Temperature:</b> {weather_data["temp"]} \xb0C. <b>Feels like:</b> {weather_data["feels_like"]} \xb0C.\n' \
                               f'<b>Pressure:</b> {weather_data["pressure"]} P. <b>Humidity:</b> {weather_data["humidity"]} %.\n' \
                               f'<b>Visibility:</b> {weather_data["visibility"]} km. <b>Wind:</b> {weather_data["wind_speed"]} m/s.\n' \
                               f'<b>Sunrise:</b> {datetime.fromtimestamp(weather_data["sunrise"]).time()}. <b>Sunset:</b> {datetime.fromtimestamp(weather_data["sunset"]).time()}.'

                logger.debug(f'Received weather data for user {username}: {user_id}. Coordinates: lat: {lat}, lon: {lon}')
                await send_message(chat_id=message['chat']['id'], text=weather_info)
            else:
                logger.warning(f'Location data doesnt found in message {message}')
                await send_message(chat_id=message['chat']['id'], text='Sorry, i didn\'t find geo data in your message. Try to send it again.')


async def send_message(chat_id: int, text: str, reply_markup: str = None, data=None):  # TODO do we need to send files in messages?
    """Sending message to tg user"""
    api_url = API_REQUEST_TPL.format(API_ACCESS_TOKEN, 'sendMessage')
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}

    if reply_markup:
        data['reply_markup'] = reply_markup

    logger.debug(f'Sending message to chat {chat_id}')
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
        logger.debug('Started')
        run_bot()
    except KeyboardInterrupt:
        logger.debug('Stopped')
