import logging
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from support_bot.db import Database
from support_bot.topic_manager import TopicManager

router = Router()
log = logging.getLogger(__name__)


def get_close_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для закрытия тикета"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Закрыть тикет", callback_data="close_ticket")]
        ]
    )


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


async def send_media_to_user(bot: Bot, user_id: int, message: Message) -> bool:
    """Отправляет медиа-сообщение пользователю"""
    try:
        if message.photo:
            await bot.send_photo(
                chat_id=user_id,
                photo=message.photo[-1].file_id,
                caption=message.caption,
                parse_mode="HTML"
            )
        elif message.video:
            await bot.send_video(
                chat_id=user_id,
                video=message.video.file_id,
                caption=message.caption,
                parse_mode="HTML"
            )
        elif message.document:
            await bot.send_document(
                chat_id=user_id,
                document=message.document.file_id,
                caption=message.caption,
                parse_mode="HTML"
            )
        elif message.animation:
            await bot.send_animation(
                chat_id=user_id,
                animation=message.animation.file_id,
                caption=message.caption,
                parse_mode="HTML"
            )
        elif message.sticker:
            await bot.send_sticker(
                chat_id=user_id,
                sticker=message.sticker.file_id
            )
        elif message.voice:
            await bot.send_voice(
                chat_id=user_id,
                voice=message.voice.file_id,
                caption=message.caption
            )
        elif message.audio:
            await bot.send_audio(
                chat_id=user_id,
                audio=message.audio.file_id,
                caption=message.caption
            )
        else:
            if message.caption:
                return await send_message_to_user(bot, user_id, message.caption)
            return False
        return True
    except TelegramForbiddenError:
        log.warning(f"Не удалось отправить медиа пользователю {user_id}: бот заблокирован или не начат диалог")
        return False
    except TelegramBadRequest as e:
        log.error(f"Ошибка при отправке медиа пользователю {user_id}: {e}")
        return False


@router.message(F.message_thread_id, F.chat.type == "supergroup")
async def operator_reply_handler(
    message: Message,
    bot: Bot,
    db: Database,
    topics: TopicManager,
    log_messages: bool = True
):
    """Обработчик ответов оператора в топике"""
    topic_id = message.message_thread_id
    chat_id = message.chat.id

    log.info(f"Получено сообщение в топике {topic_id} от {message.from_user.id}: {message.text}")

    # Ищем пользователя по топику
    user_id = None

    # Пробуем через TopicManager
    if hasattr(topics, 'get_user_id_by_topic'):
        try:
            user_id = await topics.get_user_id_by_topic(chat_id, topic_id)
        except Exception as e:
            log.error(f"Ошибка topics.get_user_id_by_topic: {e}")

    # Если не нашли — ищем напрямую в БД
    if not user_id and db:
        try:
            result = await db.fetchone(
                "SELECT user_id FROM topic_links WHERE topic_id = ? AND chat_id = ?",
                (topic_id, chat_id)
            )
            if result:
                user_id = result["user_id"]
                log.info(f"Найден пользователь {user_id} для топика {topic_id}")
            else:
                log.warning(f"Не найден пользователь для топика {topic_id}")
        except Exception as e:
            log.error(f"Ошибка поиска в БД: {e}")

    if not user_id:
        await message.reply(
            "⚠️ **Не удалось определить пользователя для этого топика.**\n\n"
            "Возможные причины:\n"
            "• Пользователь ещё не написал боту ни одного сообщения\n"
            "• Связь между топиком и пользователем не сохранена\n\n"
            "💡 Попросите пользователя написать любое сообщение боту, "
            "а затем попробуйте ответить снова."
        )
        return

    # Логируем сообщение
    if log_messages:
        await db.save_message(
            user_id=user_id,
            operator_id=message.from_user.id,
            message_text=message.text or message.caption or "[Медиа]",
            direction="operator_to_user"
        )

    # Отправляем сообщение пользователю
    success = False

    if message.text:
        success = await send_message_to_user(bot, user_id, message.text)
    elif message.photo or message.video or message.document or message.animation or message.sticker or message.voice or message.audio:
        success = await send_media_to_user(bot, user_id, message)
    else:
        await message.reply("⚠️ Этот тип сообщений пока не поддерживается.")
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
        except Exception as e:
            log.warning(f"Не удалось изменить цвет топика: {e}")

        await message.reply("✅ Сообщение доставлено пользователю.")


@router.message(F.message_thread_id, F.text.lower() == "/close")
async def close_ticket_command(message: Message, bot: Bot, db: Database, topics: TopicManager):
    """Закрытие тикета по команде /close"""
    topic_id = message.message_thread_id
    chat_id = message.chat.id

    user_id = None
    if db:
        result = await db.fetchone(
            "SELECT user_id FROM topic_links WHERE topic_id = ? AND chat_id = ?",
            (topic_id, chat_id)
        )
        if result:
            user_id = result["user_id"]

    try:
        await bot.close_forum_topic(chat_id=chat_id, message_thread_id=topic_id)
        await message.answer("✅ Тикет закрыт.")

        if user_id:
            await send_message_to_user(
                bot, user_id,
                "✅ Ваш тикет закрыт.\n"
                "Если у вас остались вопросы, создайте новую заявку через /start."
            )
    except Exception as e:
        log.error(f"Ошибка при закрытии топика: {e}")
        await message.answer("❌ Не удалось закрыть тикет.")
