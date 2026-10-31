# Brightloop

Brightloop is a FastAPI and PostgreSQL subscription-management backend covering product catalogues, quotations, subscriptions, recurring billing, invoices, payments, discounts, taxes, reporting, PDF invoices, email delivery, and Stripe PaymentIntents.

## Requirements

- Python 3.12+
- PostgreSQL 16+
- Redis when running Celery automation

## Local setup on Windows

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\scripts\configure_local.ps1
.\scripts\start_dev.ps1
```

`configure_local.ps1` prompts privately for the PostgreSQL password, URL-encodes it, generates a random JWT signing key, and creates an ignored `.env` file. `start_dev.ps1` migrates the database before starting the API.

Open:

- API health: `http://127.0.0.1:8000/health`
- OpenAPI documentation: `http://127.0.0.1:8000/docs`

## Initial administrator

Run once after migrations:

```powershell
.\.venv\Scripts\python.exe -m app.bootstrap --email admin@example.com --name "System Admin" --password "choose-a-private-strong-password"
```

Public registration creates customers only. The protected staff endpoint creates staff accounts only.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The suite verifies password rules, calendar billing, discounts before tax, usage limits, invoice line totals, Stripe minor units, and PDF generation.

## Billing automation

With Redis running and `.env` configured, start these separately:

```powershell
.\.venv\Scripts\python.exe -m celery -A app.tasks.celery_app worker --loglevel=info
.\.venv\Scripts\python.exe -m celery -A app.tasks.celery_app beat --loglevel=info
```

Scheduled jobs generate due invoices, deactivate expired plans, close expired subscriptions, and mark confirmed unpaid invoices overdue. Billing uses database row locks and duplicate-period constraints so multiple workers cannot bill the same subscription twice.

## Configuration

Run the secure configuration script or copy `.env.example`. Important variables include `DATABASE_URL`, `BRIGHTLOOP_SECRET_KEY`, `CORS_ORIGINS`, `REDIS_URL`, SMTP settings, and Stripe secrets. Never commit `.env` or paste secrets into source code.

## Production notes

- Run `alembic upgrade head` before deploying a new application version.
- Inject secrets from the hosting platform's secret manager.
- Run the API without `--reload` and with multiple workers appropriate to the deployment size.
- Run Celery worker and beat as separate services.
- Serve the API only through HTTPS.
- Back up PostgreSQL and test restoration regularly.
