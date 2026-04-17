from aiogram import types

async def matches_handler(message: types.Message):
    # Placeholder: In real implementation, fetch upcoming matches from API
    text = """
    📅 Ближайшие матчи:

    1. Спартак — Зенит (Премьер-лига, 15.04.2026)
       ТБ 2.5: 67% | ТМ 2.5: 33%

    2. ЦСКА — Локомотив (Премьер-лига, 16.04.2026)
       ТБ 2.5: 55% | ТМ 2.5: 45%

    Используйте /analyze <номер матча> для детального анализа.
    """
    await message.reply(text)