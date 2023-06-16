import logging
from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder as Board

from entities import (DATA_DELETED, FORECAST, LOCATION, LOCATION_ERROR, LOCATION_SET, NO_LOCATION_FORECAST, SETTINGS, SOON, START, CallbackData, Dialog,
                      back_btn, location_board, settings_board, start_board)
from loader import bot, db
from tools import convert_to_icon, delete_state, geocoding, get_greeting, get_tzshift, get_weather, inflect_city, reverse_geocoding, set_state

router = Router(name='start -> router')


@router.callback_query(F.data == 'back_', StateFilter('*'))
@router.message(F.chat.type.in_({'private'}), Command('start'), StateFilter('*'))
async def start(resp: CallbackQuery | Message | CallbackData, state: FSMContext):
    logging.debug('start (resp: %s, state: %s)', resp, state)
    if isinstance(resp, CallbackQuery) or await state.get_data():
        await resp.answer()
    await delete_state(state)
    msg = resp if isinstance(resp, Message) else resp.message
    uid = msg.chat.id

    with suppress(TelegramBadRequest):
        await msg.delete()

    if not await db.get_user(uid):
        await db.create_user(uid)
        text = START.format(await get_greeting(uid),
                            '! Я Зефирски 🖖🏼 А ты, кажется, ' + msg.chat.first_name + '? Приятно познакомиться! 🤝')
    else:
        text = START.format(await get_greeting(uid), ', ' + msg.chat.first_name + '! 🖖🏼')
    await msg.answer(text, reply_markup=start_board)


@router.callback_query(F.data.in_({'settings', 'back_settings'}), StateFilter('*'))
async def settings(call: CallbackQuery | CallbackData, state: FSMContext):
    logging.debug('settings (call: %s, state: %s)', call, state)
    await call.message.edit_text(SETTINGS, reply_markup=settings_board)
    await db.set_state(call.message.chat.id, 'from', 'settings')


@router.callback_query(F.data == 'back_settings', StateFilter(Dialog.get_geo))
@router.message(F.text == '🔙 Назад', StateFilter(Dialog.get_geo))
async def back_to_settings(msg: Message, state: FSMContext):
    logging.debug('back_to_settings (msg: %s, state: %s)', msg, state)
    await msg.delete()
    service_msg = await bot.send_message(msg.chat.id, 'ㅤ', reply_markup=ReplyKeyboardRemove())
    await service_msg.delete()

    await bot.delete_message(msg.chat.id, await db.get_state(msg.chat.id, 'main_msg_id'))
    if await db.get_state(msg.chat.id, 'from') == 'settings':
        await msg.answer(SETTINGS, reply_markup=settings_board)
    elif await db.get_state(msg.chat.id, 'from') == 'forecast':
        return await start(CallbackData('back_', msg), state)
    await delete_state(state)


@router.callback_query(F.data == 'send_location')
async def send_location(call: CallbackQuery | CallbackData, state: FSMContext):
    logging.debug('send_location (call: %s, state: %s)', call, state)
    await set_state(state, Dialog.get_geo)
    await call.message.delete()
    if await db.get_state(call.message.chat.id, 'from') == 'settings':
        text = LOCATION
    elif await db.get_state(call.message.chat.id, 'from') == 'forecast':
        text = '\n\n'.join([NO_LOCATION_FORECAST, LOCATION])
    main_msg = await call.message.answer(text, reply_markup=location_board)
    await db.set_state(main_msg.chat.id, 'main_msg_id', main_msg.message_id)


@router.message(F.location, StateFilter(Dialog.get_geo))
async def get_location_as_object(msg: Message, state: FSMContext):
    logging.debug('get_location_as_object (msg: %s, state: %s)', msg, state)
    await msg.delete()
    service_msg = await bot.send_message(msg.chat.id, 'ㅤ', reply_markup=ReplyKeyboardRemove())
    await service_msg.delete()

    geo = [msg.location.longitude, msg.location.latitude]
    await db.set_geo(msg.chat.id, geo)
    city = await reverse_geocoding(geo)
    await db.set_state(msg.chat.id, 'city', city)
    await db.set_state(msg.chat.id, 'tz_shift', await get_tzshift(geo))

    await bot.delete_message(msg.chat.id, await db.get_state(msg.chat.id, 'main_msg_id'))
    if await db.get_state(msg.chat.id, 'from') == 'settings':
        await msg.answer(LOCATION_SET.format(inflect_city(city, {'gent'})) + '\n\n' + SETTINGS,
                         reply_markup=settings_board)
    elif await db.get_state(msg.chat.id, 'from') == 'forecast':
        weather = await get_weather(geo)
        weather[0] = convert_to_icon(weather[0])
        weather[6] = weather[6].capitalize()
        text = FORECAST.format(inflect_city(city, {'loct'}), *weather)
        await msg.answer(LOCATION_SET.format(inflect_city(city, {'gent'})) + '\n\n' + text,
                         reply_markup=Board([[back_btn()]]).as_markup())
    await delete_state(state)


@router.message(F.text != '🔙 Назад', StateFilter(Dialog.get_geo))
async def get_location_as_text(msg: Message, state: FSMContext):
    logging.debug('get_location_as_text (msg: %s, state: %s)', msg, state)
    await msg.delete()
    try:
        geo, city = await geocoding(msg.text)
    except ValueError:
        await bot.edit_message_text(LOCATION_ERROR, msg.chat.id, await db.get_state(msg.chat.id, 'main_msg_id'))
        return
    service_msg = await bot.send_message(msg.chat.id, 'ㅤ', reply_markup=ReplyKeyboardRemove())
    await service_msg.delete()

    await db.set_geo(msg.chat.id, geo)
    await db.set_state(msg.chat.id, 'city', city)
    await db.set_state(msg.chat.id, 'tz_shift', await get_tzshift(geo))

    await bot.delete_message(msg.chat.id, await db.get_state(msg.chat.id, 'main_msg_id'))
    if await db.get_state(msg.chat.id, 'from') == 'settings':
        await msg.answer(LOCATION_SET.format(inflect_city(city, {'gent'})) + '\n\n' + SETTINGS,
                         reply_markup=settings_board)
    elif await db.get_state(msg.chat.id, 'from') == 'forecast':
        weather = await get_weather(geo)
        weather[0] = convert_to_icon(weather[0])
        weather[6] = weather[6].capitalize()
        text = FORECAST.format(inflect_city(city, {'loct'}), *weather)
        await msg.answer(LOCATION_SET.format(inflect_city(city, {'gent'})) + '\n\n' + text,
                         reply_markup=Board([[back_btn()]]).as_markup())
    await delete_state(state)


@router.callback_query(F.data == 'notify_settings')
async def notify_settings(call: CallbackQuery, state: FSMContext):
    logging.debug('notify_settings (call: %s, state: %s)', call, state)
    await call.message.edit_text(SOON, reply_markup=Board([[back_btn(text='В главное меню 🏠')]]).as_markup())


@router.callback_query(F.data == 'delete_data')
async def delete_data(call: CallbackQuery, state: FSMContext):
    logging.debug('delete_data (call: %s, state: %s)', call, state)
    await db.delete_user(call.message.chat.id)
    await call.message.edit_text(DATA_DELETED, reply_markup=Board([[back_btn(text='В главное меню 🏠')]]).as_markup())
