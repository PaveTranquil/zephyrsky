import asyncio

from pytz import timezone

from handlers import start
from loader import bot, dp, scheduler
from tools import notify_admins, send_notifies


async def main():
    await notify_admins('Бот перезапущен 🚀 /start')
    dp.include_routers(start.router)
    scheduler.start()
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    scheduler.add_job(send_notifies, 'cron', minute='*', timezone=timezone('Europe/Moscow'))
    asyncio.run(main())
