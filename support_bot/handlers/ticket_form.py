async def create_ticket(message: Message, state: FSMContext, bot: Bot, icon: str):
    data = await state.get_data()
    
    # Берём имя из анкеты, если пользователь представился
    user_name = data.get('user_name')
    # Если не представился — берём из Telegram
    if not user_name or user_name == 'Неизвестный':
        user_name = message.from_user.full_name or message.from_user.first_name or "Пользователь"
    
    sku = data.get('sku', 'Не указан')
    comment = data.get('comment', 'Не указан')
    photo_action = data.get('photo_action', '')
    has_photo = data.get('has_photo', False)
    photo_file_id = data.get('photo_file_id', None)
    
    OPERATOR_GROUP_ID = -1003953605950  # ЗАМЕНИТЕ НА ВАШ ID
    
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
        
        # Сохраняем связь
        import os
        os.makedirs('/app/data', exist_ok=True)
        with open('/app/data/topic_links.txt', 'a') as f:
            f.write(f"{topic_id},{OPERATOR_GROUP_ID},{message.from_user.id}\n")
        
        await message.answer(f"✅ Связь сохранена! (топик {topic_id} → {user_name})")
        
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
            ticket_text += f"\n📷 **Пользователь загрузил фото** ✅"
        else:
            ticket_text += f"\n📷 **Фото:** не загружено ❌"
        
        await bot.send_message(chat_id=OPERATOR_GROUP_ID, text=ticket_text, message_thread_id=topic_id)
        
        if has_photo and photo_file_id:
            await bot.send_photo(chat_id=OPERATOR_GROUP_ID, photo=photo_file_id, message_thread_id=topic_id)
        
        await message.answer(
            f"✅ **Заявка создана!**\n📌 Номер тикета: `{topic_id}`\n\n👇 Нажмите **«На главную»**",
            reply_markup=main_menu_kb
        )
        
        await state.clear()
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
