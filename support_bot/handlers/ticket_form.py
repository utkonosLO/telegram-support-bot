from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram import Bot

router = Router()

# Состояния анкеты
class TicketForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_question_type = State()
    waiting_for_photo_action = State()
    waiting_for_sku = State()
    waiting_for_comment = State()
    waiting_for_photo_upload = State()
    waiting_for_other_reason = State()
    waiting_for_attributes_sku = State()
    waiting_for_attributes_comment = State()


# ========== КЛАВИАТУРЫ ==========

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


def get_photo_upload_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📷 Загрузить фото")],
            [KeyboardButton(text="❌ Нет возможности")]
        ],
        resize_keyboard=True
    )


# ========== СТАРТ ==========

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


@router.message(TicketForm.waiting_for_name, F.text == "✅ ОК")
async def ask_name(message: Message, state: FSMContext):
    await state.set_state(TicketForm.waiting_for_name)
    await message.answer(
        "📝 **Представьтесь, пожалуйста**\n\n"
        "Как нам к вам обращаться?\n"
        "*(Например: Иван Петров или просто Иван)*",
        reply_markup=ReplyKeyboardRemove()
    )


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


# ========== ГЛАВНОЕ МЕНЮ ==========

@router.message(TicketForm.waiting_for_question_type, F.text == "📸 Некорректное фото")
async def photo_question(message: Message, state: FSMContext):
    await state.set_state(TicketForm.waiting_for_photo_action)
    await message.answer(
        "🖼️ **Некорректное фото**\n\n"
        "Что именно нужно сделать с фото?",
        reply_markup=get_photo_menu_keyboard()
    )


@router.message(TicketForm.waiting_for_question_type, F.text == "✍️ Некорректные атрибуты")
async def attributes_question(message: Message, state: FSMContext):
    await state.set_state(TicketForm.waiting_for_attributes_sku)
    await message.answer(
        "✍️ **Некорректные атрибуты**\n\n"
        "📦 Введите **шестизначный номер SKU** товара:",
        reply_markup=get_back_keyboard()
    )


