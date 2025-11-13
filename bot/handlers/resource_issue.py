from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()


def get_issue_menu_kb() -> InlineKeyboardBuilder:
    """
    Простейшее меню выдачи ресурса (заглушка).
    Потом сюда можно будет прикрутить выбор типа ресурса, срока жизни и т.д.
    """
    kb = InlineKeyboardBuilder()
    kb.button(text="Выдать ресурс", callback_data="issue_resource")
    kb.button(text="Отмена", callback_data="issue_cancel")
    kb.adjust(1)
    return kb


@router.message(F.text == "Выдать ресурс")
async def issue_menu(message: Message):
    """
    Хендлер на пункт меню "Выдать ресурс".
    Сейчас просто показывает заглушку и клавиатуру.
    """
    kb = get_issue_menu_kb()
    await message.answer(
        "🧾 Меню выдачи ресурсов\n\n"
        "Здесь позже будет логика выдачи аккаунтов/ресурсов.\n"
        "Пока это тестовый обработчик, чтобы бот корректно запускался.",
        reply_markup=kb.as_markup()
    )


@router.callback_query(F.data == "issue_resource")
async def issue_resource_stub(callback: CallbackQuery):
    """
    Заглушка на кнопку 'Выдать ресурс'.
    Вместо настоящей логики просто отвечает, что всё ок.
    """
    await callback.answer()
    await callback.message.answer(
        "✅ (Заглушка)\n"
        "Ресурс как будто бы выдан.\n"
        "Позже здесь будет реальная логика работы с БД."
    )


@router.callback_query(F.data == "issue_cancel")
async def issue_cancel(callback: CallbackQuery):
    """
    Отмена выдачи ресурса.
    """
    await callback.answer("Отменено")
    await callback.message.edit_text("Меню выдачи ресурсов закрыто.")
