import logging
from typing import Optional
import aiofiles
import os

from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

router = Router()
log = logging.getLogger(__name__)


async def get_user_id_from_file(topic_id: int) -> Optional[int]:
    """Получает user_id из файла по topic_id"""
    try:
        file_path = '/app/data/topic_links.txt'
        if not os.path.exists(file_path):
            log.warning(f"Файл {file_path} не существует")
            return None
        
        async with aiofiles.open(file_path, 'r') as f:
            lines = await f.readlines()
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(',')
                if len(parts) >= 3:
                    try:
                        file_topic_id = int(parts[0])
                        if file_topic_id == topic_id:
                            user_id = int(parts[2])
                            log.info(f"✅ Найден user_id {user_id} для топика {topic_id} из файла")
                            return user_id
                    except ValueError:
                        continue
        log.warning(f"❌ Топик {topic_id} не найден в файле")
        return None
    except Exception as e:
        log.error(f"❌ Ошибка чтения файла: {e}")
        return None


async def save_user_id_to_file(topic_id: int, chat_id: int, user_id: int) -> bool:
    """Сохраняет связь в файл"""
    try:
        os.makedirs('/app/data', exist_ok=True)
        async with aiofiles.open('/app/data/topic_links.txt', 'a') as f:
            await f.write(f"{topic_id},{chat_id},{user_id}\n")
        log.info(f"💾 Сохранена связь: топик {topic_id} -> пользователь {user_id}")
        return True
    except Exception as e:
        log.error(f"❌ Ошибка сохранения в файл: {e}")
        return False


async def send_message_to_user(bot: Bot, user_id: int, text: str, parse_mode: str = "HTML") -> bool:
    """Отправляет текстовое сообщение пользователю"""
    try:
        log.info(f"📤 Отправляем текстовое сообщение пользователю {user_id}")
        await bot.send_message(chat_id=user_id, text=text, parse_mode=parse_mode)
        log.info(f"✅ Текстовое сообщение доставлено пользователю {user_id}")
        return True
    except TelegramForbiddenError:
        log.error(f"❌ TelegramForbiddenError: бот заблокирован или пользователь {user_id} не начал диалог")
        return False
    except TelegramBadRequest as e:
        log.error(f"❌ TelegramBadRequest: {e}")
        return False
    except Exception as e:
        log.error(f"❌ Неизвестная ошибка: {e}")
        return False


async def send_photo_to_user(bot: Bot, user_id: int, photo_file_id: str, caption: str = None) -> bool:
    """Отправляет фото пользователю"""
    try:
        log.info(f"📷 Отправляем фото пользователю {user_id}")
        await bot.send_photo(chat_id=user_id, photo=photo_file_id, caption=caption, parse_mode="HTML")
        log.info(f"✅ Фото доставлено пользователю {user_id}")
        return True
    except Exception as e:
        log.error(f"❌ Ошибка при отправке фото: {e}")
        return False


async def send_document_to_user(bot: Bot, user_id: int, document_file_id: str, caption: str = None) -> bool:
    """Отправляет документ пользователю"""
    try:
        log.info(f"📄 Отправляем документ пользователю {user_id}")
        await bot.send_document(chat_id=user_id, document=document_file_id, caption=caption, parse_mode="HTML")
        log.info(f"✅ Документ доставлен пользователю {user_id}")
        return True
    except Exception as e:
        log.error(f"❌ Ошибка при отправке документа: {e}")
        return False


async def send_video_to_user(bot: Bot, user_id: int, video_file_id: str, caption: str = None) -> bool:
    """Отправляет видео пользователю"""
    try:
        log.info(f"🎬 Отправляем видео пользователю {user_id}")
        await bot.send_video(chat_id=user_id, video=video_file_id, caption=caption, parse_mode="HTML")
        log.info(f"✅ Видео доставлено пользователю {user_id}")
        return True
    except Exception as e:
        log.error(f"❌ Ошибка при отправке видео: {e}")
        return False


