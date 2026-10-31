"""Background tasks for recurring Brightloop work.

Run the worker and scheduler separately in production. The task calls the same
idempotent billing service as the API, making a retry safe.
"""

import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select

from .billing import generate_due_invoices
from .database import SessionLocal
from .models import Invoice, InvoiceStatus, Plan, Subscription, SubscriptionStatus


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
BILLING_TIMEZONE = os.getenv("BRIGHTLOOP_BILLING_TIMEZONE", "Asia/Kolkata")

celery_app = Celery("brightloop", broker=REDIS_URL, backend=REDIS_URL)
celery_app.conf.update(
    timezone=BILLING_TIMEZONE,
    enable_utc=True,
    beat_schedule={
        "generate-due-invoices-daily": {
            "task": "app.tasks.generate_due_invoices_task",
            "schedule": crontab(hour=0, minute=5),
        }
        ,"close-expired-plans-daily": {
            "task": "app.tasks.close_expired_plans_task",
            "schedule": crontab(hour=0, minute=10),
        }
        ,"close-expired-subscriptions-daily": {
            "task": "app.tasks.close_expired_subscriptions_task",
            "schedule": crontab(hour=0, minute=15),
        }
        ,"mark-overdue-invoices-daily": {
            "task": "app.tasks.mark_overdue_invoices_task",
            "schedule": crontab(hour=0, minute=20),
        }
    },
)


def billing_today() -> date:
    return datetime.now(ZoneInfo(BILLING_TIMEZONE)).date()


@celery_app.task(
    name="app.tasks.generate_due_invoices_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def generate_due_invoices_task(billing_date: str | None = None) -> dict[str, int]:
    """Generate all invoices due on or before the supplied/current billing date."""
    due_date = date.fromisoformat(billing_date) if billing_date else billing_today()
    with SessionLocal() as db:
        invoices = generate_due_invoices(db, due_date)
    return {"invoices_created": len(invoices)}


@celery_app.task(name="app.tasks.close_expired_plans_task")
def close_expired_plans_task(current_date: str | None = None) -> dict[str, int]:
    """Deactivate only plans configured to close after their availability date."""
    today = date.fromisoformat(current_date) if current_date else billing_today()
    with SessionLocal() as db:
        plans = db.scalars(select(Plan).where(Plan.active.is_(True), Plan.auto_close_on_end.is_(True), Plan.available_until < today)).all()
        for plan in plans:
            plan.active = False
        db.commit()
    return {"plans_closed": len(plans)}


@celery_app.task(name="app.tasks.close_expired_subscriptions_task")
def close_expired_subscriptions_task(current_date: str | None = None) -> dict[str, int]:
    today = date.fromisoformat(current_date) if current_date else billing_today()
    with SessionLocal() as db:
        subscriptions = db.scalars(
            select(Subscription).where(
                Subscription.expires_on.is_not(None),
                Subscription.expires_on < today,
                Subscription.status.in_((
                    SubscriptionStatus.DRAFT,
                    SubscriptionStatus.QUOTATION,
                    SubscriptionStatus.CONFIRMED,
                    SubscriptionStatus.ACTIVE,
                    SubscriptionStatus.PAUSED,
                )),
            )
        ).all()
        for subscription in subscriptions:
            subscription.status = SubscriptionStatus.CLOSED
            subscription.cancelled_on = today
        db.commit()
    return {"subscriptions_closed": len(subscriptions)}


@celery_app.task(name="app.tasks.mark_overdue_invoices_task")
def mark_overdue_invoices_task(current_date: str | None = None) -> dict[str, int]:
    today = date.fromisoformat(current_date) if current_date else billing_today()
    with SessionLocal() as db:
        invoices = db.scalars(
            select(Invoice).where(
                Invoice.due_on < today,
                Invoice.status.in_((InvoiceStatus.CONFIRMED, InvoiceStatus.ISSUED)),
            )
        ).all()
        overdue = [invoice for invoice in invoices if invoice.outstanding_balance > 0]
        for invoice in overdue:
            invoice.status = InvoiceStatus.OVERDUE
        db.commit()
    return {"invoices_marked_overdue": len(overdue)}
