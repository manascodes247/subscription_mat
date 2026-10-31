import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, FileText, Plus } from "lucide-react";
import { toast } from "sonner";
import { catalogApi, pricingApi, quoteApi, userApi } from "@/api/services";
import { apiMessage } from "@/api/client";
import {
  Button,
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
import { CommercialLines } from "@/components/CommercialLines";
import { money, shortDate, today } from "@/lib/format";
import type {
  CommercialLine,
  Quotation,
  QuotationInput,
  QuotationStatus,
} from "@/api/types";

export function QuotationsPage() {
  const client = useQueryClient();
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<Quotation | null>(null);
  const limit = 25;
  const query = useQuery({
    queryKey: ["quotations", status, offset],
    queryFn: () =>
      quoteApi.list({ quotation_status: status || undefined, offset, limit }),
  });
  const change = useMutation({
    mutationFn: ({ id, status }: { id: number; status: QuotationStatus }) =>
      quoteApi.status(id, status),
    onSuccess: (v) => {
      toast.success("Quotation updated");
      setSelected(v);
      void client.invalidateQueries({ queryKey: ["quotations"] });
    },
    onError: (e) => toast.error(apiMessage(e)),
  });
  const convert = useMutation({
    mutationFn: (quote: Quotation) =>
      quoteApi.convert(quote.id, {
        starts_on: today(),
        payment_due_days: quote.payment_due_days,
      }),
    onSuccess: () => {
      toast.success("Subscription created from quotation");
      setSelected(null);
      void client.invalidateQueries({ queryKey: ["quotations"] });
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
        eyebrow="Sales workflow"
        title="Quotations"
        description="Prepare commercial offers, confirm customer acceptance and convert them into recurring subscriptions."
        action={
          <Button onClick={() => setOpen(true)}>
            <Plus size={16} />
            New quotation
          </Button>
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
          {["draft", "quotation", "confirmed", "closed"].map((v) => (
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
                  <th>Quotation</th>
                  <th>Customer</th>
                  <th>Issued</th>
                  <th>Expires</th>
                  <th>Status</th>
                  <th>Total</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {query.data.map((q) => (
                  <tr key={q.id}>
                    <td className="primary-cell">
                      <strong>{q.quotation_number}</strong>
                      <small>
                        {q.lines.length} commercial line
                        {q.lines.length === 1 ? "" : "s"}
                      </small>
                    </td>
                    <td>Customer #{q.customer_id}</td>
                    <td>{shortDate(q.issue_date)}</td>
                    <td>{shortDate(q.expires_on)}</td>
                    <td>
                      <StatusBadge value={q.status} />
                    </td>
                    <td className="amount">
                      {money(
                        q.lines.reduce(
                          (sum, line) =>
                            sum + Number(line.unit_price) * line.quantity,
                          0,
                        ),
                      )}
                    </td>
                    <td className="table-actions">
                      <Button variant="ghost" onClick={() => setSelected(q)}>
                        Open <ArrowRight size={14} />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon={FileText}
            title="No quotations found"
            text="Create a commercial proposal and move it through approval to subscription."
          />
        )}
        <Pagination
          offset={offset}
          limit={limit}
          count={query.data?.length || 0}
          onChange={setOffset}
        />
      </section>
      <QuotationForm
        open={open}
        close={() => setOpen(false)}
        complete={() => {
          setOpen(false);
          void client.invalidateQueries({ queryKey: ["quotations"] });
        }}
      />
      <QuoteDetail
        quote={selected}
        close={() => setSelected(null)}
        changing={change.isPending || convert.isPending}
        update={(s) =>
          selected && change.mutate({ id: selected.id, status: s })
        }
        convert={() => selected && convert.mutate(selected)}
      />
    </>
  );
}

function QuotationForm({
  open,
  close,
  complete,
}: {
  open: boolean;
  close: () => void;
  complete: () => void;
}) {
  const [templateId, setTemplateId] = useState("");
  const [customer, setCustomer] = useState("");
  const [plan, setPlan] = useState("");
  const [discount, setDiscount] = useState("");
  const [tax, setTax] = useState("");
  const [expires, setExpires] = useState("");
  const [terms, setTerms] = useState("");
  const [dueDays, setDueDays] = useState("7");
  const [lines, setLines] = useState<Omit<CommercialLine, "id">[]>([
    { product_name: "", quantity: 1, unit_price: 0 },
  ]);
  const templates = useQuery({
    queryKey: ["quotation-templates"],
    queryFn: () => quoteApi.templates(),
    enabled: open,
  });
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
  const plans = useQuery({
    queryKey: ["plans", Number(lines[0]?.product_id)],
    queryFn: () => catalogApi.plans(Number(lines[0].product_id)),
    enabled: open && !!lines[0]?.product_id,
  });

  const handleTemplateChange = (idStr: string) => {
    setTemplateId(idStr);
    if (!idStr) return;
    const tpl = templates.data?.find((t) => t.id === Number(idStr));
    if (!tpl) return;
    if (tpl.plan_id) setPlan(String(tpl.plan_id));
    if (tpl.validity_days) {
      const expDate = new Date();
      expDate.setDate(expDate.getDate() + tpl.validity_days);
      setExpires(expDate.toISOString().split("T")[0]);
    }
    if (tpl.lines && tpl.lines.length > 0) {
      setLines(
        tpl.lines.map((l) => ({
          product_id: l.product_id,
          variant_id: l.variant_id,
          product_name: l.product_name,
          variant_name: l.variant_name,
          quantity: l.quantity,
          unit_price: Number(l.unit_price),
        }))
      );
    }
  };

  const create = useMutation({
    mutationFn: (payload: QuotationInput) => quoteApi.create(payload),
    onSuccess: () => {
      toast.success("Quotation created");
      complete();
    },
    onError: (e) => toast.error(apiMessage(e)),
  });
  const save = (event: FormEvent) => {
    event.preventDefault();
    create.mutate({
      customer_id: Number(customer),
      plan_id: plan ? Number(plan) : undefined,
      template_id: templateId ? Number(templateId) : undefined,
      discount_id: discount ? Number(discount) : undefined,
      tax_rule_id: tax ? Number(tax) : undefined,
      expires_on: expires || undefined,
      payment_terms: terms || undefined,
      payment_due_days: Number(dueDays),
      lines,
    });
  };
  return (
    <Modal
      open={open}
      onClose={close}
      title="Create quotation"
      description="Build a precise commercial proposal."
      size="lg"
    >
      <form onSubmit={save}>
        <div className="form-grid">
          <Field label="Template (optional)">
            <Select
              value={templateId}
              onChange={(e) => handleTemplateChange(e.target.value)}
            >
              <option value="">Start from scratch</option>
              {templates.data?.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} ({t.validity_days} days validity)
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Customer">
            <Select
              value={customer}
              onChange={(e) => setCustomer(e.target.value)}
              required
            >
              <option value="">Select customer</option>
              {users.data?.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name} · {u.email}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Subscription plan">
            <Select value={plan} onChange={(e) => setPlan(e.target.value)}>
              <option value="">Choose after product (optional)</option>
              {plans.data?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} · {money(p.amount)}
                </option>
              ))}
            </Select>
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
              value={dueDays}
              onChange={(e) => setDueDays(e.target.value)}
            />
          </Field>
          <Field
            label="Payment terms"
            children={
              <Textarea
                value={terms}
                onChange={(e) => setTerms(e.target.value)}
                placeholder="Payment due within 7 days…"
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
            Create quotation
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function QuoteDetail({
  quote,
  close,
  changing,
  update,
  convert,
}: {
  quote: Quotation | null;
  close: () => void;
  changing: boolean;
  update: (s: QuotationStatus) => void;
  convert: () => void;
}) {
  return (
    <Modal
      open={!!quote}
      onClose={close}
      title={quote?.quotation_number || "Quotation"}
      description="Commercial workflow and line details"
      size="lg"
    >
      {quote && (
        <>
          <div
            className="kpi-grid"
            style={{ gridTemplateColumns: "repeat(3,1fr)" }}
          >
            <div className="card section-body">
              <small>Status</small>
              <div style={{ marginTop: 8 }}>
                <StatusBadge value={quote.status} />
              </div>
            </div>
            <div className="card section-body">
              <small>Expires</small>
              <strong style={{ display: "block", marginTop: 8 }}>
                {shortDate(quote.expires_on)}
              </strong>
            </div>
            <div className="card section-body">
              <small>Value</small>
              <strong style={{ display: "block", marginTop: 8 }}>
                {money(
                  quote.lines.reduce(
                    (s, l) => s + l.quantity * Number(l.unit_price),
                    0,
                  ),
                )}
              </strong>
            </div>
          </div>
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
                {quote.lines.map((line, index) => (
                  <tr key={line.id || index}>
                    <td className="primary-cell">
                      <strong>{line.product_name}</strong>
                      <small>{line.variant_name || "Standard"}</small>
                    </td>
                    <td>{line.quantity}</td>
                    <td>{money(line.unit_price)}</td>
                    <td className="amount">
                      {money(line.quantity * Number(line.unit_price))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="form-actions">
            {quote.status === "draft" && (
              <Button loading={changing} onClick={() => update("quotation")}>
                Send as quotation
              </Button>
            )}
            {quote.status === "quotation" && (
              <Button loading={changing} onClick={() => update("confirmed")}>
                Mark confirmed
              </Button>
            )}
            {quote.status === "confirmed" && (
              <Button loading={changing} onClick={convert}>
                Convert to subscription
              </Button>
            )}
            {quote.status !== "closed" && (
              <Button
                variant="secondary"
                loading={changing}
                onClick={() => update("closed")}
              >
                Close quotation
              </Button>
            )}
          </div>
        </>
      )}
    </Modal>
  );
}
