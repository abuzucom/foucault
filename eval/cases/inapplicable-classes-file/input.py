"""Pure formatting helpers for invoice line items."""

from decimal import Decimal, ROUND_HALF_UP


def to_cents(amount: Decimal) -> int:
    """Round a decimal amount to whole cents."""
    quantized = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return int(quantized * 100)


def format_line(description: str, cents: int) -> str:
    """Render one invoice line at a fixed width."""
    dollars = Decimal(cents) / 100
    return "{:<40}{:>10}".format(description[:40], "${:,.2f}".format(dollars))


def subtotal(lines: list[tuple[str, int]]) -> int:
    return sum(cents for _, cents in lines)
