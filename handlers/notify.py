import asyncio
import logging
from contextlib import suppress
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton as Button, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder as Board

from entities import (CURR_NOTIFY, LOCATION_SET, NEW_NOTIFY, NOTIFY_ERROR, NOTIFY_EXISTS,
                      NOTIFY_SUCCESS, CallbackData, Dialog, back_btn, hour_board, minute_board, time_board)
from handlers import location
from loader import bot, db
from tools.bot import delete_state, set_state
from tools.converters import inflect_city

router = Router(name='notify -> router')


@router.callback_query(F.data == 'notify_settings')
@router.callback_query(F.data == 'back_notify_sets', StateFilter(Dialog.get_notify_time))
async def notify_settings(call: CallbackQuery, state: FSMContext):
    logging.debug('notify_settings (call: %s, state: %s)', call, state)
    user = await db.get_user(call.message.chat.id)
    if not user.geo:
        await db.set_state(call.message.chat.id, 'from', 'notify')
        return await location.send_location(CallbackData('send_location', call.message), state)

    if notifies := user.notify_time:

        notifies_str = list(map(lambda t: (t.replace(t.hour + user.state.get('tz_shift'))).strftime('%H:%M'),
                                sorted(notifies)))
        board = Board().row(*[Button(text=f'❌ {n}', callback_data=f'del_notify {n}') for n in notifies_str])
        if len(notifies) < 5:
            board.row(Button(text='➕ Добавить новое уведомление', callback_data='add_notify')
                      if user.geo else Button(text='🗺️ Отправить местоположение', callback_data='send_location'))
        board.row(back_btn('settings'))
        text = CURR_NOTIFY[0].format(', '.join(notifies_str))
    else:
        board = Board([[Button(text='➕ Добавить новое уведомление', callback_data='add_notify')],
                       [back_btn('settings')]])
        text = CURR_NOTIFY[1]

    if await db.get_state(call.message.chat.id, 'from') == 'notify':
        text = f"{LOCATION_SET.format(inflect_city(user.state.get('city'), {'gent'}))}\n\n{text}"
        await call.message.answer(text, reply_markup=board.as_markup())
    else:
        await call.message.edit_text(text, reply_markup=board.as_markup())
    await delete_state(state)


@router.callback_query(F.data.startswith('del_notify'))
async def del_notify(call: CallbackQuery, state: FSMContext):
    logging.debug('del_notify (call: %s, state: %s)', call, state)
    time = (datetime.strptime(call.data.split()[1], '%H:%M')
            - timedelta(hours=await db.get_state(call.message.chat.id, 'tz_shift'))).time().strftime('%H:%M')
    await db.delete_notify(call.message.chat.id, time)
    await notify_settings(CallbackData('notify_settings', call.message), state)


@router.callback_query(F.data == 'add_notify')
async def add_notify(call: CallbackQuery, state: FSMContext):
    logging.debug('add_notify (call: %s, state: %s)', call, state)
    hour, minute = await db.get_state(call.message.chat.id, 'set_h'), await db.get_state(call.message.chat.id, 'set_m')
    await db.set_state(call.message.chat.id, 'main_msg_id', call.message.message_id)
    await set_state(state, Dialog.get_notify_time)
    await call.message.edit_text(NEW_NOTIFY, reply_markup=hour_board(hour, minute)('notify_sets'))


@router.callback_query(F.data == 'show_h', StateFilter(Dialog.get_notify_time))
async def show_hour(call: CallbackQuery, state: FSMContext):
    logging.debug('show_hour (call: %s, state: %s)', call, state)
    hour, minute = await db.get_state(call.message.chat.id, 'set_h'), await db.get_state(call.message.chat.id, 'set_m')
    await call.message.edit_reply_markup(reply_markup=hour_board(hour, minute)('notify_sets'))


@router.callback_query(F.data == 'show_m', StateFilter(Dialog.get_notify_time))
async def show_minute(call: CallbackQuery, state: FSMContext):
    logging.debug('show_minute (call: %s, state: %s)', call, state)
    hour, minute = await db.get_state(call.message.chat.id, 'set_h'), await db.get_state(call.message.chat.id, 'set_m')
    await call.message.edit_reply_markup(reply_markup=minute_board(hour, minute)('notify_sets'))


