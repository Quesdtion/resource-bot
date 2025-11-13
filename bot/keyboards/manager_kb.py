from aiogram.utils.keyboard import ReplyKeyboardBuilder

def manager_main_kb():
    kb = ReplyKeyboardBuilder()
    kb.button(text="📦 Получить ресурс")
    kb.button(text="⏱ Отметить срок жизни")
    kb.button(text="📋 Мои ресурсы")
    kb.adjust(1)
    return kb.as_markup(resize_keyboard=True)
