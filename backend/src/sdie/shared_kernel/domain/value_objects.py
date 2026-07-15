"""Shared kernel: value objects used across all bounded contexts.

Value objects are immutable and compare by value, not identity.
No bounded context may redefine Money, Percentage, or TenantId locally —
that duplication is exactly what a shared kernel exists to prevent.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from uuid import UUID


class InvalidValueObjectError(ValueError):
    """Raised when a value object is constructed with invalid data."""


@dataclass(frozen=True, slots=True)
class Money:
    """Monetary amount with currency. Uses Decimal, never float, to avoid
    representation error compounding across multi-year cash flow models."""

    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))
        quantized = self.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        object.__setattr__(self, "amount", quantized)
        if len(self.currency) != 3 or not self.currency.isalpha():
            raise InvalidValueObjectError(f"Invalid ISO-4217 currency code: {self.currency!r}")

    def _check_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise InvalidValueObjectError(
                f"Cannot combine {self.currency} and {other.currency} without explicit FX conversion"
            )

    def __add__(self, other: "Money") -> "Money":
        self._check_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._check_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: Decimal | float | int) -> "Money":
        return Money(self.amount * Decimal(str(factor)), self.currency)

    def __neg__(self) -> "Money":
        return Money(-self.amount, self.currency)

    def __lt__(self, other: "Money") -> bool:
        self._check_currency(other)
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        self._check_currency(other)
        return self.amount <= other.amount

    @classmethod
    def zero(cls, currency: str = "USD") -> "Money":
        return cls(Decimal("0"), currency)

    def is_negative(self) -> bool:
        return self.amount < 0


@dataclass(frozen=True, slots=True)
class Percentage:
    """A ratio stored internally as a fraction (0.085 == 8.5%)."""

    fraction: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.fraction, Decimal):
            object.__setattr__(self, "fraction", Decimal(str(self.fraction)))

    @classmethod
    def from_percent(cls, value: float | Decimal) -> "Percentage":
        return cls(Decimal(str(value)) / Decimal("100"))

    def as_percent(self) -> Decimal:
        return self.fraction * Decimal("100")

    def __float__(self) -> float:
        return float(self.fraction)


@dataclass(frozen=True, slots=True)
class TenantId:
    """Every aggregate in every bounded context carries a TenantId.
    Enforced at the DB layer via row-level security, not just here —
    this value object is the application-layer half of that guarantee."""

    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise InvalidValueObjectError("TenantId must wrap a UUID")


@dataclass(frozen=True, slots=True)
class UserId:
    value: UUID
