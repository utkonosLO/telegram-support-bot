from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Bot

router = Router()

# Состояния анкеты
class TicketForm(StatesGroup):
    waiting_for_name = State()           # Ожидание имени
    waiting_for_question_type = State()   # Ожидание выбора типа вопроса
    waiting_for_photo_action = State()    # Ожидание действия с фото
    waiting_for_sku = State()             # Ожидание SKU
    waiting_for_comment = State()         # Ожидание комментария
    waiting_for_other_reason = State()    # Ожидание другого вопроса
    waiting_for_attributes_sku = State()  # Ожидание SKU для атрибутов
    waiting_for_attributes_comment = State()  # Ожидание комментария для атрибутов

# Клавиатуры
def get_main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📸 Некорректное фото")],
            [KeyboardButton(text="✍️ Некорректные атрибуты")],
            [KeyboardButton(text="❌ Нет фото")],
            [KeyboardButton(text="❓ Задать вопрос")]
        ],
        resize_keyboard=True
    )

def get_photo_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔄 Нужно сменить фото")],
            [KeyboardButton(text="🗑️ Нужно удалить фото")],
            [KeyboardButton(text="❓ Другое")],
            [KeyboardButton(text="◀️ Назад")]
        ],
        resize_keyboard=True
    )

def get_back_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="◀️ Назад")]],
        resize_keyboard=True
    )

# Старт бота
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(TicketForm.waiting_for_name)
    
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ ОК")]],
        resize_keyboard=True
    )
    
    await message.answer(
        "🏄‍♂️ **Ахой!**\n\n"
        "Это бот контент-команды **LO**.\n\n"
        "📌 В этого бота вы можете:\n"
        "• Оставить заявку на **некорректное фото** товара\n"
        "• Сообщить о **некорректных атрибутах**\n"
        "• Запросить информацию у нашего отдела\n\n"
        "👉 Нажмите **ОК**, чтобы продолжить",
        reply_markup=kb
    )

# После ОК - просим представиться
@router.message(TicketForm.waiting_for_name, F.text == "✅ ОК")
async def ask_name(message: Message, state: FSMContext):
    await state.set_state(TicketForm.waiting_for_name)
    await message.answer(
        "📝 **Представьтесь, пожалуйста**\n\n"
        "Как нам к вам обращаться?\n"
        "*(Например: Иван Петров или просто Иван)*",
        reply_markup=ReplyKeyboardRemove()
    )

# Сохраняем имя и показываем главное меню
@router.message(TicketForm.waiting_for_name, F.text)
async def save_name(message: Message, state: FSMContext):
    await state.update_data(user_name=message.text)
    await state.set_state(TicketForm.waiting_for_question_type)
    
    await message.answer(
        f"✨ **Приятно познакомиться, {message.text}!**\n\n"
        f"❓ **Какой у вас вопрос?**\n\n"
        f"Выберите категорию ниже 👇",
        reply_markup=get_main_menu_keyboard()
    )

# Главное меню: Некорректное фото
@router.message(TicketForm.waiting_for_question_type, F.text == "📸 Некорректное фото")
async def photo_question(message: Message, state: FSMContext):
    await state.set_state(TicketForm.waiting_for_photo_action)
    await message.answer(
        "🖼️ **Некорректное фото**\n\n"
        "Что именно нужно сделать с фото?",
        reply_markup=get_photo_menu_keyboard()
    )

# Главное меню: Некорректные атрибуты
@router.message(TicketForm.waiting_for_question_type, F.text == "✍️ Некорректные атрибуты")
async def attributes_question(message: Message, state: FSMContext):
    await state.set_state(TicketForm.waiting_for_attributes_sku)
    await message.answer(
        "✍️ **Некорректные атрибуты**\n\n"
        "📦 Введите **шестизначный номер SKU** товара:",
        reply_markup=get_back_keyboard()
    )

# Главное меню: Нет фото
@router.message(TicketForm.waiting_for_question_type, F.text == "❌ Нет фото")
async def no_photo(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "😢 **Нам очень жаль!**\n\n"
        "Мы ежедневно мониторим весь ассортимент и ставим в план товары без фото.\n\n"
        "📌 **Не требуется создавать дополнительных заявок** — если вы столкнулись с подобным, "
        "скорее всего, этот товар уже у нас в работе.\n\n"
        "✨ Всего доброго!",
        reply_markup=ReplyKeyboardRemove()
    )

