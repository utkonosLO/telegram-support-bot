import logging
import os
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command

router = Router()
log = logging.getLogger(__name__)


def find_topic_for_user(user_id: int) -> int | None:
    """Находит topic_id для пользователя"""
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
                            return int(parts[0])
                    except ValueError:
                        continue
        return None
    except Exception as e:
        log.error(f"Ошибка поиска топика: {e}")
        return None


async def send_to_topic(bot: Bot, topic_id: int, user_id: int, user_name: str, message: Message):
    """Отправляет сообщение пользователя в указанный топик"""
    OPERATOR_GROUP_ID = -1003953605950
    
    try:
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
        elif message.document:
            await bot.send_document(
                chat_id=OPERATOR_GROUP_ID,
                document=message.document.file_id,
                caption=f"👤 **{user_name}** (ID: `{user_id}`):\n{message.caption or 'Документ'}",
                message_thread_id=topic_id
            )
        else:
            await bot.send_message(
                chat_id=OPERATOR_GROUP_ID,
                text=f"👤 **{user_name}** (ID: `{user_id}`): [Неподдерживаемый тип]",
                message_thread_id=topic_id
            )
        return True
    except Exception as e:
        log.error(f"Ошибка отправки в топик {topic_id}: {e}")
        return False


async def create_new_topic(bot: Bot, user_id: int, user_name: str, message: Message) -> int | None:
    """Создаёт новый топик и сохраняет связь"""
    OPERATOR_GROUP_ID = -1003953605950
    
    try:
        topic_name = f"📩 Диалог с {user_name}"
        
        topic = await bot.create_forum_topic(
            chat_id=OPERATOR_GROUP_ID,
            name=topic_name,
            icon_color=0xFF0000
        )
        topic_id = topic.message_thread_id
        
        # Сохраняем связь
        os.makedirs('/app/data', exist_ok=True)
        with open('/app/data/topic_links.txt', 'a') as f:
            f.write(f"{topic_id},{OPERATOR_GROUP_ID},{user_id}\n")
        
        # Отправляем первое сообщение
        await send_to_topic(bot, topic_id, user_id, user_name, message)
        
        return topic_id
    except Exception as e:
        log.error(f"Ошибка создания топика: {e}")
        return None


@router.message(Command("start"))
async def start_command(message: Message, bot: Bot):
    """Обработчик команды /start — всегда создаёт новый топик"""
    user_id = message.from_user.id
    user_name = message.from_user.full_name or message.from_user.first_name or "Пользователь"
    
    # Принудительно создаём новый топик
    topic_id = await create_new_topic(bot, user_id, user_name, message)
    
    if topic_id:
        await message.answer(
            "✅ **Чат с оператором создан!**\n\n"
            "Напишите ваш вопрос, и мы ответим вам в ближайшее время.\n"
            "История предыдущих обращений не связана с этим."
        )
    else:
        await message.answer("❌ Ошибка при создании чата. Попробуйте позже.")


@router.message(F.chat.type == "private")
async def user_message_handler(message: Message, bot: Bot):
    """Обработчик обычных сообщений от пользователя"""
    user_id = message.from_user.id
    user_name = message.from_user.full_name or message.from_user.first_name or "Пользователь"
    
    # Ищем существующий топик
    topic_id = find_topic_for_user(user_id)
    
    if topic_id:
        # Отправляем в существующий топик
        success = await send_to_topic(bot, topic_id, user_id, user_name, message)
        if success:
            log.info(f"Сообщение отправлено в топик {topic_id} для {user_name}")
        else:
            # Если ошибка (например, топик закрыт) — создаём новый
            log.warning(f"Ошибка отправки в топик {topic_id}, создаём новый")
            topic_id = await create_new_topic(bot, user_id, user_name, message)
            if topic_id:
                await message.answer("✅ Создан новый чат с оператором. Ваше сообщение отправлено.")
            else:
                await message.answer("❌ Ошибка. Попробуйте позже.")
    else:
        # Нет топика — создаём новый
        topic_id = await create_new_topic(bot, user_id, user_name, message)
        if topic_id:
            await message.answer(
                "✅ **Ваше сообщение передано оператору!**\n\n"
                "Мы ответим вам в ближайшее время."
            )
        else:
            await message.answer("❌ Ошибка при создании чата. Попробуйте позже.")
