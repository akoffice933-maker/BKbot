from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from statbet_bot.database import Database


class StartStates(StatesGroup):
    waiting_for_age_confirm = State()


def _welcome_text() -> str:
    return """
Добро пожаловать в StatBet Bot!

Команды:
/matches - Список матчей
/analyze - Анализ матча
/calc_hedge - Калькулятор хеджа
/track - Отслеживать матч
/paper - Виртуальный портфель
/stats - Статистика модели
""".strip()


def _age_disclaimer_text() -> str:
    return """
Добро пожаловать в StatBet Bot!

⚠️ Важное предупреждение:
Этот бот предоставляет аналитическую информацию на основе математических моделей и не является инвестиционной рекомендацией или призывом к совершению ставок. Все решения вы принимаете самостоятельно и несете полную ответственность за них.

Использование стратегий хеджирования может нарушать правила букмекерских контор.

Для продолжения подтвердите, что вам 18+ лет и вы понимаете риски.
Ответьте сообщением: ДА
""".strip()


async def start_handler(message: types.Message, state: FSMContext, db: Database):
    user_id = message.from_user.id
    username = message.from_user.username

    async with db.pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM users WHERE telegram_id = $1", user_id)

    if user:
        await state.clear()
        await message.reply(_welcome_text())
        return

    await state.update_data(pending_username=username)
    await state.set_state(StartStates.waiting_for_age_confirm)
    await message.reply(_age_disclaimer_text())


async def process_age_confirm(message: types.Message, state: FSMContext, db: Database):
    if not message.text or message.text.strip().upper() != "ДА":
        await message.reply("Для продолжения ответьте ДА.")
        return

    user_id = message.from_user.id
    data = await state.get_data()
    username = data.get("pending_username", message.from_user.username)

    async with db.pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (telegram_id, username)
            VALUES ($1, $2)
            ON CONFLICT (telegram_id) DO NOTHING
            """,
            user_id,
            username,
        )

    await state.clear()
    await message.reply(_welcome_text())
