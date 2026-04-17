"""Formatting utilities for displaying data."""


def format_probability(prob: float, show_bar: bool = True, bar_length: int = 20) -> str:
    """
    Format probability as percentage with optional visual bar.
    
    Args:
        prob: Probability value (0.0-1.0)
        show_bar: Whether to show visual bar
        bar_length: Length of the visual bar
        
    Returns:
        Formatted string
    """
    if not 0 <= prob <= 1:
        return "❌ Ошибка данных"
    
    percent = prob * 100
    bar = ""
    
    if show_bar:
        filled = int(bar_length * prob)
        empty = bar_length - filled
        bar = f" {'█' * filled}{'░' * empty}"
    
    return f"{percent:.0f}%{bar}"


def format_currency(amount: float, currency: str = "у.е.") -> str:
    """
    Format currency amount with thousands separator.
    
    Args:
        amount: Amount to format
        currency: Currency symbol
        
    Returns:
        Formatted string
    """
    if amount < 0:
        return f"-{abs(amount):,.2f} {currency}"
    return f"{amount:,.2f} {currency}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Format percentage value.
    
    Args:
        value: Percentage value
        decimals: Number of decimal places
        
    Returns:
        Formatted string
    """
    return f"{value:.{decimals}f}%"


def format_odds(odds: float) -> str:
    """
    Format betting odds.
    
    Args:
        odds: Odds value
        
    Returns:
        Formatted string
    """
    return f"{odds:.2f}"
