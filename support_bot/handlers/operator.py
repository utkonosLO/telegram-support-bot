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
    """Сохраняет связь в файл (для отладки)"""
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
    """Отправляет сообщение пользователю с подробным логированием"""
    try:
        log.info(f"📤 Отправляем сообщение пользователю {user_id}")
        log.info(f"📝 Текст: {text[:100]}..." if len(text) > 100 else f"📝 Текст: {text}")
        
        await bot.send_message(
            chat_id=user_id, 
            text=text, 
            parse_mode=parse_mode
        )
        
        log.info(f"✅ Сообщение успешно доставлено пользователю {user_id}")
        return True
        
    except TelegramForbiddenError:
        log.error(f"❌ TelegramForbiddenError: бот заблокирован или пользователь {user_id} не начал диалог")
        log.error(f"💡 Решение: попросите пользователя написать боту любое сообщение")
        return False
        
    except TelegramBadRequest as e:
        log.error(f"❌ TelegramBadRequest: {e}")
        return False
        
    except Exception as e:
        log.error(f"❌ Неизвестная ошибка: {e}")
        return False


@router.message(F.message_thread_id, F.chat.type == "supergroup")
async def operator_reply_handler(message: Message, bot: Bot):
    """Обработчик ответов оператора в топике"""
    topic_id = message.message_thread_id
    chat_id = message.chat.id
    operator_id = message.from_user.id

    log.info(f"🔍 Получено сообщение в топике {topic_id} от оператора {operator_id}")
    log.info(f"📝 Текст сообщения: {message.text[:100] if message.text else '[не текст]'}")

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

    # Проверяем, есть ли текст сообщения
    if not message.text:
        log.warning(f"⚠️ Получено сообщение без текста (возможно, медиа) в топике {topic_id}")
        await message.reply("⚠️ Пока поддерживаются только текстовые сообщения. Медиа-файлы будут добавлены позже.")
        return

    # Отправляем сообщение пользователю
    success = await send_message_to_user(bot, user_id, message.text)

    if success:
        log.info(f"✅ Сообщение доставлено пользователю {user_id}")
        
        # Меняем цвет топика на зелёный
        try:
            await bot.edit_forum_topic(
                chat_id=chat_id,
                message_thread_id=topic_id,
                icon_color=0x00FF00  # Зелёный
            )
            log.info(f"🎨 Цвет топика {topic_id} изменён на зелёный")
        except Exception as e:
            log.warning(f"⚠️ Не удалось изменить цвет топика {topic_id}: {e}")
        
        # Не отправляем подтверждение оператору, чтобы не засорять чат
        # (можно раскомментировать, если нужно)
        # await message.reply("✅ Сообщение доставлено пользователю")
    else:
        log.error(f"❌ Не удалось доставить сообщение пользователю {user_id}")
        await message.reply(
            "❌ **Не удалось доставить сообщение пользователю.**\n\n"
            "💡 **Возможные причины:**\n"
            "• Пользователь не начал диалог с ботом\n"
            "• Пользователь заблокировал бота\n\n"
            "🔧 **Решение:** Попросите пользователя написать боту любое сообщение.\n"
            "После этого создайте НОВУЮ заявку через /start."
        )


@router.message(F.message_thread_id, F.text.lower() == "/close")
async def close_ticket_command(message: Message, bot: Bot):
    """Закрытие тикета по команде /close"""
    topic_id = message.message_thread_id
    chat_id = message.chat.id
    operator_id = message.from_user.id
    
    log.info(f"🔒 Оператор {operator_id} закрывает тикет {topic_id}")
    
    # Получаем user_id для уведомления
    user_id = await get_user_id_from_file(topic_id)
    
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
        else:
            log.warning(f"⚠️ Не найден пользователь для уведомления о закрытии тикета {topic_id}")
            
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
        "• Поддерживаются только текстовые сообщения\n\n"
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
