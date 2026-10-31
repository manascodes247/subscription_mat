from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .models import BillingInterval, DiscountType, InvoiceStatus, PaymentStatus, QuotationStatus, SubscriptionStatus, UserRole
from .security import validate_password_complexity


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=12, max_length=128)
    role: UserRole = UserRole.CUSTOMER

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        validate_password_complexity(value)
        return value


class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=20, max_length=512)
    password: str = Field(min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        validate_password_complexity(value)
        return value


class TokenRead(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    product_type: str | None = Field(default=None, max_length=80)
    sales_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    cost_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    notes: str | None = Field(default=None, max_length=2000)


class ProductRead(ProductCreate):
    id: int
    active: bool
    model_config = ConfigDict(from_attributes=True)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    product_type: str | None = Field(default=None, max_length=80)
    sales_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    cost_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    notes: str | None = Field(default=None, max_length=2000)
    active: bool | None = None


class ProductVariantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    additional_price: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)


class ProductVariantRead(ProductVariantCreate):
    id: int
    product_id: int
    active: bool
    model_config = ConfigDict(from_attributes=True)


class ProductVariantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    additional_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    active: bool | None = None


class PlanCreate(BaseModel):
    product_id: int
    name: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    interval_days: int | None = Field(default=None, gt=0, le=366)
    billing_interval: BillingInterval | None = None
    minimum_quantity: int = Field(default=1, gt=0)
    available_from: date | None = None
    available_until: date | None = None
    auto_close_on_end: bool = False
    allow_early_close: bool = True
    allow_pause: bool = True
    allow_renew: bool = True


class PlanRead(PlanCreate):
    id: int
    active: bool
    model_config = ConfigDict(from_attributes=True)


class PlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    interval_days: int | None = Field(default=None, gt=0, le=366)
    billing_interval: BillingInterval | None = None
    minimum_quantity: int | None = Field(default=None, gt=0)
    available_from: date | None = None
    available_until: date | None = None
    auto_close_on_end: bool | None = None
    allow_early_close: bool | None = None
    allow_pause: bool | None = None
    allow_renew: bool | None = None
    active: bool | None = None


class SubscriptionCreate(BaseModel):
    customer_id: int
    plan_id: int
    discount_id: int | None = None
    tax_rule_id: int | None = None
    starts_on: date
    expires_on: date | None = None
    payment_terms: str | None = Field(default=None, max_length=500)
    payment_due_days: int = Field(default=0, ge=0, le=365)
    lines: list["SubscriptionLineCreate"] = Field(default_factory=list)


class CommercialLineCreate(BaseModel):
    product_id: int | None = None
    variant_id: int | None = None
    product_name: str = Field(min_length=1, max_length=160)
    variant_name: str | None = Field(default=None, max_length=120)
    quantity: int = Field(default=1, gt=0)
    unit_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)


class CommercialLineRead(CommercialLineCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)


class SubscriptionLineCreate(CommercialLineCreate):
    pass


class SubscriptionLineRead(CommercialLineRead):
    subscription_id: int


class SubscriptionRead(BaseModel):
    id: int
    subscription_number: str | None
    customer_id: int
    plan_id: int
    discount_id: int | None
    tax_rule_id: int | None
    status: SubscriptionStatus
    starts_on: date
    next_billing_on: date
    paused_on: date | None
    cancelled_on: date | None
    expires_on: date | None
    payment_terms: str | None
    payment_due_days: int
    source_quotation_id: int | None
    lines: list[SubscriptionLineRead] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class SubscriptionAction(BaseModel):
    effective_on: date | None = None


class InvoiceRead(BaseModel):
    id: int
    subscription_id: int
    period_start: date
    period_end: date
    due_on: date
    amount: Decimal
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    status: InvoiceStatus
    customer_id_snapshot: int | None
    customer_name_snapshot: str | None
    customer_email_snapshot: str | None
    lines: list["InvoiceLineRead"] = Field(default_factory=list)
    outstanding_balance: Decimal
    model_config = ConfigDict(from_attributes=True)


class InvoiceLineRead(BaseModel):
    id: int
    product_id_snapshot: int | None
    variant_id_snapshot: int | None
    product_name: str
    variant_name: str | None
    quantity: int
    unit_price: Decimal
    line_subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    line_total: Decimal
    model_config = ConfigDict(from_attributes=True)


class InvoiceStatusUpdate(BaseModel):
    status: InvoiceStatus


class PaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    method: str = Field(min_length=1, max_length=50)
    gateway_reference: str | None = Field(default=None, max_length=160)
    received_on: date | None = None
    status: PaymentStatus = PaymentStatus.SUCCESS
    note: str | None = Field(default=None, max_length=1000)


class PaymentRead(BaseModel):
    id: int
    invoice_id: int
    amount: Decimal
    status: PaymentStatus
    method: str
    gateway_reference: str | None
    received_on: date
    note: str | None
    model_config = ConfigDict(from_attributes=True)


class QuotationTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    plan_id: int | None = None
    validity_days: int = Field(default=30, gt=0, le=3650)
    lines: list[CommercialLineCreate] = Field(min_length=1)


class QuotationTemplateRead(BaseModel):
    id: int
    name: str
    plan_id: int | None
    validity_days: int
    active: bool
    lines: list[CommercialLineRead] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class QuotationCreate(BaseModel):
    customer_id: int
    plan_id: int | None = None
    template_id: int | None = None
    discount_id: int | None = None
    tax_rule_id: int | None = None
    expires_on: date | None = None
    payment_terms: str | None = Field(default=None, max_length=500)
    payment_due_days: int = Field(default=0, ge=0, le=365)
    lines: list[CommercialLineCreate] = Field(default_factory=list)


class QuotationRead(BaseModel):
    id: int
    quotation_number: str
    customer_id: int
    plan_id: int | None
    discount_id: int | None
    tax_rule_id: int | None
    status: QuotationStatus
    issue_date: date
    expires_on: date
    payment_terms: str | None
    payment_due_days: int
    lines: list[CommercialLineRead] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class QuotationStatusUpdate(BaseModel):
    status: QuotationStatus


class QuotationConvertRequest(BaseModel):
    starts_on: date | None = None
    expires_on: date | None = None
    payment_terms: str | None = Field(default=None, max_length=500)
    payment_due_days: int | None = Field(default=None, ge=0, le=365)


class DiscountCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    discount_type: DiscountType
    value: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    starts_on: date | None = None
    ends_on: date | None = None
    minimum_purchase: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    minimum_quantity: int | None = Field(default=None, gt=0)
    usage_limit: int | None = Field(default=None, gt=0)
    product_id: int | None = None


class DiscountRead(DiscountCreate):
    id: int
    times_used: int
    active: bool
    model_config = ConfigDict(from_attributes=True)


class DiscountUpdate(BaseModel):
    value: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    starts_on: date | None = None
    ends_on: date | None = None
    minimum_purchase: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    minimum_quantity: int | None = Field(default=None, gt=0)
    usage_limit: int | None = Field(default=None, gt=0)
    product_id: int | None = None
    active: bool | None = None


class TaxRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    rate: Decimal = Field(gt=0, le=100, max_digits=5, decimal_places=2)


class TaxRuleRead(TaxRuleCreate):
    id: int
    active: bool
    model_config = ConfigDict(from_attributes=True)


class TaxRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    rate: Decimal | None = Field(default=None, gt=0, le=100, max_digits=5, decimal_places=2)
    active: bool | None = None


class FinanceDashboardRead(BaseModel):
    active_subscriptions: int
    revenue: Decimal
    payments: Decimal
    outstanding_balance: Decimal
    overdue_invoices: int
