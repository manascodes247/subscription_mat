from datetime import date, datetime
from decimal import Decimal

import pytest

from app.billing import calculate_invoice_amounts, discount_is_eligible, invoice_lines_for, next_billing_date
from app.invoice_pdf import render_invoice_pdf
from app.models import (
    Discount,
    DiscountType,
    BillingInterval,
    Invoice,
    InvoiceStatus,
    Plan,
    Product,
    Subscription,
    SubscriptionLine,
    TaxRule,
)
from app.schemas import UserCreate
from app.stripe_service import minor_units


def make_subscription(*, times_used: int = 0) -> Subscription:
    product = Product(id=1, name="Brightloop Pro")
    plan = Plan(id=1, product_id=1, name="Monthly", amount=Decimal("600"), interval_days=30)
    plan.product = product
    discount = Discount(
        id=1,
        code="TEAM10",
        discount_type=DiscountType.PERCENTAGE,
        value=Decimal("10"),
        active=True,
        minimum_purchase=Decimal("1000"),
        minimum_quantity=2,
        usage_limit=1,
        times_used=times_used,
        product_id=1,
    )
    tax = TaxRule(id=1, name="GST", rate=Decimal("18"), active=True)
    subscription = Subscription(
        id=1,
        customer_id=1,
        plan_id=1,
        plan=plan,
        discount=discount,
        tax_rule=tax,
        starts_on=date(2026, 1, 1),
        next_billing_on=date(2026, 2, 1),
    )
    subscription.lines = [
        SubscriptionLine(product_id=1, product_name="Brightloop Pro", quantity=2, unit_price=Decimal("600"))
    ]
    return subscription


def test_password_policy_rejects_weak_password() -> None:
    with pytest.raises(ValueError):
        UserCreate(email="user@example.com", full_name="User", password="alllowercasepassword")


def test_invoice_amounts_apply_eligible_discount_before_tax() -> None:
    subscription = make_subscription()
    assert discount_is_eligible(subscription, date(2026, 2, 1), Decimal("1200"))
    subtotal, discount, tax, total = calculate_invoice_amounts(subscription, date(2026, 2, 1))
    assert (subtotal, discount, tax, total) == (
        Decimal("1200.00"),
        Decimal("120.00"),
        Decimal("194.40"),
        Decimal("1274.40"),
    )
    lines = invoice_lines_for(subscription, discount, tax)
    assert sum(line.line_total for line in lines) == total


def test_usage_limit_stops_discount() -> None:
    subscription = make_subscription(times_used=1)
    assert not discount_is_eligible(subscription, date(2026, 2, 1), Decimal("1200"))


def test_stripe_minor_units_are_exact() -> None:
    assert minor_units(Decimal("1274.40")) == 127440


def test_monthly_billing_uses_calendar_months() -> None:
    plan = Plan(name="Monthly", product_id=1, amount=Decimal("10"), interval_days=30, billing_interval=BillingInterval.MONTHLY)
    assert next_billing_date(plan, date(2026, 1, 31)) == date(2026, 2, 28)
    assert next_billing_date(plan, date(2024, 2, 29)) == date(2024, 3, 29)


def test_invoice_pdf_is_valid_pdf() -> None:
    subscription = make_subscription()
    invoice = Invoice(
        id=42,
        subscription_id=1,
        subscription=subscription,
        customer_name_snapshot="Test Customer",
        customer_email_snapshot="billing@example.com",
        period_start=date(2026, 2, 1),
        period_end=date(2026, 2, 28),
        due_on=date(2026, 3, 7),
        amount=Decimal("1274.40"),
        subtotal=Decimal("1200.00"),
        discount_amount=Decimal("120.00"),
        tax_amount=Decimal("194.40"),
        status=InvoiceStatus.CONFIRMED,
        created_at=datetime(2026, 2, 1),
    )
    invoice.lines = invoice_lines_for(subscription, invoice.discount_amount, invoice.tax_amount)
    invoice.payments = []
    assert render_invoice_pdf(invoice).startswith(b"%PDF-")
