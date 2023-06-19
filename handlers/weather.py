from collections import Counter
from datetime import datetime, time, timedelta
import logging

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton as Button
from aiogram.utils.keyboard import InlineKeyboardBuilder as Board

from entities import FORECAST, LOCATION_SET, SUN_DESC, CallbackData, back_btn
from handlers import location
from loader import db
from tools.api import get_weather, get_weather_5_days
from tools.bot import delete_state
from tools.converters import inflect_city

router = Router(name='weather -> router')


@router.callback_query(F.data == 'weather forecast', StateFilter('*'))
async def forecast(call: CallbackQuery, state: FSMContext):
    logging.debug('forecast (call: %s, state: %s)', call, state)

    user = await db.get_user(call.message.chat.id)
    if not user.geo:
        await db.set_state(call.message.chat.id, 'from', 'forecast')
        return await location.send_location(CallbackData('send_location', call.message), state)

    weather, sun_status = await get_weather(user.geo)
    context = {'adverb': 'Сейчас', 'verb': '', 'feels_verb': 'ощущается'}
    text = FORECAST.format(**({'city': inflect_city(user.state['city'], {'loct'})} | weather | context))

    sun_status = {'verb_sr': 'был' if datetime.now().time() > sun_status['sunrise'] else 'будет',
                  'verb_ss': 'был' if datetime.now().time() > sun_status['sunset'] else 'будет'} | sun_status
    text += '\n\n' + SUN_DESC.format(**sun_status)

    next_ = min(filter(lambda h: h > datetime.now().hour, range(0, 25, 3))) % 24
    today, tomorrow = datetime.now().strftime('%d.%m.%Y'), (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y")
    board = Board([[
        Button(text='ㅤ', callback_data='empty0'),
        Button(text='Прямо сейчас', callback_data='empty1'),
        Button(text=f'{next_:02}:00 ➡️', callback_data=f'forecast {tomorrow if next_ == 0 else today}-{next_:02}:00')
    ], [
        Button(text='ㅤ', callback_data='empty2'),
        Button(text=today, callback_data='empty3'),
        Button(text=f'{tomorrow} ⏩', callback_data=f'forecast {tomorrow}-09:00')
    ], [Button(text='🔹 Завтра 🔹', callback_data='tomorrow forecast day')], [back_btn()]]).as_markup()

    if await db.get_state(call.message.chat.id, 'from') == 'forecast':
        text = f"{LOCATION_SET.format(inflect_city(user.state.get('city'), {'gent'}))}\n\n{text}"
        await call.message.answer(text, reply_markup=board)
    else:
        await call.message.edit_text(text, reply_markup=board)
    await delete_state(state)


@router.callback_query(F.data.startswith('forecast'))
async def forecast_by_time(call: CallbackQuery, state: FSMContext):
    logging.debug('forecast_by_time (call: %s, state: %s)', call, state)

    cb_time, user = datetime.strptime(call.data.split()[1], '%d.%m.%Y-%H:%M'), await db.get_user(call.message.chat.id)
    weather_list = await get_weather_5_days(user.geo)
    weather = next(filter(lambda w: w[0] == cb_time, weather_list))[1]
    match cb_time.date().day - datetime.now().date().day:
        case 0:
            context = {'adverb': f'Сегодня в {cb_time.strftime("%H:%M")}', 'verb': 'будет ', 'feels_verb': 'ощутится'}
        case 1:
            context = {'adverb': 'Завтра', 'verb': 'будет ', 'feels_verb': 'ощутится'}
        case _:
            context = {'adverb': 'В этот день', 'verb': 'будет ', 'feels_verb': 'ощутится'}
    text = FORECAST.format(**({'city': inflect_city(user.state['city'], {'loct'})} | weather | context))

    if cb_time - timedelta(hours=3) > datetime.now():
        p = cb_time - timedelta(hours=3)
        prev_cast_text, prev_cast_callback = '⬅️ ' + p.strftime('%H:%M'), 'forecast ' + p.strftime('%d.%m.%Y-%H:%M')
    else:
        prev_cast_text, prev_cast_callback = '⬅️ Сейчас', 'weather forecast'

    if cb_time + timedelta(hours=3) < datetime.now() + timedelta(days=5):
        n = cb_time + timedelta(hours=3)
        next_cast_text, next_cast_callback = n.strftime('%H:%M') + ' ➡️', 'forecast ' + n.strftime('%d.%m.%Y-%H:%M')
    else:
        next_cast_text, next_cast_callback = 'ㅤ', 'empty0'
    today_text = cb_time.strftime('%H:%M')

    board = Board([[
        Button(text=prev_cast_text, callback_data=prev_cast_callback),
        Button(text=today_text, callback_data='empty1'),
        Button(text=next_cast_text, callback_data=next_cast_callback)
    ]])

    if datetime.combine(cb_time - timedelta(days=1), time(9)) >= datetime.now():
        yesterday = '⏪ ' + (cb_time - timedelta(days=1)).strftime('%d.%m.%Y')
        yesterday_callback = f'forecast {(cb_time - timedelta(days=1)).strftime("%d.%m.%Y")}-09:00'
    elif prev_cast_callback != 'weather forecast':
        yesterday, yesterday_callback = '⏪ Сейчас', 'weather forecast'
    else:
        yesterday, yesterday_callback = 'ㅤ', 'empty2'
    if datetime.combine(cb_time + timedelta(days=1), time(9)) <= datetime.now() + timedelta(days=5):
        tomorrow = (cb_time + timedelta(days=1)).strftime('%d.%m.%Y') + ' ⏩'
        tomorrow_callback = f'forecast {(cb_time + timedelta(days=1)).strftime("%d.%m.%Y")}-09:00'
    else:
        tomorrow, tomorrow_callback = 'ㅤ', 'empty4'
    board.row(Button(text=yesterday, callback_data=yesterday_callback),
              Button(text=cb_time.strftime('%d.%m.%Y'), callback_data='empty3'),
              Button(text=tomorrow, callback_data=tomorrow_callback))

    if prev_cast_callback != 'weather forecast' and yesterday_callback != 'weather forecast':
        board.row(Button(text='⏮️ Сейчас', callback_data='weather forecast'),
                  Button(text='🔹 Завтра 🔹', callback_data='tomorrow forecast day'))
    else:
        board.row(Button(text='🔹 Завтра 🔹', callback_data='tomorrow forecast day'))

    board.row(back_btn())

    await call.message.edit_text(text, reply_markup=board.as_markup())


@router.callback_query(F.data.startswith('tomorrow forecast'))
async def tomorrow_forecast(call: CallbackQuery, state: FSMContext):
    logging.debug('tomorrow_forecast (call: %s, state: %s)', call, state)

    user = await db.get_user(call.message.chat.id)
    two_day_weather_list = await get_weather_5_days(user.geo, 16)
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow_list = list(filter(lambda w: w[0].day == tomorrow.day, two_day_weather_list))
    time_of_day = {'night': 'ночью', 'morning': 'утром', 'day': 'днём', 'evening': 'вечером'}[call.data.split()[-1]]
    if time_of_day == 'ночью':
        data = list(map(lambda w: w[1], filter(lambda w: w[0].hour < 5, tomorrow_list)))
    elif time_of_day == 'утром':
        data = list(map(lambda w: w[1], filter(lambda w: 5 <= w[0].hour <= 11, tomorrow_list)))
    elif time_of_day == 'днём':
        data = list(map(lambda w: w[1], filter(lambda w: 12 <= w[0].hour <= 17, tomorrow_list)))
    elif time_of_day == 'вечером':
        data = list(map(lambda w: w[1], filter(lambda w: 18 <= w[0].hour, tomorrow_list)))

    length, tod_to_icon_convert = len(data), {
        'ночью': '🌃', 'утром': '🌇', 'днём': Counter(map(lambda d: d['icon'], data)).most_common(1)[0][0],
        'вечером': '🌇'
    }
    weather = {
        'adverb': 'Завтра ' + time_of_day, 'verb': 'будет ', 'feels_verb': 'ощутится',
        'icon': tod_to_icon_convert[time_of_day],
        'desc': Counter(map(lambda d: d['desc'], data)).most_common(1)[0][0],
        'temp': round(sum(map(lambda d: d['temp'], data)) / length, 2),
        'feels_like': round(sum(map(lambda d: d['feels_like'], data)) / length, 2),
        'pressure': round(sum(map(lambda d: d['pressure'], data)) / length, 2),
        'humidity': round(sum(map(lambda d: d['humidity'], data)) / length),
        'wind_side': Counter(map(lambda d: d['wind_side'], data)).most_common(1)[0][0],
        'wind_speed': round(sum(map(lambda d: d['wind_speed'], data)) / length, 2),
        'clouds': round(sum(map(lambda d: d['clouds'], data)) / length)
    }
    text = FORECAST.format(**({'city': inflect_city(user.state['city'], {'loct'})} | weather))

    board = Board()
    board.row(Button(text='🌃 Ночью', callback_data='tomorrow forecast night'),
              Button(text='🌅 Утром', callback_data='tomorrow forecast morning'))
    board.row(Button(text='🏙️ Днём', callback_data='tomorrow forecast day'),
              Button(text='🌇 Вечером', callback_data='tomorrow forecast evening'))
    board.row(Button(text='⬅️ Сейчас', callback_data='weather forecast'),
              Button(text=tomorrow.strftime('%d.%m.%Y'), callback_data='empty0'))
    board.row(back_btn())

    await call.answer()
    if text != call.message.text:
        await call.message.edit_text(text, reply_markup=board.as_markup())
