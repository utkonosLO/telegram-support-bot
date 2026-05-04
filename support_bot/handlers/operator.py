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


# ========== КОМАНДЫ ОПЕРАТОРОВ ==========

@router.message(F.chat.type == "supergroup", F.text.lower() == "/test_general")
async def test_general_topic(message: Message, bot: Bot):
    """
    Тест отправки сообщения в GENERAL топик (ID=1)
    """
    try:
        await bot.send_message(
            chat_id=OPERATOR_GROUP_ID,
            text="🔍 **Тестовое сообщение в GENERAL топик (ID=1)**\n\nЕсли вы видите это сообщение, значит бот может отправлять сообщения в GENERAL топик.",
            message_thread_id=1
        )
        await message.answer("✅ **Тестовое сообщение отправлено в GENERAL топик!**\nПроверьте топик https://t.me/LO_Content/1")
        log.info(f"Оператор {message.from_user.id} отправил тест в GENERAL топик")
    except Exception as e:
        await message.answer(f"❌ **Ошибка при отправке в GENERAL топик:** {e}")
        log.error(f"Ошибка тестовой отправки в GENERAL: {e}")


@router.message(F.chat.type == "supergroup", F.text.lower() == "/report")
async def send_report_now(message: Message, bot: Bot):
    """
    Отправляет отчёт:
    - внутри топика → в этот топик
    - в общем чате → в GENERAL топик (ID=1)
    """
    current_topic_id = message.message_thread_id
    
    if current_topic_id:
        # Команда вызвана внутри топика
        await message.answer("📊 **Формирую отчёт для этого топика...** Пожалуйста, подождите.")
        log.info(f"📊 Отчёт запрошен в топик {current_topic_id} от {message.from_user.id}")
        try:
            await send_weekly_report_to_topic(bot, current_topic_id)
            await message.answer("✅ **Отчёт успешно отправлен в текущий топик!**")
            log.info(f"✅ Отчёт отправлен в топик {current_topic_id}")
        except Exception as e:
            await message.answer(f"❌ **Ошибка при отправке отчёта:** {e}")
            log.error(f"Ошибка отправки отчёта: {e}")
    else:
        # Команда вызвана в общем чате — отправляем в GENERAL топик
        await message.answer("📊 **Формирую отчёт для GENERAL топика...** Пожалуйста, подождите.")
        log.info(f"📊 Отчёт запрошен в GENERAL топик от {message.from_user.id}")
        try:
            await send_weekly_report_to_topic(bot, 1)
            await message.answer("✅ **Отчёт успешно отправлен в GENERAL топик!**\nПроверьте https://t.me/LO_Content/1")
            log.info(f"✅ Отчёт отправлен в GENERAL топик")
        except Exception as e:
            await message.answer(f"❌ **Ошибка при отправке отчёта в GENERAL топик:** {e}")
            log.error(f"Ошибка отправки отчёта в GENERAL: {e}")


@router.message(F.message_thread_id, F.text.lower() == "/close")
async def close_ticket_command(message: Message, bot: Bot):
    """
    Закрытие тикета по команде /close
    """
    topic_id = message.message_thread_id
    chat_id = message.chat.id
    operator_id = message.from_user.id
    
    log.info(f"🔒 Оператор {operator_id} закрывает тикет {topic_id}")
    
    user_id = get_user_id_from_file(topic_id)
    
    try:
        await bot.close_forum_topic(chat_id=chat_id, message_thread_id=topic_id)
        await message.answer("✅ **Тикет закрыт.**\n\nОператоры больше не будут видеть этот топик как активный.")
        log.info(f"✅ Топик {topic_id} закрыт")
        
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


@router.message(F.chat.type == "supergroup", F.text.lower() == "/debug")
async def debug_report(message: Message, bot: Bot):
    """
    Диагностика отправки отчёта (команда /debug)
    """
    debug_info = f"🔍 **Диагностика:**\n\n"
    debug_info += f"📌 ID группы: `{OPERATOR_GROUP_ID}`\n"
    debug_info += f"📌 Текущий чат ID: `{message.chat.id}`\n"
    debug_info += f"📌 Текущий топик ID: `{message.message_thread_id}`\n\n"
    
    stats = await get_weekly_statistics()
    
    if stats and stats['total'] > 0:
        debug_info += f"📊 **Данные за неделю:**\n"
        debug_info += f"   • Всего: {stats['total']}\n"
        debug_info += f"   • Фото: {stats['photo']}\n"
        debug_info += f"   • Атрибуты: {stats['attributes']}\n"
        debug_info += f"   • Вопросы: {stats['other']}\n"
        debug_info += f"   • Отвечено: {stats['answered']}\n"
        debug_info += f"   • Не отвечено: {stats['unanswered']}\n\n"
    else:
        debug_info += f"📊 **Нет данных за неделю**\n\n"
    
    files_to_check = [
        '/app/data/topic_links.txt',
        '/app/data/tickets_info.txt',
        '/app/data/operators_stats.txt'
    ]
    
    debug_info += f"📁 **Файлы данных:**\n"
    for file_path in files_to_check:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            debug_info += f"   ✅ {os.path.basename(file_path)} ({size} байт)\n"
        else:
            debug_info += f"   ❌ {os.path.basename(file_path)} (не существует)\n"
    
    await message.answer(debug_info)


