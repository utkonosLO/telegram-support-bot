import logging
from typing import Optional
import os

from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

router = Router()
log = logging.getLogger(__name__)


def get_user_id_from_file(topic_id: int) -> Optional[int]:
    """
    Получает user_id из файла по topic_id (синхронно)
    """
    try:
        file_path = '/app/data/topic_links.txt'
        if not os.path.exists(file_path):
            log.warning(f"Файл {file_path} не существует")
            return None
        
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(',')
                if len(parts) >= 3:
                    try:
                        if int(parts[0]) == topic_id:
                            user_id = int(parts[2])
                            log.info(f"✅ Найден user_id {user_id} для топика {topic_id}")
                            return user_id
                    except ValueError:
                        continue
        log.warning(f"❌ Топик {topic_id} не найден в файле")
        return None
    except Exception as e:
        log.error(f"❌ Ошибка чтения файла: {e}")
        return None


@router.message(F.message_thread_id, F.chat.type == "supergroup")
async def operator_reply_handler(message: Message, bot: Bot):
    """
    Обработчик ответов оператора в топике
    """
    topic_id = message.message_thread_id
    chat_id = message.chat.id
    operator_id = message.from_user.id

    # Игнорируем сервисные сообщения
    if message.content_type in [
        "forum_topic_created",
        "forum_topic_closed", 
        "forum_topic_reopened",
        "general_forum_topic_hidden",
        "general_forum_topic_unhidden",
        "new_chat_members",
        "left_chat_member",
        "pinned_message"
    ]:
        log.info(f"⏭️ Игнорируем служебное сообщение (тип: {message.content_type}) в топике {topic_id}")
        return

    log.info(f"🔍 Получено сообщение в топике {topic_id} от оператора {operator_id}")
    log.info(f"📋 Тип сообщения: {message.content_type}")

    # Ищем пользователя по топику
    user_id = get_user_id_from_file(topic_id)

    if not user_id:
        log.error(f"❌ Не найден пользователь для топика {topic_id}")
        await message.reply(
            "⚠️ **Не удалось определить пользователя для этого топика.**\n\n"
            "💡 **Решение:**\n"
            "1. Попросите пользователя написать любое сообщение боту\n"
            "2. После этого создайте НОВУЮ заявку через /start\n\n"
            "📌 Только новые заявки после обновления бота работают корректно."
        )
        return

    log.info(f"✅ Найден пользователь {user_id} для топика {topic_id}")

    # Отправляем сообщение пользователю в зависимости от типа
    success = False
    error_message = ""

    try:
        if message.text:
            # Текстовое сообщение
            log.info(f"📤 Отправляем текстовое сообщение пользователю {user_id}")
            await bot.send_message(
                chat_id=user_id,
                text=message.text,
                parse_mode="HTML"
            )
            success = True
            log.info(f"✅ Текст отправлен")

        elif message.photo:
            # Фото
            photo = message.photo[-1]
            log.info(f"📤 Отправляем фото пользователю {user_id}")
            await bot.send_photo(
                chat_id=user_id,
                photo=photo.file_id,
                caption=message.caption,
                parse_mode="HTML"
            )
            success = True
            log.info(f"✅ Фото отправлено")

        elif message.document:
            # Документ
            log.info(f"📤 Отправляем документ пользователю {user_id}")
            await bot.send_document(
                chat_id=user_id,
                document=message.document.file_id,
                caption=message.caption,
                parse_mode="HTML"
            )
            success = True
            log.info(f"✅ Документ отправлен")

        elif message.video:
            # Видео
            log.info(f"📤 Отправляем видео пользователю {user_id}")
            await bot.send_video(
                chat_id=user_id,
                video=message.video.file_id,
                caption=message.caption,
                parse_mode="HTML"
            )
            success = True
            log.info(f"✅ Видео отправлено")

        elif message.sticker:
            # Стикер
            log.info(f"📤 Отправляем стикер пользователю {user_id}")
            await bot.send_sticker(
                chat_id=user_id,
                sticker=message.sticker.file_id
            )
            success = True
            log.info(f"✅ Стикер отправлен")

        elif message.voice:
            # Голосовое
            log.info(f"📤 Отправляем голосовое пользователю {user_id}")
            await bot.send_voice(
                chat_id=user_id,
                voice=message.voice.file_id,
                caption=message.caption
            )
            success = True
            log.info(f"✅ Голосовое отправлено")

        elif message.audio:
            # Аудио
            log.info(f"📤 Отправляем аудио пользователю {user_id}")
            await bot.send_audio(
                chat_id=user_id,
                audio=message.audio.file_id,
                caption=message.caption
            )
            success = True
            log.info(f"✅ Аудио отправлено")

        else:
            error_message = f"Тип сообщения '{message.content_type}' не поддерживается"
            log.warning(f"⚠️ {error_message}")

    except TelegramForbiddenError:
        error_message = "Пользователь не начал диалог с ботом или заблокировал бота"
        log.error(f"❌ {error_message} для пользователя {user_id}")
    except TelegramBadRequest as e:
        error_message = f"Ошибка Telegram: {e}"
        log.error(f"❌ {error_message}")
    except Exception as e:
        error_message = f"Неизвестная ошибка: {e}"
        log.error(f"❌ {error_message}")

    # Обработка результата
    if success:
        log.info(f"✅ Сообщение успешно доставлено пользователю {user_id}")
        # Изменение цвета топика временно отключено из-за ограничений API
        # Цвет топика можно менять только у супергрупп с включёнными темами,
        # но в некоторых версиях API этот параметр не поддерживается
    else:
        log.error(f"❌ Не удалось доставить сообщение пользователю {user_id}")
        
        # Подробное сообщение об ошибке для оператора
        help_message = (
            f"❌ **Не удалось доставить сообщение пользователю.**\n\n"
            f"📋 **Тип вашего сообщения:** `{message.content_type}`\n"
            f"❌ **Ошибка:** {error_message}\n\n"
            f"💡 **Как правильно отвечать:**\n"
            f"1. Найдите **сообщение пользователя** в этом топике\n"
            f"2. **Нажмите на него** и выберите «Ответить»\n"
            f"3. Напишите ваш ответ и отправьте\n\n"
            f"⚠️ **Не отвечайте на системные сообщения** о создании топика!\n\n"
            f"📌 Поддерживаются: текст, фото, видео, документы, стикеры, голосовые, аудио"
        )
        await message.reply(help_message)


