export type Role = "admin" | "staff" | "customer";
export type SubscriptionStatus =
  | "draft"
  | "quotation"
  | "confirmed"
  | "active"
  | "paused"
  | "closed"
  | "cancelled"
  | "expired";
export type InvoiceStatus =
  | "draft"
  | "confirmed"
  | "issued"
  | "paid"
  | "overdue"
  | "void";
export type QuotationStatus = "draft" | "quotation" | "confirmed" | "closed";
export type PaymentStatus = "success" | "failed";
export type BillingInterval = "daily" | "weekly" | "monthly" | "yearly";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: Role;
}
export interface Product {
  id: number;
  name: string;
  description?: string;
  product_type?: string;
  sales_price?: number;
  cost_price?: number;
  notes?: string;
  active: boolean;
}
export interface ProductVariant {
  id: number;
  product_id: number;
  name: string;
  additional_price: number;
  active: boolean;
}
export interface Plan {
  id: number;
  product_id: number;
  name: string;
  amount: number;
  interval_days?: number;
  billing_interval?: BillingInterval;
  minimum_quantity: number;
  available_from?: string;
  available_until?: string;
  auto_close_on_end: boolean;
  allow_early_close: boolean;
  allow_pause: boolean;
  allow_renew: boolean;
  active: boolean;
}
export interface CommercialLine {
  id?: number;
  product_id?: number;
  variant_id?: number;
  product_name: string;
  variant_name?: string;
  quantity: number;
  unit_price: number;
}
export interface Discount {
  id: number;
  code: string;
  discount_type: "percentage" | "fixed";
  value: number;
  starts_on?: string;
  ends_on?: string;
  minimum_purchase?: number;
  minimum_quantity?: number;
  usage_limit?: number;
  times_used: number;
  product_id?: number;
  active: boolean;
}
export interface TaxRule {
  id: number;
  name: string;
  rate: number;
  active: boolean;
}
export interface QuotationTemplate {
  id: number;
  name: string;
  plan_id?: number;
  validity_days: number;
  active: boolean;
  lines: CommercialLine[];
}
export interface Quotation {
  id: number;
  quotation_number: string;
  customer_id: number;
  plan_id?: number;
  discount_id?: number;
  tax_rule_id?: number;
  status: QuotationStatus;
  issue_date: string;
  expires_on: string;
  payment_terms?: string;
  payment_due_days: number;
  lines: CommercialLine[];
}
export interface Subscription {
  id: number;
  subscription_number?: string;
  customer_id: number;
  plan_id: number;
  discount_id?: number;
  tax_rule_id?: number;
  status: SubscriptionStatus;
  starts_on: string;
  next_billing_on: string;
  paused_on?: string;
  cancelled_on?: string;
  expires_on?: string;
  payment_terms?: string;
  payment_due_days: number;
  source_quotation_id?: number;
  lines: CommercialLine[];
}
export interface InvoiceLine extends CommercialLine {
  id: number;
  product_id_snapshot?: number;
  variant_id_snapshot?: number;
  line_subtotal: number;
  discount_amount: number;
  tax_amount: number;
  line_total: number;
}
export interface Invoice {
  id: number;
  subscription_id: number;
  period_start: string;
  period_end: string;
  due_on: string;
  amount: number;
  subtotal: number;
  discount_amount: number;
  tax_amount: number;
  status: InvoiceStatus;
  customer_id_snapshot?: number;
  customer_name_snapshot?: string;
  customer_email_snapshot?: string;
  outstanding_balance: number;
  lines: InvoiceLine[];
}
export interface Payment {
  id: number;
  invoice_id: number;
  amount: number;
  status: PaymentStatus;
  method: string;
  gateway_reference?: string;
  received_on: string;
  note?: string;
}
export interface FinanceDashboard {
  active_subscriptions: number;
  revenue: number;
  payments: number;
  outstanding_balance: number;
  overdue_invoices: number;
}
export interface Token {
  access_token: string;
  token_type: string;
}

export interface UserInput {
  email: string;
  full_name: string;
  password: string;
  role?: Role;
}
export interface ProductInput {
  name: string;
  description?: string;
  product_type?: string;
  sales_price?: number;
  cost_price?: number;
  notes?: string;
}
export interface PlanInput {
  product_id: number;
  name: string;
  amount: number;
  billing_interval: BillingInterval;
  minimum_quantity: number;
  available_from?: string;
  available_until?: string;
  auto_close_on_end: boolean;
  allow_early_close: boolean;
  allow_pause: boolean;
  allow_renew: boolean;
}
export interface QuotationInput {
  customer_id: number;
  plan_id?: number;
  template_id?: number;
  discount_id?: number;
  tax_rule_id?: number;
  expires_on?: string;
  payment_terms?: string;
  payment_due_days: number;
  lines: Omit<CommercialLine, "id">[];
}
export interface SubscriptionInput {
  customer_id: number;
  plan_id: number;
  discount_id?: number;
  tax_rule_id?: number;
  starts_on: string;
  expires_on?: string;
  payment_terms?: string;
  payment_due_days: number;
  lines: Omit<CommercialLine, "id">[];
}
