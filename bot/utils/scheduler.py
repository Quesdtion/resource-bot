from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from bot.utils.daily_report import send_daily_report
from bot.utils.resource_checker import check_expired_resources

# Создаем объект планировщика
scheduler = AsyncIOScheduler()

def setup_scheduler(bot):
    """
    Инициализация и запуск задач планировщика.
    """

    # Ежедневный отчёт для руководства (в 23:50)
    scheduler.add_job(
        send_daily_report,
        CronTrigger(hour=23, minute=50),
        kwargs={"bot": bot},
        id="daily_report",
        replace_existing=True
    )

    # Проверка просроченных ресурсов каждые 10 минут
    scheduler.add_job(
        check_expired_resources,
        "interval",
        minutes=10,
        id="resource_checker",
        replace_existing=True
    )

    scheduler.start()
