"""Input validators for user data."""

import math
from typing import Optional, Tuple
from statbet_bot.constants import ValidationLimits


def validate_stake(value: str, max_stake: float = None) -> Tuple[bool, Optional[float], Optional[str]]:
    """
    Validate stake amount.
    
    Args:
        value: User input string
        max_stake: Maximum allowed stake (overrides default)
        
    Returns:
        Tuple of (is_valid, parsed_value, error_message)
    """
    if max_stake is None:
        max_stake = ValidationLimits.MAX_STAKE
    
    try:
        stake = float(value)
        
        if math.isnan(stake) or math.isinf(stake):
            return False, None, ValidationLimits.ERROR_NAN_INF
        
        if stake <= 0:
            return False, None, ValidationLimits.ERROR_STAKE_POSITIVE
        
        if stake > max_stake:
            return False, None, f"Сумма не может превышать {max_stake:,.0f}"
        
        # Проверка на разумный минимум
        if stake < ValidationLimits.MIN_STAKE:
            return False, None, f"Минимальная сумма: {ValidationLimits.MIN_STAKE}"
        
        return True, stake, None
        
    except (ValueError, TypeError):
        return False, None, ValidationLimits.ERROR_INVALID_NUMBER


def validate_odds(value: str, min_odds: float = None, max_odds: float = None) -> Tuple[bool, Optional[float], Optional[str]]:
    """
    Validate betting odds.
    
    Args:
        value: User input string
        min_odds: Minimum allowed odds (overrides default)
        max_odds: Maximum allowed odds (overrides default)
        
    Returns:
        Tuple of (is_valid, parsed_value, error_message)
    """
    if min_odds is None:
        min_odds = ValidationLimits.MIN_ODDS
    if max_odds is None:
        max_odds = ValidationLimits.MAX_ODDS
    
    try:
        odds = float(value)
        
        if math.isnan(odds) or math.isinf(odds):
            return False, None, ValidationLimits.ERROR_NAN_INF
        
        if odds <= min_odds:
            return False, None, f"Коэффициент должен быть больше {min_odds}"
        
        if odds > max_odds:
            return False, None, f"Коэффициент не может превышать {max_odds}"
        
        return True, odds, None
        
    except (ValueError, TypeError):
        return False, None, ValidationLimits.ERROR_INVALID_NUMBER


def validate_percent(value: str) -> Tuple[bool, Optional[float], Optional[str]]:
    """
    Validate percentage value (0-100).
    
    Args:
        value: User input string
        
    Returns:
        Tuple of (is_valid, parsed_value, error_message)
    """
    try:
        percent = float(value)
        
        if math.isnan(percent) or math.isinf(percent):
            return False, None, ValidationLimits.ERROR_NAN_INF
        
        if percent < ValidationLimits.MIN_PERCENT or percent > ValidationLimits.MAX_PERCENT:
            return False, None, f"Процент должен быть от {ValidationLimits.MIN_PERCENT} до {ValidationLimits.MAX_PERCENT}"
        
        return True, percent, None
        
    except (ValueError, TypeError):
        return False, None, ValidationLimits.ERROR_INVALID_NUMBER
