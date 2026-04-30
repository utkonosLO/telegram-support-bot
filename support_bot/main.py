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

    logging.basicConfig(level=getattr(logging, config.log_level.upper(), logging.INFO))
    log = logging.getLogger("support_bot")

    db: Database | None = None
    bot: Bot | None = None
    try:
        db = Database(config.db_path)
        await db.connect()
        await db.init()

        bot = Bot(
            token=config.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        dp = Dispatcher()

        topics = TopicManager(db=db, operator_group_id=config.operator_group_id)

        dp["db"] = db
        dp["topics"] = topics
        dp["log_messages"] = config.log_messages

        # Подключаем роутеры
        dp.include_router(ticket_form_router)
        dp.include_router(user_router)

        operator_router.message.filter(F.chat.id == config.operator_group_id)
        dp.include_router(operator_router)

        me = await bot.get_me()
        log.info("Started as @%s (id=%s)", me.username, me.id)

        # Запускаем polling с правильными allowed_updates
        await dp.start_polling(
            bot,
            allowed_updates=[
                "message",
                "callback_query",
                "my_chat_member",
                "chat_member",
            ]
        )

    finally:
        if db is not None:
            await db.close()
        if bot is not None:
            await bot.session.close()


def main() -> None:
    asyncio.run(_run())
