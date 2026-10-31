from datetime import date, datetime, timedelta, timezone
import os
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import case, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .billing import generate_due_invoices, next_billing_date
from .database import get_db
from .email import send_invoice_email, send_password_reset_email
from .invoice_pdf import invoice_number, render_invoice_pdf
from .models import BillingInterval, Discount, DiscountType, Invoice, InvoiceStatus, PasswordResetToken, Payment, PaymentStatus, Plan, Product, ProductVariant, Quotation, QuotationLine, QuotationStatus, QuotationTemplate, QuotationTemplateLine, Subscription, SubscriptionLine, SubscriptionStatus, TaxRule, User, UserRole
from .security import create_access_token, create_one_time_token, get_current_user, hash_one_time_token, hash_password, require_roles, verify_password
from .stripe_service import create_invoice_payment_intent, verify_webhook
from .schemas import (
    DiscountCreate, DiscountRead, DiscountUpdate, FinanceDashboardRead, InvoiceRead, InvoiceStatusUpdate, PaymentCreate, PaymentRead, PlanCreate, PlanRead, PlanUpdate, ProductCreate, ProductRead, ProductUpdate, ProductVariantCreate, ProductVariantRead, ProductVariantUpdate,
    LoginRequest, PasswordResetConfirm, PasswordResetRequest, QuotationConvertRequest, QuotationCreate, QuotationRead, QuotationStatusUpdate, QuotationTemplateCreate, QuotationTemplateRead, SubscriptionAction, SubscriptionCreate, SubscriptionLineCreate, SubscriptionRead, TokenRead, UserCreate, UserRead,
    TaxRuleCreate, TaxRuleRead, TaxRuleUpdate,
)

app = FastAPI(title="Brightloop API", version="0.1.0")
cors_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
INTERVAL_DAYS = {BillingInterval.DAILY: 1, BillingInterval.WEEKLY: 7, BillingInterval.MONTHLY: 30, BillingInterval.YEARLY: 365}


def validate_plan_dates(plan: Plan) -> None:
    if plan.available_from and plan.available_until and plan.available_until < plan.available_from:
        raise HTTPException(422, "Plan availability end date cannot precede its start date")


def validate_pagination(offset: int, limit: int) -> None:
    if offset < 0 or limit < 1 or limit > 200:
        raise HTTPException(422, "Pagination must use offset >= 0 and limit between 1 and 200")


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}


@app.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    # Public registration can only create customer accounts. Admin/staff accounts
    # are created by an administrator through the protected endpoint below.
    if payload.role != UserRole.CUSTOMER:
        raise HTTPException(403, "Only administrators can create staff or admin accounts")
    user = User(email=str(payload.email).lower(), full_name=payload.full_name, role=payload.role, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A user with this email already exists")
    db.refresh(user)
    return user


@app.get("/users", response_model=list[UserRead])
def list_users(
    role: UserRole | None = None,
    search: str | None = None,
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
):
    validate_pagination(offset, limit)
    statement = select(User).order_by(User.id.desc())
    if role:
        statement = statement.where(User.role == role)
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where((User.full_name.ilike(pattern)) | (User.email.ilike(pattern)))
    return db.scalars(statement.offset(offset).limit(limit)).all()


@app.post("/staff/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_staff_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    if payload.role != UserRole.STAFF:
        raise HTTPException(422, "This endpoint only creates staff accounts")
    user = User(email=str(payload.email).lower(), full_name=payload.full_name, role=payload.role, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A user with this email already exists")
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=TokenRead)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(func.lower(User.email) == str(payload.email).lower()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return TokenRead(access_token=create_access_token(user))


@app.post("/auth/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
def request_password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(func.lower(User.email) == str(payload.email).lower()))
    if not user:
        return {"message": "If that account exists, a reset email has been sent."}
    token = create_one_time_token()
    reset = PasswordResetToken(
        user_id=user.id,
        token_hash=hash_one_time_token(token),
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=30),
    )
    db.add(reset)
    try:
        db.flush()
        send_password_reset_email(user.email, token)
        db.commit()
    except RuntimeError as error:
        db.rollback()
        raise HTTPException(503, str(error))
    return {"message": "If that account exists, a reset email has been sent."}


@app.post("/auth/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
def confirm_password_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    reset = db.scalar(select(PasswordResetToken).where(
        PasswordResetToken.token_hash == hash_one_time_token(payload.token),
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.expires_at >= now,
    ).with_for_update())
    if not reset:
        raise HTTPException(400, "This password reset link is invalid or has expired")
    reset.user.password_hash = hash_password(payload.password)
    for active_reset in db.scalars(select(PasswordResetToken).where(
        PasswordResetToken.user_id == reset.user_id,
        PasswordResetToken.used_at.is_(None),
    )).all():
        active_reset.used_at = now
    db.commit()


@app.get("/auth/me", response_model=UserRead)
def current_user(current_user: User = Depends(get_current_user)):
    return current_user


@app.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))):
    product = Product(**payload.model_dump())
    db.add(product)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A product with this name already exists")
    db.refresh(product)
    return product


