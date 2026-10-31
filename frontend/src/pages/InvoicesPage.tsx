import { useMemo, useState, type FormEvent } from "react";
import {
  Elements,
  PaymentElement,
  useElements,
  useStripe,
} from "@stripe/react-stripe-js";
import { loadStripe } from "@stripe/stripe-js";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  Ban,
  CreditCard,
  Download,
  Mail,
  Play,
  ReceiptText,
  WalletCards,
} from "lucide-react";
import { toast } from "sonner";
import { financeApi, invoiceApi } from "@/api/services";
import { apiMessage } from "@/api/client";
import { useAuth } from "@/auth/useAuth";
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
import { money, shortDate, titleCase, today } from "@/lib/format";
import type { Invoice } from "@/api/types";

interface CheckoutData {
  client_secret: string;
  publishable_key: string;
}
export function InvoicesPage() {
  const { user } = useAuth();
  const internal = user?.role !== "customer";
  const client = useQueryClient();
  const [status, setStatus] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<Invoice | null>(null);
  const [checkout, setCheckout] = useState<CheckoutData | null>(null);
  const limit = 25;
  const query = useQuery({
    queryKey: ["invoices", status, from, to, offset],
    queryFn: () =>
      invoiceApi.list({
        invoice_status: status || undefined,
        from_date: from || undefined,
        to_date: to || undefined,
        offset,
        limit,
      }),
  });
  const send = useMutation({
    mutationFn: invoiceApi.send,
    onSuccess: () => toast.success("Invoice email queued"),
    onError: (e) => toast.error(apiMessage(e)),
  });
  const confirm = useMutation({
    mutationFn: invoiceApi.confirm,
    onSuccess: (v) => {
      toast.success("Invoice confirmed");
      setSelected(v);
      void client.invalidateQueries({ queryKey: ["invoices"] });
    },
    onError: (e) => toast.error(apiMessage(e)),
  });
  const voidInvoice = useMutation({
    mutationFn: invoiceApi.void,
    onSuccess: (v) => {
      toast.success("Invoice cancelled / voided");
      setSelected(v);
      void client.invalidateQueries({ queryKey: ["invoices"] });
      void client.invalidateQueries({ queryKey: ["finance"] });
    },
    onError: (e) => toast.error(apiMessage(e)),
  });
  const intent = useMutation({
    mutationFn: invoiceApi.paymentIntent,
    onSuccess: (data) => setCheckout(data as CheckoutData),
    onError: (e) => toast.error(apiMessage(e)),
  });
  const billing = useMutation({
    mutationFn: () => financeApi.runBilling(today()),
    onSuccess: (created) => {
      toast.success(
        created.length
          ? `${created.length} invoice(s) generated`
          : "Billing is up to date",
      );
      void client.invalidateQueries({ queryKey: ["invoices"] });
      void client.invalidateQueries({ queryKey: ["finance"] });
    },
    onError: (e) => toast.error(apiMessage(e)),
  });
  const download = async (invoice: Invoice) => {
    try {
      const blob = await invoiceApi.pdf(invoice.id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `invoice-${invoice.id}.pdf`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(apiMessage(e));
    }
  };
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
        eyebrow={internal ? "Billing & collections" : "Your billing"}
        title="Invoices & payments"
        description={
          internal
            ? "Track every receivable from draft through collection, with immutable billing snapshots."
            : "Review balances, download invoices and make secure payments."
        }
        action={
          user?.role === "admin" ? (
            <Button
              loading={billing.isPending}
              onClick={() => billing.mutate()}
            >
              <Play size={15} /> Run billing
            </Button>
          ) : undefined
        }
      />
      <div className="toolbar">
        <div className="toolbar__filters">
          <Input
            type="date"
            value={from}
            onChange={(e) => {
              setFrom(e.target.value);
              setOffset(0);
            }}
            aria-label="From date"
          />
          <Input
            type="date"
            value={to}
            onChange={(e) => {
              setTo(e.target.value);
              setOffset(0);
            }}
            aria-label="To date"
          />
        </div>
        <Select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setOffset(0);
          }}
        >
          <option value="">All statuses</option>
          {["draft", "confirmed", "issued", "paid", "overdue", "void"].map(
            (v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ),
          )}
        </Select>
      </div>
      <section className="card table-card">
        {query.data?.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Invoice</th>
                  <th>Customer</th>
                  <th>Billing period</th>
                  <th>Due</th>
                  <th>Status</th>
                  <th>Outstanding</th>
                  <th>Total</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {query.data.map((i) => (
                  <tr key={i.id}>
                    <td className="primary-cell">
                      <strong>INV-{String(i.id).padStart(5, "0")}</strong>
                      <small>Subscription #{i.subscription_id}</small>
                    </td>
                    <td className="primary-cell">
                      <strong>{i.customer_name_snapshot || "Customer"}</strong>
                      <small>
                        {i.customer_email_snapshot ||
                          `#${i.customer_id_snapshot}`}
                      </small>
                    </td>
                    <td>
                      {shortDate(i.period_start)} – {shortDate(i.period_end)}
                    </td>
                    <td>{shortDate(i.due_on)}</td>
                    <td>
                      <StatusBadge value={i.status} />
                    </td>
                    <td className="amount">{money(i.outstanding_balance)}</td>
                    <td className="amount">{money(i.amount)}</td>
                    <td className="table-actions">
                      <Button variant="ghost" onClick={() => setSelected(i)}>
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
            icon={ReceiptText}
            title="No invoices found"
            text="Adjust your filters or run billing when subscriptions become due."
          />
        )}
        <Pagination
          offset={offset}
          limit={limit}
          count={query.data?.length || 0}
          onChange={setOffset}
        />
      </section>
      <InvoiceDetail
        invoice={selected}
        internal={internal}
        admin={user?.role === "admin"}
        close={() => setSelected(null)}
        download={() => selected && void download(selected)}
        send={() => selected && send.mutate(selected.id)}
        confirm={() => selected && confirm.mutate(selected.id)}
        voidInvoice={() => selected && voidInvoice.mutate(selected.id)}
        pay={() => selected && intent.mutate(selected.id)}
        busy={send.isPending || confirm.isPending || intent.isPending || voidInvoice.isPending}
      />
      <CheckoutModal
        data={checkout}
        close={() => setCheckout(null)}
        complete={() => {
          setCheckout(null);
          setSelected(null);
          void client.invalidateQueries({ queryKey: ["invoices"] });
        }}
      />
    </>
  );
}

