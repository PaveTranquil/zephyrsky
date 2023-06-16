from contextlib import suppress
from datetime import datetime, timedelta
from random import choice
from typing import Iterable

from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message
from aiohttp import ClientSession
from pymorphy2.shapes import restore_capitalization

from loader import ADMINS, bot, db, get, morph


class AdminFilter(BaseFilter):
    """Фильтр, наследующийся от aiogram.filters.BaseFilter и ограничивающий хендлеры роутера только для админов."""

    async def __call__(self, resp: Message | CallbackQuery) -> bool:
        """
        Вызывается при передаче фильтра в список фильтров роутера и ограничивает хендлеры роутера только для админов.

        :param resp: Объект класса `Message` или `CallbackQuery`.
        :type resp: Union[aiogram.types.Message, aiogram.types.CallbackQuery]

        :return: Булево, указывающее, является ли администратором пользователь, создавший resp.
        :rtype: bool
        """
        return await (resp.chat.id if isinstance(resp, Message) else resp.message.chat.id) in ADMINS


async def notify_admins(text: str):
    """
    Асинхронно отправляет сообщение с текстом `text` всем администраторам, указанным в константе `ADMINS`. 
    Если во время отправки происходит `TelegramBadRequest`, то ошибка подавляется и функция продолжает свою работу.
    
    :param text: Текст сообщения для отправки
    :type text: str
    """
    for admin in ADMINS:
        with suppress(TelegramBadRequest):
            await bot.send_message(admin, text)


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


async def get_tzshift(geo: list[float]) -> int:
    """
    Возвращает сдвиг часового пояса относительно московского времени.
    Используется API TimeZoneDB.

    :param geo: Список из двух чисел с плавающей точкой, представляющих долготу и широту местоположения.
    :type geo: list[float]

    :return: Целое число, представляющее сдвиг часового пояса в часах.
    :rtype: int

    :raises ValueError: Если координаты недействителен или на сервере внутренняя ошибка.
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


def inflect_city(text: str, required_grammemes: Iterable[str]) -> str:
    """
    Эта функция принимает название города и список тегов граммем и возвращает склонённое название города на основе
    предоставленных тегов. Входная строка разбивается на токены, и каждый токен изменяется на основе предоставленных
    граммем с помощью pymorphy2. Восстановление заглавных букв токенов осуществляется с помощью
    pymorphy2.shapes.restore_capitalization(), прежде чем токены снова объединяются в строку, которая подаётся на выход.

    :param text: Название города для изменения.
    :type text: str
    :param required_grammemes: Список тегов граммем для использования при изменении.
    :type required_grammemes: Iterable[str]

    :return: Склонённое название города в соответствии с граммемами.
    :rtype: str
    """

    tokens = text.split()
    inflected = [
        restore_capitalization(
            morph.parse(tok)[0].inflect(required_grammemes).word,
            tok
        )
        for tok in tokens
    ]
    return " ".join(inflected)


async def get_greeting(uid: int) -> str:
    """
    Генерирует уникальное приветствие для пользователя, используя город и часовой пояс с текущим временем.

    :param uid: Telegram ID пользователя для поиска пользователя в базе данных, если он там записан.
    :type uid: int

    :return: Строка, содержащая приветствие для пользователя, основанное на его местном времени и городе.
    :rtype: str
    """

    user = await db.get_user(uid)
    if (tz_shift := user.state.get('tz_shift')) is None:
        return choice(['Привет', 'Приветик', 'Приветствую', 'Хеллоу', 'Хай', 'Йоу', 'Салют'])
    local_time, city = (datetime.now() + timedelta(hours=tz_shift)).time(), user.state.get('city')

    if 5 <= local_time.hour <= 11:
        greet = choice(['Доброе утро', 'Доброго утра', 'Доброе утречко', 'Доброго утречка', 'Утречко', 'Утро доброе',
                       'Добрейшее утро', 'Добрейшего утра', 'Добрейшее утречко', 'Добрейшего утречка'])
    elif 12 <= local_time.hour <= 16:
        greet = choice(['Добрый день', 'Доброго дня', 'Добрый денёк', 'Доброго денька', 'День добрый'
                       'Добрейший день', 'Добрейшего дня', 'Добрейший денёк', 'Добрейшего денька'])
    elif 17 <= local_time.hour <= 22:
        greet = choice(['Добрый вечер', 'Доброго вечера', 'Добрый вечерок', 'Доброго вечерка', 'Вечер добрый'
                       'Добрейший вечер', 'Добрейшего вечера', 'Добрейший вечерок', 'Добрейшего вечерка'])
    else:
        greet = choice(['Доброй ночи', 'Спокойная ночь', 'Привет глубокой ночью', 'Спокойной ночи'])
    return ' '.join([greet, 'в ' + inflect_city(city, {'loct'})])


async def send_notifies():
    """
    Вызывается каждую минуту через AsyncIOScheduler и отправляет уведомления тем, кто поставил его на текущее время.
    """

    users = await db.get_users()
    now = datetime.now().time()
    for user in users:
        for nt in user.notify_time:
            if (nt.hour, nt.minute) == (now.hour, now.minute):
                ...  # TODO: реализовать отправку уведомления с погодой
                # await bot.send_message(user.tg_id, ...)
