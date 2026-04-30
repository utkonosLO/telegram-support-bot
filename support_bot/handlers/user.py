import logging
import os
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command

router = Router()
log = logging.getLogger(__name__)


def find_last_topic_for_user(user_id: int) -> int | None:
    """Находит ПОСЛЕДНИЙ топик для пользователя (по записи в файле)"""
    try:
        file_path = '/app/data/topic_links.txt'
        if not os.path.exists(file_path):
            log.warning("Файл связей не существует")
            return None
        
        last_topic = None
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(',')
                if len(parts) >= 3:
                    try:
                        if int(parts[2]) == user_id:
                            last_topic = int(parts[0])  # Берем последний (перезаписываем)
                    except ValueError:
                        continue
        return last_topic
    except Exception as e:
        log.error(f"Ошибка чтения: {e}")
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
            log.info(f"✅ Текст отправлен в топик {topic_id}")
        elif message.photo:
            await bot.send_photo(
                chat_id=OPERATOR_GROUP_ID,
                photo=message.photo[-1].file_id,
                caption=f"👤 **{user_name}** (ID: `{user_id}`):\n{message.caption or 'Фото'}",
                message_thread_id=topic_id
            )
            log.info(f"✅ Фото отправлено в топик {topic_id}")
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


@router.message(Command("start"))
async def start_command(message: Message, bot: Bot):
    """Обработчик /start — показывает меню"""
    await message.answer(
        "🏠 **Главное меню**\n\n"
        "Чтобы создать НОВУЮ заявку, нажмите кнопку ниже:",
        reply_markup=None  # Здесь можно добавить кнопку меню
    )


@router.message(F.chat.type == "private")
async def user_message_handler(message: Message, bot: Bot):
    """Пересылает сообщение в ПОСЛЕДНИЙ существующий топик"""
    user_id = message.from_user.id
    user_name = message.from_user.full_name or message.from_user.first_name or "Пользователь"
    
    # Находим последний топик пользователя
    topic_id = find_last_topic_for_user(user_id)
    
    if topic_id:
        # Отправляем в существующий топик
        success = await send_to_topic(bot, topic_id, user_id, user_name, message)
        if success:
            await message.answer("✅ Сообщение отправлено оператору.")
        else:
            await message.answer("❌ Ошибка при отправке. Попробуйте позже.")
    else:
        # Нет топика — предлагаем создать заявку через /start
        await message.answer(
            "👋 **У вас нет активных заявок.**\n\n"
            "Чтобы создать новую заявку, отправьте команду /start и заполните анкету.\n\n"
            "📌 Каждая новая заявка создаёт отдельный диалог."
        )
