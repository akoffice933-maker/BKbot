"""Prediction service for match outcome predictions."""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from statbet_bot.models import PredictionModel


@dataclass
class PredictionResult:
    """Result of prediction."""
    tb_25: float
    tm_25: float
    factors: list[str]
    confidence: str
    error: Optional[str] = None


class PredictionService:
    """Service for match predictions."""
    
    def __init__(self):
        self.model = PredictionModel()
    
    def get_prediction(self, match_data: Dict[str, Any]) -> PredictionResult:
        """Get prediction for a match."""
        try:
            result = self.model.predict(match_data)
            return PredictionResult(
                tb_25=result["TB_2.5"],
                tm_25=result["TM_2.5"],
                factors=result["factors"],
                confidence=result["confidence"]
            )
        except Exception as e:
            return PredictionResult(
                tb_25=0.0,
                tm_25=0.0,
                factors=[],
                confidence="Unknown",
                error=str(e)
            )