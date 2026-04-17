import pandas as pd
import xgboost as xgb
import shap
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

from statbet_bot.constants import ValidationLimits


class HedgeCalculator:

    @staticmethod
    def full_hedge(stake: float, k_main: float, k_hedge: float) -> float:
        """Formula: stake * (k_main - 1) / (k_hedge - 1)"""
        if stake <= 0 or k_main <= 1 or k_hedge <= 1:
            raise ValueError("Invalid input: stake > 0, k_main > 1, k_hedge > 1")
        return stake * (k_main - 1) / (k_hedge - 1)

    @staticmethod
    def partial_hedge(stake: float, k_main: float, k_hedge: float, percent: float) -> float:
        """Formula: stake * (k_main - 1) * (percent / 100) / (k_hedge - 1)"""
        if stake <= 0 or k_main <= 1 or k_hedge <= 1 or not (0 <= percent <= 100):
            raise ValueError("Invalid input: stake > 0, k_main > 1, k_hedge > 1, 0 <= percent <= 100")
        return stake * (k_main - 1) * (percent / 100) / (k_hedge - 1)

    @staticmethod
    def lock_profit(stake: float, k_main: float, k_hedge: float) -> float:
        """Formula: stake * k_main / k_hedge"""
        if stake <= 0 or k_main <= 1 or k_hedge <= 1:
            raise ValueError("Invalid input: stake > 0, k_main > 1, k_hedge > 1")
        return stake * (k_main / k_hedge)


class HedgeInput(BaseModel):
    stake: float = Field(..., ge=ValidationLimits.MIN_STAKE, le=ValidationLimits.MAX_STAKE)
    k_main: float = Field(..., gt=ValidationLimits.MIN_ODDS, le=ValidationLimits.MAX_ODDS)
    k_hedge: float = Field(..., gt=ValidationLimits.MIN_ODDS, le=ValidationLimits.MAX_ODDS)
    percent: Optional[float] = Field(
        None,
        ge=ValidationLimits.MIN_PERCENT,
        le=ValidationLimits.MAX_PERCENT,
    )


class PredictionModel:

    def __init__(self):
        self.model = None
        self.explainer = None

    def train(self, data: pd.DataFrame):
        # Placeholder: load data, preprocess, train XGBoost
        pass

    def predict(self, match_data: dict) -> Dict[str, Any]:
        # Placeholder prediction — replace with real model inference
        return {
            "TB_2.5": 0.67,
            "TM_2.5": 0.33,
            "factors": [
                "xG последних 5 матчей: +12%",
                "Домашнее поле: +8%",
                "Травма форварда: -5%",
            ],
            "confidence": "High",
        }
