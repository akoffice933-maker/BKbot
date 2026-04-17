from aiogram import types
from aiogram.fsm.context import FSMContext
from statbet_bot.database import Database

async def start_handler(message: types.Message, state: FSMContext, db: Database):
    user_id = message.from_user.id
    username = message.from_user.username

    # Check if user exists, if not create
    async with db.pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM users WHERE telegram_id = $1", user_id)
        if not user:
            await conn.execute("INSERT INTO users (telegram_id, username) VALUES ($1, $2)", user_id, username)

    text = """
    Добро пожаловать в StatBet Bot!

    ⚠️ Важное предупреждение:
    Этот бот предоставляет аналитическую информацию на основе математических моделей и не является инвестиционной рекомендацией или призывом к совершению ставок. Все решения вы принимаете самостоятельно и несете полную ответственность за них.

    Использование стратегий хеджирования может нарушать правила букмекерских контор.

    Подтверждаете ли вы, что вам 18+ лет и вы понимаете риски?

    Команды:
    /matches - Список матчей
    /analyze - Анализ матча
    /calc_hedge - Калькулятор хеджа
    /track - Отслеживать матч
    /paper - Виртуальный портфель
    /stats - Статистика модели
    """
    await message.reply(text)