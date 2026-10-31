"""Stripe PaymentIntent integration. Keys are read only from environment variables."""

import os
from decimal import Decimal, ROUND_HALF_UP

import stripe


def configure_stripe() -> None:
    key = os.getenv("STRIPE_SECRET_KEY")
    if not key:
        raise RuntimeError("STRIPE_SECRET_KEY is not configured")
    stripe.api_key = key


def minor_units(amount: Decimal) -> int:
    return int((amount * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def create_invoice_payment_intent(invoice_id: int, amount: Decimal, customer_email: str | None) -> stripe.PaymentIntent:
    configure_stripe()
    return stripe.PaymentIntent.create(
        amount=minor_units(amount),
        currency=os.getenv("BRIGHTLOOP_CURRENCY", "INR").lower(),
        receipt_email=customer_email,
        metadata={"brightloop_invoice_id": str(invoice_id)},
        automatic_payment_methods={"enabled": True},
    )


def verify_webhook(payload: bytes, signature: str | None):
    secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    if not secret:
        raise RuntimeError("STRIPE_WEBHOOK_SECRET is not configured")
    if not signature:
        raise ValueError("Missing Stripe-Signature header")
    return stripe.Webhook.construct_event(payload, signature, secret)
