@router.message(F.message_thread_id, F.chat.type == "supergroup")
async def operator_reply_handler(message: Message, ...):
    print(f"🔍 Получено сообщение в топике {message.message_thread_id}: {message.text}")
    # ... остальной код

import logging
from typing import Optional, Union

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
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
    """
    Отправляет текстовое сообщение пользователю.
    Возвращает True, если успешно, иначе False.
    """
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
    """
    Отправляет медиа-сообщение (фото, видео, документ) пользователю.
    """
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
        elif message.animation:  # GIF
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
            # Неподдерживаемый тип медиа, пробуем отправить как текст
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


@router.message(F.chat.type == "private", F.text)
async def private_chat_handler(message: Message, bot: Bot):
    """
    Обработчик сообщений в личку с ботом — просто игнорируем или логируем.
    """
    log.info(f"Сообщение от пользователя {message.from_user.id} в личку: {message.text[:100]}")


@router.message(F.chat.type == "private", F.photo)
async def private_photo_handler(message: Message):
    """Обработчик фото в личку"""
    log.info(f"Фото от пользователя {message.from_user.id}")


# ============================================================
# ОСНОВНОЙ ОБРАБОТЧИК СООБЩЕНИЙ ОПЕРАТОРА В ТОПИКЕ
# ============================================================

@router.message(F.message_thread_id, F.chat.type == "supergroup")
async def operator_reply_handler(
    message: Message,
    bot: Bot,
    db: Database,
    topics: TopicManager,
    log_messages: bool = True
):
    """
    Обработчик ответов оператора в топике.
    Пересылает сообщение пользователю, чей тикет открыт в этом топике.
    """
    topic_id = message.message_thread_id
    chat_id = message.chat.id
    
    # Получаем user_id по topic_id из базы данных
    user_id = await topics.get_user_id_by_topic(chat_id, topic_id)
    
    if not user_id:
        # Если не нашли пользователя, возможно, топик не привязан к пользователю
        log.warning(f"Не найден пользователь для топика {topic_id} в чате {chat_id}")
        await message.reply(
            "⚠️ Не удалось определить пользователя для этого топика.\n"
            "Проверьте, что топик был создан через бота."
        )
        return
    
    # Логируем сообщение, если включено
    if log_messages:
        await db.save_message(
            user_id=user_id,
            operator_id=message.from_user.id,
            message_text=message.text or message.caption or "[Медиа]",
            direction="operator_to_user"
        )
    
    # Отправляем сообщение пользователю
    success = False
    
    # Пробуем отправить в зависимости от типа контента
    if message.text:
        success = await send_message_to_user(bot, user_id, message.text)
    elif message.photo or message.video or message.document or message.animation or message.sticker or message.voice or message.audio:
        success = await send_media_to_user(bot, user_id, message)
    else:
        # Неподдерживаемый тип сообщения
        await message.reply("⚠️ Этот тип сообщений пока не поддерживается для отправки пользователю.")
        return
    
    # Если не удалось отправить — сообщаем оператору
    if not success:
        await message.reply(
            "⚠️ **Не удалось доставить сообщение пользователю.**\n\n"
            "Возможные причины:\n"
            "• Пользователь не начинал диалог с ботом\n"
            "• Пользователь заблокировал бота\n"
            "• У пользователя закрыт чат с ботом\n\n"
            "Рекомендация: попросите пользователя написать боту любое сообщение, чтобы активировать диалог."
        )
    else:
        # Меняем цвет топика на зелёный после успешного ответа
        try:
            await bot.edit_forum_topic(
                chat_id=chat_id,
                message_thread_id=topic_id,
                icon_color=0x00FF00  # Зелёный
            )
        except Exception as e:
            log.warning(f"Не удалось изменить цвет топика {topic_id}: {e}")
        
        # Отправляем подтверждение оператору
        await message.reply("✅ Сообщение доставлено пользователю.")


# ============================================================
# ОБРАБОТЧИК КОМАНДЫ /close И ЗАКРЫТИЯ ТИКЕТА
# ============================================================

@router.message(F.message_thread_id, F.text.lower() == "/close")
async def close_ticket_command(
    message: Message,
    bot: Bot,
    db: Database,
    topics: TopicManager
):
    """Закрытие тикета по команде /close в топике"""
    topic_id = message.message_thread_id
    chat_id = message.chat.id
    
    user_id = await topics.get_user_id_by_topic(chat_id, topic_id)
    
    # Закрываем топик (делаем его закрытым для сообщений)
    try:
        await bot.close_forum_topic(
            chat_id=chat_id,
            message_thread_id=topic_id
        )
        await message.answer("✅ Тикет закрыт. Операторы больше не будут видеть этот топик как активный.")
        
        # Уведомляем пользователя
        if user_id:
            await send_message_to_user(
                bot, user_id,
                "✅ Ваш тикет закрыт.\n"
                "Если у вас остались вопросы, создайте новую заявку через /start."
            )
    except Exception as e:
        log.error(f"Ошибка при закрытии топика {topic_id}: {e}")
        await message.answer("❌ Не удалось закрыть тикет. Попробуйте позже.")


@router.callback_query(F.data == "close_ticket")
async def close_ticket_callback(
    callback: CallbackQuery,
    bot: Bot,
    db: Database,
    topics: TopicManager
):
    """Закрытие тикета по нажатию на кнопку"""
    await callback.answer("Закрываем тикет...")
    
    # Получаем топик из callback (нужно сохранять где-то в данных)
    # Упрощённо: предполагаем, что callback привязан к конкретному сообщению в топике
    topic_id = callback.message.message_thread_id
    chat_id = callback.message.chat.id
    
    if not topic_id:
        await callback.message.answer("❌ Не удалось определить топик.")
        return
    
    user_id = await topics.get_user_id_by_topic(chat_id, topic_id)
    
    try:
        await bot.close_forum_topic(
            chat_id=chat_id,
            message_thread_id=topic_id
        )
        await callback.message.answer("✅ Тикет закрыт.")
        
        if user_id:
            await send_message_to_user(
                bot, user_id,
                "✅ Ваш тикет закрыт.\n"
                "Если у вас остались вопросы, создайте новую заявку через /start."
            )
    except Exception as e:
        log.error(f"Ошибка при закрытии топика {topic_id}: {e}")
        await callback.message.answer("❌ Не удалось закрыть тикет.")


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

async def get_user_id_by_topic(topics: TopicManager, chat_id: int, topic_id: int) -> Optional[int]:
    """
    Получает ID пользователя по ID топика.
    Здесь нужно реализовать логику поиска в вашей базе данных.
    """
    # Пример: предполагаем, что в TopicManager есть метод
    return await topics.get_user_id_by_topic(chat_id, topic_id)
