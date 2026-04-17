"""Tests for HedgeCalculator, HedgeService, HedgeInput and validators."""

import pytest
from statbet_bot.models import HedgeCalculator, HedgeInput
from statbet_bot.services.hedge import HedgeService
from statbet_bot.utils.validators import validate_stake, validate_odds, validate_percent


class TestHedgeCalculator:
    """Unit-tests for raw HedgeCalculator math."""

    # --- full_hedge ---
    # Formula: stake * (k_main - 1) / (k_hedge - 1)
    # 100 * (2.0 - 1) / (1.8 - 1) = 100 / 0.8 = 125.0

    def test_full_hedge_valid(self):
        result = HedgeCalculator.full_hedge(100, 2.0, 1.8)
        assert result == pytest.approx(125.0)

    def test_full_hedge_equal_odds(self):
        # k_main == k_hedge => hedge == stake
        result = HedgeCalculator.full_hedge(100, 2.0, 2.0)
        assert result == pytest.approx(100.0)

    def test_full_hedge_invalid_stake(self):
        with pytest.raises(ValueError):
            HedgeCalculator.full_hedge(0, 2.0, 1.8)

    def test_full_hedge_negative_stake(self):
        with pytest.raises(ValueError):
            HedgeCalculator.full_hedge(-50, 2.0, 1.8)

    def test_full_hedge_k_main_le_1(self):
        with pytest.raises(ValueError):
            HedgeCalculator.full_hedge(100, 1.0, 1.8)

    def test_full_hedge_k_hedge_le_1(self):
        with pytest.raises(ValueError):
            HedgeCalculator.full_hedge(100, 2.0, 1.0)

    # --- partial_hedge ---
    # Formula: stake * (k_main - 1) * (percent / 100) / (k_hedge - 1)
    # 100 * 1.0 * 0.50 / 0.8 = 62.5

    def test_partial_hedge_50_percent(self):
        result = HedgeCalculator.partial_hedge(100, 2.0, 1.8, 50)
        assert result == pytest.approx(62.5)

    def test_partial_hedge_100_percent_equals_full(self):
        full = HedgeCalculator.full_hedge(100, 2.0, 1.8)
        partial = HedgeCalculator.partial_hedge(100, 2.0, 1.8, 100)
        assert partial == pytest.approx(full)

    def test_partial_hedge_zero_percent(self):
        # percent=0 is valid (ge=0); result must be 0.0
        result = HedgeCalculator.partial_hedge(100, 2.0, 1.8, 0)
        assert result == pytest.approx(0.0)

    def test_partial_hedge_invalid_percent(self):
        with pytest.raises(ValueError):
            HedgeCalculator.partial_hedge(100, 2.0, 1.8, 150)

    # --- lock_profit ---
    # Formula: stake * k_main / k_hedge
    # 100 * 2.0 / 1.8 = 111.111...

    def test_lock_profit_valid(self):
        result = HedgeCalculator.lock_profit(100, 2.0, 1.8)
        assert result == pytest.approx(111.11, rel=1e-3)

    def test_lock_profit_invalid_stake(self):
        with pytest.raises(ValueError):
            HedgeCalculator.lock_profit(0, 2.0, 1.8)


class TestHedgeService:
    """Integration-tests for HedgeService (validation + delegation to HedgeCalculator)."""

    def test_calculate_returns_correct_values(self):
        result = HedgeService.calculate(100, 2.0, 1.8, 50)
        assert result.error is None
        assert result.full_hedge == pytest.approx(125.0)
        assert result.partial_hedge == pytest.approx(62.5)
        assert result.lock_profit == pytest.approx(111.11, rel=1e-3)

    def test_calculate_returns_error_on_zero_stake(self):
        result = HedgeService.calculate(0, 2.0, 1.8)
        assert result.error is not None
        assert result.full_hedge is None

    def test_calculate_accepts_min_stake_boundary(self):
        result = HedgeService.calculate(0.01, 2.0, 1.8)
        assert result.error is None
        assert result.full_hedge is not None

    def test_calculate_rejects_stake_below_min(self):
        result = HedgeService.calculate(0.001, 2.0, 1.8)
        assert result.error is not None

    def test_calculate_returns_error_on_negative_stake(self):
        result = HedgeService.calculate(-10, 2.0, 1.8)
        assert result.error is not None

    def test_calculate_returns_error_on_stake_over_max(self):
        result = HedgeService.calculate(2_000_000, 2.0, 1.8)
        assert result.error is not None

    def test_calculate_returns_error_on_bad_odds(self):
        result = HedgeService.calculate(100, 1.0, 1.8)
        assert result.error is not None

    def test_calculate_returns_error_on_odds_over_max(self):
        result = HedgeService.calculate(100, 200.0, 1.8)
        assert result.error is not None

    def test_arbitrage_detected(self):
        # 1/3.0 + 1/3.0 = 0.666 < 1 => arbitrage
        result = HedgeService.calculate(100, 3.0, 3.0)
        assert result.is_arbitrage is True
        assert result.guaranteed_profit is not None
        assert result.guaranteed_profit > 0

    def test_no_arbitrage(self):
        # 1/1.5 + 1/1.5 = 1.333 > 1 => no arbitrage
        result = HedgeService.calculate(100, 1.5, 1.5)
        assert result.is_arbitrage is False
        assert result.guaranteed_profit is None


