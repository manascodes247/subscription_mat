from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    BillingInterval,
    Discount,
    DiscountType,
    Plan,
    Product,
    ProductVariant,
    QuotationTemplate,
    QuotationTemplateLine,
    TaxRule,
    User,
    UserRole,
)
from app.security import hash_password


def seed():
    with SessionLocal() as db:
        # 1. Admin
        admin = db.scalar(select(User).where(User.email == "admin@example.com"))
        if not admin:
            admin = User(
                email="admin@example.com",
                full_name="System Administrator",
                password_hash=hash_password("Admin!Brightloop2026"),
                role=UserRole.ADMIN,
            )
            db.add(admin)

        # 2. Staff
        staff = db.scalar(select(User).where(User.email == "staff@example.com"))
        if not staff:
            staff = User(
                email="staff@example.com",
                full_name="Operations Staff",
                password_hash=hash_password("Staff!Brightloop2026"),
                role=UserRole.STAFF,
            )
            db.add(staff)

        # 3. Customer
        customer = db.scalar(select(User).where(User.email == "customer@example.com"))
        if not customer:
            customer = User(
                email="customer@example.com",
                full_name="Acme Corporation",
                password_hash=hash_password("Customer!Brightloop2026"),
                role=UserRole.CUSTOMER,
            )
            db.add(customer)

        db.flush()

        # 4. Products & Variants
        product = db.scalar(select(Product).where(Product.name == "Brightloop Pro"))
        if not product:
            product = Product(
                name="Brightloop Pro",
                product_type="software",
                sales_price=Decimal("600.00"),
                cost_price=Decimal("200.00"),
                notes="Primary SaaS business management suite",
                active=True,
            )
            db.add(product)
            db.flush()

            variant = ProductVariant(
                product_id=product.id,
                name="Odoo brand",
                additional_price=Decimal("560.00"),
                active=True,
            )
            db.add(variant)
            db.flush()

            # 5. Plan
            plan = Plan(
                product_id=product.id,
                name="Monthly Pro",
                amount=Decimal("600.00"),
                interval_days=30,
                billing_interval=BillingInterval.MONTHLY,
                minimum_quantity=1,
                auto_close_on_end=False,
                allow_early_close=True,
                allow_pause=True,
                allow_renew=True,
                active=True,
            )
            db.add(plan)
            db.flush()

            # 6. Tax Rule
            tax = db.scalar(select(TaxRule).where(TaxRule.name == "GST 18%"))
            if not tax:
                tax = TaxRule(name="GST 18%", rate=Decimal("18.00"), active=True)
                db.add(tax)
                db.flush()

            # 7. Discount Rule
            discount = db.scalar(select(Discount).where(Discount.code == "TEAM10"))
            if not discount:
                discount = Discount(
                    code="TEAM10",
                    discount_type=DiscountType.PERCENTAGE,
                    value=Decimal("10.00"),
                    minimum_purchase=Decimal("1000.00"),
                    minimum_quantity=2,
                    usage_limit=10,
                    active=True,
                    product_id=product.id,
                )
                db.add(discount)
                db.flush()

            # 8. Quotation Template
            template = db.scalar(select(QuotationTemplate).where(QuotationTemplate.name == "Enterprise Launch Bundle"))
            if not template:
                template = QuotationTemplate(
                    name="Enterprise Launch Bundle",
                    plan_id=plan.id,
                    validity_days=30,
                    active=True,
                )
                db.add(template)
                db.flush()
                line = QuotationTemplateLine(
                    template_id=template.id,
                    product_id=product.id,
                    variant_id=variant.id,
                    product_name=product.name,
                    variant_name=variant.name,
                    quantity=2,
                    unit_price=Decimal("600.00"),
                )
                db.add(line)

        db.commit()
    print("Seed complete successfully.")


if __name__ == "__main__":
    seed()
