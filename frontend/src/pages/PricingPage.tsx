import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BadgePercent, Plus, ReceiptText } from "lucide-react";
import { toast } from "sonner";
import { catalogApi, pricingApi } from "@/api/services";
import { apiMessage } from "@/api/client";
import { useAuth } from "@/auth/useAuth";
import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  Field,
  Input,
  LoadingState,
  Modal,
  PageHeader,
  Select,
} from "@/components/ui";
import { money, shortDate, titleCase } from "@/lib/format";

export function PricingPage() {
  const { user } = useAuth();
  const client = useQueryClient();
  const [tab, setTab] = useState<"discounts" | "taxes">("discounts");
  const [open, setOpen] = useState(false);
  const discounts = useQuery({
    queryKey: ["discounts"],
    queryFn: () => pricingApi.discounts(true),
  });
  const taxes = useQuery({
    queryKey: ["taxes"],
    queryFn: () => pricingApi.taxes(true),
  });
  const createDiscount = useMutation({
    mutationFn: pricingApi.createDiscount,
    onSuccess: () => {
      toast.success("Discount created");
      setOpen(false);
      void client.invalidateQueries({ queryKey: ["discounts"] });
    },
    onError: (e) => toast.error(apiMessage(e)),
  });
  const createTax = useMutation({
    mutationFn: pricingApi.createTax,
    onSuccess: () => {
      toast.success("Tax rule created");
      setOpen(false);
      void client.invalidateQueries({ queryKey: ["taxes"] });
    },
    onError: (e) => toast.error(apiMessage(e)),
  });
  if (discounts.isLoading || taxes.isLoading) return <LoadingState />;
  if (discounts.isError || taxes.isError)
    return (
      <ErrorState
        message="Pricing rules could not be loaded."
        retry={() => {
          void discounts.refetch();
          void taxes.refetch();
        }}
      />
    );
  return (
    <>
      <PageHeader
        eyebrow="Revenue configuration"
        title="Pricing rules"
        description="Control promotional eligibility and tax calculation with auditable rules."
        action={
          user?.role === "admin" ? (
            <Button onClick={() => setOpen(true)}>
              <Plus size={16} />
              New {tab === "discounts" ? "discount" : "tax rule"}
            </Button>
          ) : undefined
        }
      />
      <div className="toolbar">
        <div className="toolbar__filters">
          <Button
            variant={tab === "discounts" ? "primary" : "secondary"}
            onClick={() => setTab("discounts")}
          >
            <BadgePercent size={15} />
            Discounts
          </Button>
          <Button
            variant={tab === "taxes" ? "primary" : "secondary"}
            onClick={() => setTab("taxes")}
          >
            <ReceiptText size={15} />
            Tax rules
          </Button>
        </div>
      </div>
      <section className="card table-card">
        {tab === "discounts" ? (
          discounts.data?.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Code</th>
                    <th>Value</th>
                    <th>Eligibility</th>
                    <th>Validity</th>
                    <th>Usage</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {discounts.data.map((d) => (
                    <tr key={d.id}>
                      <td className="primary-cell">
                        <strong>{d.code}</strong>
                        <small>{titleCase(d.discount_type)}</small>
                      </td>
                      <td className="amount">
                        {d.discount_type === "percentage"
                          ? `${d.value}%`
                          : money(d.value)}
                      </td>
                      <td>
                        {d.minimum_purchase
                          ? `Min. ${money(d.minimum_purchase)}`
                          : d.minimum_quantity
                            ? `Min. ${d.minimum_quantity} units`
                            : "No minimum"}
                      </td>
                      <td>
                        {shortDate(d.starts_on)} – {shortDate(d.ends_on)}
                      </td>
                      <td>
                        {d.times_used}
                        {d.usage_limit ? ` / ${d.usage_limit}` : ""}
                      </td>
                      <td>
                        <Badge tone={d.active ? "success" : "neutral"}>
                          {d.active ? "Active" : "Inactive"}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              icon={BadgePercent}
              title="No discount rules"
              text="Create a discount with dates, minimums and usage controls."
            />
          )
        ) : taxes.data?.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Tax rule</th>
                  <th>Rate</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {taxes.data.map((t) => (
                  <tr key={t.id}>
                    <td className="primary-cell">
                      <strong>{t.name}</strong>
                      <small>Tax rule #{t.id}</small>
                    </td>
                    <td className="amount">{t.rate}%</td>
                    <td>
                      <Badge tone={t.active ? "success" : "neutral"}>
                        {t.active ? "Active" : "Inactive"}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon={ReceiptText}
            title="No tax rules"
            text="Create a tax rate to apply to quotations and invoices."
          />
        )}
      </section>
      {tab === "discounts" ? (
        <DiscountForm
          open={open}
          loading={createDiscount.isPending}
          close={() => setOpen(false)}
          submit={(v) => createDiscount.mutate(v)}
        />
      ) : (
        <TaxForm
          open={open}
          loading={createTax.isPending}
          close={() => setOpen(false)}
          submit={(v) => createTax.mutate(v)}
        />
      )}
    </>
  );
}

function DiscountForm({
  open,
  loading,
  close,
  submit,
}: {
  open: boolean;
  loading: boolean;
  close: () => void;
  submit: (v: object) => void;
}) {
  const [code, setCode] = useState("");
  const [type, setType] = useState("percentage");
  const [value, setValue] = useState("");
  const [productId, setProductId] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [minPurchase, setMinPurchase] = useState("");
  const [minQuantity, setMinQuantity] = useState("");
  const [limit, setLimit] = useState("");

  const products = useQuery({
    queryKey: ["products"],
    queryFn: () => catalogApi.products(),
    enabled: open,
  });

  const save = (e: FormEvent) => {
    e.preventDefault();
    submit({
      code,
      discount_type: type,
      value: Number(value),
      product_id: productId ? Number(productId) : null,
      starts_on: start || null,
      ends_on: end || null,
      minimum_purchase: minPurchase ? Number(minPurchase) : null,
      minimum_quantity: minQuantity ? Number(minQuantity) : null,
      usage_limit: limit ? Number(limit) : null,
    });
  };
  return (
    <Modal
      open={open}
      onClose={close}
      title="Create discount"
      description="Define the offer and its commercial guardrails."
    >
      <form onSubmit={save}>
        <div className="form-grid">
          <Field label="Applicable product">
            <Select
              value={productId}
              onChange={(e) => setProductId(e.target.value)}
            >
              <option value="">Whole subscription (all products)</option>
              {products.data?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Discount code">
            <Input
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              pattern="[A-Za-z0-9_-]+"
              required
            />
          </Field>
          <Field label="Discount type">
            <Select value={type} onChange={(e) => setType(e.target.value)}>
              <option value="percentage">Percentage</option>
              <option value="fixed">Fixed amount</option>
            </Select>
          </Field>
          <Field label={type === "percentage" ? "Percentage" : "Amount"}>
            <Input
              type="number"
              min="0.01"
              step="0.01"
              max={type === "percentage" ? 100 : undefined}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              required
            />
          </Field>
          <Field label="Usage limit">
            <Input
              type="number"
              min="1"
              value={limit}
              onChange={(e) => setLimit(e.target.value)}
            />
          </Field>
          <Field label="Starts on">
            <Input
              type="date"
              value={start}
              onChange={(e) => setStart(e.target.value)}
            />
          </Field>
          <Field label="Ends on">
            <Input
              type="date"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
            />
          </Field>
          <Field label="Minimum purchase">
            <Input
              type="number"
              min="0.01"
              step="0.01"
              value={minPurchase}
              onChange={(e) => setMinPurchase(e.target.value)}
            />
          </Field>
          <Field label="Minimum quantity">
            <Input
              type="number"
              min="1"
              value={minQuantity}
              onChange={(e) => setMinQuantity(e.target.value)}
            />
          </Field>
        </div>
        <div className="form-actions">
          <Button type="button" variant="secondary" onClick={close}>
            Cancel
          </Button>
          <Button type="submit" loading={loading}>
            Create discount
          </Button>
        </div>
      </form>
    </Modal>
  );
}
function TaxForm({
  open,
  loading,
  close,
  submit,
}: {
  open: boolean;
  loading: boolean;
  close: () => void;
  submit: (v: object) => void;
}) {
  const [name, setName] = useState("");
  const [rate, setRate] = useState("");
  return (
    <Modal
      open={open}
      onClose={close}
      title="Create tax rule"
      description="Set the percentage applied after eligible discounts."
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit({ name, rate: Number(rate) });
        }}
      >
        <div className="form-grid">
          <Field label="Tax name">
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="VAT, GST, Sales tax…"
              required
            />
          </Field>
          <Field label="Tax rate (%)">
            <Input
              type="number"
              min="0.01"
              max="100"
              step="0.01"
              value={rate}
              onChange={(e) => setRate(e.target.value)}
              required
            />
          </Field>
        </div>
        <div className="form-actions">
          <Button type="button" variant="secondary" onClick={close}>
            Cancel
          </Button>
          <Button type="submit" loading={loading}>
            Create tax rule
          </Button>
        </div>
      </form>
    </Modal>
  );
}
