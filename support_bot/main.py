from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram import F
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

from support_bot.config import load_config
from support_bot.db import Database
from support_bot.handlers.operator import router as operator_router
from support_bot.handlers.user import router as user_router
from support_bot.handlers.ticket_form import router as ticket_form_router
from support_bot.topic_manager import TopicManager
from support_bot.statistics import send_daily_report, send_weekly_report

# Создаём логгер
log = logging.getLogger("support_bot")


async def daily_report_scheduler(bot: Bot):
    """
    Запускает отправку ежедневного отчёта каждый день в 09:00
    """
    while True:
        now = datetime.now()
        next_run = now.replace(hour=9, minute=0, second=0, microsecond=0)
        if now >= next_run:
            next_run = next_run + timedelta(days=1)
        
        wait_seconds = (next_run - now).total_seconds()
        log.info(f"⏰ Следующий ежедневный отчёт через {wait_seconds / 3600:.1f} часов")
        await asyncio.sleep(wait_seconds)
        
        try:
            await send_daily_report(bot)
            log.info("✅ Ежедневный отчёт успешно отправлен")
        except Exception as e:
            log.error(f"❌ Ошибка при отправке ежедневного отчёта: {e}")


async def weekly_report_scheduler(bot: Bot):
    """
    Запускает отправку еженедельного отчёта каждый понедельник в 10:00
    """
    while True:
        now = datetime.now()
        # Вычисляем следующий понедельник 10:00
        days_until_monday = (7 - now.weekday()) % 7
        
        if days_until_monday == 0 and now.hour < 10:
            # Сегодня понедельник, но ещё не 10 утра
            next_run = now.replace(hour=10, minute=0, second=0, microsecond=0)
        elif days_until_monday == 0 and now.hour >= 10:
            # Сегодня понедельник, но уже после 10 — ждём следующую неделю
            next_run = now.replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=7)
        else:
            next_run = (now + timedelta(days=days_until_monday)).replace(hour=10, minute=0, second=0, microsecond=0)
        
        wait_seconds = (next_run - now).total_seconds()
        log.info(f"⏰ Следующий еженедельный отчёт через {wait_seconds / 3600:.1f} часов")
        await asyncio.sleep(wait_seconds)
        
        try:
            await send_weekly_report(bot)
            log.info("✅ Еженедельный отчёт успешно отправлен")
        except Exception as e:
            log.error(f"❌ Ошибка при отправке еженедельного отчёта: {e}")


async def _run() -> None:
    load_dotenv()
    config = load_config()

    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    log.info("Запуск бота...")

    db: Database | None = None
    bot: Bot | None = None
    
    try:
        # Подключаем базу данных
        db = Database(config.db_path)
        await db.connect()
        await db.init()
        log.info("База данных подключена и инициализирована")

        # Создаём бота
        bot = Bot(
            token=config.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        
        # Сохраняем БД в bot.data для доступа из хендлеров
        bot.data = {"db": db}
        
        # Создаём диспетчер
        dp = Dispatcher()

        # Создаём менеджер топиков
        topics = TopicManager(db=db, operator_group_id=config.operator_group_id)

        # Передаём зависимости в диспетчер
        dp["db"] = db
        dp["topics"] = topics
        dp["log_messages"] = config.log_messages

        # Подключаем роутеры
        dp.include_router(ticket_form_router)
        dp.include_router(user_router)

        # Фильтр для операторского роутера — только сообщения из группы операторов
        operator_router.message.filter(F.chat.id == config.operator_group_id)
        dp.include_router(operator_router)

        # Получаем информацию о боте
        me = await bot.get_me()
        log.info("Бот запущен: @%s (id=%s)", me.username, me.id)
        log.info("Группа операторов: %s", config.operator_group_id)

        # Запускаем планировщики отчётов
        asyncio.create_task(daily_report_scheduler(bot))
        asyncio.create_task(weekly_report_scheduler(bot))
        log.info("📊 Планировщики отчётов запущены:")
        log.info("   • Ежедневный отчёт — каждый день в 09:00")
        log.info("   • Еженедельный отчёт — каждый понедельник в 10:00")

        # Запускаем polling с правильными allowed_updates
        await dp.start_polling(
            bot,
            allowed_updates=[
                "message",           # Обычные сообщения
                "callback_query",    # Нажатия на кнопки
                "my_chat_member",    # Изменения в чате с ботом
                "chat_member",       # Изменения в участниках чата
            ]
        )
        
    except Exception as e:
        log.error(f"Критическая ошибка при запуске бота: {e}")
        raise
        
    finally:
        if db is not None:
            await db.close()
            log.info("Соединение с БД закрыто")
        if bot is not None:
            await bot.session.close()
            log.info("Сессия бота закрыта")


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
