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
                            log.info(f"Найден user_id {user_id} для топика {topic_id} из файла")
                            return user_id
                    except ValueError:
                        continue
        log.warning(f"Топик {topic_id} не найден в файле")
        return None
    except Exception as e:
        log.error(f"Ошибка чтения файла: {e}")
        return None


async def save_user_id_to_file(topic_id: int, chat_id: int, user_id: int) -> bool:
    """Сохраняет связь в файл (для отладки)"""
    try:
        os.makedirs('/app/data', exist_ok=True)
        async with aiofiles.open('/app/data/topic_links.txt', 'a') as f:
            await f.write(f"{topic_id},{chat_id},{user_id}\n")
        log.info(f"Сохранена связь: топик {topic_id} -> пользователь {user_id}")
        return True
    except Exception as e:
        log.error(f"Ошибка сохранения в файл: {e}")
        return False


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


@router.message(F.message_thread_id, F.chat.type == "supergroup")
async def operator_reply_handler(message: Message, bot: Bot):
    topic_id = message.message_thread_id
    chat_id = message.chat.id

    log.info(f"🔍 Сообщение в топике {topic_id} от {message.from_user.id}")

    # Ищем пользователя по топику в файле
    user_id = await get_user_id_from_file(topic_id)

    if not user_id:
        await message.reply(
            "⚠️ **Не удалось определить пользователя для этого топика.**\n\n"
            "💡 Попросите пользователя написать любое сообщение боту, "
            "а затем создайте новую заявку через /start."
        )
        return

    log.info(f"✅ Найден пользователь {user_id} для топика {topic_id}")

    if message.text:
        success = await send_message_to_user(bot, user_id, message.text)
        if success:
            # Меняем цвет топика на зелёный
            try:
                await bot.edit_forum_topic(
                    chat_id=chat_id,
                    message_thread_id=topic_id,
                    icon_color=0x00FF00
                )
                log.info(f"✅ Цвет топика {topic_id} изменён на зелёный")
            except Exception as e:
                log.warning(f"Не удалось изменить цвет: {e}")
            
            # Не спамим подтверждением, чтобы не засорять чат
            # await message.reply("✅ Сообщение доставлено")
        else:
            await message.reply("❌ Не удалось доставить сообщение пользователю.")
    else:
        await message.reply("⚠️ Пока поддерживаются только текстовые сообщения.")


@router.message(F.message_thread_id, F.text.lower() == "/close")
async def close_ticket_command(message: Message, bot: Bot):
    topic_id = message.message_thread_id
    chat_id = message.chat.id
    
    user_id = await get_user_id_from_file(topic_id)
    
    try:
        await bot.close_forum_topic(chat_id=chat_id, message_thread_id=topic_id)
        await message.answer("✅ Тикет закрыт.")
        
        if user_id:
            await send_message_to_user(bot, user_id, "✅ Ваш тикет закрыт. Спасибо!")
    except Exception as e:
        log.error(f"Ошибка закрытия: {e}")
        await message.answer("❌ Не удалось закрыть тикет.")
