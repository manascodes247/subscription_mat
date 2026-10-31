import { api } from "./client";
import type {
  Discount,
  FinanceDashboard,
  Invoice,
  Payment,
  Plan,
  Product,
  ProductInput,
  ProductVariant,
  Quotation,
  QuotationInput,
  QuotationStatus,
  QuotationTemplate,
  Subscription,
  SubscriptionInput,
  TaxRule,
  Token,
  User,
  UserInput,
} from "./types";

const data = <T>(request: Promise<{ data: T }>) =>
  request.then((response) => response.data);
export const authApi = {
  login: (email: string, password: string) =>
    data<Token>(api.post("/auth/login", { email, password })),
  me: () => data<User>(api.get("/auth/me")),
  requestReset: (email: string) =>
    data(api.post("/auth/password-reset/request", { email })),
  confirmReset: (token: string, password: string) =>
    data(api.post("/auth/password-reset/confirm", { token, password })),
};
export const userApi = {
  list: (params?: object) => data<User[]>(api.get("/users", { params })),
  createCustomer: (payload: UserInput) =>
    data<User>(api.post("/users", { ...payload, role: "customer" })),
  createStaff: (payload: UserInput) =>
    data<User>(api.post("/staff/users", { ...payload, role: "staff" })),
};
export const catalogApi = {
  products: (include_inactive = false) =>
    data<Product[]>(api.get("/products", { params: { include_inactive } })),
  product: (id: number) => data<Product>(api.get(`/products/${id}`)),
  createProduct: (payload: ProductInput) =>
    data<Product>(api.post("/products", payload)),
  updateProduct: (
    id: number,
    payload: Partial<ProductInput & { active: boolean }>,
  ) => data<Product>(api.patch(`/products/${id}`, payload)),
  variants: (productId: number, include_inactive = false) =>
    data<ProductVariant[]>(
      api.get(`/products/${productId}/variants`, {
        params: { include_inactive },
      }),
    ),
  createVariant: (
    productId: number,
    payload: { name: string; additional_price: number },
  ) =>
    data<ProductVariant>(api.post(`/products/${productId}/variants`, payload)),
  plans: (productId: number, include_inactive = false) =>
    data<Plan[]>(
      api.get(`/products/${productId}/plans`, { params: { include_inactive } }),
    ),
  createPlan: (payload: object) => data<Plan>(api.post("/plans", payload)),
};
export const pricingApi = {
  discounts: (include_inactive = false) =>
    data<Discount[]>(api.get("/discounts", { params: { include_inactive } })),
  createDiscount: (payload: object) =>
    data<Discount>(api.post("/discounts", payload)),
  taxes: (include_inactive = false) =>
    data<TaxRule[]>(api.get("/tax-rules", { params: { include_inactive } })),
  createTax: (payload: object) =>
    data<TaxRule>(api.post("/tax-rules", payload)),
};
export const quoteApi = {
  list: (params?: object) =>
    data<Quotation[]>(api.get("/quotations", { params })),
  templates: () => data<QuotationTemplate[]>(api.get("/quotation-templates")),
  create: (payload: QuotationInput) =>
    data<Quotation>(api.post("/quotations", payload)),
  status: (id: number, status: QuotationStatus) =>
    data<Quotation>(api.patch(`/quotations/${id}/status`, { status })),
  convert: (id: number, payload: object) =>
    data<Subscription>(api.post(`/quotations/${id}/convert`, payload)),
};
export const subscriptionApi = {
  list: (params?: object) =>
    data<Subscription[]>(api.get("/subscriptions", { params })),
  get: (id: number) => data<Subscription>(api.get(`/subscriptions/${id}`)),
  create: (payload: SubscriptionInput) =>
    data<Subscription>(api.post("/subscriptions", payload)),
  action: (
    id: number,
    action:
      | "mark-quotation"
      | "confirm"
      | "activate"
      | "pause"
      | "resume"
      | "close"
      | "renew",
    effective_on?: string,
  ) =>
    data<Subscription>(
      api.post(`/subscriptions/${id}/${action}`, {
        effective_on: effective_on || null,
      }),
    ),
};
export const invoiceApi = {
  list: (params?: object) => data<Invoice[]>(api.get("/invoices", { params })),
  get: (id: number) => data<Invoice>(api.get(`/invoices/${id}`)),
  payments: (id: number) =>
    data<Payment[]>(api.get(`/invoices/${id}/payments`)),
  recordPayment: (id: number, payload: object) =>
    data<Payment>(api.post(`/invoices/${id}/payments`, payload)),
  confirm: (id: number) => data<Invoice>(api.post(`/invoices/${id}/confirm`)),
  void: (id: number) => data<Invoice>(api.post(`/invoices/${id}/void`)),
  send: (id: number) => data(api.post(`/invoices/${id}/send`)),
  pdf: (id: number) =>
    api
      .get(`/invoices/${id}/print`, { responseType: "blob" })
      .then(({ data }) => data as Blob),
  paymentIntent: (id: number) =>
    data<{
      payment_intent_id: string;
      client_secret: string;
      publishable_key: string;
    }>(api.post(`/invoices/${id}/stripe/payment-intent`)),
};
export const financeApi = {
  dashboard: () => data<FinanceDashboard>(api.get("/finance/dashboard")),
  runBilling: (billing_date?: string) =>
    data<Invoice[]>(
      api.post("/billing/run", null, { params: { billing_date } }),
    ),
};
