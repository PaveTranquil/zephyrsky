import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder as Board

from entities import FORECAST, CallbackData, back_btn
from handlers.start import send_location
from loader import db
from tools import convert_to_icon, get_weather, inflect_city

router = Router(name='weather -> router')


@router.callback_query(F.data == 'weather forecast', StateFilter('*'))
async def forecast(call: CallbackQuery, state: FSMContext):
    logging.debug('forecast (call: %s, state: %s)', call, state)

    if not (await db.get_user(call.message.chat.id)).geo:
        await db.set_state(call.message.chat.id, 'from', 'forecast')
        return await send_location(CallbackData('send_location', call.message), state)

    user = await db.get_user(call.message.chat.id)
    weather = await get_weather(user.geo)
    weather[0] = convert_to_icon(weather[0])
    weather[6] = weather[6].capitalize()
    text = FORECAST.format(inflect_city(user.state['city'], {'loct'}), *weather)

    await call.message.edit_text(text, reply_markup=Board([[back_btn()]]).as_markup())
