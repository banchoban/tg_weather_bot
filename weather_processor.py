# This module used for getting weather information from weather api (for nuw it is openweathermap)

import asyncio
import json
import csv
import logging

from decouple import config

from helpers.requester import make_request

API_TOKEN = config('WEATHER_API_KEY')

logger = logging.getLogger(__name__)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)


async def get_current_weather(lat: float, lon: float):  # FIXME various api methods
    """Making request to weather api for getting current weather data"""
    logger.debug(f'Trying to get weather data for lat: {lat}, lon: {lon}')

    api_url = f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric&appid={API_TOKEN}'

    response = await make_request(url=api_url)
    json_data = json.loads(response)
    weather_data = parse_weather_data(json_data)

    return weather_data


def parse_weather_data(json_data: dict):
    """Parsing required data fields from json with received weather data"""
    logger.debug('Parsing received weather data')

    result = dict()

    with open('weather_conditions.csv') as file:  # searching suitable weather emoji in csv file
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

    logger.debug('Weather data successfully parsed')
    return result


if __name__ == '__main__':
    print(asyncio.run(get_current_weather({'latitude': '55.4507', 'longitude': '37.3656'})))  # for testing api requests  FIXME
