from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
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

    db = None
    bot = None
    
    try:
        db = Database(config.db_path)
        await db.connect()
        await db.init()
        log.info("База данных подключена")

        bot = Bot(
            token=config.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        
        dp = Dispatcher()
        topics = TopicManager(db=db, operator_group_id=config.operator_group_id)

        dp["db"] = db
        dp["topics"] = topics
        dp["log_messages"] = config.log_messages

        dp.include_router(ticket_form_router)
        dp.include_router(user_router)
        dp.include_router(operator_router)

        me = await bot.get_me()
        log.info("Бот запущен: @%s", me.username)

        await dp.start_polling(
            bot,
            allowed_updates=[
                "message",
                "callback_query",
                "my_chat_member",
                "chat_member",
            ]
        )
        
    except Exception as e:
        log.error(f"Ошибка: {e}")
        raise
        
    finally:
        if db:
            await db.close()
        if bot:
            await bot.session.close()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
