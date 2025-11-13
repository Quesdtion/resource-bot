from db.connection import get_connection

async def check_expired_resources(bot=None):
    """
    Проверяет ресурсы с истёкшим сроком действия.
    """

    conn = await get_connection()
    cur = await conn.cursor()

    # Найти ресурсы, срок которых истёк
    await cur.execute("""
        SELECT id, user_id, resource_type, expires_at
        FROM issued_resources
        WHERE expires_at < NOW() AND status = 'active';
    """)
    expired = await cur.fetchall()

    for res in expired:
        rid, user_id, rtype, expdate = res

        # Обновляем статус
        await cur.execute("""
            UPDATE issued_resources
            SET status = 'expired'
            WHERE id = %s
        """, (rid,))

        # Уведомляем менеджера
        if bot:
            try:
                await bot.send_message(
                    user_id,
                    f"⚠️ Ресурс **{rtype}** истёк.\nДата истечения: {expdate}"
                )
            except:
                pass

    await conn.commit()
    await cur.close()
    await conn.close()
