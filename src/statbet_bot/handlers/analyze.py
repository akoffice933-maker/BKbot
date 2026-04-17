from aiogram import types
from statbet_bot.services.prediction import PredictionService
from statbet_bot.utils.formatters import format_probability, format_percentage, format_odds

service = PredictionService()

async def analyze_handler(message: types.Message):
    # Placeholder: Parse match ID from message
    result = service.get_prediction({})  # Dummy data

    if result.error:
        await message.reply(f"❌ Ошибка анализа: {result.error}")
        return

    text = (
        "📊 ВЕРОЯТНОСТНАЯ ОЦЕНКА МОДЕЛИ\n"
        "Матч: Спартак — Зенит\n\n"
        f"🔮 Исходы:\n"
        f"• ТБ 2.5: {format_probability(result.tb_25)}\n"
        f"• ТМ 2.5: {format_probability(result.tm_25)}\n\n"
        "📈 Рыночная оценка (Implied Probability):\n"
        f"• ТБ 2.5: ~51% (кэф {format_odds(1.95)})\n"
        f"• ТМ 2.5: ~48% (кэф {format_odds(2.10)})\n\n"
        "🔍 Ключевые факторы (SHAP):\n"
        + "\n".join(f"• {f}" for f in result.factors)
        + "\n\n"
        "⚠️ Данные носят ознакомительный характер."
    )
    await message.reply(text)