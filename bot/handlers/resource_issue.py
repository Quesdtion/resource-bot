# Формируем красивый вывод
header = f"📦 Выдано ресурсов: {len(resources)} (тип: {r_type})\n\n"

lines = []
for i, r in enumerate(resources, start=1):
    login = r["login"]
    password = r["password"]
    lines.append(f"{i}) {login} | {password}")

text = header + "\n".join(lines)

await message.answer(text, reply_markup=manager_menu_kb())