@router.message(F.message_thread_id, F.text.lower() == "/close")
async def close_ticket_command(message: Message, bot: Bot):
    """
    Закрытие тикета по команде /close
    """
    topic_id = message.message_thread_id
    chat_id = message.chat.id
    operator_id = message.from_user.id
    
    log.info(f"🔒 Оператор {operator_id} закрывает тикет {topic_id}")
    
    # Получаем user_id для уведомления
    user_id = get_user_id_from_file(topic_id)
    
    try:
        # Закрываем топик
        await bot.close_forum_topic(
            chat_id=chat_id,
            message_thread_id=topic_id
        )
        await message.answer("✅ **Тикет закрыт.**\n\nОператоры больше не будут видеть этот топик как активный.")
        log.info(f"✅ Топик {topic_id} закрыт")
        
        # Уведомляем пользователя
        if user_id:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text="✅ **Ваш тикет закрыт.**\n\nСпасибо, что обратились к нам!\nЕсли у вас остались вопросы, создайте новую заявку через /start."
                )
                log.info(f"✅ Пользователь {user_id} уведомлён о закрытии тикета")
            except Exception as e:
                log.warning(f"⚠️ Не удалось уведомить пользователя {user_id}: {e}")
            
    except Exception as e:
        log.error(f"❌ Ошибка при закрытии топика {topic_id}: {e}")
        await message.answer("❌ **Не удалось закрыть тикет.** Попробуйте позже.")


@router.message(F.chat.type == "supergroup", F.text.lower() == "/help")
async def operator_help(message: Message):
    """
    Справка для операторов
    """
    help_text = (
        "🤖 **Справка для операторов**\n\n"
        "📌 **Основные команды:**\n"
        "• `/close` - закрыть текущий тикет\n"
        "• `/help` - показать эту справку\n\n"
        "📌 **Как отвечать пользователям:**\n"
        "• Найдите **сообщение пользователя** в топике\n"
        "• **Нажмите на него** и выберите «Ответить»\n"
        "• Напишите ваш ответ\n\n"
        "📌 **Поддерживаемые типы сообщений:**\n"
        "• Текстовые сообщения\n"
        "• Фото\n"
        "• Видео\n"
        "• Документы\n"
        "• Стикеры\n"
        "• Голосовые сообщения\n"
        "• Аудио\n\n"
        "📌 **Важно:**\n"
        "• Отвечайте ТОЛЬКО на сообщения пользователя\n"
        "• Не отвечайте на системные сообщения о создании топика\n"
        "• Если пользователь не получает ответ - попросите его написать любое сообщение боту"
    )
    await message.answer(help_text, parse_mode="HTML")
