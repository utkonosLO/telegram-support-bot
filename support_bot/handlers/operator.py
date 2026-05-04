import logging
from typing import Optional
import os
from datetime import datetime

from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from support_bot.statistics import (
    mark_ticket_as_answered, 
    save_operator_reply, 
    send_weekly_report_to_topic,
    get_weekly_statistics,
    OPERATOR_GROUP_ID
)

router = Router()
log = logging.getLogger(__name__)


def get_user_id_from_file(topic_id: int) -> Optional[int]:
    """Получает user_id из файла по topic_id"""
    try:
        file_path = '/app/data/topic_links.txt'
        if not os.path.exists(file_path):
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
                            return int(parts[2])
                    except ValueError:
                        continue
        return None
    except Exception as e:
        log.error(f"Ошибка чтения файла: {e}")
        return None


# ========== КОМАНДЫ ОПЕРАТОРОВ (ДОЛЖНЫ БЫТЬ ПЕРВЫМИ) ==========

@router.message(F.chat.type == "supergroup", F.text.lower() == "/report")
async def send_report_now(message: Message, bot: Bot):
    """
    Отправляет отчёт в текущий топик
    """
    current_topic_id = message.message_thread_id
    
    log.info(f"📊 Получена команда /report от {message.from_user.id} в топике {current_topic_id}")
    
    if not current_topic_id:
        await message.answer("❌ **Ошибка:** Команда должна быть вызвана внутри топика!")
        return
    
    await message.answer("📊 **Формирую отчёт...** Пожалуйста, подождите.")
    
    try:
        await send_weekly_report_to_topic(bot, current_topic_id)
        await message.answer("✅ **Отчёт успешно отправлен!**")
        log.info(f"✅ Отчёт отправлен в топик {current_topic_id}")
    except Exception as e:
        await message.answer(f"❌ **Ошибка:** {e}")
        log.error(f"Ошибка: {e}")


@router.message(F.message_thread_id, F.text.lower() == "/close")
async def close_ticket_command(message: Message, bot: Bot):
    """Закрытие тикета по команде /close"""
    topic_id = message.message_thread_id
    chat_id = message.chat.id
    operator_id = message.from_user.id
    
    log.info(f"🔒 Оператор {operator_id} закрывает тикет {topic_id}")
    
    user_id = get_user_id_from_file(topic_id)
    
    try:
        await bot.close_forum_topic(chat_id=chat_id, message_thread_id=topic_id)
        await message.answer("✅ **Тикет закрыт.**")
        
        if user_id:
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text="✅ **Ваш тикет закрыт.** Спасибо за обращение!"
                )
            except Exception as e:
                log.warning(f"Не удалось уведомить пользователя: {e}")
    except Exception as e:
        log.error(f"Ошибка: {e}")
        await message.answer("❌ **Не удалось закрыть тикет.**")


@router.message(F.chat.type == "supergroup", F.text.lower() == "/help")
async def operator_help(message: Message):
    """Справка для операторов"""
    help_text = (
        "🤖 **Справка для операторов**\n\n"
        "📌 **Команды:**\n"
        "• `/close` - закрыть текущий тикет\n"
        "• `/report` - отправить еженедельный отчёт\n"
        "• `/help` - показать справку\n\n"
        "📌 **Как отвечать:**\n"
        "• Нажмите на сообщение пользователя → «Ответить»\n"
        "• Напишите ответ и отправьте"
    )
    await message.answer(help_text, parse_mode="HTML")


# ========== ОСНОВНОЙ ОБРАБОТЧИК СООБЩЕНИЙ (ДОЛЖЕН БЫТЬ ПОСЛЕДНИМ) ==========

@router.message(F.message_thread_id, F.chat.type == "supergroup")
async def operator_reply_handler(message: Message, bot: Bot):
    """
    Обработчик ответов оператора в топике (только для отправки пользователю)
    """
    topic_id = message.message_thread_id
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
        log.info(f"⏭️ Игнорируем служебное сообщение: {message.content_type}")
        return

    log.info(f"🔍 Получено сообщение в топике {topic_id} от оператора {operator_id}")

    user_id = get_user_id_from_file(topic_id)

    if not user_id:
        await message.reply("⚠️ **Не удалось определить пользователя для этого топика.**")
        return

    log.info(f"✅ Найден пользователь {user_id}")

    try:
        if message.text:
            await bot.send_message(chat_id=user_id, text=message.text, parse_mode="HTML")
            await mark_ticket_as_answered(topic_id)
            await save_operator_reply(operator_id, topic_id)
            log.info(f"✅ Сообщение отправлено пользователю {user_id}")
        else:
            await message.reply("⚠️ Этот тип сообщений пока не поддерживается.")
    except Exception as e:
        log.error(f"Ошибка: {e}")
        await message.reply(f"❌ Ошибка: {e}")
