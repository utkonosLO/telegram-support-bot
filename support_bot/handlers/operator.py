import logging
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

router = Router()
log = logging.getLogger(__name__)


async def send_message_to_user(bot: Bot, user_id: int, text: str, parse_mode: str = "HTML") -> bool:
    try:
        await bot.send_message(chat_id=user_id, text=text, parse_mode=parse_mode)
        return True
    except TelegramForbiddenError:
        log.warning(f"Не удалось отправить сообщение пользователю {user_id}")
        return False
    except TelegramBadRequest as e:
        log.error(f"Ошибка при отправке: {e}")
        return False


async def get_user_id_by_topic(db, chat_id: int, topic_id: int) -> Optional[int]:
    """Универсальный поиск user_id по топику"""
    try:
        # Пробуем разные варианты выполнения запроса
        result = None
        
        # Вариант 1: fetch_one
        if hasattr(db, 'fetch_one'):
            result = await db.fetch_one(
                "SELECT user_id FROM topic_links WHERE topic_id = ? AND chat_id = ?",
                (topic_id, chat_id)
            )
        # Вариант 2: select
        elif hasattr(db, 'select'):
            result = await db.select(
                "SELECT user_id FROM topic_links WHERE topic_id = ? AND chat_id = ?",
                (topic_id, chat_id)
            )
        # Вариант 3: execute + fetchone
        elif hasattr(db, 'execute'):
            cursor = await db.execute(
                "SELECT user_id FROM topic_links WHERE topic_id = ? AND chat_id = ?",
                (topic_id, chat_id)
            )
            if hasattr(cursor, 'fetchone'):
                result = await cursor.fetchone()
        # Вариант 4: query
        elif hasattr(db, 'query'):
            result = await db.query(
                "SELECT user_id FROM topic_links WHERE topic_id = ? AND chat_id = ?",
                (topic_id, chat_id)
            )
            if result and isinstance(result, list) and len(result) > 0:
                result = result[0]
        
        if result:
            if isinstance(result, dict):
                return result.get("user_id")
            elif isinstance(result, (tuple, list)):
                return result[0]
            elif hasattr(result, 'user_id'):
                return result.user_id
        return None
        
    except Exception as e:
        log.error(f"Ошибка при поиске: {e}")
        return None


async def save_topic_link(db, topic_id: int, chat_id: int, user_id: int) -> bool:
    """Универсальное сохранение связи"""
    try:
        if hasattr(db, 'execute'):
            await db.execute(
                "INSERT OR REPLACE INTO topic_links (topic_id, chat_id, user_id) VALUES (?, ?, ?)",
                (topic_id, chat_id, user_id)
            )
            if hasattr(db, 'commit'):
                await db.commit()
            return True
        elif hasattr(db, 'query'):
            await db.query(
                "INSERT OR REPLACE INTO topic_links (topic_id, chat_id, user_id) VALUES (?, ?, ?)",
                (topic_id, chat_id, user_id)
            )
            return True
        return False
    except Exception as e:
        log.error(f"Ошибка сохранения: {e}")
        return False


@router.message(F.message_thread_id, F.chat.type == "supergroup")
async def operator_reply_handler(message: Message, bot: Bot, db):
    topic_id = message.message_thread_id
    chat_id = message.chat.id

    log.info(f"🔍 Сообщение в топике {topic_id} от {message.from_user.id}")

    if not db:
        await message.reply("❌ Ошибка: БД не доступна.")
        return

    user_id = await get_user_id_by_topic(db, chat_id, topic_id)

    if not user_id:
        await message.reply(
            "⚠️ **Не удалось определить пользователя для этого топика.**\n\n"
            "💡 Попросите пользователя написать любое сообщение боту, "
            "а затем создайте новую заявку через /start."
        )
        return

    log.info(f"✅ Найден пользователь {user_id}")

    if message.text:
        success = await send_message_to_user(bot, user_id, message.text)
        if success:
            try:
                await bot.edit_forum_topic(chat_id=chat_id, message_thread_id=topic_id, icon_color=0x00FF00)
            except:
                pass


@router.message(F.message_thread_id, F.text.lower() == "/close")
async def close_ticket_command(message: Message, bot: Bot, db):
    topic_id = message.message_thread_id
    chat_id = message.chat.id
    user_id = await get_user_id_by_topic(db, chat_id, topic_id)
    
    try:
        await bot.close_forum_topic(chat_id=chat_id, message_thread_id=topic_id)
        await message.answer("✅ Тикет закрыт.")
        if user_id:
            await send_message_to_user(bot, user_id, "✅ Ваш тикет закрыт. Спасибо!")
    except Exception as e:
        log.error(f"Ошибка: {e}")
        await message.answer("❌ Не удалось закрыть тикет.")
