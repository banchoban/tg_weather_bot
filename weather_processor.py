import asyncio
import json
import csv

from decouple import config

from helpers.requester import make_request

API_TOKEN = config('WEATHER_API_KEY')


async def get_weather_data(lat, lon):

    api_url = f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric&appid={API_TOKEN}'

    response = await make_request(url=api_url)
    json_data = json.loads(response)

    return json_data


async def get_current_weather(payload: dict):  # FIXME various api methods
    lat = payload['latitude']
    lon = payload['longitude']

    json_data = await get_weather_data(lat=lat, lon=lon)
    weather_data = parse_weather_data(json_data)

    return weather_data


def parse_weather_data(json_data: dict):
    result = dict()

    with open('weather_conditions.csv') as file:
        reader = csv.reader(file)
        for row in reader:
            if str(json_data['weather'][0]['id']) == row[0]:
                result['icon'] = row[1]
                break

    result['city'] = json_data["name"]
    result['weather'] = json_data["weather"][0]["description"].title()
    result['temp'] = json_data["main"]["temp"]
    result['feels_like'] = json_data["main"]["feels_like"]
    result['pressure'] = json_data["main"]["pressure"]
    result['humidity'] = json_data["main"]["humidity"]
    result['visibility'] = json_data["visibility"] / 1000
    result['wind_speed'] = json_data["wind"]["speed"]
    result['sunrise'] = json_data["sys"]["sunrise"]
    result['sunset'] = json_data["sys"]["sunset"]

    return result


if __name__ == '__main__':
    print(asyncio.run(get_current_weather({'latitude': '55.4507', 'longitude': '37.3656'})))
