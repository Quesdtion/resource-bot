from aiogram import Router, types
from aiogram.filters import Command

from bot.utils.queries import DBQueries

router = Router()


@router.message(Command("import_resources"))
async def import_resources(message: types.Message, role: str | None = None):
    """
    Импорт пачки ресурсов текстом.
    Формат сообщения:

    /import_resources mamba 58
    login1;pass1;proxy1
    login2;pass2;
    login3;pass3;proxy3

    - первая строка: команда, тип, цена за единицу
    - дальше: по одной строке на ресурс: login;password;proxy(опционально)
    """

    if role != "owner":
        await message.answer("⛔ Эта команда доступна только владельцу (owner).")
        return

    lines = message.text.strip().splitlines()
    if len(lines) < 2:
        await message.answer(
            "❗ Неверный формат.\n\n"
            "Пример:\n"
            "/import_resources mamba 58\n"
            "login1;pass1;proxy1\n"
            "login2;pass2;\n"
            "login3;pass3;proxy3"
        )
        return

    # Разбираем первую строку: /import_resources type price
    header_parts = lines[0].split()
    if len(header_parts) < 3:
        await message.answer(
            "❗ В первой строке укажи тип и цену.\n"
            "Пример: /import_resources mamba 58"
        )
        return

    _, res_type, price_str = header_parts[:3]

    # Парсим цену
    try:
        price = float(price_str.replace(",", "."))
    except ValueError:
        await message.answer("❗ Цена должна быть числом, пример: 58 или 58.5")
        return

    pool = message.bot.db

    total = 0
    success = 0
    failed = 0

    resources_to_add = []

    # Остальные строки — ресурсы
    for raw_line in lines[1:]:
        line = raw_line.strip()
        if not line:
            continue

        total += 1
        parts = [p.strip() for p in line.split(";")]

        if len(parts) < 2:
            failed += 1
            continue

        login = parts[0]
        password = parts[1]
        proxy = parts[2] if len(parts) >= 3 and parts[2] else None

        resources_to_add.append((login, password, proxy))

    if not resources_to_add:
        await message.answer("❗ Не нашёл ни одной корректной строки с ресурсом.")
        return

    async with pool.acquire() as conn:
        for login, password, proxy in resources_to_add:
            try:
                await conn.execute(
                    DBQueries.ADD_RESOURCE,
                    res_type,
                    login,
                    password,
                    proxy,
                    None,   # supplier_id
                    price,
                )
                success += 1
            except Exception:
                failed += 1

    text = [
        "✅ Импорт завершён.",
        f"Тип: <b>{res_type}</b>",
        f"Цена за единицу: <b>{price}</b>",
        "",
        f"Всего строк: {total}",
        f"Успешно добавлено: <b>{success}</b>",
    ]
    if failed:
        text.append(f"С ошибками: <b>{failed}</b>")

    await message.answer("\n".join(text))
