from aiogram import types

async def track_handler(message: types.Message):
    await message.reply("Функция отслеживания матчей в разработке.")

async def untrack_handler(message: types.Message):
    await message.reply("Функция снятия с отслеживания в разработке.")

async def status_handler(message: types.Message):
    await message.reply("Статус: В разработке.")

async def paper_handler(message: types.Message):
    await message.reply("Виртуальный портфель: Баланс 10000 у.е.")

async def stats_handler(message: types.Message):
    await message.reply("Статистика модели: Brier Score 0.25, ROI 5%.")