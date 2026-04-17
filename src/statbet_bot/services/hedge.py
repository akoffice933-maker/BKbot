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
    pm_price: Optional[float] = None
    cross_hedge_amount: Optional[float] = None
    arbitrage_margin_pm: Optional[float] = None
    error: Optional[str] = None


@dataclass
class ArbitrageResult:
    """Result of arbitrage detection between bookmaker odds and Polymarket."""

    is_arbitrage: bool
    margin: Optional[float]
    bookmaker_implied_probability: Optional[float]
    polymarket_yes_price: Optional[float]
    polymarket_no_price: Optional[float]
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
    def _validate_pm_price(pm_price: float) -> Optional[str]:
        if not 0 < pm_price < 1:
            return "Цена Polymarket должна быть между 0 и 1"
        return None

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
    def _validate_cross_inputs(
        cls,
        stake: float,
        odds_main: float,
        pm_yes_price: float,
        percent: float,
    ) -> Optional[str]:
        try:
            HedgeInput(stake=stake, k_main=odds_main, k_hedge=2.0, percent=percent)
        except ValidationError as exc:
            first_error = exc.errors()[0]
            field_name = first_error["loc"][0]
            error_type = first_error["type"]

            if field_name == "stake":
                if error_type == "greater_than_equal":
                    return f"Сумма ставки должна быть не меньше {cls.MIN_STAKE}"
                if error_type == "less_than_equal":
                    return f"Сумма ставки не может превышать {cls.MAX_STAKE:,.0f}"
            if field_name == "k_main":
                if error_type == "greater_than":
                    return "Коэффициент должен быть больше 1.0"
                if error_type == "less_than_equal":
                    return f"Коэффициент не может превышать {cls.MAX_ODDS}"
            if field_name == "percent":
                return f"Процент покрытия должен быть от {cls.MIN_PERCENT} до {cls.MAX_PERCENT}"

            return "Некорректные входные данные"

        return cls._validate_pm_price(pm_yes_price)
    
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

    @classmethod
    def calculate_cross_hedge(
        cls,
        odds_main: float,
        pm_yes_price: float,
        stake: float,
        percent: float = 100.0,
    ) -> HedgeResult:
        """
        Calculate cross-hedge against Polymarket NO shares using a Yes price.

        The Polymarket NO share price is derived as `1 - pm_yes_price`, then
        converted to effective decimal odds via `1 / no_price`.
        """
        error = cls._validate_cross_inputs(stake, odds_main, pm_yes_price, percent)
        if error:
            return HedgeResult(
                full_hedge=None,
                partial_hedge=None,
                lock_profit=None,
                is_arbitrage=False,
                guaranteed_profit=None,
                pm_price=pm_yes_price,
                cross_hedge_amount=None,
                arbitrage_margin_pm=None,
                error=error,
            )

        pm_no_price = 1.0 - pm_yes_price
        pm_no_odds = 1.0 / pm_no_price

        full_hedge = HedgeCalculator.full_hedge(stake, odds_main, pm_no_odds)
        partial_hedge = HedgeCalculator.partial_hedge(stake, odds_main, pm_no_odds, percent)
        lock_profit = HedgeCalculator.lock_profit(stake, odds_main, pm_no_odds)
        is_arbitrage, guaranteed_profit, margin = cls._check_arbitrage_with_pm(
            stake,
            odds_main,
            pm_yes_price,
        )

        return HedgeResult(
            full_hedge=full_hedge,
            partial_hedge=partial_hedge,
            lock_profit=lock_profit,
            is_arbitrage=is_arbitrage,
            guaranteed_profit=guaranteed_profit,
            pm_price=pm_yes_price,
            cross_hedge_amount=partial_hedge,
            arbitrage_margin_pm=margin,
        )

    @classmethod
    def detect_arbitrage_with_pm(cls, odds: float, pm_price: float) -> ArbitrageResult:
        """Detect arbitrage between bookmaker odds and Polymarket YES price."""
        # 1. Validate pm_price independently
        pm_err = cls._validate_pm_price(pm_price)
        if pm_err:
            return ArbitrageResult(
                is_arbitrage=False,
                margin=None,
                bookmaker_implied_probability=None,
                polymarket_yes_price=pm_price,
                polymarket_no_price=None,
                error=pm_err,
            )

        # 2. Validate odds independently
        if odds <= cls.MIN_ODDS:
            return ArbitrageResult(
                is_arbitrage=False,
                margin=None,
                bookmaker_implied_probability=None,
                polymarket_yes_price=pm_price,
                polymarket_no_price=None,
                error="Коэффициент должен быть больше 1.0",
            )
        if odds > cls.MAX_ODDS:
            return ArbitrageResult(
                is_arbitrage=False,
                margin=None,
                bookmaker_implied_probability=None,
                polymarket_yes_price=pm_price,
                polymarket_no_price=None,
                error=f"Коэффициент не может превышать {cls.MAX_ODDS}",
            )

        # 3. Calculate arbitrage
        bookmaker_probability = 1 / odds
        polymarket_no_price = 1 - pm_price
        implied_prob_sum = bookmaker_probability + polymarket_no_price
        margin = 1.0 - implied_prob_sum

        return ArbitrageResult(
            is_arbitrage=margin > 0,
            margin=margin if margin > 0 else None,
            bookmaker_implied_probability=bookmaker_probability,
            polymarket_yes_price=pm_price,
            polymarket_no_price=polymarket_no_price,
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
    def _check_arbitrage_with_pm(
        stake: float,
        odds_main: float,
        pm_yes_price: float,
    ) -> tuple[bool, Optional[float], Optional[float]]:
        """
        Check arbitrage between bookmaker odds on YES and Polymarket NO shares.

        Arbitrage exists when: 1/odds_main + (1 - pm_yes_price) < 1
        """
        polymarket_no_price = 1.0 - pm_yes_price
        implied_prob_sum = (1 / odds_main) + polymarket_no_price

        if implied_prob_sum < 1.0:
            margin = 1.0 - implied_prob_sum
            pm_no_odds = 1.0 / polymarket_no_price
            total_stake = stake + (stake * odds_main / pm_no_odds)
            guaranteed_profit = total_stake * margin
            return True, guaranteed_profit, margin

        return False, None, None
    
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

