"""Polymarket handlers with inline buttons and pagination."""

from __future__ import annotations

import json
import logging
from typing import Any

from aiogram import types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from statbet_bot.services.polymarket import PolymarketService, PolymarketServiceError

logger = logging.getLogger(__name__)

SEARCH_PAGE_SIZE = 5


class PmStates(StatesGroup):
    """FSM states for Polymarket cross-hedge calculator."""
    waiting_for_odds = State()
    waiting_for_pm_price = State()


# ──────────────────────────────────────────────
# /pm command: search by text or show by slug
# ──────────────────────────────────────────────

async def pm_handler(message: types.Message, state: FSMContext, pm: PolymarketService):
    """Handle /pm command with arguments."""
    text = message.text.strip()
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        await message.reply(
            "📊 Использование:\n"
            "• `/pm search <запрос>` — поиск рынков\n"
            "• `/pm <slug>` — показать рынок по slug\n"
            "\nДля кросс-хеджа используйте `/xhedge`"
        )
        return

    await state.clear()

    command = parts[1].strip().lower()
    if command == "search":
        await _handle_search(message, pm)
    else:
        await _handle_show_by_slug(message, parts[1].strip(), pm)


# ──────────────────────────────────────────────
# Callback handlers for pagination and details
# ──────────────────────────────────────────────

async def cb_pm_page(call: types.CallbackQuery, state: FSMContext, pm: PolymarketService):
    """Handle pagination buttons."""
    data = json.loads(call.data.split(":", 1)[1])
    query = data.get("q", "")
    page = data.get("page", 1)

    await _handle_search(call.message, pm, query=query, page=page)
    await call.answer()


async def cb_pm_detail(call: types.CallbackQuery, pm: PolymarketService):
    """Handle detail button click."""
    slug = call.data.split(":", 1)[1]
    await call.answer()

    loading_msg = await call.message.answer("⏳ Загружаю рынок...")

    try:
        market = await pm.get_market(slug)
        text = _format_market_card(market)
        await loading_msg.edit_text(text, parse_mode="HTML")
    except PolymarketServiceError as e:
        await loading_msg.edit_text(f"❌ Ошибка: {e}")
    except Exception as e:
        logger.exception("Error in polymarket detail")
        await loading_msg.edit_text(f"❌ Ошибка загрузки: {e}")


# ──────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────

async def _handle_search(
    message: types.Message | types.CallbackQuery,
    pm: PolymarketService,
    query: str = "",
    page: int = 1,
):
    """Search markets and show results with pagination."""
    if isinstance(message, types.CallbackQuery):
        msg = message.message
    else:
        msg = message

    # Parse query from page data or use empty
    search_query = query if query else msg.text.split("search", 1)[-1].strip() if hasattr(msg, "text") and msg.text else ""

    if not search_query:
        await msg.answer(
            "🔍 Введите запрос для поиска:\n"
            "`/pm search <тема>`\n\n"
            "Пример: `/pm search election`"
        )
        return

    await msg.answer(f"🔍 Ищу: *{search_query}*", parse_mode="Markdown")

    try:
        markets = await pm.search_markets(search_query, limit=(page + 1) * SEARCH_PAGE_SIZE)
    except PolymarketServiceError as e:
        await msg.answer(f"❌ Ошибка поиска: {e}")
        return
    except Exception as e:
        logger.exception("Polymarket search error")
        await msg.answer(f"❌ Ошибка: {e}")
        return

    if not markets:
        await msg.answer(f"😔 Ничего не найдено по запросу «{search_query}»")
        return

    # Slice current page
    start = (page - 1) * SEARCH_PAGE_SIZE
    end = start + SEARCH_PAGE_SIZE
    page_items = markets[start:end]

    # Build keyboard
    keyboard = _build_search_keyboard(page_items, page, has_next=end < len(markets), query=search_query)

    text = f"📊 Результаты поиска: «{search_query}» (стр. {page})\n\n"
    for i, m in enumerate(page_items, start=1):
        price_text = ""
        if m.get("yes_price") is not None:
            yes_p = m["yes_price"]
            no_p = m.get("no_price")
            price_text = f"  Yes: {yes_p:.2%} | No: {no_p:.2%}" if no_p else f"  Yes: {yes_p:.2%}"
        status = "🟢" if m.get("active") else "🔴"
        question = m.get("question", "Без вопроса")
        if len(question) > 100:
            question = question[:97] + "..."
        text += f"{status} {i}. {question}\n{price_text}\n\n"

    await msg.answer(text, reply_markup=keyboard, parse_mode="HTML")


async def _handle_show_by_slug(message: types.Message, slug: str, pm: PolymarketService):
    """Show market details by slug."""
    try:
        market = await pm.get_market(slug)
    except PolymarketServiceError as e:
        await message.answer(f"❌ Ошибка: {e}")
        return
    except Exception as e:
        logger.exception("Polymarket market error")
        await message.answer(f"❌ Ошибка загрузки: {e}")
        return

    text = _format_market_card(market)
    await message.answer(text, parse_mode="HTML")


def _format_market_card(market: dict[str, Any]) -> str:
    """Format market as HTML card."""
    question = market.get("question", "N/A")
    status = "🟢 Active" if market.get("active") else "🔴 Closed"
    category = market.get("category", "N/A")

    lines = [
        f"📊 <b>{question}</b>",
        f"",
        f"Статус: {status}",
        f"Категория: {category}",
    ]

    yes_price = market.get("yes_price")
    no_price = market.get("no_price")

    if yes_price is not None:
        yes_odds = 1 / yes_price if yes_price > 0 else float("inf")
        no_odds = 1 / no_price if no_price and no_price > 0 else float("inf")

        lines.append("")
        lines.append("💰 <b>Цены:</b>")
        lines.append(f"  Yes: {yes_price:.2%} = {yes_odds:.2f} кэф")
        if no_price is not None:
            lines.append(f"  No:  {no_price:.2%} = {no_odds:.2f} кэф")
    else:
        lines.append("")
        lines.append("💰 Цены не доступны")

    url = market.get("url")
    if url:
        lines.append("")
        lines.append(f"🔗 <a href='{url}'>Открыть в Polymarket</a>")

    lines.append("")
    lines.append(f"⚠️ Не является инвестиционной рекомендацией.")

    return "\n".join(lines)


def _build_search_keyboard(
    markets: list[dict],
    page: int,
    has_next: bool,
    query: str,
) -> InlineKeyboardMarkup:
    """Build inline keyboard with detail buttons and pagination."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    # Detail buttons for each market
    for m in markets:
        slug = m.get("slug")
        question = m.get("question", "Unknown")[:50]
        if not slug:
            continue
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=f"📖 {question}", callback_data=f"pm_detail:{slug}")
        ])

    # Pagination row
    nav_row = []
    if page > 1:
        prev_data = json.dumps({"q": query, "page": page - 1})
        nav_row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"pm_page:{prev_data}"))
    if has_next:
        next_data = json.dumps({"q": query, "page": page + 1})
        nav_row.append(InlineKeyboardButton(text="Далее ➡️", callback_data=f"pm_page:{next_data}"))

    if nav_row:
        keyboard.inline_keyboard.append(nav_row)

    return keyboard
