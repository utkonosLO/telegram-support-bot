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


async def get_user_id_by_topic(db: Database, chat_id: int, topic_id: int) -> Optional[int]:
    """Получает user_id из таблицы topic_links по topic_id и chat_id"""
    try:
        result = await db.fetchone(
            "SELECT user_id FROM topic_links WHERE topic_id = ? AND chat_id = ?",
            (topic_id, chat_id)
        )
        if result:
            return result["user_id"]
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

    # Проверяем, что БД доступна
    if not db:
        log.error("База данных не доступна!")
        await message.reply("❌ Ошибка: база данных не доступна. Обратитесь к администратору.")
        return

    # Ищем пользователя по топику
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

    # Логируем сообщение, если включено
    if log_messages and hasattr(db, 'save_message'):
        try:
            await db.save_message(
                user_id=user_id,
                operator_id=message.from_user.id,
                message_text=message.text or message.caption or "[Медиа]",
                direction="operator_to_user"
            )
        except Exception as e:
            log.error(f"Ошибка при сохранении сообщения в лог: {e}")

    # Отправляем сообщение пользователю
    success = False

    if message.text:
        success = await send_message_to_user(bot, user_id, message.text)
    elif message.photo or message.video or message.document or message.animation or message.sticker or message.voice or message.audio:
        success = await send_media_to_user(bot, user_id, message)
    else:
        await message.reply("⚠️ Этот тип сообщений пока не поддерживается для отправки пользователю.")
        return

    if not success:
        await message.reply(
            "⚠️ **Не удалось доставить сообщение пользователю.**\n\n"
            "Возможные причины:\n"
            "• Пользователь не начинал диалог с ботом\n"
            "• Пользователь заблокировал бота\n"
            "• У пользователя закрыт чат с ботом\n\n"
            "💡 **Рекомендация:** Попросите пользователя написать боту любое сообщение, чтобы активировать диалог."
        )
    else:
        # Меняем цвет топика на зелёный после успешного ответа
        try:
            await bot.edit_forum_topic(
                chat_id=chat_id,
                message_thread_id=topic_id,
                icon_color=0x00FF00  # Зелёный
            )
            log.info(f"✅ Цвет топика {topic_id} изменён на зелёный")
        except Exception as e:
            log.warning(f"Не удалось изменить цвет топика {topic_id}: {e}")

        # Отправляем подтверждение оператору (опционально, можно убрать)
        # await message.reply("✅ Сообщение доставлено пользователю.")


@router.message(F.message_thread_id, F.text.lower() == "/close")
async def close_ticket_command(message: Message, bot: Bot, db: Database):
    """
    Закрытие тикета по команде /close в топике
    """
    topic_id = message.message_thread_id
    chat_id = message.chat.id

    log.info(f"🔒 Закрытие тикета {topic_id} оператором {message.from_user.id}")

    if not db:
        await message.reply("❌ Ошибка: база данных не доступна.")
        return

    # Получаем user_id для уведомления пользователя
    user_id = await get_user_id_by_topic(db, chat_id, topic_id)

    try:
        # Закрываем топик
        await bot.close_forum_topic(
            chat_id=chat_id,
            message_thread_id=topic_id
        )
        await message.answer("✅ **Тикет закрыт.**\n\nОператоры больше не будут видеть этот топик как активный.")

        # Уведомляем пользователя, если нашли
        if user_id:
            await send_message_to_user(
                bot, user_id,
                "✅ **Ваш тикет закрыт.**\n\n"
                "Спасибо, что обратились к нам!\n"
                "Если у вас остались вопросы, создайте новую заявку через /start."
            )
            log.info(f"✅ Пользователь {user_id} уведомлён о закрытии тикета {topic_id}")
        else:
            log.warning(f"Не удалось уведомить пользователя о закрытии тикета {topic_id}")

    except Exception as e:
        log.error(f"Ошибка при закрытии топика {topic_id}: {e}")
        await message.answer("❌ **Не удалось закрыть тикет.** Попробуйте позже.")


# ========== ВСПОМОГАТЕЛЬНЫЕ КОМАНДЫ ДЛЯ ОПЕРАТОРОВ ==========

@router.message(F.chat.type == "supergroup", F.text.lower() == "/help")
async def operator_help(message: Message):
    """Справка для операторов"""
    help_text = (
        "🤖 **Справка для операторов**\n\n"
        "📌 **Основные команды:**\n"
        "• `/close` - закрыть текущий тикет\n"
        "• `/help` - показать эту справку\n\n"
        "📌 **Как отвечать пользователям:**\n"
        "• Просто напишите сообщение в топике - оно будет отправлено пользователю\n"
        "• Поддерживаются текстовые сообщения и медиа (фото, видео, документы)\n\n"
        "📌 **Цвета топиков:**\n"
        "• 🔴 Красный - новый тикет, ожидает ответа оператора\n"
        "• 🟢 Зелёный - оператор ответил пользователю\n\n"
        "📌 **Если пользователь не получает ответ:**\n"
        "• Убедитесь, что пользователь написал боту хотя бы одно сообщение\n"
        "• Попросите пользователя написать любое слово в чат с ботом\n\n"
        "📌 **Полезные ссылки:**\n"
        "• [Поддержка](https://t.me/your_support_chat)"
    )
    await message.answer(help_text, parse_mode="HTML", disable_web_page_preview=True)
