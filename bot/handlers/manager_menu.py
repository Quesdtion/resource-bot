from aiogram import Router, types
from aiogram.filters import Command
from bot.keyboards.manager_kb import manager_main_kb

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Это бот выдачи ресурсов. Выбери действие:",
        reply_markup=manager_main_kb()
    )
from aiogram import F

@router.message()
async def any_message_log(message: types.Message):
    print(f"UPDATE: {message.from_user.id} -> {message.text}")
