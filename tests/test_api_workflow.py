import asyncio
from datetime import date, timedelta
from decimal import Decimal

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User, UserRole
from app.security import hash_password


def test_complete_api_workflow() -> None:
    asyncio.run(_complete_api_workflow())


async def _complete_api_workflow() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    with TestSession() as db:
        db.add(User(
            email="admin@example.com",
            full_name="Admin",
            password_hash=hash_password("Admin!Workflow2026"),
            role=UserRole.ADMIN,
        ))
        db.commit()

    def override_db():
        db: Session = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            login = await client.post("/auth/login", json={"email": "ADMIN@example.com", "password": "Admin!Workflow2026"})
            assert login.status_code == 200
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

            customer = (await client.post("/users", json={"email": "customer@example.com", "full_name": "Customer", "password": "Customer!Workflow2026", "role": "customer"})).json()
            product = (await client.post("/products", headers=headers, json={"name": "Pro", "product_type": "software", "sales_price": "600", "cost_price": "200"})).json()
            variant = (await client.post(f"/products/{product['id']}/variants", headers=headers, json={"name": "Odoo brand", "additional_price": "560"})).json()
            plan = (await client.post("/plans", headers=headers, json={"product_id": product["id"], "name": "Monthly", "amount": "600", "billing_interval": "monthly", "minimum_quantity": 2})).json()
            tax = (await client.post("/tax-rules", headers=headers, json={"name": "GST 18", "rate": "18"})).json()
            discount = (await client.post("/discounts", headers=headers, json={"code": "TEAM10", "discount_type": "percentage", "value": "10", "minimum_purchase": "1000", "minimum_quantity": 2, "usage_limit": 1, "product_id": product["id"]})).json()

            today = date.today()
            quote_response = await client.post("/quotations", headers=headers, json={
                "customer_id": customer["id"],
                "plan_id": plan["id"],
                "discount_id": discount["id"],
                "tax_rule_id": tax["id"],
                "expires_on": (today + timedelta(days=30)).isoformat(),
                "payment_terms": "Due within 7 days",
                "payment_due_days": 7,
                "lines": [{"product_id": product["id"], "variant_id": variant["id"], "product_name": product["name"], "variant_name": variant["name"], "quantity": 2, "unit_price": "600"}],
            })
            assert quote_response.status_code == 201
            quote = quote_response.json()
            for next_status in ("quotation", "confirmed"):
                response = await client.patch(f"/quotations/{quote['id']}/status", headers=headers, json={"status": next_status})
                assert response.status_code == 200

            subscription = (await client.post(f"/quotations/{quote['id']}/convert", headers=headers, json={"starts_on": today.isoformat(), "expires_on": (today + timedelta(days=365)).isoformat()})).json()
            assert subscription["discount_id"] == discount["id"]
            assert subscription["tax_rule_id"] == tax["id"]
            assert subscription["payment_due_days"] == 7
            for action in ("mark-quotation", "confirm", "activate"):
                response = await client.post(f"/subscriptions/{subscription['id']}/{action}", headers=headers)
                assert response.status_code == 200
            active = response.json()

            billing_date = active["next_billing_on"]
            generated = (await client.post("/billing/run", headers=headers, params={"billing_date": billing_date})).json()
            invoice = next(item for item in generated if item["subscription_id"] == subscription["id"])
            assert Decimal(invoice["amount"]) == Decimal("1274.40")
            assert (await client.post("/billing/run", headers=headers, params={"billing_date": billing_date})).json() == []
            assert (date.fromisoformat(invoice["due_on"]) - date.fromisoformat(invoice["period_start"])).days == 7

            confirmed = (await client.post(f"/invoices/{invoice['id']}/confirm", headers=headers)).json()
            pdf = await client.get(f"/invoices/{invoice['id']}/print", headers=headers)
            assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF-")
            payment = await client.post(f"/invoices/{invoice['id']}/payments", headers=headers, json={"amount": confirmed["amount"], "method": "bank_transfer", "status": "success", "note": "Automated settlement"})
            assert payment.status_code == 201
            paid = (await client.get(f"/invoices/{invoice['id']}", headers=headers)).json()
            assert paid["status"] == "paid"
            assert Decimal(paid["outstanding_balance"]) == 0

            # Test listing payments
            payments = (await client.get(f"/invoices/{invoice['id']}/payments", headers=headers)).json()
            assert len(payments) == 1
            assert payments[0]["method"] == "bank_transfer"
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_quotation_template_and_invoice_void() -> None:
    asyncio.run(_template_and_void_workflow())


async def _template_and_void_workflow() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    with TestSession() as db:
        db.add(User(
            email="admin2@example.com",
            full_name="Admin Two",
            password_hash=hash_password("Admin!Workflow2026"),
            role=UserRole.ADMIN,
        ))
        db.commit()

    def override_db():
        db: Session = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            login = await client.post("/auth/login", json={"email": "admin2@example.com", "password": "Admin!Workflow2026"})
            assert login.status_code == 200
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

            customer = (await client.post("/users", json={"email": "cust2@example.com", "full_name": "Cust Two", "password": "Customer!Workflow2026", "role": "customer"})).json()
            product = (await client.post("/products", headers=headers, json={"name": "Enterprise", "sales_price": "1500"})).json()
            plan = (await client.post("/plans", headers=headers, json={"product_id": product["id"], "name": "Annual", "amount": "1500", "billing_interval": "yearly"})).json()

            # Create quotation template
            tpl_resp = await client.post("/quotation-templates", headers=headers, json={
                "name": "Standard Enterprise Package",
                "plan_id": plan["id"],
                "validity_days": 45,
                "lines": [{"product_id": product["id"], "product_name": product["name"], "quantity": 1, "unit_price": "1500"}],
            })
            assert tpl_resp.status_code == 201
            templates = (await client.get("/quotation-templates", headers=headers)).json()
            assert any(t["name"] == "Standard Enterprise Package" for t in templates)

            # Create quotation from template lines
            quote = (await client.post("/quotations", headers=headers, json={
                "customer_id": customer["id"],
                "plan_id": plan["id"],
                "payment_due_days": 14,
                "lines": [{"product_id": product["id"], "product_name": product["name"], "quantity": 1, "unit_price": "1500"}],
            })).json()
            assert quote["status"] == "draft"

            # Advance quote to quotation and confirmed
            await client.patch(f"/quotations/{quote['id']}/status", headers=headers, json={"status": "quotation"})
            await client.patch(f"/quotations/{quote['id']}/status", headers=headers, json={"status": "confirmed"})

            # Convert to subscription
            sub_resp = await client.post(f"/quotations/{quote['id']}/convert", headers=headers, json={"starts_on": date.today().isoformat()})
            assert sub_resp.status_code == 201
            sub = sub_resp.json()
            for action in ("mark-quotation", "confirm", "activate"):
                action_resp = await client.post(f"/subscriptions/{sub['id']}/{action}", headers=headers)
                assert action_resp.status_code == 200

            # Bill and void
            invoices = (await client.post("/billing/run", headers=headers, params={"billing_date": sub["next_billing_on"]})).json()
            inv = invoices[0]
            assert inv["status"] == "draft"

            # Test void invoice
            voided = (await client.post(f"/invoices/{inv['id']}/void", headers=headers)).json()
            assert voided["status"] == "void"
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()

