import logging
from contextlib import suppress
from datetime import time

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton as Button, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder as Board

from entities import (CURR_NOTIFY, CallbackData, Dialog, back_btn, location_board,
                      settings_board, start_board)
from loader import bot, db
from tools.api import geocoding, get_tzshift, get_weather, reverse_geocoding
from tools.bot import delete_state, get_greeting, set_state
from tools.converters import inflect_city, weather_id_to_icon

router = Router(name='notify -> router')


@router.callback_query(F.data == 'notify_settings')
async def notify_settings(call: CallbackQuery, state: FSMContext):
    logging.debug('notify_settings (call: %s, state: %s)', call, state)
    if notifies := (await db.get_user(call.message.chat.id)).notify_time:
        notifies_str = list(map(lambda t: t.strftime('%H:%M'), sorted(notifies)))
        if len(notifies) < 5:
            board = Board([[Button(text=f'❌ {n}', callback_data='del_notify {n}') for n in notifies_str],
                           [Button(text='➕ Добавить новое уведомление', callback_data='add_notify')],
                           [back_btn('settings')]])
        else:
            board = Board([[Button(text=f'❌ {n}', callback_data='del_notify {n}') for n in notifies_str],
                           [back_btn('settings')]])
        board.add(back_btn('settings'))
        await call.message.edit_text(CURR_NOTIFY[0].format(', '.join(notifies_str)), reply_markup=board.as_markup())
    else:
        board = Board([[Button(text='➕ Добавить новое уведомление', callback_data='add_notify')],
                       [back_btn('settings')]])
        await call.message.answer(CURR_NOTIFY[1], reply_markup=board.as_markup())
