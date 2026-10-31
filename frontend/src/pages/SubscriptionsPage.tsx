import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  FileText,
  Pause,
  Play,
  Plus,
  RefreshCcw,
  RotateCcw,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import {
  catalogApi,
  pricingApi,
  subscriptionApi,
  userApi,
} from "@/api/services";
import { apiMessage } from "@/api/client";
import { useAuth } from "@/auth/useAuth";
import { CommercialLines } from "@/components/CommercialLines";
import {
  Button,
  DetailRow,
  EmptyState,
  ErrorState,
  Field,
  Input,
  LoadingState,
  Modal,
  PageHeader,
  Pagination,
  Select,
  StatusBadge,
  Textarea,
} from "@/components/ui";
import { money, shortDate, today } from "@/lib/format";
import type {
  CommercialLine,
  Subscription,
  SubscriptionInput,
} from "@/api/types";

export function SubscriptionsPage() {
  const { user } = useAuth();
  const internal = user?.role !== "customer";
  const client = useQueryClient();
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<Subscription | null>(null);
  const limit = 25;
  const query = useQuery({
    queryKey: ["subscriptions", status, offset],
    queryFn: () =>
      subscriptionApi.list({
        subscription_status: status || undefined,
        offset,
        limit,
      }),
  });
  const action = useMutation({
    mutationFn: ({
      id,
      name,
    }: {
      id: number;
      name:
        | "mark-quotation"
        | "confirm"
        | "activate"
        | "pause"
        | "resume"
        | "close"
        | "renew";
    }) => subscriptionApi.action(id, name, today()),
    onSuccess: (value) => {
      toast.success("Subscription updated");
      setSelected(value);
      void client.invalidateQueries({ queryKey: ["subscriptions"] });
    },
    onError: (e) => toast.error(apiMessage(e)),
  });
  if (query.isLoading) return <LoadingState />;
  if (query.isError)
    return (
      <ErrorState
        message={apiMessage(query.error)}
        retry={() => void query.refetch()}
      />
    );
  return (
    <>
      <PageHeader
        eyebrow={internal ? "Recurring revenue" : "Your agreements"}
        title="Subscriptions"
        description={
          internal
            ? "Manage every recurring agreement across its complete commercial lifecycle."
            : "Review and manage your active recurring services."
        }
        action={
          internal ? (
            <Button onClick={() => setOpen(true)}>
              <Plus size={16} />
              New subscription
            </Button>
          ) : undefined
        }
      />
      <div className="toolbar">
        <div />
        <Select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setOffset(0);
          }}
        >
          <option value="">All statuses</option>
          {[
            "draft",
            "quotation",
            "confirmed",
            "active",
            "paused",
            "closed",
            "expired",
          ].map((v) => (
            <option key={v} value={v}>
              {v}
            </option>
          ))}
        </Select>
      </div>
      <section className="card table-card">
        {query.data?.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Subscription</th>
                  <th>Customer</th>
                  <th>Start date</th>
                  <th>Next billing</th>
                  <th>Status</th>
                  <th>Recurring value</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {query.data.map((s) => (
                  <tr key={s.id}>
                    <td className="primary-cell">
                      <strong>
                        {s.subscription_number ||
                          `SUB-${String(s.id).padStart(5, "0")}`}
                      </strong>
                      <small>Plan #{s.plan_id}</small>
                    </td>
                    <td>Customer #{s.customer_id}</td>
                    <td>{shortDate(s.starts_on)}</td>
                    <td>{shortDate(s.next_billing_on)}</td>
                    <td>
                      <StatusBadge value={s.status} />
                    </td>
                    <td className="amount">
                      {money(
                        s.lines.reduce(
                          (sum, line) =>
                            sum + line.quantity * Number(line.unit_price),
                          0,
                        ),
                      )}
                    </td>
                    <td className="table-actions">
                      <Button variant="ghost" onClick={() => setSelected(s)}>
                        Manage <ArrowRight size={14} />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon={RefreshCcw}
            title="No subscriptions found"
            text={
              internal
                ? "Create one directly or convert a confirmed quotation."
                : "Your subscriptions will appear here once confirmed."
            }
          />
        )}
        <Pagination
          offset={offset}
          limit={limit}
          count={query.data?.length || 0}
          onChange={setOffset}
        />
      </section>
      {internal && (
        <SubscriptionForm
          open={open}
          close={() => setOpen(false)}
          complete={() => {
            setOpen(false);
            void client.invalidateQueries({ queryKey: ["subscriptions"] });
          }}
        />
      )}
      <SubscriptionDetail
        subscription={selected}
        internal={internal}
        close={() => setSelected(null)}
        busy={action.isPending}
        run={(name) => selected && action.mutate({ id: selected.id, name })}
      />
    </>
  );
}