@app.get("/products", response_model=list[ProductRead])
def list_products(include_inactive: bool = False, db: Session = Depends(get_db)):
    statement = select(Product).order_by(Product.name)
    if not include_inactive:
        statement = statement.where(Product.active.is_(True))
    return db.scalars(statement).all()


@app.get("/products/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    return product


@app.patch("/products/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A product with this name already exists")
    db.refresh(product)
    return product


@app.post("/products/{product_id}/variants", response_model=ProductVariantRead, status_code=status.HTTP_201_CREATED)
def create_variant(product_id: int, payload: ProductVariantCreate, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))):
    if not db.get(Product, product_id): raise HTTPException(404, "Product not found")
    variant = ProductVariant(product_id=product_id, **payload.model_dump())
    db.add(variant); db.commit(); db.refresh(variant)
    return variant


@app.get("/products/{product_id}/variants", response_model=list[ProductVariantRead])
def list_variants(product_id: int, include_inactive: bool = False, db: Session = Depends(get_db)):
    if not db.get(Product, product_id): raise HTTPException(404, "Product not found")
    q = select(ProductVariant).where(ProductVariant.product_id == product_id).order_by(ProductVariant.name)
    if not include_inactive: q = q.where(ProductVariant.active.is_(True))
    return db.scalars(q).all()


@app.patch("/product-variants/{variant_id}", response_model=ProductVariantRead)
def update_variant(variant_id: int, payload: ProductVariantUpdate, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))):
    variant = db.get(ProductVariant, variant_id)
    if not variant: raise HTTPException(404, "Product variant not found")
    for field, value in payload.model_dump(exclude_unset=True).items(): setattr(variant, field, value)
    db.commit(); db.refresh(variant)
    return variant


@app.post("/plans", response_model=PlanRead, status_code=status.HTTP_201_CREATED)
def create_plan(payload: PlanCreate, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))):
    if not db.get(Product, payload.product_id):
        raise HTTPException(404, "Product not found")
    values = payload.model_dump()
    if payload.billing_interval:
        values["interval_days"] = INTERVAL_DAYS[payload.billing_interval]
    elif not payload.interval_days:
        raise HTTPException(422, "Provide a billing interval or interval days")
    plan = Plan(**values)
    validate_plan_dates(plan)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@app.post("/discounts", response_model=DiscountRead, status_code=status.HTTP_201_CREATED)
def create_discount(payload: DiscountCreate, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))):
    if payload.discount_type == DiscountType.PERCENTAGE and payload.value > 100:
        raise HTTPException(422, "Percentage discounts cannot exceed 100")
    if payload.starts_on and payload.ends_on and payload.ends_on < payload.starts_on:
        raise HTTPException(422, "Discount end date cannot precede its start date")
    if payload.product_id and not db.get(Product, payload.product_id):
        raise HTTPException(404, "Discount product not found")
    discount = Discount(**payload.model_dump())
    db.add(discount)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A discount with this code already exists")
    db.refresh(discount)
    return discount


@app.get("/discounts", response_model=list[DiscountRead])
def list_discounts(include_inactive: bool = False, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF))):
    statement = select(Discount).order_by(Discount.code)
    if not include_inactive:
        statement = statement.where(Discount.active.is_(True))
    return db.scalars(statement).all()


@app.patch("/discounts/{discount_id}", response_model=DiscountRead)
def update_discount(discount_id: int, payload: DiscountUpdate, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))):
    discount = db.get(Discount, discount_id)
    if not discount:
        raise HTTPException(404, "Discount not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(discount, field, value)
    if discount.product_id and not db.get(Product, discount.product_id):
        raise HTTPException(404, "Discount product not found")
    if discount.discount_type == DiscountType.PERCENTAGE and discount.value > 100:
        raise HTTPException(422, "Percentage discounts cannot exceed 100")
    if discount.starts_on and discount.ends_on and discount.ends_on < discount.starts_on:
        raise HTTPException(422, "Discount end date cannot precede its start date")
    db.commit()
    db.refresh(discount)
    return discount


@app.post("/tax-rules", response_model=TaxRuleRead, status_code=status.HTTP_201_CREATED)
def create_tax_rule(payload: TaxRuleCreate, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))):
    rule = TaxRule(**payload.model_dump())
    db.add(rule)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A tax rule with this name already exists")
    db.refresh(rule)
    return rule


