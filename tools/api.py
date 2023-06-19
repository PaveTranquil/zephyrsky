from aiohttp import ClientSession
from datetime import datetime

from loader import get
from tools.converters import degrees_to_side, weather_id_to_icon


def extract_weather_data(data: dict) -> dict:
    return {
        'icon': weather_id_to_icon(data['weather'][0]['id']),
        'desc': data['weather'][0]['description'],
        'temp': data['main']['temp'],
        'feels_like': data['main']['feels_like'],
        'pressure': round(data['main']['pressure'] * 0.750064, 2),
        'humidity': data['main']['humidity'],
        'wind_side': degrees_to_side(data['wind']['deg']).capitalize(),
        'wind_speed': data['wind']['speed'],
        'clouds': data['clouds']['all']
    }


async def get_weather(geo: list[float]) -> list:
    """
    Получает информацию о текущей погоде по координатам, используя OpenWeatherMap API.

    :param geo: Список из двух чисел с плавающей точкой, представляющих долготу и широту местоположения.
    :type geo: list[float]

    :return: список из цифр, представляющих погоду.
    :rtype: list

    :raises ValueError: Если координаты недействителен или на сервере внутренняя ошибка.
    :raises ConnectionError: Если возникает проблема с подключением к API OpenWeatherMap.
    """

    async with ClientSession() as session:
        params = {'lon': geo[0], 'lat': geo[1], 'units': 'metric', 'lang': 'ru', 'appid': get('APIKEY_WEATHER')}
        async with session.get('https://api.openweathermap.org/data/2.5/weather', params=params) as resp:
            r_dict = await resp.json()
            if resp.status == 200:
                if r_dict['cod'] == 200:
                    return extract_weather_data(r_dict), {
                        'sunrise': datetime.fromtimestamp(r_dict['sys']['sunrise']).time(),
                        'sunset': datetime.fromtimestamp(r_dict['sys']['sunset']).time()
                    }
                raise ValueError
            raise ConnectionError


async def get_weather_5_days(geo: list[float], cnt: int = 40) -> list:
    async with ClientSession() as session:
        params = {'lon': geo[0], 'lat': geo[1], 'cnt': cnt, 'units': 'metric',
                  'lang': 'ru', 'appid': get('APIKEY_WEATHER')}
        async with session.get('https://api.openweathermap.org/data/2.5/forecast', params=params) as resp:
            r_dict = await resp.json()
            if resp.status == 200:
                if r_dict['cod'] == '200':
                    return [(datetime.fromtimestamp(weather['dt']), extract_weather_data(weather))
                            for weather in r_dict['list']]
                raise ValueError
            raise ConnectionError


async def reverse_geocoding(geo: list[float]) -> str:
    """
    Геокодирует обратно долготу и широту местоположения в город, к которому принадлежат координаты.
    Используется API Геокодера Яндекса.

    :param geo: Список из двух чисел с плавающей точкой, представляющих долготу и широту местоположения.
    :type geo: list[float]

    :return: Строка, представляющая название города, найденного из геокода.
    :rtype: str

    :raises ValueError: Если геокод недействителен или в ответе не найдено название города.
    :raises ConnectionError: Если возникает проблема с подключением к API Геокодера Яндекса.
    """

    async with ClientSession() as session:
        # params = {'format': 'jsonv2', 'lon': geo[0], 'lat': geo[1]}
        # async with session.get('https://nominatim.openstreetmap.org/reverse', params=params) as resp:
        params = {'geocode': f'{geo[0]}, {geo[1]}', 'kind': 'locality',
                  'apikey': get('APIKEY_GEOCODE'), 'format': 'json'}
        async with session.get('https://geocode-maps.yandex.ru/1.x', params=params) as resp:
            resp_dict = await resp.json()
            if resp.status == 200:
                if resp_dict['response']['GeoObjectCollection']['featureMember']:
                    return resp_dict['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['name']
                raise ValueError
            raise ConnectionError


async def geocoding(city: str) -> tuple[tuple[float], str]:
    """
    Геокодирует город в долготу и широту своего местоположения.
    Используется API Геокодера Яндекса.

    :param city: Строка, представляющая название города.
    :type city: str

    :return: Кортеж из двух чисел с плавающей точкой и корректное названием города, найденные из геокода.
    :rtype: tuple[tuple[float], str]

    :raises ValueError: Если геокод недействителен или в ответе не найдены координаты.
    :raises ConnectionError: Если возникает проблема с подключением к API Геокодера Яндекса.
    """

    async with ClientSession() as session:
        params = {'geocode': city, 'apikey': get('APIKEY_GEOCODE'), 'format': 'json'}
        async with session.get('https://geocode-maps.yandex.ru/1.x', params=params) as resp:
            resp_dict = await resp.json()
            if resp.status == 200:
                if resp_dict['response']['GeoObjectCollection']['featureMember']:
                    geo = resp_dict['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['Point']['pos']
                    return (
                        tuple(map(float, geo.split())),
                        resp_dict['response']['GeoObjectCollection']['featureMember'][0]['GeoObject']['name']
                    )
                raise ValueError
            raise ConnectionError


async def get_tzshift(geo: list[float]) -> int:
    """
    Возвращает сдвиг часового пояса относительно московского времени.
    Используется API TimeZoneDB.

    :param geo: Список из двух чисел с плавающей точкой, представляющих долготу и широту местоположения.
    :type geo: list[float]

    :return: Целое число, представляющее сдвиг часового пояса в часах.
    :rtype: int

    :raises ValueError: Если координаты недействительны или на сервере внутренняя ошибка.
    :raises ConnectionError: Если возникает проблема с подключением к API TimeZoneDB.
    """

    async with ClientSession() as session:
        params = {'key': get('APIKEY_TIMEZONE'), 'format': 'json', 'by': 'position', 'lng': geo[0], 'lat': geo[1]}
        async with session.get('http://api.timezonedb.com/v2.1/get-time-zone', params=params) as resp:
            resp_dict = await resp.json()
            if resp.status == 200:
                if resp_dict['status'] == 'OK':
                    return resp_dict['gmtOffset'] // 3600 - 3
                raise ValueError
            raise ConnectionError