function SubscriptionForm({
  open,
  close,
  complete,
}: {
  open: boolean;
  close: () => void;
  complete: () => void;
}) {
  const [customer, setCustomer] = useState("");
  const [product, setProduct] = useState("");
  const [plan, setPlan] = useState("");
  const [discount, setDiscount] = useState("");
  const [tax, setTax] = useState("");
  const [start, setStart] = useState(today());
  const [expires, setExpires] = useState("");
  const [terms, setTerms] = useState("");
  const [due, setDue] = useState("7");
  const [lines, setLines] = useState<Omit<CommercialLine, "id">[]>([
    { product_name: "", quantity: 1, unit_price: 0 },
  ]);
  const users = useQuery({
    queryKey: ["users", "customers"],
    queryFn: () => userApi.list({ role: "customer", limit: 100 }),
    enabled: open,
  });
  const products = useQuery({
    queryKey: ["products"],
    queryFn: () => catalogApi.products(),
    enabled: open,
  });
  const plans = useQuery({
    queryKey: ["plans", Number(product)],
    queryFn: () => catalogApi.plans(Number(product)),
    enabled: open && !!product,
  });
  const discounts = useQuery({
    queryKey: ["discounts"],
    queryFn: () => pricingApi.discounts(),
    enabled: open,
  });
  const taxes = useQuery({
    queryKey: ["taxes"],
    queryFn: () => pricingApi.taxes(),
    enabled: open,
  });
  const create = useMutation({
    mutationFn: (v: SubscriptionInput) => subscriptionApi.create(v),
    onSuccess: () => {
      toast.success("Draft subscription created");
      complete();
    },
    onError: (e) => toast.error(apiMessage(e)),
  });
  const save = (e: FormEvent) => {
    e.preventDefault();
    create.mutate({
      customer_id: Number(customer),
      plan_id: Number(plan),
      discount_id: discount ? Number(discount) : undefined,
      tax_rule_id: tax ? Number(tax) : undefined,
      starts_on: start,
      expires_on: expires || undefined,
      payment_terms: terms || undefined,
      payment_due_days: Number(due),
      lines,
    });
  };
  return (
    <Modal
      open={open}
      onClose={close}
      title="Create subscription"
      description="Create a draft recurring agreement and move it through approval."
      size="lg"
    >
      <form onSubmit={save}>
        <div className="form-grid">
          <Field label="Customer">
            <Select
              value={customer}
              onChange={(e) => setCustomer(e.target.value)}
              required
            >
              <option value="">Select customer</option>
              {users.data?.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Product">
            <Select
              value={product}
              onChange={(e) => {
                setProduct(e.target.value);
                setPlan("");
              }}
              required
            >
              <option value="">Select product</option>
              {products.data?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Billing plan">
            <Select
              value={plan}
              onChange={(e) => setPlan(e.target.value)}
              required
            >
              <option value="">Select plan</option>
              {plans.data?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} · {money(p.amount)}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Starts on">
            <Input
              type="date"
              value={start}
              onChange={(e) => setStart(e.target.value)}
              required
            />
          </Field>
          <Field label="Expires on">
            <Input
              type="date"
              value={expires}
              onChange={(e) => setExpires(e.target.value)}
            />
          </Field>
          <Field label="Payment due days">
            <Input
              type="number"
              min="0"
              max="365"
              value={due}
              onChange={(e) => setDue(e.target.value)}
            />
          </Field>
          <Field label="Discount">
            <Select
              value={discount}
              onChange={(e) => setDiscount(e.target.value)}
            >
              <option value="">No discount</option>
              {discounts.data?.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.code}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Tax rule">
            <Select value={tax} onChange={(e) => setTax(e.target.value)}>
              <option value="">No tax</option>
              {taxes.data?.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} · {t.rate}%
                </option>
              ))}
            </Select>
          </Field>
          <Field
            label="Payment terms"
            children={
              <Textarea
                value={terms}
                onChange={(e) => setTerms(e.target.value)}
              />
            }
          />
        </div>
        <div style={{ marginTop: 20 }}>
          <CommercialLines
            lines={lines}
            products={products.data || []}
            onChange={setLines}
          />
        </div>
        <div className="form-actions">
          <Button type="button" variant="secondary" onClick={close}>
            Cancel
          </Button>
          <Button type="submit" loading={create.isPending}>
            Create draft
          </Button>
        </div>
      </form>
    </Modal>
  );
}

