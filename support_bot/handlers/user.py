import logging
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest

from support_bot.db import Database
from support_bot.topic_manager import TopicManager

router = Router()
log = logging.getLogger(__name__)


def get_user_id_from_file(topic_id: int) -> int | None:
    """Получает user_id из файла (синхронно)"""
    import os
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
    except Exception:
        return None


def find_topic_for_user(user_id: int) -> int | None:
    """Находит открытый топик для пользователя"""
    import os
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
                        if int(parts[2]) == user_id:
                            return int(parts[0])  # topic_id
                    except ValueError:
                        continue
        return None
    except Exception:
        return None


@router.message(F.chat.type == "private")
async def user_message_handler(
    message: Message,
    bot: Bot,
    db: Database,
    topics: TopicManager,
    log_messages: bool = True
):
    """
    Обработчик сообщений от пользователя в личку
    """
    user_id = message.from_user.id
    user_name = message.from_user.full_name
    
    log.info(f"📩 Получено сообщение от пользователя {user_id} ({user_name}): {message.text[:50] if message.text else '[медиа]'}")

    # Проверяем, есть ли уже открытый топик для этого пользователя
    topic_id = find_topic_for_user(user_id)
    
    OPERATOR_GROUP_ID = -1003953605950  # Замените на ваш ID группы

    if topic_id:
        # Топик существует — отправляем сообщение в него
        log.info(f"✅ Найден существующий топик {topic_id} для пользователя {user_id}")
        
        try:
            # Отправляем сообщение пользователя в существующий топик
            if message.text:
                await bot.send_message(
                    chat_id=OPERATOR_GROUP_ID,
                    text=f"👤 **{user_name}** (ID: `{user_id}`):\n{message.text}",
                    message_thread_id=topic_id
                )
            elif message.photo:
                await bot.send_photo(
                    chat_id=OPERATOR_GROUP_ID,
                    photo=message.photo[-1].file_id,
                    caption=f"👤 **{user_name}** (ID: `{user_id}`):\n{message.caption or 'Фото'}",
                    message_thread_id=topic_id
                )
            else:
                await bot.send_message(
                    chat_id=OPERATOR_GROUP_ID,
                    text=f"👤 **{user_name}** (ID: `{user_id}`): [Неподдерживаемый тип сообщения]",
                    message_thread_id=topic_id
                )
            
            log.info(f"✅ Сообщение отправлено в существующий топик {topic_id}")
            
        except Exception as e:
            log.error(f"❌ Ошибка при отправке в топик {topic_id}: {e}")
            # Если ошибка — создаём новый топик
            topic_id = None
    
    if not topic_id:
        # Нет открытого топика — создаём новый
        log.info(f"🆕 Создаём новый топик для пользователя {user_id}")
        
        topic_name = f"📩 Сообщение от {user_name}"
        
        try:
            topic = await bot.create_forum_topic(
                chat_id=OPERATOR_GROUP_ID,
                name=topic_name,
                icon_color=0xFF0000
            )
            topic_id = topic.message_thread_id
            
            # Сохраняем связь
            import os
            os.makedirs('/app/data', exist_ok=True)
            with open('/app/data/topic_links.txt', 'a') as f:
                f.write(f"{topic_id},{OPERATOR_GROUP_ID},{user_id}\n")
            
            log.info(f"✅ Создан новый топик {topic_id} для пользователя {user_id}")
            
            # Отправляем приветственное сообщение
            await bot.send_message(
                chat_id=OPERATOR_GROUP_ID,
                text=f"🆕 **НОВЫЙ ДИАЛОГ**\n\n👤 **Пользователь:** {user_name}\n🆔 **ID:** `{user_id}`\n\n💬 Первое сообщение:",
                message_thread_id=topic_id
            )
            
            # Отправляем само сообщение
            if message.text:
                await bot.send_message(
                    chat_id=OPERATOR_GROUP_ID,
                    text=message.text,
                    message_thread_id=topic_id
                )
            elif message.photo:
                await bot.send_photo(
                    chat_id=OPERATOR_GROUP_ID,
                    photo=message.photo[-1].file_id,
                    caption=message.caption,
                    message_thread_id=topic_id
                )
                
        except Exception as e:
            log.error(f"❌ Ошибка при создании топика: {e}")
            await message.answer("❌ Произошла ошибка. Пожалуйста, попробуйте позже.")
