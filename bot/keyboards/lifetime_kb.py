from aiogram.utils.keyboard import InlineKeyboardBuilder

def lifetime_kb(resource_id: int):
    kb = InlineKeyboardBuilder()
    options = [
        ("10 минут", 10),
        ("20 минут", 20),
        ("30 минут", 30),
        ("1 час", 60),
        ("2 часа", 120),
        ("6 часов", 360),
        ("12 часов", 720),
        ("24 часа", 1440),
        ("До блокировки", -1),
    ]
    for text, val in options:
        kb.button(text=text, callback_data=f"lt_{resource_id}:{val}")
    kb.adjust(1)
    return kb.as_markup()
