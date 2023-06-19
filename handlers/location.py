import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from entities import (CURR_LOCATION, LOCATION, LOCATION_ERROR, NO_LOCATION_FORECAST, NO_LOCATION_NOTIFY, CallbackData,
                      Dialog, location_board)
from handlers import notify, start, weather
from loader import bot, db
from tools.api import geocoding, get_tzshift, reverse_geocoding
from tools.bot import delete_state, set_state
from tools.converters import inflect_city

router = Router(name='location -> router')


@router.callback_query(F.data == 'send_location')
async def send_location(call: CallbackQuery | CallbackData, state: FSMContext):
    logging.debug('send_location (call: %s, state: %s)', call, state)
    await set_state(state, Dialog.get_geo)
    if await db.get_state(call.message.chat.id, 'from') == 'settings':
        if city := await db.get_state(call.message.chat.id, 'city'):
            text = f"{CURR_LOCATION.format(inflect_city(city, {'gent'}))}\n\n{LOCATION}"
        else:
            text = LOCATION
    elif await db.get_state(call.message.chat.id, 'from') == 'forecast':
        text = f'{NO_LOCATION_FORECAST}\n\n{LOCATION}'
    elif await db.get_state(call.message.chat.id, 'from') == 'notify':
        text = NO_LOCATION_NOTIFY
    await call.message.delete()
    main_msg = await call.message.answer(text, reply_markup=location_board)
    await db.set_state(main_msg.chat.id, 'main_msg_id', main_msg.message_id)


@router.message(F.location, StateFilter(Dialog.get_geo))
async def get_location_as_object(msg: Message, state: FSMContext):
    logging.debug('get_location_as_object (msg: %s, state: %s)', msg, state)

    geo = [msg.location.longitude, msg.location.latitude]
    await db.set_geo(msg.chat.id, geo)
    city = await reverse_geocoding(geo)
    await db.set_state(msg.chat.id, 'city', city)
    await db.set_state(msg.chat.id, 'tz_shift', await get_tzshift(geo))

    await msg.delete()
    service_msg = await bot.send_message(msg.chat.id, 'ㅤ', reply_markup=ReplyKeyboardRemove())
    await service_msg.delete()
    await bot.delete_message(msg.chat.id, await db.get_state(msg.chat.id, 'main_msg_id'))
    if await db.get_state(msg.chat.id, 'from') == 'settings':
        await start.settings(CallbackData('settings', msg), state)
    elif await db.get_state(msg.chat.id, 'from') == 'forecast':
        await weather.forecast(CallbackData('weather forecast', msg), state)
    elif await db.get_state(msg.chat.id, 'from') == 'notify':
        await notify.notify_settings(CallbackData('notify_settings', msg), state)
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

    await db.set_geo(msg.chat.id, geo)
    await db.set_state(msg.chat.id, 'city', city)
    await db.set_state(msg.chat.id, 'tz_shift', await get_tzshift(geo))

    service_msg = await bot.send_message(msg.chat.id, 'ㅤ', reply_markup=ReplyKeyboardRemove())
    await service_msg.delete()
    await bot.delete_message(msg.chat.id, await db.get_state(msg.chat.id, 'main_msg_id'))
    if await db.get_state(msg.chat.id, 'from') == 'settings':
        await start.settings(CallbackData('settings', msg), state)
    elif await db.get_state(msg.chat.id, 'from') == 'forecast':
        await weather.forecast(CallbackData('weather forecast', msg), state)
    elif await db.get_state(msg.chat.id, 'from') == 'notify':
        await notify.notify_settings(CallbackData('notify_settings', msg), state)
    await delete_state(state)
