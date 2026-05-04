import os
import logging
from datetime import datetime, timedelta
from collections import defaultdict

log = logging.getLogger(__name__)

OPERATOR_GROUP_ID = -1003953605950
REPORT_TOPIC_ID = 254  # Ваш новый топик для отчётов


async def get_daily_statistics():
    """
    Собирает статистику за последние 24 часа
    """
    try:
        file_path = '/app/data/tickets_info.txt'
        if not os.path.exists(file_path):
            return None
        
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        
        stats = {
            'total': 0,
            'photo': 0,
            'attributes': 0,
            'other': 0,
            'answered': 0,
            'unanswered': 0,
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
                        if created_at >= yesterday:
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
                    except (ValueError, IndexError):
                        continue
        
        return stats
    except Exception as e:
        log.error(f"Ошибка сбора дневной статистики: {e}")
        return None


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
                            
                            stats['by_date'][created_at.strftime('%d.%m')] += 1
                    except:
                        continue
        return stats
    except Exception as e:
        log.error(f"Ошибка сбора недельной статистики: {e}")
        return None


async def get_operators_stats(days: int = 7):
    """
    Статистика по операторам за указанное количество дней
    """
    try:
        file_path = '/app/data/operators_stats.txt'
        if not os.path.exists(file_path):
            return None
        
        cutoff = datetime.now() - timedelta(days=days)
        operators = defaultdict(int)
        
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split('|')
                if len(parts) >= 3:
                    try:
                        reply_time = datetime.fromisoformat(parts[2])
                        if reply_time >= cutoff:
                            operators[parts[0]] += 1
                    except:
                        continue
        return dict(operators)
    except Exception as e:
        log.error(f"Ошибка: {e}")
        return None


async def save_ticket_info(topic_id: int, ticket_type: str, user_id: int, user_name: str):
    os.makedirs('/app/data', exist_ok=True)
    with open('/app/data/tickets_info.txt', 'a') as f:
        f.write(f"{topic_id}|{ticket_type}|unanswered|{datetime.now().isoformat()}|{user_id}|{user_name}\n")


async def mark_ticket_as_answered(topic_id: int):
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
            if len(parts) >= 4 and int(parts[0]) == topic_id and parts[2] != 'answered':
                parts[2] = 'answered'
                tickets.append('|'.join(parts))
            else:
                tickets.append(line)
    
    if tickets:
        with open(file_path, 'w') as f:
            for ticket in tickets:
                f.write(f"{ticket}\n")


async def save_operator_reply(operator_id: int, topic_id: int):
    os.makedirs('/app/data', exist_ok=True)
    with open('/app/data/operators_stats.txt', 'a') as f:
        f.write(f"{operator_id}|{topic_id}|{datetime.now().isoformat()}\n")


async def send_daily_report(bot):
    """Отправляет ежедневный отчёт за предыдущий день"""
    log.info("📊 Формируем ежедневный отчёт")
    
    stats = await get_daily_statistics()
    
    if not stats or stats['total'] == 0:
        report = f"📊 **Ежедневный отчёт**\n\n📅 **Дата:** {datetime.now().strftime('%d.%m.%Y')}\n\n✨ За вчерашний день не было ни одной заявки.\n🥳 Отличная работа!"
    else:
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%d.%m.%Y')
        percent = (stats['answered'] / stats['total']) * 100 if stats['total'] > 0 else 0
        
        report = f"📊 **Ежедневный отчёт**\n\n📅 **Дата:** {yesterday}\n\n"
        report += f"📌 **Всего заявок:** {stats['total']}\n\n"
        report += "📂 **По категориям:**\n"
        report += f"   📸 Фото: {stats['photo']}\n"
        report += f"   ✍️ Атрибуты: {stats['attributes']}\n"
        report += f"   ❓ Вопросы: {stats['other']}\n\n"
        report += "📊 **По статусам:**\n"
        report += f"   ✅ Отвечено: {stats['answered']}\n"
        report += f"   ⏳ Ожидают: {stats['unanswered']}\n\n"
        report += f"📈 **Процент отвеченных:** {percent:.1f}%\n"
    
    await bot.send_message(
        chat_id=OPERATOR_GROUP_ID,
        text=report,
        message_thread_id=REPORT_TOPIC_ID,
        parse_mode="Markdown"
    )
    log.info("✅ Ежедневный отчёт отправлен")


async def send_weekly_report(bot):
    """Отправляет еженедельный отчёт"""
    log.info("📊 Формируем еженедельный отчёт")
    
    stats = await get_weekly_statistics()
    
    if not stats or stats['total'] == 0:
        report = f"📊 **Еженедельная сводка**\n\n📅 **Неделя:** {datetime.now().strftime('%d.%m.%Y')}\n\n✨ За неделю не было ни одной заявки.\n🥳 Отличная работа!"
    else:
        now = datetime.now()
        week_start = (now - timedelta(days=7)).strftime('%d.%m.%Y')
        week_end = now.strftime('%d.%m.%Y')
        percent = (stats['answered'] / stats['total']) * 100 if stats['total'] > 0 else 0
        
        report = f"📊 **Еженедельная сводка**\n\n📅 **Период:** {week_start} – {week_end}\n\n"
        report += f"📌 **Всего заявок:** {stats['total']}\n\n"
        report += "📂 **По категориям:**\n"
        report += f"   📸 Фото: {stats['photo']}\n"
        report += f"   ✍️ Атрибуты: {stats['attributes']}\n"
        report += f"   ❓ Вопросы: {stats['other']}\n\n"
        report += "📊 **По статусам:**\n"
        report += f"   ✅ Отвечено: {stats['answered']}\n"
        report += f"   ⏳ Ожидают: {stats['unanswered']}\n\n"
        report += f"📈 **Процент отвеченных:** {percent:.1f}%\n\n"
        
        if stats['by_date']:
            report += "📅 **По дням:**\n"
            for date in sorted(stats['by_date'].keys()):
                report += f"   • {date}: {stats['by_date'][date]} заявок\n"
            report += "\n"
        
        operators_stats = await get_operators_stats(7)
        if operators_stats:
            report += "👥 **Активность операторов:**\n"
            for op_id, count in sorted(operators_stats.items(), key=lambda x: x[1], reverse=True)[:5]:
                report += f"   • Оператор `{op_id}`: {count} ответов\n"
            report += "\n"
        
        if stats['answered'] == stats['total'] and stats['total'] > 0:
            report += "🏆 **Отлично! Все заявки обработаны!**"
        elif percent > 70:
            report += "👍 **Хороший результат!** Но есть ещё заявки в работе."
        else:
            report += "⚠️ **Обратите внимание!** Много заявок ожидают ответа."
    
    await bot.send_message(
        chat_id=OPERATOR_GROUP_ID,
        text=report,
        message_thread_id=REPORT_TOPIC_ID,
        parse_mode="Markdown"
    )
    log.info("✅ Еженедельный отчёт отправлен")


async def send_report_to_topic(bot, topic_id: int):
    """Отправляет отчёт в указанный топик (для команды /report)"""
    await send_weekly_report_to_topic(bot, topic_id)


async def send_weekly_report_to_topic(bot, topic_id: int):
    """Отправляет еженедельную сводку в указанный топик"""
    await send_weekly_report(bot)


async def send_test_report(bot):
    """Тестовая отправка"""
    test_message = "📊 **ТЕСТОВЫЙ ОТЧЁТ**\n\nЕсли вы видите это сообщение, значит бот может отправлять сообщения в топик 254."
    await bot.send_message(
        chat_id=OPERATOR_GROUP_ID,
        text=test_message,
        message_thread_id=REPORT_TOPIC_ID,
        parse_mode="Markdown"
    )
    return True
