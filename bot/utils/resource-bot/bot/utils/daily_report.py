from db.connection import get_connection

async def send_daily_report(bot):
    """
    Генерация и отправка ежедневного отчёта руководству.
    """

    conn = await get_connection()
    cur = await conn.cursor()

    # Количество выданных ресурсов за день
    await cur.execute("""
        SELECT resource_type, COUNT(*)
        FROM issued_resources
        WHERE issued_at::date = CURRENT_DATE
        GROUP BY resource_type;
    """)
    resources = await cur.fetchall()

    report_text = "📊 Ежедневный отчёт\n\n"

    if resources:
        for item in resources:
            report_text += f"• {item[0]} — {item[1]} шт.\n"
    else:
        report_text += "Сегодня не было выдач ресурсов.\n"

    report_text += "\nОтчёт сформирован автоматически."

    # ID твоего руководящего Telegram чата
    ADMIN_CHAT_ID = 123456789  # ← Замени на свой ID

    await bot.send_message(ADMIN_CHAT_ID, report_text)

    await cur.close()
    await conn.close()
