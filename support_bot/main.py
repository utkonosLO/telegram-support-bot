from __future__ import annotations

import asyncio
import logging

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


async def _run() -> None:
    load_dotenv()
    config = load_config()

    logging.basicConfig(
        level=getattr(logging, config.log_level.upper(), logging.INFO),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    log = logging.getLogger("support_bot")

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