@router.message(TicketForm.waiting_for_question_type, F.text == "❌ Нет фото")
async def no_photo(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "😢 **Нам очень жаль!**\n\n"
        "Мы ежедневно мониторим весь ассортимент и ставим в план товары без фото.\n\n"
        "📌 **Не требуется создавать дополнительных заявок** — если вы столкнулись с подобным, "
        "скорее всего, этот товар уже у нас в работе.\n\n"
        "✨ Всего доброго!\n\n"
        "👇 Нажмите **/start**, чтобы начать заново.",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(TicketForm.waiting_for_question_type, F.text == "❓ Задать вопрос")
async def ask_question(message: Message, state: FSMContext):
    await state.set_state(TicketForm.waiting_for_other_reason)
    await message.answer(
        "💬 **Опишите ваш вопрос или проблему**\n\n"
        "Мы передадим его в соответствующий отдел:\n\n"
        "✏️ Напишите ваш вопрос:",
        reply_markup=get_back_keyboard()
    )


# ========== ФОТО МЕНЮ ==========

@router.message(TicketForm.waiting_for_photo_action, F.text == "🔄 Нужно сменить фото")
async def change_photo(message: Message, state: FSMContext):
    await state.update_data(photo_action="сменить фото", question_type="photo")
    await state.set_state(TicketForm.waiting_for_sku)
    await message.answer(
        "📦 Введите **шестизначный номер SKU** товара:",
        reply_markup=get_back_keyboard()
    )


@router.message(TicketForm.waiting_for_photo_action, F.text == "🗑️ Нужно удалить фото")
async def delete_photo(message: Message, state: FSMContext):
    await state.update_data(photo_action="удалить фото", question_type="photo")
    await state.set_state(TicketForm.waiting_for_sku)
    await message.answer(
        "📦 Введите **шестизначный номер SKU** товара:",
        reply_markup=get_back_keyboard()
    )


@router.message(TicketForm.waiting_for_photo_action, F.text == "❓ Другое")
async def photo_other(message: Message, state: FSMContext):
    await state.update_data(photo_action="другое", question_type="photo")
    await state.set_state(TicketForm.waiting_for_sku)
    await message.answer(
        "📦 Введите **шестизначный номер SKU** товара:",
        reply_markup=get_back_keyboard()
    )


@router.message(TicketForm.waiting_for_photo_action, F.text == "◀️ Назад")
async def photo_back(message: Message, state: FSMContext):
    await state.set_state(TicketForm.waiting_for_question_type)
    await message.answer(
        "❓ **Какой у вас вопрос?**",
        reply_markup=get_main_menu_keyboard()
    )


# ========== SKU И КОММЕНТАРИЙ ==========

@router.message(TicketForm.waiting_for_sku, F.text)
async def get_photo_sku(message: Message, state: FSMContext):
    if message.text == "◀️ Назад":
        await state.set_state(TicketForm.waiting_for_photo_action)
        await message.answer(
            "🖼️ **Некорректное фото**\n\nЧто нужно сделать с фото?",
            reply_markup=get_photo_menu_keyboard()
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


@router.message(TicketForm.waiting_for_comment, F.text)
async def get_photo_comment(message: Message, state: FSMContext):
    if message.text == "◀️ Назад":
        await state.set_state(TicketForm.waiting_for_sku)
        await message.answer(
            "📦 Введите **шестизначный номер SKU** товара:",
            reply_markup=get_back_keyboard()
        )
        return
    
    await state.update_data(comment=message.text)
    await state.set_state(TicketForm.waiting_for_photo_upload)
    
    await message.answer(
        "📸 **У вас есть возможность загрузить корректное фото?**\n\n"
        "📌 *Подойдет фото с телефона на светлом фоне с равномерным освещением.*\n\n"
        "Вы можете:\n"
        "• Отправить фото в этом сообщении\n"
        "• Нажать «❌ Нет возможности», если не можете загрузить",
        reply_markup=get_photo_upload_keyboard()
    )


# ========== ЗАГРУЗКА ФОТО ==========

@router.message(TicketForm.waiting_for_photo_upload, F.photo)
async def handle_photo_upload(message: Message, state: FSMContext, bot: Bot):
    photo = message.photo[-1]
    await state.update_data(has_photo=True, photo_file_id=photo.file_id)
    
    await message.answer(
        "✅ **Спасибо! Фото успешно получено.**\n\n"
        "Мы передадим его вместе с вашей заявкой.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    await create_ticket(message, state, bot, "📸")


@router.message(TicketForm.waiting_for_photo_upload, F.text == "❌ Нет возможности")
async def no_photo_upload(message: Message, state: FSMContext, bot: Bot):
    await state.update_data(has_photo=False)
    
    await message.answer(
        "😔 **Очень жаль!**\n\n"
        "Мы всё равно передадим вашу заявку в работу.\n"
        "Постараемся помочь с описательной частью, которую вы указали.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    await create_ticket(message, state, bot, "📸")


@router.message(TicketForm.waiting_for_photo_upload, F.text)
async def invalid_photo_response(message: Message, state: FSMContext):
    await message.answer(
        "❓ Пожалуйста, отправьте **фото** или нажмите кнопку **«❌ Нет возможности»**.",
        reply_markup=get_photo_upload_keyboard()
    )


# ========== АТРИБУТЫ ==========

@router.message(TicketForm.waiting_for_attributes_sku, F.text)
async def get_attributes_sku(message: Message, state: FSMContext):
    if message.text == "◀️ Назад":
        await state.set_state(TicketForm.waiting_for_question_type)
        await message.answer(
            "❓ **Какой у вас вопрос?**",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    await state.update_data(sku=message.text, question_type="attributes")
    await state.set_state(TicketForm.waiting_for_attributes_comment)
    await message.answer(
        "💬 **Введите комментарий**\n\n"
        "Опишите, какой атрибут некорректен, какие данные указаны неверно:\n\n"
        "✏️ Ваш комментарий:",
        reply_markup=get_back_keyboard()
    )


@router.message(TicketForm.waiting_for_attributes_comment, F.text)
async def get_attributes_comment(message: Message, state: FSMContext, bot: Bot):
    if message.text == "◀️ Назад":
        await state.set_state(TicketForm.waiting_for_attributes_sku)
        await message.answer(
            "📦 Введите **шестизначный номер SKU** товара:",
            reply_markup=get_back_keyboard()
        )
        return
    
    await state.update_data(comment=message.text)
    await create_attributes_ticket(message, state, bot)


# ========== ДРУГОЙ ВОПРОС ==========

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


# ========== СОЗДАНИЕ ТИКЕТА (ФОТО) ==========

async def create_ticket(message: Message, state: FSMContext, bot: Bot, icon: str):
    data = await state.get_data()
    user_name = data.get('user_name', 'Неизвестный')
    sku = data.get('sku', 'Не указан')
    comment = data.get('comment', 'Не указан')
    photo_action = data.get('photo_action', '')
    has_photo = data.get('has_photo', False)
    photo_file_id = data.get('photo_file_id', None)
    
    OPERATOR_GROUP_ID = -1003953605950  # ЗАМЕНИТЕ НА ВАШ ID ГРУППЫ
    
    topic_name = f"{icon} Заявка от {user_name} (SKU: {sku})"
    
    main_menu_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🏠 На главную")]],
        resize_keyboard=True
    )
    
    try:
        # Создаём топик
        topic = await bot.create_forum_topic(
            chat_id=OPERATOR_GROUP_ID,
            name=topic_name,
            icon_color=0xFF0000
        )
        topic_id = topic.message_thread_id
        
        # ========== СОХРАНЯЕМ СВЯЗЬ ==========
        db = message.bot.data.get("db") if hasattr(message.bot, 'data') else None
        if db:
            try:
                # Пробуем execute + commit
                if hasattr(db, 'execute'):
                    await db.execute(
                        "INSERT OR REPLACE INTO topic_links (topic_id, chat_id, user_id) VALUES (?, ?, ?)",
                        (topic_id, OPERATOR_GROUP_ID, message.from_user.id)
                    )
                    if hasattr(db, 'commit'):
                        await db.commit()
                    await message.answer(f"✅ Связь сохранена! (топик {topic_id} → пользователь {message.from_user.id})")
                elif hasattr(db, 'query'):
                    await db.query(
                        "INSERT OR REPLACE INTO topic_links (topic_id, chat_id, user_id) VALUES (?, ?, ?)",
                        (topic_id, OPERATOR_GROUP_ID, message.from_user.id)
                    )
                    await message.answer(f"✅ Связь сохранена! (топик {topic_id})")
                else:
                    await message.answer("⚠️ Не удалось сохранить связь: нет метода execute или query")
            except Exception as e:
                await message.answer(f"⚠️ Ошибка сохранения связи: {e}")
        else:
            await message.answer("⚠️ БД не найдена в bot.data!")
        # ====================================
        
        # Отправляем сообщение в топик
        ticket_text = (
            f"🆕 **НОВАЯ ЗАЯВКА**\n\n"
            f"👤 **Пользователь:** {user_name}\n"
            f"🆔 **ID:** `{message.from_user.id}`\n"
            f"📦 **SKU:** `{sku}`\n"
        )
        
        if photo_action:
            ticket_text += f"📸 **Действие:** {photo_action}\n"
        
        ticket_text += f"\n💬 **Комментарий:**\n{comment}\n"
        
        if has_photo:
            ticket_text += f"\n📷 **Пользователь загрузил корректное фото** ✅"
        else:
            ticket_text += f"\n📷 **Корректное фото:** не загружено ❌"
        
        await bot.send_message(
            chat_id=OPERATOR_GROUP_ID,
            text=ticket_text,
            message_thread_id=topic_id
        )
        
        # Отправляем фото, если есть
        if has_photo and photo_file_id:
            await bot.send_photo(
                chat_id=OPERATOR_GROUP_ID,
                photo=photo_file_id,
                caption="📷 **Корректное фото от пользователя**",
                message_thread_id=topic_id
            )
        
        # Подтверждение пользователю
        await message.answer(
            f"✅ **Заявка успешно создана!**\n\n"
            f"Наши операторы скоро свяжутся с вами в этом чате.\n"
            f"📌 Номер вашего тикета: `{topic_id}`\n\n"
            f"👇 Нажмите **«На главную»**, чтобы создать новую заявку.",
            reply_markup=main_menu_kb
        )
        
        await state.clear()
        
    except Exception as e:
        await message.answer(
            f"❌ **Ошибка при создании заявки:**\n`{e}`",
            reply_markup=ReplyKeyboardRemove()
        )
        print(f"Ошибка: {e}")


# ========== СОЗДАНИЕ ТИКЕТА (АТРИБУТЫ) ==========

async def create_attributes_ticket(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user_name = data.get('user_name', 'Неизвестный')
    sku = data.get('sku', 'Не указан')
    comment = data.get('comment', 'Не указан')
    
    OPERATOR_GROUP_ID = -1003953605950  # ЗАМЕНИТЕ НА ВАШ ID ГРУППЫ
    
    topic_name = f"✍️ Заявка от {user_name} (SKU: {sku})"
    
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
        
        # Сохраняем связь
        db = message.bot.data.get("db") if hasattr(message.bot, 'data') else None
        if db and hasattr(db, 'execute'):
            await db.execute(
                "INSERT OR REPLACE INTO topic_links (topic_id, chat_id, user_id) VALUES (?, ?, ?)",
                (topic_id, OPERATOR_GROUP_ID, message.from_user.id)
            )
            if hasattr(db, 'commit'):
                await db.commit()
        
        ticket_text = (
            f"🆕 **НОВАЯ ЗАЯВКА (АТРИБУТЫ)**\n\n"
            f"👤 **Пользователь:** {user_name}\n"
            f"🆔 **ID:** `{message.from_user.id}`\n"
            f"📦 **SKU:** `{sku}`\n\n"
            f"💬 **Комментарий:**\n{comment}"
        )
        
        await bot.send_message(
            chat_id=OPERATOR_GROUP_ID,
            text=ticket_text,
            message_thread_id=topic_id
        )
        
        await message.answer(
            f"✅ **Заявка успешно создана!**\n\n"
            f"📌 Номер тикета: `{topic_id}`\n\n"
            f"👇 Нажмите **«На главную»**",
            reply_markup=main_menu_kb
        )
        
        await state.clear()
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        print(f"Ошибка: {e}")


# ========== СОЗДАНИЕ ТИКЕТА (ВОПРОС) ==========

async def create_other_ticket(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user_name = data.get('user_name', 'Неизвестный')
    question = data.get('question', 'Не указан')
    
    OPERATOR_GROUP_ID = -1003953605950  # ЗАМЕНИТЕ НА ВАШ ID ГРУППЫ
    
    topic_name = f"❓ Вопрос от {user_name}"
    
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
        
        # Сохраняем связь
        db = message.bot.data.get("db") if hasattr(message.bot, 'data') else None
        if db and hasattr(db, 'execute'):
            await db.execute(
                "INSERT OR REPLACE INTO topic_links (topic_id, chat_id, user_id) VALUES (?, ?, ?)",
                (topic_id, OPERATOR_GROUP_ID, message.from_user.id)
            )
            if hasattr(db, 'commit'):
                await db.commit()
        
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
            f"✅ **Ваш вопрос передан!**\n\n"
            f"📌 Номер заявки: `{topic_id}`\n\n"
            f"👇 Нажмите **«На главную»**",
            reply_markup=main_menu_kb
        )
        
        await state.clear()
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
        print(f"Ошибка: {e}")


# ========== НА ГЛАВНУЮ ==========

@router.message(F.text == "🏠 На главную")
async def go_to_main_menu(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(TicketForm.waiting_for_question_type)
    
    await message.answer(
        "🏠 **Главное меню**\n\n"
        "❓ **Какой у вас вопрос?**\n\n"
        "Выберите категорию ниже 👇",
        reply_markup=get_main_menu_keyboard()
    )