# Главное меню: Задать вопрос
@router.message(TicketForm.waiting_for_question_type, F.text == "❓ Задать вопрос")
async def ask_question(message: Message, state: FSMContext):
    await state.set_state(TicketForm.waiting_for_other_reason)
    await message.answer(
        "💬 **Опишите ваш вопрос или проблему**\n\n"
        "Мы передадим его в соответствующий отдел:\n\n"
        "✏️ Напишите ваш вопрос:",
        reply_markup=get_back_keyboard()
    )

# Фото меню: Сменить фото
@router.message(TicketForm.waiting_for_photo_action, F.text == "🔄 Нужно сменить фото")
async def change_photo(message: Message, state: FSMContext):
    await state.update_data(photo_action="сменить фото")
    await state.set_state(TicketForm.waiting_for_sku)
    await message.answer(
        "📦 Введите **шестизначный номер SKU** товара:",
        reply_markup=get_back_keyboard()
    )

# Фото меню: Удалить фото
@router.message(TicketForm.waiting_for_photo_action, F.text == "🗑️ Нужно удалить фото")
async def delete_photo(message: Message, state: FSMContext):
    await state.update_data(photo_action="удалить фото")
    await state.set_state(TicketForm.waiting_for_sku)
    await message.answer(
        "📦 Введите **шестизначный номер SKU** товара:",
        reply_markup=get_back_keyboard()
    )

# Фото меню: Другое
@router.message(TicketForm.waiting_for_photo_action, F.text == "❓ Другое")
async def photo_other(message: Message, state: FSMContext):
    await state.update_data(photo_action="другое")
    await state.set_state(TicketForm.waiting_for_sku)
    await message.answer(
        "📦 Введите **шестизначный номер SKU** товара:",
        reply_markup=get_back_keyboard()
    )

