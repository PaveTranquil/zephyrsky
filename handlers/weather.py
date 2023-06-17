import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder as Board

from entities import FORECAST, CallbackData, back_btn
from handlers.location import send_location
from loader import db
from tools.api import get_weather
from tools.converters import inflect_city, weather_id_to_icon

router = Router(name='weather -> router')


@router.callback_query(F.data == 'weather forecast', StateFilter('*'))
async def forecast(call: CallbackQuery, state: FSMContext):
    logging.debug('forecast (call: %s, state: %s)', call, state)

    user = await db.get_user(call.message.chat.id)
    if not user.geo:
        await db.set_state(call.message.chat.id, 'from', 'forecast')
        return await send_location(CallbackData('send_location', call.message), state)

    weather = await get_weather(user.geo)
    weather[0] = weather_id_to_icon(weather[0])
    weather[6] = weather[6].capitalize()
    text = FORECAST.format(inflect_city(user.state['city'], {'loct'}), *weather)

    await call.message.edit_text(text, reply_markup=Board([[back_btn()]]).as_markup())
