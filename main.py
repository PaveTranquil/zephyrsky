import asyncio

from pytz import timezone

from handlers import location, notify, start, weather
from loader import bot, dp, scheduler
from tools.bot import notify_admins, restore_states, send_notifies


async def main():
    await restore_states()
    dp.include_routers(start.router, weather.router, location.router, notify.router)
    scheduler.start()
    await notify_admins('Бот перезапущен 🚀 /start')
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    scheduler.add_job(send_notifies, 'cron', minute='*', timezone=timezone('Europe/Moscow'))
    asyncio.run(main())