# Получаем SKU для фото
@router.message(TicketForm.waiting_for_sku, F.text)
async def get_photo_sku(message: Message, state: FSMContext):
    if message.text == "◀️ Назад":
        await state.set_state(TicketForm.waiting_for_question_type)
        await message.answer(
            "❓ **Какой у вас вопрос?**",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    await state.update_data(sku=message.text)
    await state.set_state(TicketForm.waiting_for_comment)
    await message.answer(
        "💬 **Введите комментарий**\n\n"
        "Опишите, что именно не так с фото, какие нужны изменения:\n\n"
        "✏️ Ваш комментарий:",
        reply_markup=get_back_keyboard()
    )

# Получаем SKU для атрибутов
@router.message(TicketForm.waiting_for_attributes_sku, F.text)
async def get_attributes_sku(message: Message, state: FSMContext):
    if message.text == "◀️ Назад":
        await state.set_state(TicketForm.waiting_for_question_type)
        await message.answer(
            "❓ **Какой у вас вопрос?**",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    await state.update_data(sku=message.text)
    await state.set_state(TicketForm.waiting_for_attributes_comment)
    await message.answer(
        "💬 **Введите комментарий**\n\n"
        "Опишите, какой атрибут некорректен, какие данные указаны неверно:\n\n"
        "✏️ Ваш комментарий:",
        reply_markup=get_back_keyboard()
    )

# Получаем комментарий для фото
@router.message(TicketForm.waiting_for_comment, F.text)
async def get_photo_comment(message: Message, state: FSMContext, bot: Bot):
    if message.text == "◀️ Назад":
        await state.set_state(TicketForm.waiting_for_photo_action)
        await message.answer(
            "🖼️ **Некорректное фото**\n\nЧто нужно сделать с фото?",
            reply_markup=get_photo_menu_keyboard()
        )
        return
    
    await state.update_data(comment=message.text)
    await create_ticket(message, state, bot, "📸")

# Получаем комментарий для атрибутов
@router.message(TicketForm.waiting_for_attributes_comment, F.text)
async def get_attributes_comment(message: Message, state: FSMContext, bot: Bot):
    if message.text == "◀️ Назад":
        await state.set_state(TicketForm.waiting_for_question_type)
        await message.answer(
            "❓ **Какой у вас вопрос?**",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    await state.update_data(comment=message.text)
    await create_ticket(message, state, bot, "✍️")

# Получаем другой вопрос
@router.message(TicketForm.waiting_for_other_reason, F.text)
async def get_other_question(message: Message, state: FSMContext, bot: Bot):
    if message.text == "◀️ Назад":
        await state.set_state(TicketForm.waiting_for_question_type)
        await message.answer(
            "❓ **Какой у вас вопрос?**",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    await state.update_data(question=message.text, is_other=True)
    await create_other_ticket(message, state, bot)

# Функция создания топика для фото/атрибутов
async def create_ticket(message: Message, state: FSMContext, bot: Bot, icon: str):
    data = await state.get_data()
    user_name = data.get('user_name', 'Неизвестный')
    sku = data.get('sku', 'Не указан')
    comment = data.get('comment', 'Не указан')
    photo_action = data.get('photo_action', '')
    
    OPERATOR_GROUP_ID = -1003953605950  # Замените на ваш ID группы
    
    # Формируем название топика
    topic_name = f"{icon} Заявка от {user_name} (SKU: {sku})"
    
    try:
        # Создаём топик с красным смайликом 🔴
        topic = await bot.create_forum_topic(
            chat_id=OPERATOR_GROUP_ID,
            name=topic_name,
            icon_color=0xFF0000  # Красный цвет
        )
        topic_id = topic.message_thread_id
        
        # Отправляем сообщение в топик
        ticket_text = (
            f"🆕 **НОВАЯ ЗАЯВКА**\n\n"
            f"👤 **Пользователь:** {user_name}\n"
            f"🆔 **ID:** `{message.from_user.id}`\n"
            f"📦 **SKU:** `{sku}`\n"
        )
        
        if photo_action:
            ticket_text += f"📸 **Действие:** {photo_action}\n"
        
        ticket_text += f"\n💬 **Комментарий:**\n{comment}"
        
        await bot.send_message(
            chat_id=OPERATOR_GROUP_ID,
            text=ticket_text,
            message_thread_id=topic_id
        )
        
        # Отправляем пользователю подтверждение
        await message.answer(
            "✅ **Заявка успешно создана!**\n\n"
            "Наши операторы скоро свяжутся с вами в этом чате.\n"
            "📌 Номер вашего тикета: `" + str(topic_id) + "`",
            reply_markup=ReplyKeyboardRemove()
        )
        
        await state.clear()
        
    except Exception as e:
        await message.answer(
            "❌ **Ошибка при создании заявки**\n\n"
            "Пожалуйста, попробуйте позже или обратитесь в поддержку напрямую.",
            reply_markup=ReplyKeyboardRemove()
        )
        print(f"Ошибка создания топика: {e}")

# Функция создания топика для "Задать вопрос"
async def create_other_ticket(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user_name = data.get('user_name', 'Неизвестный')
    question = data.get('question', 'Не указан')
    
    OPERATOR_GROUP_ID = -1003953605950
    
    topic_name = f"❓ Вопрос от {user_name}"
    
    try:
        topic = await bot.create_forum_topic(
            chat_id=OPERATOR_GROUP_ID,
            name=topic_name,
            icon_color=0xFF0000
        )
        topic_id = topic.message_thread_id
        
        ticket_text = (
            f"🆕 **ВОПРОС ПОЛЬЗОВАТЕЛЯ**\n\n"
            f"👤 **Пользователь:** {user_name}\n"
            f"🆔 **ID:** `{message.from_user.id}`\n\n"
            f"💬 **Вопрос:**\n{question}"
        )
        
        await bot.send_message(
            chat_id=OPERATOR_GROUP_ID,
            text=ticket_text,
            message_thread_id=topic_id
        )
        
        await message.answer(
            "✅ **Ваш вопрос передан в наш отдел!**\n\n"
            "Ответ придёт вам в этот чат в ближайшее время.\n"
            "📌 Номер вашей заявки: `" + str(topic_id) + "`",
            reply_markup=ReplyKeyboardRemove()
        )
        
        await state.clear()
        
    except Exception as e:
        await message.answer(
            "❌ **Ошибка при отправке вопроса**\n\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=ReplyKeyboardRemove()
        )
        print(f"Ошибка создания топика: {e}")
