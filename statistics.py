import os
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot
from collections import defaultdict

# ID группы и топика GENERAL
OPERATOR_GROUP_ID = -1003953605950
GENERAL_TOPIC_ID = 1  # Обычно ID общего топика = 1

async def get_statistics():
    """Собирает статистику по заявкам из файла"""
    try:
        file_path = '/app/data/topic_links.txt'
        if not os.path.exists(file_path):
            return None
        
        # Собираем данные по заявкам
        stats = {
            'total': 0,
            'photo': 0,      # Заявки по фото
            'attributes': 0,  # Заявки по атрибутам
            'other': 0,       # Вопросы
            'answered': 0,    # Отвеченные (есть ответ оператора)
            'unanswered': 0,  # Неотвеченные
            'by_date': defaultdict(int)
        }
        
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(',')
                if len(parts) >= 3:
                    stats['total'] += 1
                    # Здесь нужно определять тип заявки
                    # Это можно сделать по названию топика, но для простоты считаем
                    
        return stats
    except Exception as e:
        print(f"Ошибка сбора статистики: {e}")
        return None


async def collect_tickets_info(bot: Bot):
    """Собирает информацию о топиках из группы"""
    try:
        # Получаем список топиков (только если есть такой метод API)
        # В Telegram API нет прямого метода получить список всех топиков,
        # поэтому используем файл topic_links.txt для хранения информации
        # о типе заявки и статусе
        
        file_path = '/app/data/tickets_info.txt'
        tickets = []
        
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split('|')
                    if len(parts) >= 4:
                        tickets.append({
                            'topic_id': int(parts[0]),
                            'type': parts[1],  # photo, attributes, other
                            'status': parts[2],  # answered, unanswered
                            'created_at': parts[3]
                        })
        return tickets
    except Exception as e:
        print(f"Ошибка: {e}")
        return []


async def update_ticket_status(topic_id: int, status: str):
    """Обновляет статус заявки (при ответе оператора)"""
    try:
        file_path = '/app/data/tickets_info.txt'
        tickets = []
        
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split('|')
                    if len(parts) >= 4 and int(parts[0]) != topic_id:
                        tickets.append(line)
        
        # Добавляем новую запись или обновляем существующую
        # Здесь нужно найти существующую запись и обновить статус
        
        with open(file_path, 'w') as f:
            for ticket in tickets:
                f.write(f"{ticket}\n")
    except Exception as e:
        print(f"Ошибка: {e}")


async def send_daily_statistics(bot: Bot):
    """Отправляет ежедневную статистику в GENERAL топик"""
    stats = await get_statistics()
    tickets = await collect_tickets_info(bot)
    
    if not stats and not tickets:
        return
    
    # Формируем сообщение
    now = datetime.now()
    date_str = now.strftime("%d.%m.%Y")
    
    report = f"📊 **Ежедневный отчёт**\n"
    report += f"📅 **Дата:** {date_str}\n\n"
    
    # Общая статистика
    report += f"📌 **Всего заявок:** {stats['total'] if stats else 0}\n\n"
    
    # Статистика по категориям
    report += "📂 **По категориям:**\n"
    if stats:
        report += f"   📸 Некорректное фото: {stats.get('photo', 0)}\n"
        report += f"   ✍️ Некорректные атрибуты: {stats.get('attributes', 0)}\n"
        report += f"   ❓ Вопросы: {stats.get('other', 0)}\n\n"
    
    # Статистика по статусам
    answered = 0
    unanswered = 0
    
    for ticket in tickets:
        if ticket.get('status') == 'answered':
            answered += 1
        else:
            unanswered += 1
    
    report += "📊 **По статусам:**\n"
    report += f"   ✅ Отвечено: {answered}\n"
    report += f"   ⏳ Ожидают ответа: {unanswered}\n\n"
    
    # Процент выполнения
    if answered + unanswered > 0:
        percent = (answered / (answered + unanswered)) * 100
        report += f"📈 **Процент отвеченных:** {percent:.1f}%\n"
    
    # Отправляем в GENERAL топик
    try:
        await bot.send_message(
            chat_id=OPERATOR_GROUP_ID,
            text=report,
            message_thread_id=GENERAL_TOPIC_ID,
            parse_mode="Markdown"
        )
        print("Статистика отправлена в GENERAL топик")
    except Exception as e:
        print(f"Ошибка отправки статистики: {e}")
