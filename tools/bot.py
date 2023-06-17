from contextlib import suppress
from datetime import datetime, timedelta
from random import choice

from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import CallbackQuery, InlineKeyboardButton as Button, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder as Board

from loader import ADMINS, bot, db, storage
from tools.api import get_weather
from tools.converters import inflect_city, weather_id_to_icon
from entities import FORECAST


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


async def set_state(ctx: FSMContext, state: State):
    await ctx.set_state(state)
    await db.set_state(ctx.key.chat_id, 'aiogram_state', str(state).split("'")[1])


async def delete_state(ctx: FSMContext):
    await ctx.clear()
    for key in ['aiogram_state', 'main_msg_id', 'from', 'set_h', 'set_m']:
        try:
            await db.delete_state(ctx.key.chat_id, key)
        except (ValueError, KeyError):
            pass


async def restore_states():
    users = await db.get_users()
    for user in users:
        if state := user.state.get('aiogram_state'):
            await storage.set_state(bot, StorageKey(bot.id, user.tg_id, user.tg_id), state)


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


async def get_greeting(uid: int, with_city: bool = True) -> str:
    """
    Генерирует уникальное приветствие для пользователя, используя город и часовой пояс с текущим временем.

    :param uid: Telegram ID пользователя для поиска пользователя в базе данных, если он там записан.
    :type uid: int

    :return: Строка, содержащая приветствие для пользователя, основанное на его местном времени и городе.
    :rtype: str
    """

    user = await db.get_user(uid)
    if (tz_shift := user.state.get('tz_shift')) is None:
        return choice(['Привет', 'Приветик', 'Приветствую', 'Хэллоу', 'Хай', 'Йоу', 'Салют']), ''
    local_time, city = (datetime.now() + timedelta(hours=tz_shift)).time(), user.state.get('city')

    if 5 <= local_time.hour <= 11:
        greet = choice(['Доброе утро', 'Доброго утра', 'Доброе утречко', 'Доброго утречка', 'Утречко', 'Утро доброе',
                       'Добрейшее утро', 'Добрейшего утра', 'Добрейшее утречко', 'Добрейшего утречка'])
        icon = '🌅'
    elif 12 <= local_time.hour <= 16:
        greet = choice(['Добрый день', 'Доброго дня', 'Добрый денёк', 'Доброго денька', 'День добрый',
                       'Добрейший день', 'Добрейшего дня', 'Добрейший денёк', 'Добрейшего денька'])
        icon = '🏙️'
    elif 17 <= local_time.hour <= 22:
        greet = choice(['Добрый вечер', 'Доброго вечера', 'Добрый вечерок', 'Доброго вечерка', 'Вечер добрый',
                       'Добрейший вечер', 'Добрейшего вечера', 'Добрейший вечерок', 'Добрейшего вечерка'])
        icon = '🌇'
    else:
        greet = choice(['Доброй ночи', 'Спокойная ночь', 'Привет глубокой ночью', 'Спокойной ночи'])
        icon = '🌃'
    return (f"{greet} в {inflect_city(city, {'loct'})}" if with_city else greet), icon


async def send_notifies():
    """
    Вызывается каждую минуту через AsyncIOScheduler и отправляет уведомления тем, кто поставил его на текущее время.
    """

    users = await db.get_users()
    now = datetime.now().time()
    for user in users:
        for nt in user.notify_time:
            if (nt.hour, nt.minute) == (now.hour, now.minute):  # TODO: отправка с учётом часового пояса
                weather = await get_weather(user.geo)  # TODO: учесть, что пользователь мог ещё не записать геолокацию
                weather[0] = weather_id_to_icon(weather[0])
                weather[6] = weather[6].capitalize()
                text = FORECAST.format(inflect_city(user.state['city'], {'loct'}), *weather)
                board = Board([[Button(text='Спасибо 🫂', callback_data='ok')]]).as_markup()
                await bot.send_message(user.tg_id, f'{"! ".join(await get_greeting(user.tg_id, False))}\n\n{text}',
                                       reply_markup=board)