type ActionName =
  | "mark-quotation"
  | "confirm"
  | "activate"
  | "pause"
  | "resume"
  | "close"
  | "renew";
function SubscriptionDetail({
  subscription,
  internal,
  close,
  busy,
  run,
}: {
  subscription: Subscription | null;
  internal: boolean;
  close: () => void;
  busy: boolean;
  run: (name: ActionName) => void;
}) {
  if (!subscription) return null;
  const actions: {
    name: ActionName;
    label: string;
    icon: typeof Play;
    show: boolean;
    danger?: boolean;
  }[] = [
    {
      name: "mark-quotation",
      label: "Move to quotation",
      icon: FileText,
      show: internal && subscription.status === "draft",
    },
    {
      name: "confirm",
      label: "Confirm",
      icon: Play,
      show: internal && subscription.status === "quotation",
    },
    {
      name: "activate",
      label: "Activate",
      icon: Play,
      show: internal && subscription.status === "confirmed",
    },
    {
      name: "pause",
      label: "Pause",
      icon: Pause,
      show: subscription.status === "active",
    },
    {
      name: "resume",
      label: "Resume",
      icon: Play,
      show: subscription.status === "paused",
    },
    {
      name: "renew",
      label: "Renew",
      icon: RotateCcw,
      show: ["active", "expired", "closed"].includes(subscription.status),
    },
    {
      name: "close",
      label: "Close",
      icon: XCircle,
      show: !["closed", "expired"].includes(subscription.status),
      danger: true,
    },
  ];
  return (
    <Modal
      open
      title={
        subscription.subscription_number || `Subscription #${subscription.id}`
      }
      description="Agreement lifecycle and billing details"
      onClose={close}
      size="lg"
    >
      <div className="content-grid">
        <div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Quantity</th>
                  <th>Unit price</th>
                  <th>Total</th>
                </tr>
              </thead>
              <tbody>
                {subscription.lines.map((l, i) => (
                  <tr key={l.id || i}>
                    <td className="primary-cell">
                      <strong>{l.product_name}</strong>
                      <small>{l.variant_name || "Standard"}</small>
                    </td>
                    <td>{l.quantity}</td>
                    <td>{money(l.unit_price)}</td>
                    <td className="amount">
                      {money(l.quantity * Number(l.unit_price))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="card section-body metric-list">
          <DetailRow
            label="Status"
            value={<StatusBadge value={subscription.status} />}
          />
          <DetailRow label="Starts" value={shortDate(subscription.starts_on)} />
          <DetailRow
            label="Next billing"
            value={shortDate(subscription.next_billing_on)}
          />
          <DetailRow
            label="Expires"
            value={shortDate(subscription.expires_on)}
          />
          <DetailRow
            label="Payment terms"
            value={
              subscription.payment_terms ||
              `${subscription.payment_due_days} day(s)`
            }
          />
        </div>
      </div>
      <div className="form-actions">
        {actions
          .filter((a) => a.show)
          .map(({ name, label, icon: Icon, danger }) => (
            <Button
              key={name}
              loading={busy}
              variant={danger ? "danger" : "secondary"}
              onClick={() => run(name)}
            >
              <Icon size={15} />
              {label}
            </Button>
          ))}
      </div>
    </Modal>
  );
}
