import os
from datetime import datetime, timedelta
from collections import defaultdict

OPERATOR_GROUP_ID = -1003953605950  # ЗАМЕНИТЕ НА ВАШ ID ГРУППЫ
GENERAL_TOPIC_ID = 1  # ID общего топика (обычно 1)


async def get_weekly_statistics():
    """
    Собирает статистику за последние 7 дней
    """
    try:
        file_path = '/app/data/tickets_info.txt'
        if not os.path.exists(file_path):
            return None
        
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        
        stats = {
            'total': 0,
            'photo': 0,
            'attributes': 0,
            'other': 0,
            'answered': 0,
            'unanswered': 0,
            'by_date': defaultdict(int)
        }
        
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split('|')
                if len(parts) >= 4:
                    try:
                        created_at = datetime.fromisoformat(parts[3])
                        if created_at >= week_ago:
                            stats['total'] += 1
                            ticket_type = parts[1]
                            status = parts[2]
                            
                            if ticket_type == 'photo':
                                stats['photo'] += 1
                            elif ticket_type == 'attributes':
                                stats['attributes'] += 1
                            elif ticket_type == 'other':
                                stats['other'] += 1
                            
                            if status == 'answered':
                                stats['answered'] += 1
                            else:
                                stats['unanswered'] += 1
                            
                            date_key = created_at.strftime('%d.%m')
                            stats['by_date'][date_key] += 1
                    except (ValueError, IndexError):
                        continue
        
        return stats
    except Exception as e:
        print(f"Ошибка сбора статистики: {e}")
        return None


async def get_operators_stats():
    """
    Статистика по операторам (кто сколько ответил)
    """
    try:
        file_path = '/app/data/operators_stats.txt'
        if not os.path.exists(file_path):
            return None
        
        week_ago = datetime.now() - timedelta(days=7)
        operators = defaultdict(int)
        
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split('|')
                if len(parts) >= 3:
                    try:
                        operator_id = parts[0]
                        reply_time = datetime.fromisoformat(parts[2])
                        if reply_time >= week_ago:
                            operators[operator_id] += 1
                    except (ValueError, IndexError):
                        continue
        
        return dict(operators)
    except Exception as e:
        print(f"Ошибка сбора статистики операторов: {e}")
        return None


async def save_ticket_info(topic_id: int, ticket_type: str, user_id: int, user_name: str):
    """
    Сохраняет информацию о созданной заявке
    ticket_type: 'photo', 'attributes', 'other'
    """
    try:
        file_path = '/app/data/tickets_info.txt'
        os.makedirs('/app/data', exist_ok=True)
        
        created_at = datetime.now().isoformat()
        
        with open(file_path, 'a') as f:
            f.write(f"{topic_id}|{ticket_type}|unanswered|{created_at}|{user_id}|{user_name}\n")
    except Exception as e:
        print(f"Ошибка сохранения информации о заявке: {e}")


async def mark_ticket_as_answered(topic_id: int):
    """
    Отмечает заявку как отвеченную
    """
    try:
        file_path = '/app/data/tickets_info.txt'
        if not os.path.exists(file_path):
            return
        
        tickets = []
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split('|')
                if len(parts) >= 4 and int(parts[0]) == topic_id:
                    parts[2] = 'answered'
                    tickets.append('|'.join(parts))
                else:
                    tickets.append(line)
        
        with open(file_path, 'w') as f:
            for ticket in tickets:
                f.write(f"{ticket}\n")
                
    except Exception as e:
        print(f"Ошибка обновления статуса: {e}")


async def save_operator_reply(operator_id: int, topic_id: int):
    """
    Сохраняет факт ответа оператора
    """
    try:
        file_path = '/app/data/operators_stats.txt'
        os.makedirs('/app/data', exist_ok=True)
        
        reply_time = datetime.now().isoformat()
        
        with open(file_path, 'a') as f:
            f.write(f"{operator_id}|{topic_id}|{reply_time}\n")
    except Exception as e:
        print(f"Ошибка сохранения ответа оператора: {e}")


async def send_weekly_report(bot):
    """
    Отправляет еженедельную сводку в GENERAL топик
    """
    stats = await get_weekly_statistics()
    
    if not stats or stats['total'] == 0:
        report = "📊 **Еженедельная сводка**\n\n"
        report += f"📅 **Неделя:** {datetime.now().strftime('%d.%m.%Y')}\n\n"
        report += "✨ За прошедшую неделю не было ни одной заявки.\n"
        report += "🥳 Отличная работа!"
    else:
        now = datetime.now()
        week_start = (now - timedelta(days=7)).strftime('%d.%m.%Y')
        week_end = now.strftime('%d.%m.%Y')
        
        report = "📊 **Еженедельная сводка**\n\n"
        report += f"📅 **Период:** {week_start} – {week_end}\n\n"
        
        report += f"📌 **Всего заявок:** {stats['total']}\n\n"
        
        report += "📂 **По категориям:**\n"
        report += f"   📸 Некорректное фото: {stats['photo']}\n"
        report += f"   ✍️ Некорректные атрибуты: {stats['attributes']}\n"
        report += f"   ❓ Вопросы: {stats['other']}\n\n"
        
        report += "📊 **По статусам:**\n"
        report += f"   ✅ Отвечено: {stats['answered']}\n"
        report += f"   ⏳ Ожидают ответа: {stats['unanswered']}\n\n"
        
        if stats['total'] > 0:
            percent = (stats['answered'] / stats['total']) * 100
            report += f"📈 **Процент отвеченных:** {percent:.1f}%\n\n"
        
        if stats['by_date']:
            report += "📅 **По дням:**\n"
            for date in sorted(stats['by_date'].keys()):
                report += f"   • {date}: {stats['by_date'][date]} заявок\n"
            report += "\n"
        
        operators_stats = await get_operators_stats()
        if operators_stats:
            report += "👥 **Активность операторов:**\n"
            sorted_ops = sorted(operators_stats.items(), key=lambda x: x[1], reverse=True)
            for op_id, count in sorted_ops[:5]:
                report += f"   • Оператор `{op_id}`: {count} ответов\n"
            report += "\n"
        
        if stats['answered'] == stats['total'] and stats['total'] > 0:
            report += "🏆 **Отлично! Все заявки обработаны!**\n"
        elif stats['answered'] / stats['total'] > 0.7 if stats['total'] > 0 else False:
            report += "👍 **Хороший результат!** Но есть ещё заявки в работе.\n"
        else:
            report += "⚠️ **Обратите внимание!** Много заявок ожидают ответа.\n"
    
    try:
        await bot.send_message(
            chat_id=OPERATOR_GROUP_ID,
            text=report,
            message_thread_id=GENERAL_TOPIC_ID,
            parse_mode="Markdown"
        )
        print(f"Еженедельная сводка отправлена в GENERAL топик")
    except Exception as e:
        print(f"Ошибка отправки сводки: {e}")
