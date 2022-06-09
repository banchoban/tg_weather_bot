# This is main module of project, used for interaction with telegram api
# TODO move methods into class?

import json
import asyncio
import logging
import sys

from decouple import config
from datetime import datetime  # TODO timezones

from helpers.requester import make_request, parse_user_data
from weather_processor import get_current_weather
from database_processor import DBProcessor


API_ACCESS_TOKEN = config('TG_TOKEN')
API_REQUEST_TPL = 'https://api.telegram.org/bot{}/{}'  # URL format: (API token, method name)

logger = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)


class TgWeatherBot:

    def __init__(self, db_path):
        self.DBProcessor = DBProcessor(db_path)
        self.updates_queue = list()
        self.command_mapping = {'/start': self.send_start_msg,
                                'register': self.send_register_msg,
                                'location': self.send_register_msg,
                                'current_weather': self.send_current_weather_msg}

        self.chats = dict()

    def __del__(self):
        self.DBProcessor.__del__()

    async def send_message(self, chat_id: int, text: str, reply_markup: str = None,
                           data=None):  # TODO do we need to send files in messages?
        """Sending message to tg user"""
        api_url = API_REQUEST_TPL.format(API_ACCESS_TOKEN, 'sendMessage')
        data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}

        if reply_markup:
            data['reply_markup'] = reply_markup

        # self.chats[chat_id] += 1

        logger.debug(f'Sending message to chat {chat_id}')
        await make_request(url=api_url, payload=data)

    async def update_message(self, chat_id: int, text: str, reply_markup: str = None):
        message_id = self.chats.get(chat_id)
        api_url = API_REQUEST_TPL.format(API_ACCESS_TOKEN, 'editMessageText')
        if not message_id:
            logger.error(f'Message id for chat {chat_id} missing!')
            return

        data = {'chat_id': chat_id, 'message_id': message_id, 'text': text, 'parse_mode': 'HTML'}

        if reply_markup:
            data['reply_markup'] = reply_markup
        else:
            data['reply_markup'] = json.dumps(self.set_default_kb(chat_id))

        logger.debug(f'Updating message in chat {chat_id}')
        await make_request(url=api_url, payload=data)

    async def send_start_msg(self, user_id: int):  # todo remove if
        """Sending greeting message to user"""

        reply_markup = {'inline_keyboard': self.set_default_kb(user_id)}
        user_data = self.DBProcessor.get_user_from_db(user_id)  # todo remove two continuous request to db

        if user_data:
            if user_data[2]:
                text = f'Hi, {user_data[2]}! How can i help you?'
            else:
                text = f'Hi, {user_data[1]}! How can i help you?'
        else:
            text = f'Hi! How can i help you?'

        await self.send_message(chat_id=user_id, text=text, reply_markup=json.dumps(reply_markup))  # todo edit commands list for user

    async def send_register_msg(self, user_id: int):
        """Sending registration request to current user and setting up tg keyboard for interaction with bot"""

        if self.DBProcessor.get_user_from_db(user_id):
            logger.warning(f'User {user_id} already exists in db')
            reply_markup = {'inline_keyboard': self.set_default_kb(user_id)}
            # await self.update_message(chat_id=user_id, text='You are already registered!', reply_markup=json.dumps(reply_markup))
            # return

        logger.debug(f'Requesting user {user_id} to send location data')
        await self.send_message(chat_id=user_id, text='Please, send me your current location.')

    async def send_current_weather_msg(self, user_id: int):
        """Getting current weather data and sending it to user"""
        user_data = self.DBProcessor.get_user_from_db(user_id)

        if not user_data:
            logger.warning(f'Can not get weather for user {user_id}. User is not in db!')
            await self.send_register_msg(user_id)
            return

        reply_markup = {'inline_keyboard': self.set_default_kb(user_id)}
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
        await self.update_message(chat_id=user_id, text=weather_info, reply_markup=json.dumps(reply_markup))

    def set_default_kb(self, user_id: int) -> list:
        """Setting default keyboard in chat with required user"""
        keyboard = [[]]

        if not self.DBProcessor.get_user_from_db(user_id):  # TODO
            keyboard[0].append({'text': 'Register', 'callback_data': 'register'})
        else:
            keyboard[0].append({'text': 'Change location', 'callback_data': 'location'})
            keyboard[0].append({'text': 'Current weather', 'callback_data': 'current_weather'})

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

    async def get_updates(self):
        """Getting list of updates from tg"""
        updates_offset = 0

        while True:
            api_url = f'{API_REQUEST_TPL.format(API_ACCESS_TOKEN, "getUpdates")}?offset={updates_offset}'

            response = await make_request(url=api_url)
            update = json.loads(response)

            try:
                if update.get('error_code'):
                    logger.error(update['error_code'] + ': ' + update['description'])
                elif update.get('result'):
                    logger.debug(f'Received {len(update["result"])} updates from Telegram')
                    updates_offset = update['result'][-1]['update_id'] + 1
                    self.updates_queue.extend(update['result'])
            except KeyError as error:
                logger.error(f'Error while receiving telegram updates: KeyError: {error}')
            except IndexError as error:
                logger.error(f'Error while receiving telegram updates: IndexError: {error}')

            await asyncio.sleep(2.0)

    async def process_updates(self):
        """Processing updates, received from tg"""
        while True:
            if not self.updates_queue:
                await asyncio.sleep(3.0)
                continue

            json_data = self.updates_queue[0]
            self.updates_queue.remove(json_data)

            logger.debug(f'Processing update {json_data}')

            if json_data.get('message'):  # reading place coords to get actual weather data
                await self.process_message(json_data)
                continue
            elif json_data.get('callback_query'):
                await self.process_callback_query(json_data)
                continue
            else:
                logger.debug(f'Unexpected update type received: {json_data}')
                continue

    async def process_callback_query(self, json_data: dict):
        try:
            query = json_data['callback_query']

            user_data = parse_user_data(query["from"])

            logger.debug(f'Received callback query from user {user_data["user_name"]}: {user_data["user_id"]}')

            self.chats[user_data['user_id']] = query['message']['message_id']
            await self.command_mapping[query['data']](user_data['user_id'])
            return

        except KeyError as error:
            logger.error(f'Error while parsing received tg message: KeyError: {error}')
            return
        except Exception as error:
            logger.error(f'Error while parsing received tg message: {type(error)}: {error}')
            return

    async def process_message(self, json_data: dict):
        try:
            message = json_data['message']

            user_data = parse_user_data(message["from"])

            # self.chats[user_data['user_id']] = message['message_id']

            logger.debug(f'Received message from user {user_data["user_name"]}: {user_data["user_id"]}')

            reply_markup = {'keyboard': self.set_default_kb(user_data["user_id"]), 'resize_keyboard': True}

            if 'location' in message:  # todo warn about unexpected location receivings
                logger.debug(f'Received location data from user: {user_data["user_id"]}: {user_data["user_name"]}')

                db_user_data = self.DBProcessor.get_user_from_db(user_data["user_id"])

                location_data = json.dumps(message["location"])

                if db_user_data:
                    self.DBProcessor.update_location(id=user_data["user_id"], location=location_data)
                    text = 'Location data updated.'
                    logger.debug(f'Location data for user: {user_data["user_id"]}: {user_data["user_name"]} updated.')
                else:
                    self.DBProcessor.add_user_to_db(id=user_data["user_id"], username=user_data["user_name"], first_name=user_data["first_name"],
                                                    location=location_data)
                    text = 'You have successfully registered!'
                    logger.debug(f'User: {user_data["user_id"]}: {user_data["user_name"]} successfully added in db')

                reply_markup = {'inline_keyboard': self.set_default_kb(user_data["user_id"])}

                await self.send_message(chat_id=user_data["user_id"], text=text, reply_markup=json.dumps(reply_markup))
                return
        except KeyError as error:
            logger.error(f'Error while parsing received tg message: KeyError: {error}')
            return
        except Exception as error:
            logger.error(f'Error while parsing received tg message: {type(error)}: {error}')
            return

        if message.get('text') and message['text'].startswith('/') and message['text'] in self.command_mapping:
            logger.debug(f'Received {message["text"]} command from user {user_data["user_id"]}: {user_data["user_name"]}')
            await self.command_mapping[message['text']](user_id=user_data["user_id"])
            logger.debug(f'Command {message["text"]} for user {user_data["user_id"]}: {user_data["user_name"]} executed')
            return
        else:
            logger.warning(f"Command text from user: {user_data['user_name']} unrecognized! Message text: {message.get('text')}")
            # await self.send_message(chat_id=user_data["user_id"],
            #                    text='Your message was not recognized! Please, check it and try to send again.',
            #                    reply_markup=json.dumps(reply_markup))

    def run_bot(self):
        """Run tasks for receiving and processing updates"""
        ioloop = asyncio.get_event_loop()
        tasks = [ioloop.create_task(self.get_updates()), ioloop.create_task(self.process_updates())]
        wait_tasks = asyncio.wait(tasks)
        ioloop.run_until_complete(wait_tasks)
        ioloop.close()


if __name__ == '__main__':
    db_path = sys.argv[1]
    tg_bot = TgWeatherBot(db_path)
    try:
        logger.setLevel(logging.DEBUG)
        logger.debug('Started')
        logger.debug(f'DB path: {db_path}')
        tg_bot.run_bot()
    except KeyboardInterrupt:
        logger.info('Stopped')
    finally:
        tg_bot.__del__()

