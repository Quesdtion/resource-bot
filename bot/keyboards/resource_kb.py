from aiogram.utils.keyboard import InlineKeyboardBuilder

def receipt_state_kb(resource_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="🟢 Рабочий", callback_data=f"rcpt_working:{resource_id}")
    kb.button(text="🔴 В блоке", callback_data=f"rcpt_blocked:{resource_id}")
    kb.button(text="⚠️ Ошибка входа", callback_data=f"rcpt_error:{resource_id}")
    kb.adjust(1)
    return kb.as_markup()
