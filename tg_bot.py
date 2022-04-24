# This is main module of project, used for interaction with telegram api
# TODO move methods into class?

import json
import asyncio
import logging

from decouple import config
from datetime import datetime  # TODO timezones

from helpers.requester import make_request
from weather_processor import get_current_weather
from database_processor import DBProcessor

API_ACCESS_TOKEN = config('TG_TOKEN')
API_REQUEST_TPL = 'https://api.telegram.org/bot{}/{}'  # URL format: (API token, method name)
# TODAY_DATE = datetime.utcnow().date()
DBProcessor = DBProcessor('sqlite3.db')


logger = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

updates_queue = list()
# TODO users db


async def send_start_msg(user_id: int):  # todo remove if
    """Sending greeting message to user"""

    reply_markup = {'keyboard': set_default_kb(user_id), 'resize_keyboard': True}
    user_data = DBProcessor.get_user_from_db(user_id)

    if user_data:
        if user_data[2]:
            text = f'Hi, {user_data[2]}! How can i help you?'
        else:
            text = f'Hi, {user_data[1]}! How can i help you?'
    else:
        text = f'Hi! How can i help you?'

    await send_message(chat_id=user_id, text=text, reply_markup=json.dumps(reply_markup))


async def send_register_msg(user_id: int):
    """Sending registration request to current user and setting up tg keyboard for interaction with bot"""

    if DBProcessor.get_user_from_db(user_id):
        logger.warning(f'User {user_id} already exists in db')
        reply_markup = {'keyboard': set_default_kb(user_id), 'resize_keyboard': True}
        await send_message(chat_id=user_id, text='You are already registered!', reply_markup=json.dumps(reply_markup))
        return

    location_button = {'text': 'Share location', 'request_location': True}
    keyboard = [[location_button]]
    reply_markup = {'keyboard': keyboard, 'resize_keyboard': True}

    logger.debug(f'Requesting user {user_id} to send location data')
    await send_message(chat_id=user_id, text='Please, send me your current location. With this i can send you actual weather data anytime :)', reply_markup=json.dumps(reply_markup))


async def send_current_weather_msg(user_id: int):
    """Getting current weather data and sending it to user"""
    user_data = DBProcessor.get_user_from_db(user_id)

    if not user_data:
        logger.warning(f'Can not get weather for user {user_id}. User is not in db!')
        await send_register_msg(user_id)
        return

    reply_markup = {'keyboard': set_default_kb(user_id), 'resize_keyboard': True}
    user_name = user_data[1]
    location = json.loads(user_data[3])
    lat = location['latitude']
    lon = location['longitude']

    logger.debug(f'Getting weather data for user {user_name}: {user_id}. Coordinates: lat: {lat}, lon: {lon}')

    weather_data = await get_current_weather(lat=lat, lon=lon)

    if not weather_data:
        return

    weather_info = f'Current weather data for <b>{weather_data["city"]}</b>\n' \
                   f'<b>Weather:</b> {weather_data["weather"]} {weather_data["icon"]}\n' \
                   f'<b>Temperature:</b> {weather_data["temp"]} \xb0C. <b>Feels like:</b> {weather_data["feels_like"]} \xb0C.\n' \
                   f'<b>Pressure:</b> {weather_data["pressure"]} P. <b>Humidity:</b> {weather_data["humidity"]} %.\n' \
                   f'<b>Visibility:</b> {weather_data["visibility"]} km. <b>Wind:</b> {weather_data["wind_speed"]} m/s.\n' \
                   f'<b>Sunrise:</b> {datetime.fromtimestamp(weather_data["sunrise"]).time()}. <b>Sunset:</b> {datetime.fromtimestamp(weather_data["sunset"]).time()}.'

    logger.debug(f'Received weather data for user {user_name}: {user_id}. Coordinates: lat: {lat}, lon: {lon}')
    await send_message(chat_id=user_id, text=weather_info, reply_markup=json.dumps(reply_markup))


command_mapping = {'/start': send_start_msg,
                   'Register': send_register_msg,
                   'Current weather': send_current_weather_msg}


def set_default_kb(user_id: int) -> list:
    """Setting default keyboard in chat with required user"""
    current_weather_button = {'text': 'Current weather'}
    keyboard = [[current_weather_button]]

    if not DBProcessor.get_user_from_db(user_id):  # TODO
        keyboard[0].append({'text': 'Register'})

    return keyboard


# TODO
'''
async def make_weather_mailing():  
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

        try:
            if update['result']:
                logger.debug(f'Received {len(update["result"])} updates from Telegram')
                updates_offset = update['result'][-1]['update_id'] + 1
                updates_queue.extend(update['result'])
        except KeyError as error:
            logger.error(f'Error while receiving telegram updates: KeyError: {error}')
        except IndexError as error:
            logger.error(f'Error while receiving telegram updates: IndexError: {error}')

        await asyncio.sleep(2.0)


async def process_updates():
    """Processing updates, received from tg"""
    while True:
        if not updates_queue:
            await asyncio.sleep(3.0)
            continue

        json_data = updates_queue[0]
        updates_queue.remove(json_data)

        logger.debug(f'Processing update {json_data}')

        if json_data.get('message'):  # reading place coords to get actual weather data
            try:
                message = json_data['message']

                user_id = message["from"]["id"]
                user_name = message["from"]["username"]

                if message["from"].get("first_name"):
                    first_name = message["from"]["first_name"]
                else:
                    first_name = None

                logger.debug(f'Received message from user {user_name}: {user_id}')

                if message.get('text') and message['text'] in command_mapping:
                    logger.debug(f'Received {message["text"]} command from user {user_id}: {user_name}')
                    await command_mapping[message['text']](user_id=user_id)
                    logger.debug(f'Command {message["text"]} for user {user_id}: {user_name} executed')
                    continue

                if'location' in message:
                    logger.debug(f'Received location data from user: {user_id}: {user_name}')

                    user_data = DBProcessor.get_user_from_db(user_id)

                    if user_data:  # TODO
                        reply_markup = {'keyboard': set_default_kb(user_id), 'resize_keyboard': True}
                        text = 'You are already registered!'
                        logger.warning(f'User: {user_id}: {user_name} already exists in db!')
                    else:
                        DBProcessor.add_user_to_db(id=user_id, username=user_name, first_name=first_name, location=json.dumps(message["location"]))
                        reply_markup = {'keyboard': set_default_kb(user_id), 'resize_keyboard': True}
                        text = 'Thanks, you have successfully registered!'
                        logger.debug(f'User: {user_id}: {user_name} successfully added in db')
            except KeyError as error:
                logger.error(f'Error while parsing received tg message: KeyError: {error}')
                continue
            except Exception as error:
                logger.error(f'Error while parsing received tg message: {type(error)}: {error}')
                continue

            await send_message(chat_id=user_id, text=text, reply_markup=json.dumps(reply_markup))


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
        logger.info('Started')
        run_bot()
    except KeyboardInterrupt:
        DBProcessor.__del__()
        logger.info('Stopped')
