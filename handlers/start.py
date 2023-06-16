import logging
from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter, Text
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from entities import START, CallbackData, start_board
from loader import db
from tools import get_greeting

router = Router(name='start -> router')


@router.callback_query(Text('back_'), StateFilter('*'))
@router.message(F.chat.type.in_({'private'}), Command('start'), StateFilter('*'))
async def start(resp: CallbackQuery | Message | CallbackData, state: FSMContext):
    logging.debug('start (resp: %s, state: %s)', resp, state)
    if isinstance(resp, CallbackQuery) or await state.get_data():
        await resp.answer()
    await state.clear()
    msg = resp if isinstance(resp, Message) else resp.message
    uid = msg.chat.id

    with suppress(TelegramBadRequest):
        await msg.delete()

    if not await db.get_user(uid):
        text = START.format(await get_greeting(uid),
                            '! Я Зефирски 🖖🏼 А ты, кажется, ' + msg.from_user.first_name + '? Приятно познакомиться')
        await db.create_user(uid)
    else:
        text = START.format(await get_greeting(uid), ', ' + msg.from_user.first_name)
    await msg.answer(text, reply_markup=start_board)