async def send_sticker_to_user(bot: Bot, user_id: int, sticker_file_id: str) -> bool:
    """Отправляет стикер пользователю"""
    try:
        log.info(f"🏷️ Отправляем стикер пользователю {user_id}")
        await bot.send_sticker(chat_id=user_id, sticker=sticker_file_id)
        log.info(f"✅ Стикер доставлен пользователю {user_id}")
        return True
    except Exception as e:
        log.error(f"❌ Ошибка при отправке стикера: {e}")
        return False


async def send_voice_to_user(bot: Bot, user_id: int, voice_file_id: str, caption: str = None) -> bool:
    """Отправляет голосовое сообщение пользователю"""
    try:
        log.info(f"🎤 Отправляем голосовое сообщение пользователю {user_id}")
        await bot.send_voice(chat_id=user_id, voice=voice_file_id, caption=caption)
        log.info(f"✅ Голосовое сообщение доставлено пользователю {user_id}")
        return True
    except Exception as e:
        log.error(f"❌ Ошибка при отправке голосового сообщения: {e}")
        return False


@router.message(F.message_thread_id, F.chat.type == "supergroup")
async def operator_reply_handler(message: Message, bot: Bot):
    """Обработчик ответов оператора в топике (поддерживает текст, фото, видео, документы, стикеры, голосовые)"""
    topic_id = message.message_thread_id
    chat_id = message.chat.id
    operator_id = message.from_user.id

    log.info(f"🔍 Получено сообщение в топике {topic_id} от оператора {operator_id}")

    # Ищем пользователя по топику в файле
    user_id = await get_user_id_from_file(topic_id)

    if not user_id:
        log.error(f"❌ Не найден пользователь для топика {topic_id}")
        await message.reply(
            "⚠️ **Не удалось определить пользователя для этого топика.**\n\n"
            "💡 **Решение:**\n"
            "1. Попросите пользователя написать любое сообщение боту\n"
            "2. После этого создайте НОВУЮ заявку через /start\n"
            "3. Старые заявки не будут работать\n\n"
            "📌 Только новые заявки после обновления бота имеют сохранённую связь."
        )
        return

    log.info(f"✅ Найден пользователь {user_id} для топика {topic_id}")

    # Обрабатываем разные типы сообщений
    success = False

    # Текстовое сообщение
    if message.text:
        log.info(f"📝 Текст: {message.text[:100] if message.text else '[пусто]'}")
        success = await send_message_to_user(bot, user_id, message.text)
    
    # Фото
    elif message.photo:
        photo = message.photo[-1]
        caption = message.caption or ""
        success = await send_photo_to_user(bot, user_id, photo.file_id, caption)
    
    # Документ
    elif message.document:
        caption = message.caption or ""
        success = await send_document_to_user(bot, user_id, message.document.file_id, caption)
    
    # Видео
    elif message.video:
        caption = message.caption or ""
        success = await send_video_to_user(bot, user_id, message.video.file_id, caption)
    
    # Стикер
    elif message.sticker:
        success = await send_sticker_to_user(bot, user_id, message.sticker.file_id)
    
    # Голосовое сообщение
    elif message.voice:
        caption = message.caption or ""
        success = await send_voice_to_user(bot, user_id, message.voice.file_id, caption)
    
    # Аудио
    elif message.audio:
        caption = message.caption or ""
        success = await send_audio_to_user(bot, user_id, message.audio.file_id, caption)
    
    # Неподдерживаемый тип
    else:
        log.warning(f"⚠️ Неподдерживаемый тип сообщения в топике {topic_id}")
        await message.reply(
            "⚠️ **Этот тип сообщений пока не поддерживается.**\n\n"
            "Поддерживаются:\n"
            "• Текстовые сообщения\n"
            "• Фото\n"
            "• Документы\n"
            "• Видео\n"
            "• Стикеры\n"
            "• Голосовые сообщения\n"
            "• Аудио"
        )
        return

    # Обработка результата отправки
    if success:
        log.info(f"✅ Сообщение доставлено пользователю {user_id}")
        
        # Меняем цвет топика на зелёный
        try:
            await bot.edit_forum_topic(
                chat_id=chat_id,
                message_thread_id=topic_id,
                icon_color=0x00FF00
            )
            log.info(f"🎨 Цвет топика {topic_id} изменён на зелёный")
        except Exception as e:
            log.warning(f"⚠️ Не удалось изменить цвет топика {topic_id}: {e}")
        
        # Не отправляем подтверждение оператору, чтобы не засорять чат
    else:
        log.error(f"❌ Не удалось доставить сообщение пользователю {user_id}")
        await message.reply(
            "❌ **Не удалось доставить сообщение пользователю.**\n\n"
            "💡 **Возможные причины:**\n"
            "• Пользователь не начал диалог с ботом\n"
            "• Пользователь заблокировал бота\n\n"
            "🔧 **Решение:** Попросите пользователя написать любое сообщение боту.\n"
            "После этого создайте НОВУЮ заявку через /start.\n\n"
            "📌 **Важно:** Старые заявки, созданные до обновления бота, не работают.\n"
            "Используйте только новые заявки."
        )