@router.message(F.chat.type == "supergroup", F.text.lower() == "/help")
async def operator_help(message: Message):
    """
    Справка для операторов
    """
    help_text = (
        "🤖 **Справка для операторов**\n\n"
        "📌 **Команды:**\n"
        "• `/close` - закрыть текущий тикет\n"
        "• `/report` - отправить еженедельный отчёт\n"
        "   - внутри топика → отчёт в этот топик\n"
        "   - в общем чате → отчёт в GENERAL топик\n"
        "• `/debug` - диагностика системы\n"
        "• `/test_general` - тест отправки в GENERAL топик\n"
        "• `/help` - показать справку\n\n"
        "📌 **Как отвечать пользователям:**\n"
        "• Нажмите на сообщение пользователя → «Ответить»\n"
        "• Напишите ответ и отправьте\n\n"
        "📌 **Поддерживаемые типы сообщений:**\n"
        "• Текст, фото, видео, документы, стикеры, голосовые, аудио\n\n"
        "📊 **Статистика:**\n"
        "• Автоматический отчёт каждый понедельник в 10:00\n"
        "• Ручной отчёт через `/report`"
    )
    await message.answer(help_text, parse_mode="HTML")


# ========== ОСНОВНОЙ ОБРАБОТЧИК СООБЩЕНИЙ (ДЛЯ ОТВЕТОВ ПОЛЬЗОВАТЕЛЯМ) ==========

@router.message(F.message_thread_id, F.chat.type == "supergroup")
async def operator_reply_handler(message: Message, bot: Bot):
    """
    Обработчик ответов оператора в топике (отправляет сообщения пользователю)
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
        log.info(f"⏭️ Игнорируем служебное сообщение (тип: {message.content_type}) в топике {topic_id}")
        return

    log.info(f"🔍 Получено сообщение в топике {topic_id} от оператора {operator_id}")
    log.info(f"📋 Тип сообщения: {message.content_type}")

    user_id = get_user_id_from_file(topic_id)

    if not user_id:
        log.error(f"❌ Не найден пользователь для топика {topic_id}")
        await message.reply(
            "⚠️ **Не удалось определить пользователя для этого топика.**\n\n"
            "💡 **Решение:**\n"
            "1. Попросите пользователя написать любое сообщение боту\n"
            "2. После этого создайте НОВУЮ заявку через /start"
        )
        return

    log.info(f"✅ Найден пользователь {user_id} для топика {topic_id}")

    success = False
    error_message = ""

    try:
        if message.text:
            log.info(f"📤 Отправляем текстовое сообщение пользователю {user_id}")
            await bot.send_message(chat_id=user_id, text=message.text, parse_mode="HTML")
            success = True
            log.info(f"✅ Текст отправлен")

        elif message.photo:
            photo = message.photo[-1]
            log.info(f"📤 Отправляем фото пользователю {user_id}")
            await bot.send_photo(chat_id=user_id, photo=photo.file_id, caption=message.caption, parse_mode="HTML")
            success = True
            log.info(f"✅ Фото отправлено")

        elif message.document:
            log.info(f"📤 Отправляем документ пользователю {user_id}")
            await bot.send_document(chat_id=user_id, document=message.document.file_id, caption=message.caption, parse_mode="HTML")
            success = True
            log.info(f"✅ Документ отправлен")

        elif message.video:
            log.info(f"📤 Отправляем видео пользователю {user_id}")
            await bot.send_video(chat_id=user_id, video=message.video.file_id, caption=message.caption, parse_mode="HTML")
            success = True
            log.info(f"✅ Видео отправлено")

        elif message.sticker:
            log.info(f"📤 Отправляем стикер пользователю {user_id}")
            await bot.send_sticker(chat_id=user_id, sticker=message.sticker.file_id)
            success = True
            log.info(f"✅ Стикер отправлен")

        elif message.voice:
            log.info(f"📤 Отправляем голосовое пользователю {user_id}")
            await bot.send_voice(chat_id=user_id, voice=message.voice.file_id, caption=message.caption)
            success = True
            log.info(f"✅ Голосовое отправлено")

        elif message.audio:
            log.info(f"📤 Отправляем аудио пользователю {user_id}")
            await bot.send_audio(chat_id=user_id, audio=message.audio.file_id, caption=message.caption)
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

    if success:
        log.info(f"✅ Сообщение успешно доставлено пользователю {user_id}")
        await mark_ticket_as_answered(topic_id)
        await save_operator_reply(operator_id, topic_id)
    else:
        log.error(f"❌ Не удалось доставить сообщение пользователю {user_id}")
        await message.reply(
            f"❌ **Не удалось доставить сообщение.**\n\n"
            f"📋 Тип: `{message.content_type}`\n"
            f"❌ Ошибка: {error_message}\n\n"
            f"💡 Убедитесь, что пользователь написал боту хотя бы одно сообщение."
        )
