"""Cross-hedge calculator between bookmaker odds and Polymarket."""

from __future__ import annotations

from aiogram import types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command

from statbet_bot.services.hedge import HedgeService
from statbet_bot.utils.validators import validate_odds
from statbet_bot.utils.formatters import format_currency, format_odds, format_percentage


class CrossHedgeStates(StatesGroup):
    """FSM for cross-hedge input."""
    waiting_for_odds = State()
    waiting_for_pm_price = State()
    waiting_for_stake = State()


async def xhedge_handler(message: types.Message, state: FSMContext):
    """Start cross-hedge calculator."""
    await state.clear()
    await message.reply(
        "🔄 КРОСС-ХЕДЖ (БК ↔ Polymarket)\n\n"
        "Рассчитайте хедж между букмекерским коэффициентом "
        "и ценой на Polymarket.\n\n"
        "Введите коэффициент БК (больше 1.0):\n\n"
        "Для отмены: /cancel"
    )
    await state.set_state(CrossHedgeStates.waiting_for_odds)


async def process_odds(message: types.Message, state: FSMContext):
    is_valid, odds, error = validate_odds(message.text)
    if not is_valid:
        await message.reply(f"❌ Ошибка: {error}\n\nВведите коэффициент заново:")
        return

    await state.update_data(odds_main=odds)
    await message.reply(
        f"✅ Коэффициент БК: {format_odds(odds)}\n\n"
        f"Введите цену Yes на Polymarket (0.0 — 1.0):\n\n"
        "Пример: 0.55"
    )
    await state.set_state(CrossHedgeStates.waiting_for_pm_price)


async def process_pm_price(message: types.Message, state: FSMContext):
    text = message.text.strip()
    try:
        pm_price = float(text)
    except ValueError:
        await message.reply("❌ Введите число (например: 0.55)\n\nПопробуйте снова:")
        return

    if not 0 < pm_price < 1:
        await message.reply(
            "❌ Цена должна быть строго между 0 и 1.\n\n"
            "Введите заново:"
        )
        return

    await state.update_data(pm_price=pm_price)
    await message.reply(
        f"✅ Цена Polymarket Yes: {format_percentage(pm_price)}\n\n"
        f"Введите сумму ставки (или 0 для default 100):"
    )
    await state.set_state(CrossHedgeStates.waiting_for_stake)


async def process_stake(message: types.Message, state: FSMContext):
    try:
        stake = float(message.text.strip())
    except ValueError:
        await message.reply("❌ Введите число.\n\nПопробуйте снова:")
        return

    if stake <= 0:
        stake = 100.0

    await state.update_data(stake=stake)
    data = await state.get_data()
    odds_main = data["odds_main"]
    pm_price = data["pm_price"]

    # Calculate cross hedge
    result = HedgeService.calculate_cross_hedge(
        odds_main=odds_main,
        pm_yes_price=pm_price,
        stake=stake,
        percent=100.0,
    )

    if result.error:
        await message.reply(f"❌ Ошибка расчета: {result.error}")
        await state.clear()
        return

    # Check arbitrage
    arb = HedgeService.detect_arbitrage_with_pm(odds_main, pm_price)

    # Build response
    pm_no_price = 1 - pm_price
    pm_no_odds = 1 / pm_no_price if pm_no_price > 0 else float("inf")

    text_parts = [
        "🔄 КРОСС-ХЕДЖ ОТЧЁТ\n",
        "📊 Параметры:",
        f"  • Кэф БК: {format_odds(odds_main)}",
        f"  • Polymarket Yes: {format_percentage(pm_price)} (= {format_odds(HedgeService.calculate_cross_hedge(1, 0, pm_price, 0).pm_price if False else 1/pm_price)})" if pm_price > 0 else f"  • Polymarket Yes: {format_percentage(pm_price)}",
        f"  • Polymarket No: {format_percentage(pm_no_price)} (= {format_odds(pm_no_odds)})",
        f"  • Стейк: {format_currency(stake)}\n",
        "📈 Результаты:",
        f"  • Full Hedge: {format_currency(result.full_hedge or 0)}",
        f"  • Lock Profit: {format_currency(result.lock_profit or 0)}\n",
    ]

    if result.is_arbitrage and result.guaranteed_profit:
        text_parts.append("🟢 АРБИТРАЖ ОБНАРУЖЕН!")
        text_parts.append(f"  • Маржа: {format_percentage(result.arbitrage_margin_pm or 0)}")
        text_parts.append(f"  • Гарантированная прибыль: {format_currency(result.guaranteed_profit)}\n")

    if arb.is_arbitrage and arb.margin:
        text_parts.append(f"📊 Arbitrage Margin: {format_percentage(arb.margin)}")
        text_parts.append(f"  • Implied Prob (BK): {format_percentage(arb.bookmaker_implied_probability or 0)}")
        text_parts.append(f"  • PM No Price: {format_percentage(arb.polymarket_no_price or 0)}\n")

    text_parts.append("⚠️ Не является инвестиционной рекомендацией.")

    await message.reply("\n".join(text_parts))
    await state.clear()


async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.reply(
        "❌ Расчет отменен.\n\n"
        "Используйте /xhedge для нового расчета."
    )
