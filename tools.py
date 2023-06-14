from contextlib import suppress

from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from loader import ADMINS, bot, db


async def is_admin(uid: int) -> bool:
    """
    Проверяет, является ли пользователь с указанным Telegram ID администратором.

    :param uid: Telegram ID пользователя
    :type uid: int

    :return: булево, указывающее, является ли пользователь администратором или нет
    :rtype: bool
    """
    return uid in ADMINS


class AdminFilter(BaseFilter):
    """Фильтр, наследующийся от aiogram.filters.BaseFilter и ограничивающий хендлеры роутера только для админов."""

    async def __call__(self, resp: Message | CallbackQuery) -> bool:
        """
        Вызывается при передаче фильтра в список фильтров роутера и ограничивает хендлеры роутера только для админов.

        :param resp: Объект класса `Message` или `CallbackQuery`.
        :type resp: Union[aiogram.types.Message, aiogram.types.CallbackQuery]

        :return: булево, указывающее, является ли администратором пользователь, создавший resp.
        :rtype: bool
        """
        return await is_admin(resp.chat.id if isinstance(resp, Message) else resp.message.chat.id)


async def notify_admins(text: str):
    """
    Асинхронно отправляет сообщение с текстом `text` всем администраторам, указанным в константе `ADMINS`. 
    Если во время отправки происходит `TelegramBadRequest`, то ошибка подавляется и функция продолжает свою работу.
    """
    for admin in ADMINS:
        with suppress(TelegramBadRequest):
            await bot.send_message(admin, text)