class TestHedgeInput:
    """Tests for Pydantic HedgeInput model."""

    def test_valid_input(self):
        hi = HedgeInput(stake=100, k_main=2.0, k_hedge=1.8, percent=50)
        assert hi.stake == 100
        assert hi.percent == 50

    def test_valid_input_allows_max_boundaries(self):
        hi = HedgeInput(stake=1_000_000, k_main=100.0, k_hedge=100.0, percent=100)
        assert hi.stake == 1_000_000
        assert hi.k_main == 100.0

    def test_optional_percent_defaults_to_none(self):
        hi = HedgeInput(stake=100, k_main=2.0, k_hedge=1.8)
        assert hi.percent is None

    def test_invalid_stake_negative(self):
        with pytest.raises(Exception):
            HedgeInput(stake=-1, k_main=2.0, k_hedge=1.8)

    def test_invalid_stake_zero(self):
        with pytest.raises(Exception):
            HedgeInput(stake=0, k_main=2.0, k_hedge=1.8)

    def test_invalid_k_main(self):
        with pytest.raises(Exception):
            HedgeInput(stake=100, k_main=0.5, k_hedge=1.8)

    def test_invalid_percent_over_100(self):
        with pytest.raises(Exception):
            HedgeInput(stake=100, k_main=2.0, k_hedge=1.8, percent=200)

    def test_invalid_percent_negative(self):
        with pytest.raises(Exception):
            HedgeInput(stake=100, k_main=2.0, k_hedge=1.8, percent=-1)

    def test_invalid_stake_over_max(self):
        with pytest.raises(Exception):
            HedgeInput(stake=1_000_000.01, k_main=2.0, k_hedge=1.8)

    def test_invalid_odds_over_max(self):
        with pytest.raises(Exception):
            HedgeInput(stake=100, k_main=100.1, k_hedge=1.8)


class TestValidators:
    """Tests for utility validators."""

    # --- validate_stake ---

    def test_stake_valid(self):
        ok, val, err = validate_stake("100")
        assert ok is True and val == 100.0 and err is None

    def test_stake_zero(self):
        ok, val, err = validate_stake("0")
        assert ok is False and err is not None

    def test_stake_negative(self):
        ok, val, err = validate_stake("-50")
        assert ok is False

    def test_stake_text(self):
        ok, val, err = validate_stake("abc")
        assert ok is False

    def test_stake_nan(self):
        ok, val, err = validate_stake("nan")
        assert ok is False

    def test_stake_inf(self):
        ok, val, err = validate_stake("inf")
        assert ok is False

    def test_stake_exceeds_max(self):
        ok, val, err = validate_stake("9999999999")
        assert ok is False

    # --- validate_odds ---

    def test_odds_valid(self):
        ok, val, err = validate_odds("2.5")
        assert ok is True and val == 2.5

    def test_odds_le_1(self):
        ok, val, err = validate_odds("1.0")
        assert ok is False

    def test_odds_exceeds_max(self):
        ok, val, err = validate_odds("200")
        assert ok is False

    def test_odds_text(self):
        ok, val, err = validate_odds("high")
        assert ok is False

    def test_odds_error_message_correct(self):
        ok, val, err = validate_odds("0.5")
        assert ok is False
        assert "1.0" in err

    # --- validate_percent ---

    def test_percent_valid(self):
        ok, val, err = validate_percent("75")
        assert ok is True and val == 75.0

    def test_percent_zero(self):
        ok, val, err = validate_percent("0")
        assert ok is True and val == 0.0

    def test_percent_hundred(self):
        ok, val, err = validate_percent("100")
        assert ok is True

    def test_percent_over_hundred(self):
        ok, val, err = validate_percent("101")
        assert ok is False

    def test_percent_negative(self):
        ok, val, err = validate_percent("-1")
        assert ok is False