@app.get("/tax-rules", response_model=list[TaxRuleRead])
def list_tax_rules(include_inactive: bool = False, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF))):
    statement = select(TaxRule).order_by(TaxRule.name)
    if not include_inactive:
        statement = statement.where(TaxRule.active.is_(True))
    return db.scalars(statement).all()


@app.patch("/tax-rules/{tax_rule_id}", response_model=TaxRuleRead)
def update_tax_rule(tax_rule_id: int, payload: TaxRuleUpdate, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))):
    rule = db.get(TaxRule, tax_rule_id)
    if not rule:
        raise HTTPException(404, "Tax rule not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A tax rule with this name already exists")
    db.refresh(rule)
    return rule


@app.get("/products/{product_id}/plans", response_model=list[PlanRead])
def list_product_plans(product_id: int, include_inactive: bool = False, db: Session = Depends(get_db)):
    if not db.get(Product, product_id):
        raise HTTPException(404, "Product not found")
    statement = select(Plan).where(Plan.product_id == product_id).order_by(Plan.amount)
    if not include_inactive:
        statement = statement.where(Plan.active.is_(True))
    return db.scalars(statement).all()


@app.patch("/plans/{plan_id}", response_model=PlanRead)
def update_plan(
    plan_id: int,
    payload: PlanUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    plan = db.get(Plan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    # Existing subscriptions retain their invoice history. Deactivation prevents
    # the plan from being selected for future subscriptions without deleting it.
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(plan, field, value)
    if payload.billing_interval:
        plan.interval_days = INTERVAL_DAYS[payload.billing_interval]
    validate_plan_dates(plan)
    db.commit()
    db.refresh(plan)
    return plan


def validate_commercial_line(line, db: Session) -> None:
    if line.product_id and not db.get(Product, line.product_id):
        raise HTTPException(404, "Product on line item not found")
    if line.variant_id:
        variant = db.get(ProductVariant, line.variant_id)
        if not variant:
            raise HTTPException(404, "Product variant on line item not found")
        if line.product_id and variant.product_id != line.product_id:
            raise HTTPException(422, "The selected variant does not belong to the product")


def commercial_line_values(line) -> dict:
    fields = ("product_id", "variant_id", "product_name", "variant_name", "quantity", "unit_price")
    return {field: getattr(line, field) for field in fields}


def new_document_number(prefix: str) -> str:
    return f"{prefix}-{date.today():%Y%m%d}-{uuid4().hex[:10].upper()}"


@app.post("/quotation-templates", response_model=QuotationTemplateRead, status_code=status.HTTP_201_CREATED)
def create_quotation_template(
    payload: QuotationTemplateCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    if payload.plan_id and not db.get(Plan, payload.plan_id):
        raise HTTPException(404, "Plan not found")
    for line in payload.lines:
        validate_commercial_line(line, db)
    template = QuotationTemplate(
        name=payload.name,
        plan_id=payload.plan_id,
        validity_days=payload.validity_days,
        lines=[QuotationTemplateLine(**commercial_line_values(line)) for line in payload.lines],
    )
    db.add(template)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A quotation template with this name already exists")
    db.refresh(template)
    return template


@app.get("/quotation-templates", response_model=list[QuotationTemplateRead])
def list_quotation_templates(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
):
    statement = select(QuotationTemplate).order_by(QuotationTemplate.name)
    if not include_inactive:
        statement = statement.where(QuotationTemplate.active.is_(True))
    return db.scalars(statement).all()


@app.post("/quotations", response_model=QuotationRead, status_code=status.HTTP_201_CREATED)
def create_quotation(
    payload: QuotationCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
):
    customer = db.get(User, payload.customer_id)
    if not customer or customer.role != UserRole.CUSTOMER:
        raise HTTPException(422, "Quotations can only be created for customer accounts")
    template = db.get(QuotationTemplate, payload.template_id) if payload.template_id else None
    if payload.template_id and (not template or not template.active):
        raise HTTPException(409, "This quotation template is not available")
    plan_id = payload.plan_id if payload.plan_id is not None else (template.plan_id if template else None)
    if plan_id and not db.get(Plan, plan_id):
        raise HTTPException(404, "Plan not found")
    if payload.discount_id:
        discount = db.get(Discount, payload.discount_id)
        if not discount or not discount.active:
            raise HTTPException(409, "This discount is not available")
    if payload.tax_rule_id:
        tax_rule = db.get(TaxRule, payload.tax_rule_id)
        if not tax_rule or not tax_rule.active:
            raise HTTPException(409, "This tax rule is not available")
    line_values = payload.lines or ([] if not template else template.lines)
    if not line_values:
        raise HTTPException(422, "A quotation needs at least one product line")
    for line in line_values:
        validate_commercial_line(line, db)
    issue_date = date.today()
    expiry = payload.expires_on or issue_date + timedelta(days=template.validity_days if template else 30)
    if expiry < issue_date:
        raise HTTPException(422, "Quotation expiry cannot precede its issue date")
    quotation = Quotation(
        quotation_number=new_document_number("QT"),
        customer_id=customer.id,
        plan_id=plan_id,
        discount_id=payload.discount_id,
        tax_rule_id=payload.tax_rule_id,
        issue_date=issue_date,
        expires_on=expiry,
        payment_terms=payload.payment_terms,
        payment_due_days=payload.payment_due_days,
        lines=[QuotationLine(**commercial_line_values(line)) for line in line_values],
    )
    db.add(quotation)
    db.commit()
    db.refresh(quotation)
    return quotation


@app.get("/quotations", response_model=list[QuotationRead])
def list_quotations(
    quotation_status: QuotationStatus | None = None,
    offset: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_pagination(offset, limit)
    statement = select(Quotation).order_by(Quotation.id.desc())
    if current_user.role == UserRole.CUSTOMER:
        statement = statement.where(Quotation.customer_id == current_user.id)
    if quotation_status:
        statement = statement.where(Quotation.status == quotation_status)
    return db.scalars(statement.offset(offset).limit(limit)).all()


def get_quotation_or_404(quotation_id: int, db: Session, *, for_update: bool = False) -> Quotation:
    statement = select(Quotation).where(Quotation.id == quotation_id)
    if for_update:
        statement = statement.with_for_update()
    quotation = db.scalar(statement)
    if not quotation:
        raise HTTPException(404, "Quotation not found")
    return quotation


@app.patch("/quotations/{quotation_id}/status", response_model=QuotationRead)
def update_quotation_status(
    quotation_id: int,
    payload: QuotationStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
):
    quotation = get_quotation_or_404(quotation_id, db, for_update=True)
    transitions = {
        QuotationStatus.DRAFT: {QuotationStatus.QUOTATION, QuotationStatus.CLOSED},
        QuotationStatus.QUOTATION: {QuotationStatus.CONFIRMED, QuotationStatus.CLOSED},
        QuotationStatus.CONFIRMED: {QuotationStatus.CLOSED},
        QuotationStatus.CLOSED: set(),
    }
    if payload.status not in transitions[quotation.status]:
        raise HTTPException(409, "This quotation status transition is not allowed")
    if payload.status == QuotationStatus.CONFIRMED and quotation.expires_on < date.today():
        raise HTTPException(409, "Expired quotations cannot be confirmed")
    quotation.status = payload.status
    db.commit()
    db.refresh(quotation)
    return quotation


@app.post("/quotations/{quotation_id}/convert", response_model=SubscriptionRead, status_code=status.HTTP_201_CREATED)
def convert_quotation_to_subscription(
    quotation_id: int,
    payload: QuotationConvertRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
):
    quotation = get_quotation_or_404(quotation_id, db, for_update=True)
    if quotation.status != QuotationStatus.CONFIRMED:
        raise HTTPException(409, "Only confirmed quotations can become subscriptions")
    if quotation.expires_on < date.today():
        raise HTTPException(409, "Expired quotations cannot become subscriptions")
    if not quotation.plan_id:
        raise HTTPException(422, "A quotation needs a plan before conversion")
    plan = db.get(Plan, quotation.plan_id)
    if not plan or not plan.active or not plan.product.active:
        raise HTTPException(409, "This plan is not available for a new subscription")
    if sum(line.quantity for line in quotation.lines) < plan.minimum_quantity:
        raise HTTPException(422, "Quotation quantity is below the plan minimum")
    starts_on = payload.starts_on or date.today()
    subscription = Subscription(
        subscription_number=new_document_number("SUB"),
        customer_id=quotation.customer_id,
        plan_id=plan.id,
        discount_id=quotation.discount_id,
        tax_rule_id=quotation.tax_rule_id,
        source_quotation_id=quotation.id,
        starts_on=starts_on,
        next_billing_on=next_billing_date(plan, starts_on),
        expires_on=payload.expires_on,
        payment_terms=payload.payment_terms or quotation.payment_terms,
        payment_due_days=quotation.payment_due_days if payload.payment_due_days is None else payload.payment_due_days,
        status=SubscriptionStatus.DRAFT,
        lines=[
            SubscriptionLine(
                product_id=line.product_id,
                variant_id=line.variant_id,
                product_name=line.product_name,
                variant_name=line.variant_name,
                quantity=line.quantity,
                unit_price=line.unit_price,
            )
            for line in quotation.lines
        ],
    )
    quotation.status = QuotationStatus.CLOSED
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


@app.post("/subscriptions", response_model=SubscriptionRead, status_code=status.HTTP_201_CREATED)
def create_subscription(payload: SubscriptionCreate, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF))):
    customer = db.get(User, payload.customer_id)
    plan = db.get(Plan, payload.plan_id)
    if not customer or not plan:
        raise HTTPException(404, "Customer or plan not found")
    if customer.role != UserRole.CUSTOMER:
        raise HTTPException(422, "Subscriptions can only be created for customer accounts")
    if not plan.active or not plan.product.active:
        raise HTTPException(409, "This plan is not available for new subscriptions")
    if plan.available_from and payload.starts_on < plan.available_from or plan.available_until and payload.starts_on > plan.available_until:
        raise HTTPException(409, "This plan is not available on the subscription start date")
    if payload.discount_id:
        discount = db.get(Discount, payload.discount_id)
        if not discount or not discount.active:
            raise HTTPException(409, "This discount is not available")
    if payload.tax_rule_id:
        tax_rule = db.get(TaxRule, payload.tax_rule_id)
        if not tax_rule or not tax_rule.active:
            raise HTTPException(409, "This tax rule is not available")
    if payload.lines and sum(line.quantity for line in payload.lines) < plan.minimum_quantity:
        raise HTTPException(422, "Subscription quantity is below the plan minimum")
    for line in payload.lines:
        validate_commercial_line(line, db)
    values = payload.model_dump(exclude={"lines"})
    subscription = Subscription(
        **values,
        subscription_number=new_document_number("SUB"),
        next_billing_on=next_billing_date(plan, payload.starts_on),
        lines=[SubscriptionLine(**commercial_line_values(line)) for line in payload.lines],
        status=SubscriptionStatus.DRAFT,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def get_subscription_or_404(subscription_id: int, db: Session, *, for_update: bool = False) -> Subscription:
    statement = select(Subscription).where(Subscription.id == subscription_id)
    if for_update:
        statement = statement.with_for_update()
    subscription = db.scalar(statement)
    if not subscription:
        raise HTTPException(404, "Subscription not found")
    return subscription


def require_subscription_owner_or_team(subscription: Subscription, current_user: User) -> None:
    if current_user.role == UserRole.CUSTOMER and subscription.customer_id != current_user.id:
        raise HTTPException(403, "You can only manage your own subscriptions")


@app.post("/subscriptions/{subscription_id}/mark-quotation", response_model=SubscriptionRead)
def mark_subscription_as_quotation(
    subscription_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
):
    subscription = get_subscription_or_404(subscription_id, db, for_update=True)
    if subscription.status != SubscriptionStatus.DRAFT:
        raise HTTPException(409, "Only draft subscriptions can become quotations")
    subscription.status = SubscriptionStatus.QUOTATION
    db.commit()
    db.refresh(subscription)
    return subscription


@app.post("/subscriptions/{subscription_id}/confirm", response_model=SubscriptionRead)
def confirm_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
):
    subscription = get_subscription_or_404(subscription_id, db, for_update=True)
    if subscription.status != SubscriptionStatus.QUOTATION:
        raise HTTPException(409, "Only quotation subscriptions can be confirmed")
    subscription.status = SubscriptionStatus.CONFIRMED
    db.commit()
    db.refresh(subscription)
    return subscription


@app.post("/subscriptions/{subscription_id}/activate", response_model=SubscriptionRead)
def activate_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
):
    subscription = get_subscription_or_404(subscription_id, db, for_update=True)
    if subscription.status != SubscriptionStatus.CONFIRMED:
        raise HTTPException(409, "Only confirmed subscriptions can be activated")
    if subscription.expires_on and subscription.expires_on < date.today():
        raise HTTPException(409, "Expired subscriptions cannot be activated")
    subscription.status = SubscriptionStatus.ACTIVE
    db.commit()
    db.refresh(subscription)
    return subscription


@app.get("/subscriptions", response_model=list[SubscriptionRead])
def list_subscriptions(subscription_status: SubscriptionStatus | None = None, offset: int = 0, limit: int = 50, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    validate_pagination(offset, limit)
    statement = select(Subscription).order_by(Subscription.id.desc())
    if current_user.role == UserRole.CUSTOMER:
        statement = statement.where(Subscription.customer_id == current_user.id)
    if subscription_status:
        statement = statement.where(Subscription.status == subscription_status)
    return db.scalars(statement.offset(offset).limit(limit)).all()


@app.get("/subscriptions/{subscription_id}", response_model=SubscriptionRead)
def get_subscription(subscription_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    subscription = get_subscription_or_404(subscription_id, db)
    if current_user.role == UserRole.CUSTOMER and subscription.customer_id != current_user.id:
        raise HTTPException(403, "You can only view your own subscriptions")
    return subscription


@app.post("/subscriptions/{subscription_id}/pause", response_model=SubscriptionRead)
def pause_subscription(subscription_id: int, payload: SubscriptionAction, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    subscription = get_subscription_or_404(subscription_id, db, for_update=True)
    require_subscription_owner_or_team(subscription, current_user)
    if subscription.status != SubscriptionStatus.ACTIVE:
        raise HTTPException(409, "Only active subscriptions can be paused")
    if not subscription.plan.allow_pause:
        raise HTTPException(409, "This plan does not allow pausing")
    subscription.status = SubscriptionStatus.PAUSED
    subscription.paused_on = payload.effective_on or date.today()
    db.commit()
    db.refresh(subscription)
    return subscription


@app.post("/subscriptions/{subscription_id}/resume", response_model=SubscriptionRead)
def resume_subscription(subscription_id: int, payload: SubscriptionAction, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    subscription = get_subscription_or_404(subscription_id, db, for_update=True)
    require_subscription_owner_or_team(subscription, current_user)
    if subscription.status != SubscriptionStatus.PAUSED:
        raise HTTPException(409, "Only paused subscriptions can be resumed")
    if not subscription.plan.active or not subscription.plan.product.active:
        raise HTTPException(409, "This plan is no longer available")
    resumed_on = payload.effective_on or date.today()
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.paused_on = None
    # A pause does not create backdated bills. The renewed cycle starts on resume.
    subscription.next_billing_on = next_billing_date(subscription.plan, resumed_on)
    db.commit()
    db.refresh(subscription)
    return subscription


@app.post("/subscriptions/{subscription_id}/close", response_model=SubscriptionRead)
@app.post("/subscriptions/{subscription_id}/cancel", response_model=SubscriptionRead, deprecated=True)
def cancel_subscription(subscription_id: int, payload: SubscriptionAction, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    subscription = get_subscription_or_404(subscription_id, db, for_update=True)
    require_subscription_owner_or_team(subscription, current_user)
    if subscription.status not in (SubscriptionStatus.ACTIVE, SubscriptionStatus.PAUSED):
        raise HTTPException(409, "Only active or paused subscriptions can be cancelled")
    if not subscription.plan.allow_early_close:
        raise HTTPException(409, "This plan does not allow early closing")
    subscription.status = SubscriptionStatus.CLOSED
    subscription.cancelled_on = payload.effective_on or date.today()
    db.commit()
    db.refresh(subscription)
    return subscription


@app.post("/subscriptions/{subscription_id}/renew", response_model=SubscriptionRead)
def renew_subscription(subscription_id: int, payload: SubscriptionAction, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    subscription = get_subscription_or_404(subscription_id, db, for_update=True)
    require_subscription_owner_or_team(subscription, current_user)
    if subscription.status not in (SubscriptionStatus.CLOSED, SubscriptionStatus.CANCELLED, SubscriptionStatus.EXPIRED):
        raise HTTPException(409, "Only closed or expired subscriptions can be renewed")
    if not subscription.plan.allow_renew:
        raise HTTPException(409, "This plan does not allow renewal")
    if not subscription.plan.active or not subscription.plan.product.active:
        raise HTTPException(409, "This plan is no longer available")
    renewed_on = payload.effective_on or date.today()
    subscription.status = SubscriptionStatus.DRAFT
    subscription.starts_on = renewed_on
    subscription.next_billing_on = next_billing_date(subscription.plan, renewed_on)
    subscription.paused_on = None
    subscription.cancelled_on = None
    db.commit()
    db.refresh(subscription)
    return subscription


@app.get("/invoices", response_model=list[InvoiceRead])
def list_invoices(invoice_status: InvoiceStatus | None = None, from_date: date | None = None, to_date: date | None = None, offset: int = 0, limit: int = 50, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    validate_pagination(offset, limit)
    if from_date and to_date and to_date < from_date:
        raise HTTPException(422, "End date cannot precede start date")
    statement = select(Invoice).order_by(Invoice.id.desc())
    if current_user.role == UserRole.CUSTOMER:
        statement = statement.join(Subscription).where(Subscription.customer_id == current_user.id)
    if invoice_status:
        statement = statement.where(Invoice.status == invoice_status)
    if from_date:
        statement = statement.where(Invoice.period_start >= from_date)
    if to_date:
        statement = statement.where(Invoice.period_start <= to_date)
    return db.scalars(statement.offset(offset).limit(limit)).all()


@app.get("/finance/dashboard", response_model=FinanceDashboardRead)
def finance_dashboard(
    from_date: date | None = None,
    to_date: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
):
    if from_date and to_date and to_date < from_date:
        raise HTTPException(422, "End date cannot precede start date")
    active_subscriptions = db.scalar(select(func.count(Subscription.id)).where(Subscription.status == SubscriptionStatus.ACTIVE)) or 0
    payment_statement = select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.status == PaymentStatus.SUCCESS)
    if from_date:
        payment_statement = payment_statement.where(Payment.received_on >= from_date)
    if to_date:
        payment_statement = payment_statement.where(Payment.received_on <= to_date)
    payments = db.scalar(payment_statement) or 0
    received = select(func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.invoice_id == Invoice.id,
        Payment.status == PaymentStatus.SUCCESS,
    ).scalar_subquery()
    invoice_statement = select(
        func.coalesce(func.sum(Invoice.amount - received), 0),
        func.coalesce(func.sum(case((Invoice.status == InvoiceStatus.OVERDUE, 1), else_=0)), 0),
    ).where(Invoice.status != InvoiceStatus.VOID)
    if from_date:
        invoice_statement = invoice_statement.where(Invoice.period_start >= from_date)
    if to_date:
        invoice_statement = invoice_statement.where(Invoice.period_start <= to_date)
    outstanding, overdue = db.execute(invoice_statement).one()
    return FinanceDashboardRead(
        active_subscriptions=active_subscriptions,
        revenue=payments,
        payments=payments,
        outstanding_balance=outstanding,
        overdue_invoices=overdue,
    )


@app.get("/invoices/{invoice_id}", response_model=InvoiceRead)
def get_invoice(invoice_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    if current_user.role == UserRole.CUSTOMER and invoice.subscription.customer_id != current_user.id:
        raise HTTPException(403, "You can only view your own invoices")
    return invoice


@app.post("/invoices/{invoice_id}/stripe/payment-intent")
def create_stripe_payment_intent(invoice_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    if current_user.role == UserRole.CUSTOMER and invoice.subscription.customer_id != current_user.id:
        raise HTTPException(403, "You can only pay your own invoices")
    if invoice.status not in (InvoiceStatus.CONFIRMED, InvoiceStatus.OVERDUE, InvoiceStatus.ISSUED):
        raise HTTPException(409, "Only confirmed invoices can be paid")
    if invoice.outstanding_balance <= 0:
        raise HTTPException(409, "This invoice has no outstanding balance")
    if invoice.stripe_payment_intent_id:
        raise HTTPException(409, "A Stripe payment intent already exists for this invoice")
    try:
        intent = create_invoice_payment_intent(invoice.id, invoice.outstanding_balance, invoice.customer_email_snapshot)
    except RuntimeError as error:
        raise HTTPException(503, str(error))
    invoice.stripe_payment_intent_id = intent.id
    db.commit()
    return {"payment_intent_id": intent.id, "client_secret": intent.client_secret, "publishable_key": os.getenv("STRIPE_PUBLISHABLE_KEY")}


@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    try:
        event = verify_webhook(payload, request.headers.get("Stripe-Signature"))
    except (RuntimeError, ValueError) as error:
        raise HTTPException(400, str(error))
    if event["type"] != "payment_intent.succeeded":
        return {"received": True}
    intent = event["data"]["object"]
    invoice_id = intent.get("metadata", {}).get("brightloop_invoice_id")
    if not invoice_id:
        return {"received": True}
    invoice = db.scalar(select(Invoice).where(Invoice.id == int(invoice_id)).with_for_update())
    if not invoice or invoice.stripe_payment_intent_id != intent["id"]:
        raise HTTPException(400, "Stripe payment does not match an invoice")
    if db.scalar(select(Payment).where(Payment.gateway_reference == intent["id"])):
        return {"received": True}
    amount = Decimal(intent["amount_received"]) / Decimal("100")
    if amount > invoice.outstanding_balance:
        raise HTTPException(400, "Stripe payment exceeds the outstanding balance")
    payment = Payment(invoice_id=invoice.id, amount=amount, status=PaymentStatus.SUCCESS, method="stripe", gateway_reference=intent["id"], received_on=date.today(), note="Recorded from Stripe webhook")
    db.add(payment)
    db.flush()
    received_amount = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.invoice_id == invoice.id,
        Payment.status == PaymentStatus.SUCCESS,
    ))
    if received_amount == invoice.amount:
        invoice.status = InvoiceStatus.PAID
    db.commit()
    return {"received": True}


@app.get("/invoices/{invoice_id}/print")
def print_invoice(invoice_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    if current_user.role == UserRole.CUSTOMER and invoice.subscription.customer_id != current_user.id:
        raise HTTPException(403, "You can only print your own invoices")
    if invoice.status == InvoiceStatus.DRAFT:
        raise HTTPException(409, "Draft invoices cannot be printed")
    pdf_bytes = render_invoice_pdf(invoice)
    number = invoice_number(invoice)
    return StreamingResponse(iter([pdf_bytes]), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{number}.pdf"'})


@app.post("/invoices/{invoice_id}/send")
def send_invoice(invoice_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF))):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    if invoice.status in (InvoiceStatus.DRAFT, InvoiceStatus.VOID):
        raise HTTPException(409, "Only confirmed invoices can be sent")
    number = invoice_number(invoice)
    try:
        send_invoice_email(invoice.customer_email_snapshot or invoice.subscription.customer.email, number, render_invoice_pdf(invoice))
    except RuntimeError as error:
        raise HTTPException(503, str(error))
    return {"message": "Invoice sent", "invoice_number": number}


@app.patch("/invoices/{invoice_id}/status", response_model=InvoiceRead)
def update_invoice_status(invoice_id: int, payload: InvoiceStatusUpdate, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    if payload.status != InvoiceStatus.VOID:
        raise HTTPException(422, "Use the confirm endpoint or record a payment for workflow changes")
    if invoice.status not in (InvoiceStatus.DRAFT, InvoiceStatus.CONFIRMED, InvoiceStatus.ISSUED, InvoiceStatus.OVERDUE):
        raise HTTPException(409, "This invoice cannot be voided")
    invoice.status = InvoiceStatus.VOID
    db.commit()
    db.refresh(invoice)
    return invoice


@app.post("/invoices/{invoice_id}/confirm", response_model=InvoiceRead)
def confirm_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF)),
):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    if invoice.status != InvoiceStatus.DRAFT:
        raise HTTPException(409, "Only draft invoices can be confirmed")
    invoice.status = InvoiceStatus.CONFIRMED
    db.commit()
    db.refresh(invoice)
    return invoice


@app.post("/invoices/{invoice_id}/void", response_model=InvoiceRead)
def void_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    if invoice.status not in (InvoiceStatus.DRAFT, InvoiceStatus.CONFIRMED, InvoiceStatus.ISSUED, InvoiceStatus.OVERDUE):
        raise HTTPException(409, "This invoice cannot be voided")
    invoice.status = InvoiceStatus.VOID
    db.commit()
    db.refresh(invoice)
    return invoice


@app.post("/invoices/{invoice_id}/payments", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def record_payment(invoice_id: int, payload: PaymentCreate, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN, UserRole.STAFF))):
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id).with_for_update())
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    if invoice.status == InvoiceStatus.VOID:
        raise HTTPException(409, "Payments cannot be recorded against a void invoice")
    if invoice.status not in (InvoiceStatus.CONFIRMED, InvoiceStatus.ISSUED, InvoiceStatus.OVERDUE):
        raise HTTPException(409, "Only confirmed invoices can accept payments")
    if payload.status == PaymentStatus.SUCCESS:
        received_amount = db.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.invoice_id == invoice.id, Payment.status == PaymentStatus.SUCCESS
            )
        )
        if received_amount + payload.amount > invoice.amount:
            raise HTTPException(409, "Payment exceeds the outstanding invoice balance")
    payment = Payment(
        invoice_id=invoice.id,
        amount=payload.amount,
        status=payload.status,
        method=payload.method,
        gateway_reference=payload.gateway_reference,
        received_on=payload.received_on or date.today(),
        note=payload.note,
    )
    db.add(payment)
    try:
        db.flush()
        if payload.status == PaymentStatus.SUCCESS:
            received_amount = db.scalar(
                select(func.coalesce(func.sum(Payment.amount), 0)).where(
                    Payment.invoice_id == invoice.id, Payment.status == PaymentStatus.SUCCESS
                )
            )
            if received_amount == invoice.amount:
                invoice.status = InvoiceStatus.PAID
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This gateway payment reference already exists")
    db.refresh(payment)
    return payment


@app.get("/invoices/{invoice_id}/payments", response_model=list[PaymentRead])
def list_invoice_payments(invoice_id: int, offset: int = 0, limit: int = 50, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    validate_pagination(offset, limit)
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    if current_user.role == UserRole.CUSTOMER and invoice.subscription.customer_id != current_user.id:
        raise HTTPException(403, "You can only view payments for your own invoices")
    return db.scalars(select(Payment).where(Payment.invoice_id == invoice_id).order_by(Payment.id.desc()).offset(offset).limit(limit)).all()


@app.post("/billing/run", response_model=list[InvoiceRead])
def run_billing(billing_date: date | None = None, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))):
    return generate_due_invoices(db, billing_date or date.today())
