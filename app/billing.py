from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from dateutil.relativedelta import relativedelta
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .models import BillingInterval, Discount, DiscountType, Invoice, InvoiceLine, InvoiceStatus, Plan, Subscription, SubscriptionStatus


MONEY = Decimal("0.01")


def next_billing_date(plan: Plan, period_start):
    if plan.billing_interval == BillingInterval.DAILY:
        return period_start + timedelta(days=1)
    if plan.billing_interval == BillingInterval.WEEKLY:
        return period_start + timedelta(weeks=1)
    if plan.billing_interval == BillingInterval.MONTHLY:
        return period_start + relativedelta(months=1)
    if plan.billing_interval == BillingInterval.YEARLY:
        return period_start + relativedelta(years=1)
    return period_start + timedelta(days=plan.interval_days)


def subscription_line_subtotal(subscription: Subscription) -> Decimal:
    return sum((line.quantity * line.unit_price for line in subscription.lines), Decimal("0")) or subscription.plan.amount


def discount_is_eligible(subscription: Subscription, billing_date, subtotal: Decimal, check_usage_limit: bool = True) -> bool:
    discount = subscription.discount
    if not discount or not discount.active:
        return False
    if discount.starts_on and discount.starts_on > billing_date:
        return False
    if discount.ends_on and discount.ends_on < billing_date:
        return False
    if check_usage_limit and discount.usage_limit is not None and discount.times_used >= discount.usage_limit:
        return False
    if discount.minimum_purchase is not None and subtotal < discount.minimum_purchase:
        return False
    quantity = sum((line.quantity for line in subscription.lines), 0)
    if not subscription.lines:
        quantity = 1
    if discount.minimum_quantity is not None and quantity < discount.minimum_quantity:
        return False
    if discount.product_id is not None:
        product_ids = {line.product_id for line in subscription.lines}
        if not subscription.lines:
            product_ids.add(subscription.plan.product_id)
        if discount.product_id not in product_ids:
            return False
    return True


def reserve_discount_usage(db: Session, subscription: Subscription, billing_date, subtotal: Decimal) -> bool:
    """Atomically reserve one discount use in the invoice transaction."""
    discount = subscription.discount
    if not discount or not discount_is_eligible(subscription, billing_date, subtotal, check_usage_limit=False):
        return False
    conditions = [Discount.id == discount.id]
    if discount.usage_limit is not None:
        conditions.append(Discount.times_used < Discount.usage_limit)
    result = db.execute(
        update(Discount)
        .where(*conditions)
        .values(times_used=Discount.times_used + 1)
    )
    return result.rowcount == 1


def calculate_invoice_amounts(subscription: Subscription, billing_date, apply_discount: bool | None = None):
    """Calculate a tax-after-discount total and preserve it on the invoice."""
    subtotal = subscription_line_subtotal(subscription)
    discount_amount = Decimal("0")
    discount = subscription.discount
    should_apply_discount = apply_discount if apply_discount is not None else discount_is_eligible(subscription, billing_date, subtotal)
    if should_apply_discount:
        if discount.discount_type == DiscountType.PERCENTAGE:
            discount_amount = subtotal * discount.value / Decimal("100")
        else:
            discount_amount = discount.value
        discount_amount = min(discount_amount, subtotal)
    taxable_amount = subtotal - discount_amount
    tax_amount = Decimal("0")
    if subscription.tax_rule:
        tax_amount = taxable_amount * subscription.tax_rule.rate / Decimal("100")
    return tuple(value.quantize(MONEY, rounding=ROUND_HALF_UP) for value in (subtotal, discount_amount, tax_amount, taxable_amount + tax_amount))


def invoice_lines_for(subscription: Subscription, discount_amount: Decimal, tax_amount: Decimal) -> list[InvoiceLine]:
    source_lines = list(subscription.lines)
    if not source_lines:
        source_lines = [
            type("PlanLine", (), {
                "product_id": subscription.plan.product_id,
                "variant_id": None,
                "product_name": subscription.plan.product.name,
                "variant_name": None,
                "quantity": 1,
                "unit_price": subscription.plan.amount,
            })()
        ]
    subtotals = [(line, (line.quantity * line.unit_price).quantize(MONEY, rounding=ROUND_HALF_UP)) for line in source_lines]
    total_subtotal = sum((subtotal for _, subtotal in subtotals), Decimal("0"))
    lines: list[InvoiceLine] = []
    distributed_discount = Decimal("0")
    distributed_tax = Decimal("0")
    for index, (line, subtotal) in enumerate(subtotals):
        if index == len(subtotals) - 1:
            line_discount = discount_amount - distributed_discount
        elif total_subtotal:
            line_discount = (discount_amount * subtotal / total_subtotal).quantize(MONEY, rounding=ROUND_HALF_UP)
            distributed_discount += line_discount
        else:
            line_discount = Decimal("0")
        taxable_subtotal = subtotal - line_discount
        taxable_total = total_subtotal - discount_amount
        if index == len(subtotals) - 1:
            line_tax = tax_amount - distributed_tax
        elif taxable_total:
            line_tax = (tax_amount * taxable_subtotal / taxable_total).quantize(MONEY, rounding=ROUND_HALF_UP)
            distributed_tax += line_tax
        else:
            line_tax = Decimal("0")
        lines.append(InvoiceLine(
            product_id_snapshot=line.product_id,
            variant_id_snapshot=line.variant_id,
            product_name=line.product_name,
            variant_name=line.variant_name,
            quantity=line.quantity,
            unit_price=line.unit_price,
            line_subtotal=subtotal,
            discount_amount=line_discount,
            tax_amount=line_tax,
            line_total=taxable_subtotal + line_tax,
        ))
    return lines


def generate_due_invoices(db: Session, billing_date):
    """Create each due invoice once, protected by a database unique constraint."""
    subscriptions = db.scalars(
        select(Subscription).where(
            Subscription.status == SubscriptionStatus.ACTIVE,
            Subscription.next_billing_on <= billing_date,
        ).with_for_update(skip_locked=True)
    ).all()
    created: list[Invoice] = []
    for subscription in subscriptions:
        period_start = subscription.next_billing_on
        next_period_start = next_billing_date(subscription.plan, period_start)
        period_end = next_period_start - timedelta(days=1)
        existing = db.scalar(
            select(Invoice).where(
                Invoice.subscription_id == subscription.id,
                Invoice.period_start == period_start,
                Invoice.period_end == period_end,
            )
        )
        if existing:
            continue
        subtotal = subscription_line_subtotal(subscription)
        discount_reserved = reserve_discount_usage(db, subscription, period_start, subtotal)
        subtotal, discount_amount, tax_amount, total = calculate_invoice_amounts(subscription, period_start, apply_discount=discount_reserved)
        invoice = Invoice(
            subscription_id=subscription.id,
            customer_id_snapshot=subscription.customer_id,
            customer_name_snapshot=subscription.customer.full_name,
            customer_email_snapshot=subscription.customer.email,
            period_start=period_start,
            period_end=period_end,
            due_on=period_start + timedelta(days=subscription.payment_due_days),
            amount=total,
            subtotal=subtotal,
            discount_amount=discount_amount,
            tax_amount=tax_amount,
            # The finance team confirms a prepared draft before it becomes
            # collectible; this matches the required billing workflow.
            status=InvoiceStatus.DRAFT,
            lines=invoice_lines_for(subscription, discount_amount, tax_amount),
        )
        db.add(invoice)
        subscription.next_billing_on = next_period_start
        created.append(invoice)
    db.commit()
    for invoice in created:
        db.refresh(invoice)
    return created
