import json

import asyncio
import aiohttp
from decouple import config
from datetime import datetime  # TODO timezones

API_ACCESS_TOKEN = config('TG_TOKEN')
API_REQUEST_TPL = 'https://api.telegram.org/bot{}/{}'  # URL format: (API token, method name)
TODAY_DATE = datetime.utcnow().date()

subscribers_list = [337886033]


async def make_request(url: str, payload=None):
    """Default method for making HTTP requests"""

    if not payload:
        async with aiohttp.ClientSession() as session:
            async with session.get(url=url, timeout=10) as response:

                text = await response.text()

                return text
    else:
        return  # TODO POST request


async def make_weather_mailing():
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

        # TODO process

        await asyncio.sleep(2.0)


def run_bot():
    ioloop = asyncio.get_event_loop()
    tasks = [ioloop.create_task(get_updates())]
    wait_tasks = asyncio.wait(tasks)
    ioloop.run_until_complete(wait_tasks)
    ioloop.close()


if __name__ == '__main__':
    run_bot()
