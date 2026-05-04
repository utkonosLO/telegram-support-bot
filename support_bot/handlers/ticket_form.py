from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram import Bot
import os

from support_bot.statistics import save_ticket_info

router = Router()

class TicketForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_question_type = State()
    waiting_for_photo_action = State()
    waiting_for_sku = State()
    waiting_for_comment = State()
    waiting_for_packaging_photo = State()      # НОВОЕ: фото упаковки
    waiting_for_barcode_photo = State()        # НОВОЕ: фото штрихкода
    waiting_for_other_reason = State()
    waiting_for_attributes_sku = State()
    waiting_for_attributes_comment = State()
    waiting_for_no_photo_sku = State()
    waiting_for_no_photo_comment = State()


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


def get_skip_keyboard():
    """Клавиатура с кнопкой пропуска"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⏭️ Пропустить")]],
        resize_keyboard=True
    )


async def check_name(message: Message, state: FSMContext) -> bool:
    """Проверяет, представился ли пользователь"""
    data = await state.get_data()
    if not data.get('user_name'):
        await state.set_state(TicketForm.waiting_for_name)
        await message.answer(
            "📝 **Представьтесь, пожалуйста**\n\n"
            "Как нам к вам обращаться?\n"
            "*(Например: Иван Петров или просто Иван)*",
            reply_markup=ReplyKeyboardRemove()
        )
        return False
    return True


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
        "• Сообщить о товаре **без фото**\n"
        "• Запросить информацию у нашего отдела\n\n"
        "👉 Нажмите **ОК**, чтобы продолжить",
        reply_markup=kb
    )


@router.message(TicketForm.waiting_for_name, F.text == "✅ ОК")
async def ask_name(message: Message, state: FSMContext):
    await state.set_state(TicketForm.waiting_for_name)
    await message.answer(
        "📝 **Представьтесь, пожалуйста**\n\n"
        "Как нам к вам обращаться?",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(TicketForm.waiting_for_name, F.text)
async def save_name(message: Message, state: FSMContext):
    await state.update_data(user_name=message.text)
    await state.set_state(TicketForm.waiting_for_question_type)
    
    await message.answer(
        f"✨ **Приятно познакомиться, {message.text}!**\n\n"
        f"❓ **Какой у вас вопрос?**",
        reply_markup=get_main_menu_keyboard()
    )


# ========== ГЛАВНОЕ МЕНЮ ==========

@router.message(TicketForm.waiting_for_question_type, F.text == "📸 Некорректное фото")
async def photo_question(message: Message, state: FSMContext):
    if not await check_name(message, state):
        return
    await state.set_state(TicketForm.waiting_for_packaging_photo)
    await message.answer(
        "📸 **Шаг 1: Приложите фото упаковки товара**\n\n"
        "Сфотографируйте упаковку товара и отправьте фото.\n\n"
        "📌 *Это поможет нам идентифицировать товар*\n\n"
        "• Отправьте фото упаковки\n"
        "• Или нажмите «Пропустить»",
        reply_markup=get_skip_keyboard()
    )


@router.message(TicketForm.waiting_for_question_type, F.text == "✍️ Некорректные атрибуты")
async def attributes_question(message: Message, state: FSMContext):
    if not await check_name(message, state):
        return
    await state.set_state(TicketForm.waiting_for_attributes_sku)
    await message.answer(
        "✍️ **Некорректные атрибуты**\n\n📦 Введите **шестизначный номер SKU** товара:",
        reply_markup=get_back_keyboard()
    )


@router.message(TicketForm.waiting_for_question_type, F.text == "❌ Нет фото")
async def no_photo_question(message: Message, state: FSMContext):
    if not await check_name(message, state):
        return
    await state.set_state(TicketForm.waiting_for_no_photo_sku)
    await message.answer(
        "😔 **Товар без фото**\n\n"
        "📦 Введите **шестизначный номер SKU** товара, чтобы мы могли добавить его в план работ:",
        reply_markup=get_back_keyboard()
    )


@router.message(TicketForm.waiting_for_question_type, F.text == "❓ Задать вопрос")
async def ask_question(message: Message, state: FSMContext):
    if not await check_name(message, state):
        return
    await state.set_state(TicketForm.waiting_for_other_reason)
    await message.answer(
        "💬 **Опишите ваш вопрос или проблему**\n\n✏️ Напишите ваш вопрос:",
        reply_markup=get_back_keyboard()
    )


# ========== ФОТО УПАКОВКИ ==========

@router.message(TicketForm.waiting_for_packaging_photo, F.photo)
async def handle_packaging_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    await state.update_data(has_packaging_photo=True, packaging_photo_id=photo.file_id)
    await message.answer("✅ **Фото упаковки получено!**")
    await state.set_state(TicketForm.waiting_for_barcode_photo)
    await message.answer(
        "📸 **Шаг 2: Приложите фото штрихкода (ШК) с упаковки товара**\n\n"
        "Дополнительно приложите фото штрихкода на упаковке.\n\n"
        "📌 *Это поможет нам быстрее обработать вашу заявку*\n\n"
        "• Отправьте фото ШК\n"
        "• Или нажмите «Пропустить»",
        reply_markup=get_skip_keyboard()
    )


@router.message(TicketForm.waiting_for_packaging_photo, F.text == "⏭️ Пропустить")
async def skip_packaging_photo(message: Message, state: FSMContext):
    await state.update_data(has_packaging_photo=False)
    await message.answer("⏭️ **Фото упаковки пропущено**")
    await state.set_state(TicketForm.waiting_for_barcode_photo)
    await message.answer(
        "📸 **Шаг 2: Приложите фото штрихкода (ШК) с упаковки товара**\n\n"
        "Дополнительно приложите фото штрихкода на упаковке.\n\n"
        "📌 *Это поможет нам быстрее обработать вашу заявку*\n\n"
        "• Отправьте фото ШК\n"
        "• Или нажмите «Пропустить»",
        reply_markup=get_skip_keyboard()
    )


@router.message(TicketForm.waiting_for_packaging_photo, F.text)
async def invalid_packaging_response(message: Message, state: FSMContext):
    await message.answer(
        "❓ Пожалуйста, отправьте **фото упаковки** или нажмите **«Пропустить»**.",
        reply_markup=get_skip_keyboard()
    )


# ========== ФОТО ШТРИХКОДА ==========

@router.message(TicketForm.waiting_for_barcode_photo, F.photo)
async def handle_barcode_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    await state.update_data(has_barcode=True, barcode_photo_id=photo.file_id)
    await message.answer("✅ **Фото штрихкода получено!**")
    await state.set_state(TicketForm.waiting_for_photo_action)
    await message.answer(
        "🖼️ **Некорректное фото**\n\nЧто именно нужно сделать с фото?",
        reply_markup=get_photo_menu_keyboard()
    )


@router.message(TicketForm.waiting_for_barcode_photo, F.text == "⏭️ Пропустить")
async def skip_barcode_photo(message: Message, state: FSMContext):
    await state.update_data(has_barcode=False)
    await message.answer("⏭️ **Фото штрихкода пропущено**")
    await state.set_state(TicketForm.waiting_for_photo_action)
    await message.answer(
        "🖼️ **Некорректное фото**\n\nЧто именно нужно сделать с фото?",
        reply_markup=get_photo_menu_keyboard()
    )


@router.message(TicketForm.waiting_for_barcode_photo, F.text)
async def invalid_barcode_response(message: Message, state: FSMContext):
    await message.answer(
        "❓ Пожалуйста, отправьте **фото штрихкода** или нажмите **«Пропустить»**.",
        reply_markup=get_skip_keyboard()
    )


# ========== ФОТО МЕНЮ ==========

@router.message(TicketForm.waiting_for_photo_action, F.text == "🔄 Нужно сменить фото")
async def change_photo(message: Message, state: FSMContext):
    await state.update_data(photo_action="сменить фото", question_type="photo")
    await state.set_state(TicketForm.waiting_for_sku)
    await message.answer("📦 Введите **шестизначный номер SKU** товара:", reply_markup=get_back_keyboard())


@router.message(TicketForm.waiting_for_photo_action, F.text == "🗑️ Нужно удалить фото")
async def delete_photo(message: Message, state: FSMContext):
    await state.update_data(photo_action="удалить фото", question_type="photo")
    await state.set_state(TicketForm.waiting_for_sku)
    await message.answer("📦 Введите **шестизначный номер SKU** товара:", reply_markup=get_back_keyboard())


@router.message(TicketForm.waiting_for_photo_action, F.text == "❓ Другое")
async def photo_other(message: Message, state: FSMContext):
    await state.update_data(photo_action="другое", question_type="photo")
    await state.set_state(TicketForm.waiting_for_sku)
    await message.answer("📦 Введите **шестизначный номер SKU** товара:", reply_markup=get_back_keyboard())


@router.message(TicketForm.waiting_for_photo_action, F.text == "◀️ Назад")
async def photo_back(message: Message, state: FSMContext):
    await state.set_state(TicketForm.waiting_for_question_type)
    await message.answer("❓ **Какой у вас вопрос?**", reply_markup=get_main_menu_keyboard())


# ========== SKU И КОММЕНТАРИЙ ==========

@router.message(TicketForm.waiting_for_sku, F.text)
async def get_photo_sku(message: Message, state: FSMContext):
    if message.text == "◀️ Назад":
        await state.set_state(TicketForm.waiting_for_photo_action)
        await message.answer("🖼️ **Некорректное фото**\n\nЧто нужно сделать с фото?", reply_markup=get_photo_menu_keyboard())
        return
    
    await state.update_data(sku=message.text)
    await state.set_state(TicketForm.waiting_for_comment)
    await message.answer(
        "💬 **Введите комментарий**\n\nОпишите, что именно не так с фото:",
        reply_markup=get_back_keyboard()
    )


@router.message(TicketForm.waiting_for_comment, F.text)
async def get_photo_comment(message: Message, state: FSMContext):
    if message.text == "◀️ Назад":
        await state.set_state(TicketForm.waiting_for_sku)
        await message.answer("📦 Введите **шестизначный номер SKU** товара:", reply_markup=get_back_keyboard())
        return
    
    await state.update_data(comment=message.text)
    await create_ticket(message, state)


# ========== НЕТ ФОТО: SKU И КОММЕНТАРИЙ ==========

@router.message(TicketForm.waiting_for_no_photo_sku, F.text)
async def get_no_photo_sku(message: Message, state: FSMContext):
    if message.text == "◀️ Назад":
        await state.set_state(TicketForm.waiting_for_question_type)
        await message.answer("❓ **Какой у вас вопрос?**", reply_markup=get_main_menu_keyboard())
        return
    
    await state.update_data(sku=message.text, question_type="no_photo")
    await state.set_state(TicketForm.waiting_for_no_photo_comment)
    await message.answer(
        "💬 **Введите комментарий** (необязательно)\n\n"
        "Опишите ситуацию или оставьте поле пустым:",
        reply_markup=get_back_keyboard()
    )


@router.message(TicketForm.waiting_for_no_photo_comment, F.text)
async def get_no_photo_comment(message: Message, state: FSMContext, bot: Bot):
    if message.text == "◀️ Назад":
        await state.set_state(TicketForm.waiting_for_no_photo_sku)
        await message.answer("📦 Введите **шестизначный номер SKU** товара:", reply_markup=get_back_keyboard())
        return
    
    comment = message.text if message.text != "◀️ Назад" else ""
    await state.update_data(comment=comment)
    await create_no_photo_ticket(message, state, bot)


# ========== АТРИБУТЫ ==========

@router.message(TicketForm.waiting_for_attributes_sku, F.text)
async def get_attributes_sku(message: Message, state: FSMContext):
    if message.text == "◀️ Назад":
        await state.set_state(TicketForm.waiting_for_question_type)
        await message.answer("❓ **Какой у вас вопрос?**", reply_markup=get_main_menu_keyboard())
        return
    
    await state.update_data(sku=message.text, question_type="attributes")
    await state.set_state(TicketForm.waiting_for_attributes_comment)
    await message.answer(
        "💬 **Введите комментарий**\n\nОпишите, какой атрибут некорректен:",
        reply_markup=get_back_keyboard()
    )


@router.message(TicketForm.waiting_for_attributes_comment, F.text)
async def get_attributes_comment(message: Message, state: FSMContext, bot: Bot):
    if message.text == "◀️ Назад":
        await state.set_state(TicketForm.waiting_for_attributes_sku)
        await message.answer("📦 Введите **шестизначный номер SKU** товара:", reply_markup=get_back_keyboard())
        return
    
    await state.update_data(comment=message.text)
    await create_attributes_ticket(message, state, bot)


# ========== ДРУГОЙ ВОПРОС ==========

@router.message(TicketForm.waiting_for_other_reason, F.text)
async def get_other_question(message: Message, state: FSMContext, bot: Bot):
    if message.text == "◀️ Назад":
        await state.set_state(TicketForm.waiting_for_question_type)
        await message.answer("❓ **Какой у вас вопрос?**", reply_markup=get_main_menu_keyboard())
        return
    
    await state.update_data(question=message.text, is_other=True)
    await create_other_ticket(message, state, bot)


# ========== ФУНКЦИИ СОЗДАНИЯ ТИКЕТОВ ==========

async def create_ticket(message: Message, state: FSMContext):
    """Создание тикета для заявки по фото"""
    data = await state.get_data()
    
    user_name = data.get('user_name')
    if not user_name or user_name == 'Неизвестный':
        user_name = message.from_user.full_name or message.from_user.first_name or "Пользователь"
    
    sku = data.get('sku', 'Не указан')
    comment = data.get('comment', 'Не указан')
    photo_action = data.get('photo_action', '')
    has_packaging_photo = data.get('has_packaging_photo', False)
    has_barcode = data.get('has_barcode', False)
    packaging_photo_id = data.get('packaging_photo_id', None)
    barcode_photo_id = data.get('barcode_photo_id', None)
    
    OPERATOR_GROUP_ID = -1003953605950
    
    topic_name = f"📸 Заявка от {user_name} (SKU: {sku})"
    
    main_menu_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🏠 На главную")]],
        resize_keyboard=True
    )
    
    try:
        bot = message.bot
        
        topic = await bot.create_forum_topic(
            chat_id=OPERATOR_GROUP_ID,
            name=topic_name,
            icon_color=0xFF0000
        )
        topic_id = topic.message_thread_id
        
        os.makedirs('/app/data', exist_ok=True)
        with open('/app/data/topic_links.txt', 'a') as f:
            f.write(f"{topic_id},{OPERATOR_GROUP_ID},{message.from_user.id}\n")
        
        await save_ticket_info(topic_id, 'photo', message.from_user.id, user_name)
        
        ticket_text = (
            f"🆕 **НОВАЯ ЗАЯВКА**\n\n"
            f"👤 **Пользователь:** {user_name}\n"
            f"🆔 **ID:** `{message.from_user.id}`\n"
            f"📦 **SKU:** `{sku}`\n"
        )
        
        if photo_action:
            ticket_text += f"📸 **Действие:** {photo_action}\n"
        
        ticket_text += f"\n💬 **Комментарий:**\n{comment}\n\n"
        
        if has_packaging_photo:
            ticket_text += f"📦 **Фото упаковки:** получено ✅\n"
        else:
            ticket_text += f"📦 **Фото упаковки:** не получено ❌\n"
        
        if has_barcode:
            ticket_text += f"🔢 **Фото штрихкода:** получено ✅"
        else:
            ticket_text += f"🔢 **Фото штрихкода:** не получено ❌"
        
        await bot.send_message(chat_id=OPERATOR_GROUP_ID, text=ticket_text, message_thread_id=topic_id)
        
        if has_packaging_photo and packaging_photo_id:
            await bot.send_photo(chat_id=OPERATOR_GROUP_ID, photo=packaging_photo_id, message_thread_id=topic_id)
        
        if has_barcode and barcode_photo_id:
            await bot.send_photo(chat_id=OPERATOR_GROUP_ID, photo=barcode_photo_id, message_thread_id=topic_id)
        
        await message.answer(
            f"✅ **Заявка создана!**\n📌 Номер тикета: `{topic_id}`\n\n👇 Нажмите **«На главную»**",
            reply_markup=main_menu_kb
        )
        
        await state.clear()
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


async def create_no_photo_ticket(message: Message, state: FSMContext, bot: Bot):
    """Создание тикета для заявки "Нет фото" (без запроса фото)"""
    data = await state.get_data()
    
    user_name = data.get('user_name')
    if not user_name or user_name == 'Неизвестный':
        user_name = message.from_user.full_name or message.from_user.first_name or "Пользователь"
    
    sku = data.get('sku', 'Не указан')
    comment = data.get('comment', '')
    
    OPERATOR_GROUP_ID = -1003953605950
    
    topic_name = f"❌ Заявка от {user_name} (SKU: {sku}) - Нет фото"
    
    main_menu_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🏠 На главную")]],
        resize_keyboard=True
    )
    
    try:
        topic = await bot.create_forum_topic(
            chat_id=OPERATOR_GROUP_ID,
            name=topic_name,
            icon_color=0xFF0000
        )
        topic_id = topic.message_thread_id
        
        os.makedirs('/app/data', exist_ok=True)
        with open('/app/data/topic_links.txt', 'a') as f:
            f.write(f"{topic_id},{OPERATOR_GROUP_ID},{message.from_user.id}\n")
        
        await save_ticket_info(topic_id, 'no_photo', message.from_user.id, user_name)
        
        ticket_text = (
            f"🆕 **ЗАЯВКА: ТОВАР БЕЗ ФОТО**\n\n"
            f"👤 **Пользователь:** {user_name}\n"
            f"🆔 **ID:** `{message.from_user.id}`\n"
            f"📦 **SKU:** `{sku}`\n"
        )
        
        if comment:
            ticket_text += f"\n💬 **Комментарий:**\n{comment}\n"
        else:
            ticket_text += f"\n💬 **Комментарий:** не указан\n"
        
        await bot.send_message(chat_id=OPERATOR_GROUP_ID, text=ticket_text, message_thread_id=topic_id)
        
        await message.answer(
            f"✅ **Заявка принята!**\n"
            f"📌 Мы добавим товар с SKU `{sku}` в план работ.\n"
            f"📌 Номер тикета: `{topic_id}`\n\n"
            f"👇 Нажмите **«На главную»**",
            reply_markup=main_menu_kb
        )
        
        await state.clear()
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


async def create_attributes_ticket(message: Message, state: FSMContext, bot: Bot):
    """Создание тикета для атрибутов (без запроса фото)"""
    data = await state.get_data()
    
    user_name = data.get('user_name')
    if not user_name or user_name == 'Неизвестный':
        user_name = message.from_user.full_name or message.from_user.first_name or "Пользователь"
    
    sku = data.get('sku', 'Не указан')
    comment = data.get('comment', 'Не указан')
    
    OPERATOR_GROUP_ID = -1003953605950
    
    topic_name = f"✍️ Заявка от {user_name} (SKU: {sku})"
    
    main_menu_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🏠 На главную")]],
        resize_keyboard=True
    )
    
    try:
        topic = await bot.create_forum_topic(chat_id=OPERATOR_GROUP_ID, name=topic_name, icon_color=0xFF0000)
        topic_id = topic.message_thread_id
        
        os.makedirs('/app/data', exist_ok=True)
        with open('/app/data/topic_links.txt', 'a') as f:
            f.write(f"{topic_id},{OPERATOR_GROUP_ID},{message.from_user.id}\n")
        
        await save_ticket_info(topic_id, 'attributes', message.from_user.id, user_name)
        
        ticket_text = (
            f"🆕 **НОВАЯ ЗАЯВКА (АТРИБУТЫ)**\n\n"
            f"👤 **Пользователь:** {user_name}\n"
            f"🆔 **ID:** `{message.from_user.id}`\n"
            f"📦 **SKU:** `{sku}`\n\n"
            f"💬 **Комментарий:**\n{comment}"
        )
        
        await bot.send_message(chat_id=OPERATOR_GROUP_ID, text=ticket_text, message_thread_id=topic_id)
        
        await message.answer(
            f"✅ **Заявка создана!**\n📌 Номер тикета: `{topic_id}`\n\n👇 Нажмите **«На главную»**",
            reply_markup=main_menu_kb
        )
        
        await state.clear()
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


async def create_other_ticket(message: Message, state: FSMContext, bot: Bot):
    """Создание тикета для вопроса"""
    data = await state.get_data()
    
    user_name = data.get('user_name')
    if not user_name or user_name == 'Неизвестный':
        user_name = message.from_user.full_name or message.from_user.first_name or "Пользователь"
    
    question = data.get('question', 'Не указан')
    
    OPERATOR_GROUP_ID = -1003953605950
    
    topic_name = f"❓ Вопрос от {user_name}"
    
    main_menu_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🏠 На главную")]],
        resize_keyboard=True
    )
    
    try:
        topic = await bot.create_forum_topic(chat_id=OPERATOR_GROUP_ID, name=topic_name, icon_color=0xFF0000)
        topic_id = topic.message_thread_id
        
        os.makedirs('/app/data', exist_ok=True)
        with open('/app/data/topic_links.txt', 'a') as f:
            f.write(f"{topic_id},{OPERATOR_GROUP_ID},{message.from_user.id}\n")
        
        await save_ticket_info(topic_id, 'other', message.from_user.id, user_name)
        
        ticket_text = (
            f"🆕 **ВОПРОС ПОЛЬЗОВАТЕЛЯ**\n\n"
            f"👤 **Пользователь:** {user_name}\n"
            f"🆔 **ID:** `{message.from_user.id}`\n\n"
            f"💬 **Вопрос:**\n{question}"
        )
        
        await bot.send_message(chat_id=OPERATOR_GROUP_ID, text=ticket_text, message_thread_id=topic_id)
        
        await message.answer(
            f"✅ **Вопрос передан!**\n📌 Номер заявки: `{topic_id}`\n\n👇 Нажмите **«На главную»**",
            reply_markup=main_menu_kb
        )
        
        await state.clear()
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


@router.message(F.text == "🏠 На главную")
async def go_to_main_menu(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(TicketForm.waiting_for_question_type)
    await message.answer(
        "🏠 **Главное меню**\n\n❓ **Какой у вас вопрос?**",
        reply_markup=get_main_menu_keyboard()
    )