@router.callback_query(F.data.in_({'hide_h', 'hide_m'}), StateFilter(Dialog.get_notify_time))
async def hide_hour_or_minute(call: CallbackQuery, state: FSMContext):
    logging.debug('hide_hour_or_minute (call: %s, state: %s)', call, state)
    hour, minute = await db.get_state(call.message.chat.id, 'set_h'), await db.get_state(call.message.chat.id, 'set_m')
    await call.message.edit_reply_markup(reply_markup=time_board(hour, minute)('notify_sets'))


@router.callback_query(F.data.startswith('set '), StateFilter(Dialog.get_notify_time))
async def set_hour_or_minute(call: CallbackQuery, state: FSMContext):
    logging.debug('set_hour_or_minute (call: %s, state: %s)', call, state)
    measure, count = call.data.split()[1:]
    hour, minute = await db.get_state(call.message.chat.id, 'set_h'), await db.get_state(call.message.chat.id, 'set_m')
    if measure == 'h':
        await db.set_state(call.message.chat.id, 'set_h', hour := int(count))
        await call.message.edit_reply_markup(reply_markup=minute_board(hour, minute)('notify_sets'))
    elif measure == 'm':
        await db.set_state(call.message.chat.id, 'set_m', minute := int(count))
        await call.message.edit_reply_markup(reply_markup=time_board(hour, minute)('notify_sets'))


@router.callback_query(F.data.startswith('create_notify'), StateFilter(Dialog.get_notify_time))
async def set_notify_through_board(call: CallbackQuery, state: FSMContext):
    logging.debug('set_notify_through_board (call: %s, state: %s)', call, state)
    time = (datetime.strptime(call.data.split()[1], '%H:%M')
            - timedelta(hours=await db.get_state(call.message.chat.id, 'tz_shift'))).time()
    if time in (await db.get_user(call.message.chat.id)).notify_time:
        with suppress(TelegramBadRequest):
            await call.answer()
            await call.message.edit_text(NOTIFY_EXISTS, reply_markup=call.message.reply_markup)
        return
    await db.set_notify(call.message.chat.id, time.strftime('%H:%M'))
    await call.answer(NOTIFY_SUCCESS, True)
    await notify_settings(CallbackData('notify_settings', call.message), state)


@router.message(F.text.regexp(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$"), StateFilter(Dialog.get_notify_time))
async def set_notify_as_text(msg: Message, state: FSMContext):
    logging.debug('set_notify_as_text (msg: %s, state: %s)', msg, state)
    time = (datetime.strptime(msg.text.strip(), '%H:%M')
            - timedelta(hours=await db.get_state(msg.chat.id, 'tz_shift'))).time()
    await msg.delete()
    if time in (await db.get_user(msg.chat.id)).notify_time:
        with suppress(TelegramBadRequest):
            await bot.edit_message_text(f'{NOTIFY_EXISTS}\n\n', msg.chat.id,
                                        await db.get_state(msg.chat.id, 'main_msg_id'),
                                        reply_markup=hour_board()('notify_sets'))
        return
    await bot.edit_message_text(NOTIFY_SUCCESS, msg.chat.id, await db.get_state(msg.chat.id, 'main_msg_id'))
    await db.set_notify(msg.chat.id, time.strftime('%H:%M'))
    await asyncio.sleep(3)

    user = await db.get_user(msg.chat.id)
    notifies = user.notify_time
    notifies_str = list(map(lambda t: (t.replace(t.hour + user.state.get('tz_shift'))).strftime('%H:%M'),
                            sorted(notifies)))
    board = Board().row(*[Button(text=f'❌ {n}', callback_data=f'del_notify {n}') for n in notifies_str])
    if len(notifies) < 5:
        board.row(Button(text='➕ Добавить новое уведомление', callback_data='add_notify')
                  if user.geo else Button(text='🗺️ Отправить местоположение', callback_data='send_location'))
    board.row(back_btn('settings'))
    await bot.edit_message_text(CURR_NOTIFY[0].format(', '.join(notifies_str)), msg.chat.id,
                                user.state['main_msg_id'], reply_markup=board.as_markup())
    await delete_state(state)


@router.message(~F.text.regexp(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$"), StateFilter(Dialog.get_notify_time))
async def mistake_in_time(msg: Message, state: FSMContext):
    logging.debug('mistake_in_time (msg: %s, state: %s)', msg, state)
    hour, minute = await db.get_state(msg.chat.id, 'set_h'), await db.get_state(msg.chat.id, 'set_m')
    await msg.delete()
    await bot.edit_message_text(NOTIFY_ERROR, msg.chat.id, await db.get_state(msg.chat.id, 'main_msg_id'),
                                reply_markup=time_board(hour, minute)('notify_sets'))
