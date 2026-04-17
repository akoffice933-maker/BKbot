from aiogram import types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from statbet_bot.services.hedge import HedgeService
from statbet_bot.utils.validators import validate_stake, validate_odds, validate_percent
from statbet_bot.utils.formatters import format_currency, format_odds, format_percentage


class HedgeStates(StatesGroup):
    waiting_for_stake = State()
    waiting_for_k_main = State()
    waiting_for_k_hedge = State()
    waiting_for_percent = State()


async def cancel_handler(message: types.Message, state: FSMContext):
    """Handle /cancel command to exit FSM."""
    await state.clear()
    await message.reply(
        "❌ Расчет отменен.\n\n"
        "Используйте /calc_hedge для начала нового расчета."
    )


async def calc_hedge_handler(message: types.Message, state: FSMContext):
    await message.reply(
        "📊 Введите сумму условной позиции:\n\n"
        "Для отмены используйте /cancel"
    )
    await state.set_state(HedgeStates.waiting_for_stake)


async def process_stake(message: types.Message, state: FSMContext):
    is_valid, stake, error = validate_stake(message.text)
    if not is_valid:
        await message.reply(f"❌ Ошибка: {error}")
        return
    await state.update_data(stake=stake)
    await message.reply(
        f"✓ Сумма: {format_currency(stake)}\n\n"
        f"Введите коэффициент позиции:"
    )
    await state.set_state(HedgeStates.waiting_for_k_main)


async def process_k_main(message: types.Message, state: FSMContext):
    is_valid, k_main, error = validate_odds(message.text)
    if not is_valid:
        await message.reply(f"❌ Ошибка: {error}")
        return
    await state.update_data(k_main=k_main)
    await message.reply(
        f"✓ Коэффициент позиции: {format_odds(k_main)}\n\n"
        f"Введите коэффициент противоположного исхода:"
    )
    await state.set_state(HedgeStates.waiting_for_k_hedge)


async def process_k_hedge(message: types.Message, state: FSMContext):
    is_valid, k_hedge, error = validate_odds(message.text)
    if not is_valid:
        await message.reply(f"❌ Ошибка: {error}")
        return
    await state.update_data(k_hedge=k_hedge)
    await message.reply(
        f"✓ Коэффициент хеджа: {format_odds(k_hedge)}\n\n"
        f"Введите желаемый % покрытия (0-100):"
    )
    await state.set_state(HedgeStates.waiting_for_percent)


async def process_percent(message: types.Message, state: FSMContext):
    is_valid, percent, error = validate_percent(message.text)
    if not is_valid:
        await message.reply(f"❌ Ошибка: {error}")
        return
    data = await state.get_data()
    stake = data['stake']
    k_main = data['k_main']
    k_hedge = data['k_hedge']

    result = HedgeService.calculate(stake, k_main, k_hedge, percent)

    if result.error:
        await message.reply(f"❌ Ошибка расчета: {result.error}")
        await state.clear()
        return

    # Format output with formatters
    arbitrage_note = ""
    if result.is_arbitrage:
        arbitrage_note = (
            f"\n🎯 АРБИТРАЖ ОБНАРУЖЕН!\n"
            f"Гарантированная прибыль: {format_currency(result.guaranteed_profit)}"
        )

    text = (
        f"📊 РАСЧЕТ ХЕДЖА\n\n"
        f"Параметры:\n"
        f"• Сумма позиции: {format_currency(stake)}\n"
        f"• Кэф позиции: {format_odds(k_main)}\n"
        f"• Кэф хеджа: {format_odds(k_hedge)}\n"
        f"• Покрытие: {format_percentage(percent)}\n\n"
        f"Результаты:\n"
        f"• Full Hedge: {format_currency(result.full_hedge)}\n"
        f"• Partial Hedge ({format_percentage(percent)}): {format_currency(result.partial_hedge)}\n"
        f"• Lock Profit: {format_currency(result.lock_profit)}\n"
        f"{arbitrage_note}\n\n"
        f"⚠️ Не является инвестиционной рекомендацией."
    )

    await message.reply(text)
    await state.clear()
