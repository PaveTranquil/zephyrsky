from dataclasses import dataclass

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton as Button, KeyboardButton as KButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder as Board, ReplyKeyboardBuilder as KBoard

start_board = Board([
    [Button(text='Прогноз погоды', callback_data='weather forecast')],
    [Button(text='Настройки', callback_data='settings')]
]).as_markup()
back_btn = lambda data='', text='': Button(text='🔙 Назад' if not text else text, callback_data=f'back_{data}')
settings_board = Board([
    [Button(text='🗺️ Обновить местоположение', callback_data='send_location')],
    [Button(text='🔔 Настроить уведомления', callback_data='notify_settings')],
    [back_btn()]
]).as_markup()

location_board = KBoard(markup=[[KButton(text='🗺️ Отправить своё местоположение', request_location=True)]]).as_markup(
    one_time_keyboard=True, resize_keyboard=True
)


START = ('{}{}! 🤝\n\nС помощью ветров знаний и сил солнца, '
         'неба и дождя я предсказываю прогноз погоды на каждый день! Нажми на кнопку «Прогноз погоды», чтобы узнать '
         'прогноз погоды на сегодня, на завтра и даже на целую неделю вперёд. ⛅\n\nТы можешь настроить меня в '
         '«Настройках» и указать своё местоположение или время, когда ты хочешь получать уведомления. 🔔')


@dataclass
class CallbackData:
    data: str
    message: Message


class Dialog(StatesGroup):
    get_geo = State()
    get_notify_time = State()
