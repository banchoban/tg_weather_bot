import asyncio
import json

from decouple import config

from helpers.requester import make_request

API_TOKEN = config('WEATHER_API_KEY')


async def get_weather_data(lat, lon):

    api_url = f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric&appid={API_TOKEN}'  # TODO

    response = await make_request(url=api_url)
    json_data = json.loads(response)

    return json_data


async def get_current_weather(payload: dict):  # FIXME various api methods
    lat = payload['lat']
    lon = payload['lon']

    json_data = await get_weather_data(lat=lat, lon=lon)

    return json_data


if __name__ == '__main__':
    asyncio.run(get_current_weather({'lat': '55.4507', 'lon': '37.3656'}))
