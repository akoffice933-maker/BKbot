from aiogram import Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.state import any_state
from statbet_bot.handlers.start import StartStates, process_age_confirm, start_handler
from statbet_bot.handlers.matches import matches_handler
from statbet_bot.handlers.analyze import analyze_handler
from statbet_bot.handlers.calc_hedge import (
    calc_hedge_handler,
    process_stake,
    process_k_main,
    process_k_hedge,
    process_percent,
    cancel_handler,
    HedgeStates
)
from statbet_bot.handlers.other import track_handler, untrack_handler, status_handler, paper_handler, stats_handler


def register_handlers(dp: Dispatcher):
    # Command filters for aiogram 3.x
    dp.message.register(start_handler, Command("start"))
    dp.message.register(matches_handler, Command("matches"))
    dp.message.register(analyze_handler, Command("analyze"))
    dp.message.register(calc_hedge_handler, Command("calc_hedge"))
    dp.message.register(track_handler, Command("track"))
    dp.message.register(untrack_handler, Command("untrack"))
    dp.message.register(cancel_handler, Command("cancel"), any_state)
    dp.message.register(status_handler, Command("status"))
    dp.message.register(paper_handler, Command("paper"))
    dp.message.register(stats_handler, Command("stats"))

    # FSM handlers - use F filter to match state
    dp.message.register(process_age_confirm, F.text, StartStates.waiting_for_age_confirm)
    dp.message.register(process_stake, F.text, HedgeStates.waiting_for_stake)
    dp.message.register(process_k_main, F.text, HedgeStates.waiting_for_k_main)
    dp.message.register(process_k_hedge, F.text, HedgeStates.waiting_for_k_hedge)
    dp.message.register(process_percent, F.text, HedgeStates.waiting_for_percent)