async def send_audio_to_user(bot: Bot, user_id: int, audio_file_id: str, caption: str = None) -> bool:
    """Отправляет аудио пользователю"""
    try:
        log.info(f"🎵 Отправляем аудио пользователю {user_id}")
        await bot.send_audio(chat_id=user_id, audio=audio_file_id, caption=caption)
        log.info(f"✅ Аудио доставлено пользователю {user_id}")
        return True
    except Exception as e:
        log.error(f"❌ Ошибка при отправке аудио: {e}")
        return False


@router.message(F.message_thread_id, F.text.lower() == "/close")
async def close_ticket_command(message: Message, bot: Bot):
    """Закрытие тикета по команде /close"""
    topic_id = message.message_thread_id
    chat_id = message.chat.id
    operator_id = message.from_user.id
    
    log.info(f"🔒 Оператор {operator_id} закрывает тикет {topic_id}")
    
    user_id = await get_user_id_from_file(topic_id)
    
    try:
        await bot.close_forum_topic(
            chat_id=chat_id,
            message_thread_id=topic_id
        )
        await message.answer("✅ **Тикет закрыт.**\n\nОператоры больше не будут видеть этот топик как активный.")
        log.info(f"✅ Топик {topic_id} закрыт")
        
        if user_id:
            success = await send_message_to_user(
                bot, user_id,
                "✅ **Ваш тикет закрыт.**\n\n"
                "Спасибо, что обратились к нам!\n"
                "Если у вас остались вопросы, создайте новую заявку через /start."
            )
            if success:
                log.info(f"✅ Пользователь {user_id} уведомлён о закрытии тикета {topic_id}")
            else:
                log.warning(f"⚠️ Не удалось уведомить пользователя {user_id} о закрытии тикета {topic_id}")
            
    except Exception as e:
        log.error(f"❌ Ошибка при закрытии топика {topic_id}: {e}")
        await message.answer("❌ **Не удалось закрыть тикет.** Попробуйте позже.")


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
        "• Поддерживаются: текст, фото, видео, документы, стикеры, голосовые, аудио\n\n"
        "📌 **Цвета топиков:**\n"
        "• 🔴 Красный - новый тикет, ожидает ответа оператора\n"
        "• 🟢 Зелёный - оператор ответил пользователю\n\n"
        "📌 **Если пользователь не получает ответ:**\n"
        "• Убедитесь, что пользователь написал боту хотя бы одно сообщение\n"
        "• Попросите пользователя написать любое слово в чат с ботом\n"
        "• После этого создайте НОВУЮ заявку через /start\n\n"
        "📌 **Важно:** Старые заявки, созданные до обновления бота, не работают.\n"
        "Используйте только новые заявки."
    )
    await message.answer(help_text, parse_mode="HTML")
