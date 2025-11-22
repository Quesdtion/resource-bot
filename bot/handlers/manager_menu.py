# handlers/manager_menu.py

from aiogram import Router, types
from utils.splitter import split_message_lines
from keyboards.back import back_only_kb

router = Router()


@router.message(commands=["my_resources"])
async def my_resources(message: types.Message):
    # Генерация списка ресурсов (пример)
    lines = [
        f"Ресурс {i}: состояние — OK"
        for i in range(1, 250)   # Пример большого списка
    ]

    parts = list(split_message_lines(lines))

    for part in parts[:-1]:
        await message.answer(part)

    # Последнее сообщение + кнопка
    await message.answer(parts[-1], reply_markup=back_only_kb())