function InvoiceDetail({
  invoice,
  internal,
  admin,
  close,
  download,
  send,
  confirm,
  voidInvoice,
  pay,
  busy,
}: {
  invoice: Invoice | null;
  internal: boolean;
  admin: boolean;
  close: () => void;
  download: () => void;
  send: () => void;
  confirm: () => void;
  voidInvoice: () => void;
  pay: () => void;
  busy: boolean;
}) {
  const [recording, setRecording] = useState(false);
  const paymentsQuery = useQuery({
    queryKey: ["invoice-payments", invoice?.id],
    queryFn: () => (invoice ? invoiceApi.payments(invoice.id) : Promise.resolve([])),
    enabled: !!invoice,
  });

  if (!invoice) return null;
  if (recording)
    return (
      <PaymentForm
        invoice={invoice}
        close={() => setRecording(false)}
        complete={() => {
          setRecording(false);
          close();
        }}
      />
    );
  return (
    <Modal
      open
      title={`Invoice INV-${String(invoice.id).padStart(5, "0")}`}
      description={`${invoice.customer_name_snapshot || "Customer"} · Due ${shortDate(invoice.due_on)}`}
      onClose={close}
      size="lg"
    >
      <div className="content-grid">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Item</th>
                <th>Qty</th>
                <th>Unit price</th>
                <th>Total</th>
              </tr>
            </thead>
            <tbody>
              {invoice.lines.map((line) => (
                <tr key={line.id}>
                  <td className="primary-cell">
                    <strong>{line.product_name}</strong>
                    <small>{line.variant_name || "Standard"}</small>
                  </td>
                  <td>{line.quantity}</td>
                  <td>{money(line.unit_price)}</td>
                  <td className="amount">{money(line.line_total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="card section-body metric-list">
          <DetailRow
            label="Status"
            value={<StatusBadge value={invoice.status} />}
          />
          <DetailRow label="Subtotal" value={money(invoice.subtotal)} />
          <DetailRow
            label="Discount"
            value={`− ${money(invoice.discount_amount)}`}
          />
          <DetailRow label="Tax" value={money(invoice.tax_amount)} />
          <DetailRow label="Total" value={money(invoice.amount)} />
          <DetailRow
            label="Outstanding"
            value={money(invoice.outstanding_balance)}
          />
        </div>
      </div>
      {paymentsQuery.data && paymentsQuery.data.length > 0 && (
        <div style={{ marginTop: 20 }}>
          <h4 style={{ fontSize: "0.85rem", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-muted)", marginBottom: 8 }}>
            Payment History ({paymentsQuery.data.length})
          </h4>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Method</th>
                  <th>Reference</th>
                  <th>Note</th>
                  <th style={{ textAlign: "right" }}>Amount</th>
                </tr>
              </thead>
              <tbody>
                {paymentsQuery.data.map((p) => (
                  <tr key={p.id}>
                    <td>{shortDate(p.received_on)}</td>
                    <td>{titleCase(p.method)}</td>
                    <td>{p.gateway_reference || "—"}</td>
                    <td>{p.note || "—"}</td>
                    <td className="amount" style={{ textAlign: "right" }}>{money(p.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      <div className="form-actions">
        <Button variant="secondary" onClick={download}>
          <Download size={15} />
          Download PDF
        </Button>
        {internal && (
          <Button variant="secondary" loading={busy} onClick={send}>
            <Mail size={15} />
            Send
          </Button>
        )}
        {internal && invoice.status === "draft" && (
          <Button loading={busy} onClick={confirm}>
            Confirm
          </Button>
        )}
        {internal && Number(invoice.outstanding_balance) > 0 && (
          <Button variant="secondary" onClick={() => setRecording(true)}>
            <WalletCards size={15} />
            Record payment
          </Button>
        )}
        {admin && !["paid", "void"].includes(invoice.status) && (
          <Button variant="danger" loading={busy} onClick={voidInvoice}>
            <Ban size={15} />
            Void invoice
          </Button>
        )}
        {Number(invoice.outstanding_balance) > 0 &&
          ["confirmed", "issued", "overdue"].includes(invoice.status) && (
            <Button loading={busy} onClick={pay}>
              <CreditCard size={15} />
              Pay securely
            </Button>
          )}
      </div>
    </Modal>
  );
}

function PaymentForm({
  invoice,
  close,
  complete,
}: {
  invoice: Invoice | null;
  close: () => void;
  complete: () => void;
}) {
  const client = useQueryClient();
  const [amount, setAmount] = useState(
    String(invoice?.outstanding_balance || ""),
  );
  const [method, setMethod] = useState("bank_transfer");
  const [reference, setReference] = useState("");
  const [note, setNote] = useState("");
  const [date, setDate] = useState(today());
  const mutation = useMutation({
    mutationFn: (payload: object) =>
      invoiceApi.recordPayment(invoice!.id, payload),
    onSuccess: () => {
      toast.success("Payment recorded");
      void client.invalidateQueries({ queryKey: ["invoices"] });
      complete();
    },
    onError: (e) => toast.error(apiMessage(e)),
  });
  if (!invoice) return null;
  const save = (e: FormEvent) => {
    e.preventDefault();
    mutation.mutate({
      amount: Number(amount),
      method,
      gateway_reference: reference || null,
      received_on: date,
      status: "success",
      note: note || null,
    });
  };
  return (
    <Modal
      open
      title="Record payment"
      description={`Apply a payment to INV-${String(invoice.id).padStart(5, "0")}`}
      onClose={close}
    >
      <form onSubmit={save}>
        <div className="form-grid">
          <Field label="Amount">
            <Input
              type="number"
              min="0.01"
              max={Number(invoice.outstanding_balance)}
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              required
            />
          </Field>
          <Field label="Payment method">
            <Select value={method} onChange={(e) => setMethod(e.target.value)}>
              <option value="bank_transfer">Bank transfer</option>
              <option value="cash">Cash</option>
              <option value="card">Card</option>
              <option value="cheque">Cheque</option>
            </Select>
          </Field>
          <Field label="Received on">
            <Input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              required
            />
          </Field>
          <Field label="Reference">
            <Input
              value={reference}
              onChange={(e) => setReference(e.target.value)}
              placeholder="Transaction or cheque reference"
            />
          </Field>
          <Field
            label="Internal note"
            children={
              <Textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
            }
          />
        </div>
        <div className="form-actions">
          <Button type="button" variant="secondary" onClick={close}>
            Cancel
          </Button>
          <Button type="submit" loading={mutation.isPending}>
            Record payment
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function CheckoutModal({
  data,
  close,
  complete,
}: {
  data: CheckoutData | null;
  close: () => void;
  complete: () => void;
}) {
  const stripe = useMemo(
    () => (data?.publishable_key ? loadStripe(data.publishable_key) : null),
    [data?.publishable_key],
  );
  return (
    <Modal
      open={!!data}
      onClose={close}
      title="Secure card payment"
      description="Your card details are securely handled by Stripe."
    >
      {data && stripe && (
        <Elements
          stripe={stripe}
          options={{
            clientSecret: data.client_secret,
            appearance: {
              theme: "stripe",
              variables: {
                colorPrimary: "#2f6bff",
                borderRadius: "9px",
                fontFamily: "DM Sans, sans-serif",
              },
            },
          }}
        >
          <CheckoutForm complete={complete} />
        </Elements>
      )}
    </Modal>
  );
}
function CheckoutForm({ complete }: { complete: () => void }) {
  const stripe = useStripe();
  const elements = useElements();
  const [loading, setLoading] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!stripe || !elements) return;
    setLoading(true);
    const result = await stripe.confirmPayment({
      elements,
      confirmParams: { return_url: window.location.href },
      redirect: "if_required",
    });
    if (result.error)
      toast.error(result.error.message || "Payment could not be completed");
    else {
      toast.success("Payment submitted successfully");
      complete();
    }
    setLoading(false);
  };
  return (
    <form onSubmit={submit}>
      <PaymentElement />
      <div className="form-actions">
        <Button type="submit" loading={loading} disabled={!stripe}>
          Pay invoice
        </Button>
      </div>
    </form>
  );
}
