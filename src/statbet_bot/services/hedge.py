"""Hedge calculation service with validation."""

from typing import Optional
from dataclasses import dataclass
from pydantic import ValidationError

from statbet_bot.models import HedgeCalculator, HedgeInput
from statbet_bot.constants import ValidationLimits


@dataclass
class HedgeResult:
    """Result of hedge calculation."""
    full_hedge: Optional[float]
    partial_hedge: Optional[float]
    lock_profit: Optional[float]
    is_arbitrage: bool
    guaranteed_profit: Optional[float]
    error: Optional[str] = None


class HedgeService:
    """Service for calculating hedging strategies."""
    
    # Use constants from ValidationLimits
    MIN_ODDS = ValidationLimits.MIN_ODDS
    MAX_ODDS = ValidationLimits.MAX_ODDS
    MAX_STAKE = ValidationLimits.MAX_STAKE
    MIN_STAKE = ValidationLimits.MIN_STAKE
    MIN_PERCENT = ValidationLimits.MIN_PERCENT
    MAX_PERCENT = ValidationLimits.MAX_PERCENT

    @staticmethod
    def _validate_inputs(
        stake: float,
        k_main: float,
        k_hedge: float,
        percent: float = 100.0
    ) -> Optional[str]:
        """Validate input parameters."""
        try:
            HedgeInput(stake=stake, k_main=k_main, k_hedge=k_hedge, percent=percent)
        except ValidationError as exc:
            first_error = exc.errors()[0]
            field_name = first_error["loc"][0]
            error_type = first_error["type"]

            if field_name == "stake":
                if error_type == "greater_than_equal":
                    return f"Сумма ставки должна быть не меньше {HedgeService.MIN_STAKE}"
                if error_type == "less_than_equal":
                    return f"Сумма ставки не может превышать {HedgeService.MAX_STAKE:,.0f}"
            if field_name == "k_main":
                if error_type == "greater_than":
                    return "Коэффициент должен быть больше 1.0"
                if error_type == "less_than_equal":
                    return f"Коэффициент не может превышать {HedgeService.MAX_ODDS}"
            if field_name == "k_hedge":
                if error_type == "greater_than":
                    return "Коэффициент хеджа должен быть больше 1.0"
                if error_type == "less_than_equal":
                    return f"Коэффициент хеджа не может превышать {HedgeService.MAX_ODDS}"
            if field_name == "percent":
                return (
                    f"Процент покрытия должен быть от "
                    f"{HedgeService.MIN_PERCENT} до {HedgeService.MAX_PERCENT}"
                )

            return "Некорректные входные данные"

        return None
    
    @classmethod
    def calculate(
        cls,
        stake: float,
        k_main: float,
        k_hedge: float,
        percent: float = 100.0
    ) -> HedgeResult:
        """
        Calculate all hedge strategies.
        
        Args:
            stake: Original stake amount
            k_main: Odds of the original bet
            k_hedge: Odds of the opposite outcome
            percent: Percentage to hedge (0-100)
            
        Returns:
            HedgeResult with all calculations
        """
        # Validate inputs
        error = cls._validate_inputs(stake, k_main, k_hedge, percent)
        if error:
            return HedgeResult(
                full_hedge=None,
                partial_hedge=None,
                lock_profit=None,
                is_arbitrage=False,
                guaranteed_profit=None,
                error=error
            )
        
        # Delegate all math to HedgeCalculator (single source of truth)
        full_hedge = HedgeCalculator.full_hedge(stake, k_main, k_hedge)
        partial_hedge = HedgeCalculator.partial_hedge(stake, k_main, k_hedge, percent)
        lock_profit = HedgeCalculator.lock_profit(stake, k_main, k_hedge)
        
        # Check for arbitrage opportunity
        is_arbitrage, guaranteed_profit = cls._check_arbitrage(stake, k_main, k_hedge)
        
        return HedgeResult(
            full_hedge=full_hedge,
            partial_hedge=partial_hedge,
            lock_profit=lock_profit,
            is_arbitrage=is_arbitrage,
            guaranteed_profit=guaranteed_profit
        )
    
    @staticmethod
    def _check_arbitrage(
        stake: float,
        k_main: float,
        k_hedge: float
    ) -> tuple[bool, Optional[float]]:
        """
        Check if arbitrage opportunity exists.
        
        Arbitrage exists when: 1/k1 + 1/k2 < 1
        
        Returns:
            Tuple of (is_arbitrage, guaranteed_profit_amount)
        """
        implied_prob_sum = (1 / k_main) + (1 / k_hedge)
        
        if implied_prob_sum < 1.0:
            # Calculate guaranteed profit percentage
            profit_margin = 1.0 - implied_prob_sum
            
            # Calculate optimal stakes for arbitrage
            total_stake = stake + (stake * k_main / k_hedge)
            guaranteed_profit = total_stake * profit_margin
            
            return True, guaranteed_profit
        
        return False, None
    
    @staticmethod
    def calculate_roi(
        stake: float,
        odds: float,
        win_probability: float
    ) -> float:
        """
        Calculate expected ROI for a bet.
        
        Args:
            stake: Bet amount
            odds: Betting odds
            win_probability: Win probability (0.0-1.0)
            
        Returns:
            Expected ROI as percentage
        """
        if not 0 <= win_probability <= 1:
            raise ValueError("Probability must be between 0 and 1")
        
        expected_return = (stake * odds * win_probability) - stake
        roi = (expected_return / stake) * 100 if stake > 0 else 0
        
        return roi

