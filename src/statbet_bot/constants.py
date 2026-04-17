"""Application-wide constants and validation limits."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ValidationLimits:
    """Validation limits for user inputs."""
    
    # Stake limits
    MIN_STAKE: float = 0.01  # inclusive: stake must be >= 0.01
    MAX_STAKE: float = 1_000_000.0
    
    # Odds limits
    MIN_ODDS: float = 1.0  # exclusive: must be > 1.0
    MAX_ODDS: float = 100.0
    
    # Percentage limits
    MIN_PERCENT: float = 0.0
    MAX_PERCENT: float = 100.0
    
    # Token validation
    MIN_TOKEN_LENGTH: int = 10
    
    # Placeholder tokens to reject
    INVALID_TOKENS: tuple = ("your_token_here", "changeme", "")

    # Error messages
    ERROR_INVALID_NUMBER: str = "Введите корректное число"
    ERROR_NAN_INF: str = "Некорректное числовое значение"
    ERROR_STAKE_POSITIVE: str = "Сумма должна быть положительной"


@dataclass(frozen=True)
class BotDefaults:
    """Default values for bot features."""
    
    # Virtual betting
    DEFAULT_VIRTUAL_BALANCE: float = 10_000.0
    
    # Live tracker
    LIVE_PROBABILITY_THRESHOLD: float = 10.0  # percent delta for notifications
    
    # Rate limiting
    RATE_LIMIT_COOLDOWN_SECONDS: int = 5
    
    # Pagination
    MATCHES_PER_PAGE: int = 10


@dataclass(frozen=True)
class Messages:
    """Common message templates."""
    
    DISCLAIMER = "⚠️ Не является инвестиционной рекомендацией. Все решения вы принимаете самостоятельно."
    
    ERROR_INVALID_NUMBER = "Введите корректное число"
    ERROR_NAN_INF = "Некорректное числовое значение"
    ERROR_STAKE_POSITIVE = "Сумма должна быть положительной"
    ERROR_MIN_STAKE = "Минимальная сумма"

