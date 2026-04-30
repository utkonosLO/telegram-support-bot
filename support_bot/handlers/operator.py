import logging
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from support_bot.db import Database

router = Router()
log = logging.getLogger(__name__)


async def send_message_to_user(bot: Bot, user_id: int, text: str, parse_mode: str = "HTML") -> bool:
    """Отправляет текстовое сообщение пользователю"""
    try:
        await bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode=parse_mode
        )
        return True
    except TelegramForbiddenError:
        log.warning(f"Не удалось отправить сообщение пользователю {user_id}: бот заблокирован или не начат диалог")
        return False
    except TelegramBadRequest as e:
        log.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
        return False


async def get_user_id_by_topic(db: Database, chat_id: int, topic_id: int) -> Optional[int]:
    """Получает user_id из таблицы topic_links по topic_id и chat_id"""
    try:
        # Используем метод, который есть в вашем Database
        # Возможно, это fetch_one или select
        if hasattr(db, 'fetch_one'):
            result = await db.fetch_one(
                "SELECT user_id FROM topic_links WHERE topic_id = ? AND chat_id = ?",
                (topic_id, chat_id)
            )
        elif hasattr(db, 'select'):
            result = await db.select(
                "SELECT user_id FROM topic_links WHERE topic_id = ? AND chat_id = ?",
                (topic_id, chat_id)
            )
        else:
            # Прямой execute + fetchone
            cursor = await db.execute(
                "SELECT user_id FROM topic_links WHERE topic_id = ? AND chat_id = ?",
                (topic_id, chat_id)
            )
            result = await cursor.fetchone()
        
        if result:
            # result может быть словарём, кортежем или объектом
            if isinstance(result, dict):
                return result.get("user_id")
            elif isinstance(result, (tuple, list)):
                return result[0]
            else:
                return getattr(result, 'user_id', None)
        else:
            log.warning(f"Не найден пользователь для топика {topic_id} в чате {chat_id}")
            return None
    except Exception as e:
        log.error(f"Ошибка при поиске пользователя по топику: {e}")
        return None


@router.message(F.message_thread_id, F.chat.type == "supergroup")
async def operator_reply_handler(
    message: Message,
    bot: Bot,
    db: Database,
    log_messages: bool = True
):
    """
    Обработчик ответов оператора в топике.
    Пересылает сообщение пользователю, чей тикет открыт в этом топике.
    """
    topic_id = message.message_thread_id
    chat_id = message.chat.id

    log.info(f"🔍 Получено сообщение в топике {topic_id} от оператора {message.from_user.id}")

    if not db:
        log.error("База данных не доступна!")
        await message.reply("❌ Ошибка: база данных не доступна. Обратитесь к администратору.")
        return

    user_id = await get_user_id_by_topic(db, chat_id, topic_id)

    if not user_id:
        await message.reply(
            "⚠️ **Не удалось определить пользователя для этого топика.**\n\n"
            "Возможные причины:\n"
            "• Пользователь ещё не написал боту ни одного сообщения\n"
            "• Связь между топиком и пользователем не сохранена\n\n"
            "💡 **Решение:** Попросите пользователя написать любое сообщение боту, "
            "а затем попробуйте ответить снова.\n\n"
            "📌 Если проблема повторяется, создайте новую заявку через /start."
        )
        return

    log.info(f"✅ Найден пользователь {user_id} для топика {topic_id}")

    # Отправляем сообщение пользователю
    success = False

    if message.text:
        success = await send_message_to_user(bot, user_id, message.text)
    else:
        await message.reply("⚠️ Этот тип сообщений пока не поддерживается для отправки пользователю.")
        return

    if not success:
        await message.reply(
            "⚠️ **Не удалось доставить сообщение пользователю.**\n\n"
            "Возможные причины:\n"
            "• Пользователь не начинал диалог с ботом\n"
            "• Пользователь заблокировал бота\n\n"
            "💡 Попросите пользователя написать любое сообщение боту."
        )
    else:
        # Меняем цвет топика на зелёный
        try:
            await bot.edit_forum_topic(
                chat_id=chat_id,
                message_thread_id=topic_id,
                icon_color=0x00FF00
            )
            log.info(f"✅ Цвет топика {topic_id} изменён на зелёный")
        except Exception as e:
            log.warning(f"Не удалось изменить цвет топика: {e}")

        # Не отправляем подтверждение оператору, чтобы не засорять чат
        # await message.reply("✅ Сообщение доставлено пользователю.")


@router.message(F.message_thread_id, F.text.lower() == "/close")
async def close_ticket_command(message: Message, bot: Bot, db: Database):
    """Закрытие тикета по команде /close"""
    topic_id = message.message_thread_id
    chat_id = message.chat.id

    log.info(f"🔒 Закрытие тикета {topic_id} оператором {message.from_user.id}")

    if not db:
        await message.reply("❌ Ошибка: база данных не доступна.")
        return

    user_id = await get_user_id_by_topic(db, chat_id, topic_id)

    try:
        await bot.close_forum_topic(chat_id=chat_id, message_thread_id=topic_id)
        await message.answer("✅ **Тикет закрыт.**")

        if user_id:
            await send_message_to_user(
                bot, user_id,
                "✅ **Ваш тикет закрыт.**\n\n"
                "Спасибо, что обратились к нам!\n"
                "Если у вас остались вопросы, создайте новую заявку через /start."
            )
    except Exception as e:
        log.error(f"Ошибка при закрытии топика: {e}")
        await message.answer("❌ Не удалось закрыть тикет.")
