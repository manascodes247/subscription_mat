import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Box, Layers3, Plus, Settings2 } from "lucide-react";
import { toast } from "sonner";
import { catalogApi } from "@/api/services";
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
  SearchBox,
  Select,
  Textarea,
} from "@/components/ui";
import { money, titleCase } from "@/lib/format";
import type { BillingInterval, Product } from "@/api/types";

export function CatalogPage() {
  const { user } = useAuth();
  const client = useQueryClient();
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<Product | null>(null);
  const products = useQuery({
    queryKey: ["products", true],
    queryFn: () => catalogApi.products(true),
  });
  const create = useMutation({
    mutationFn: catalogApi.createProduct,
    onSuccess: (value) => {
      toast.success("Product created");
      setOpen(false);
      void client.invalidateQueries({ queryKey: ["products"] });
      setSelected(value);
    },
    onError: (e) => toast.error(apiMessage(e)),
  });
  const visible = useMemo(
    () =>
      (products.data || []).filter((p) =>
        `${p.name} ${p.product_type || ""}`
          .toLowerCase()
          .includes(search.toLowerCase()),
      ),
    [products.data, search],
  );
  if (products.isLoading) return <LoadingState />;
  if (products.isError)
    return (
      <ErrorState
        message={apiMessage(products.error)}
        retry={() => void products.refetch()}
      />
    );
  return (
    <>
      <PageHeader
        eyebrow="Commercial catalog"
        title="Products & plans"
        description="Shape your recurring offers with products, priced variants and flexible billing plans."
        action={
          user?.role === "admin" ? (
            <Button onClick={() => setOpen(true)}>
              <Plus size={16} />
              New product
            </Button>
          ) : undefined
        }
      />
      <div className="toolbar">
        <SearchBox
          value={search}
          onChange={setSearch}
          placeholder="Search product catalog…"
        />
        <div className="toolbar__filters">
          <Badge tone="info">
            {visible.filter((p) => p.active).length} active products
          </Badge>
        </div>
      </div>
      <section className="card table-card">
        {visible.length ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Product</th>
                  <th>Type</th>
                  <th>Sales price</th>
                  <th>Cost</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {visible.map((product) => (
                  <tr key={product.id}>
                    <td className="primary-cell">
                      <strong>{product.name}</strong>
                      <small>{product.description || "No description"}</small>
                    </td>
                    <td>{product.product_type || "Service"}</td>
                    <td className="amount">{money(product.sales_price)}</td>
                    <td>{money(product.cost_price)}</td>
                    <td>
                      <Badge tone={product.active ? "success" : "neutral"}>
                        {product.active ? "Active" : "Inactive"}
                      </Badge>
                    </td>
                    <td className="table-actions">
                      <Button
                        variant="ghost"
                        onClick={() => setSelected(product)}
                      >
                        Configure <Settings2 size={14} />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon={Box}
            title="No products yet"
            text="Create your first recurring product to start building plans."
          />
        )}
      </section>
      <ProductForm
        open={open}
        loading={create.isPending}
        onClose={() => setOpen(false)}
        onSubmit={(v) => create.mutate(v)}
      />
      {selected && (
        <ProductDrawer
          product={selected}
          admin={user?.role === "admin"}
          onClose={() => setSelected(null)}
        />
      )}
    </>
  );
}

function ProductForm({
  open,
  loading,
  onClose,
  onSubmit,
}: {
  open: boolean;
  loading: boolean;
  onClose: () => void;
  onSubmit: (v: {
    name: string;
    description?: string;
    product_type?: string;
    sales_price?: number;
    cost_price?: number;
    notes?: string;
  }) => void;
}) {
  const [name, setName] = useState("");
  const [type, setType] = useState("service");
  const [description, setDescription] = useState("");
  const [sales, setSales] = useState("");
  const [cost, setCost] = useState("");
  const [notes, setNotes] = useState("");
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Create product"
      description="Add the commercial foundation for variants and recurring plans."
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit({
            name,
            product_type: type,
            description,
            sales_price: sales ? Number(sales) : undefined,
            cost_price: cost ? Number(cost) : undefined,
            notes,
          });
        }}
      >
        <div className="form-grid">
          <Field label="Product name">
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </Field>
          <Field label="Product type">
            <Input
              value={type}
              onChange={(e) => setType(e.target.value)}
              placeholder="Service, software, membership…"
            />
          </Field>
          <Field label="Sales price">
            <Input
              type="number"
              min="0"
              step="0.01"
              value={sales}
              onChange={(e) => setSales(e.target.value)}
            />
          </Field>
          <Field label="Cost price">
            <Input
              type="number"
              min="0"
              step="0.01"
              value={cost}
              onChange={(e) => setCost(e.target.value)}
            />
          </Field>
          <Field
            label="Description"
            children={
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            }
          />
          <Field
            label="Internal notes"
            children={
              <Textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            }
          />
        </div>
        <div className="form-actions">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" loading={loading}>
            Create product
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function ProductDrawer({
  product,
  admin,
  onClose,
}: {
  product: Product;
  admin: boolean;
  onClose: () => void;
}) {
  const client = useQueryClient();
  const [tab, setTab] = useState<"plans" | "variants">("plans");
  const [form, setForm] = useState(false);
  const plans = useQuery({
    queryKey: ["plans", product.id],
    queryFn: () => catalogApi.plans(product.id, true),
  });
  const variants = useQuery({
    queryKey: ["variants", product.id],
    queryFn: () => catalogApi.variants(product.id, true),
  });
  const addVariant = useMutation({
    mutationFn: (v: { name: string; additional_price: number }) =>
      catalogApi.createVariant(product.id, v),
    onSuccess: () => {
      toast.success("Variant added");
      setForm(false);
      void client.invalidateQueries({ queryKey: ["variants", product.id] });
    },
    onError: (e) => toast.error(apiMessage(e)),
  });
  const addPlan = useMutation({
    mutationFn: (v: object) =>
      catalogApi.createPlan({ ...v, product_id: product.id }),
    onSuccess: () => {
      toast.success("Plan added");
      setForm(false);
      void client.invalidateQueries({ queryKey: ["plans", product.id] });
    },
    onError: (e) => toast.error(apiMessage(e)),
  });
  return (
    <Modal
      open
      title={product.name}
      description={product.description || "Product configuration"}
      onClose={onClose}
      size="lg"
    >
      <div className="toolbar">
        <div className="toolbar__filters">
          <Button
            variant={tab === "plans" ? "primary" : "secondary"}
            onClick={() => {
              setTab("plans");
              setForm(false);
            }}
          >
            <Layers3 size={15} />
            Plans
          </Button>
          <Button
            variant={tab === "variants" ? "primary" : "secondary"}
            onClick={() => {
              setTab("variants");
              setForm(false);
            }}
          >
            <Box size={15} />
            Variants
          </Button>
        </div>
        {admin && (
          <Button variant="secondary" onClick={() => setForm(!form)}>
            <Plus size={15} />
            Add {tab === "plans" ? "plan" : "variant"}
          </Button>
        )}
      </div>
      {form &&
        (tab === "variants" ? (
          <VariantForm
            loading={addVariant.isPending}
            submit={(v) => addVariant.mutate(v)}
          />
        ) : (
          <PlanForm
            loading={addPlan.isPending}
            submit={(v) => addPlan.mutate(v)}
          />
        ))}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              {tab === "plans" ? (
                <>
                  <th>Plan</th>
                  <th>Interval</th>
                  <th>Minimum</th>
                  <th>Rules</th>
                  <th>Price</th>
                </>
              ) : (
                <>
                  <th>Variant</th>
                  <th>Additional price</th>
                  <th>Status</th>
                </>
              )}
            </tr>
          </thead>
          <tbody>
            {tab === "plans"
              ? (plans.data || []).map((p) => (
                  <tr key={p.id}>
                    <td className="primary-cell">
                      <strong>{p.name}</strong>
                      <small>
                        {shortAvailability(p.available_from, p.available_until)}
                      </small>
                    </td>
                    <td>
                      {titleCase(
                        p.billing_interval || `${p.interval_days} days`,
                      )}
                    </td>
                    <td>{p.minimum_quantity}</td>
                    <td>
                      {[
                        p.allow_pause && "Pause",
                        p.allow_renew && "Renew",
                        p.allow_early_close && "Early close",
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </td>
                    <td className="amount">{money(p.amount)}</td>
                  </tr>
                ))
              : (variants.data || []).map((v) => (
                  <tr key={v.id}>
                    <td className="primary-cell">
                      <strong>{v.name}</strong>
                      <small>Variant #{v.id}</small>
                    </td>
                    <td className="amount">+{money(v.additional_price)}</td>
                    <td>
                      <Badge tone={v.active ? "success" : "neutral"}>
                        {v.active ? "Active" : "Inactive"}
                      </Badge>
                    </td>
                  </tr>
                ))}
          </tbody>
        </table>
      </div>
    </Modal>
  );
}
const shortAvailability = (from?: string, to?: string) =>
  from || to
    ? `${from || "Any time"} – ${to || "Open ended"}`
    : "Always available";
function VariantForm({
  loading,
  submit,
}: {
  loading: boolean;
  submit: (v: { name: string; additional_price: number }) => void;
}) {
  const [name, setName] = useState("");
  const [price, setPrice] = useState("");
  return (
    <form
      className="card section-body"
      onSubmit={(e) => {
        e.preventDefault();
        submit({ name, additional_price: Number(price || 0) });
      }}
    >
      <div className="form-grid">
        <Field label="Variant name">
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </Field>
        <Field label="Additional price">
          <Input
            type="number"
            min="0"
            step="0.01"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            required
          />
        </Field>
      </div>
      <div className="form-actions">
        <Button type="submit" loading={loading}>
          Save variant
        </Button>
      </div>
    </form>
  );
}
function PlanForm({
  loading,
  submit,
}: {
  loading: boolean;
  submit: (v: object) => void;
}) {
  const [name, setName] = useState("");
  const [amount, setAmount] = useState("");
  const [interval, setInterval] = useState<BillingInterval>("monthly");
  const [min, setMin] = useState("1");
  const [from, setFrom] = useState("");
  const [until, setUntil] = useState("");
  const [autoClose, setAutoClose] = useState(false);
  const [allowEarlyClose, setAllowEarlyClose] = useState(true);
  const [allowPause, setAllowPause] = useState(true);
  const [allowRenew, setAllowRenew] = useState(true);

  return (
    <form
      className="card section-body"
      onSubmit={(e) => {
        e.preventDefault();
        submit({
          name,
          amount: Number(amount),
          billing_interval: interval,
          minimum_quantity: Number(min),
          available_from: from || null,
          available_until: until || null,
          auto_close_on_end: autoClose,
          allow_early_close: allowEarlyClose,
          allow_pause: allowPause,
          allow_renew: allowRenew,
        });
      }}
    >
      <div className="form-grid">
        <Field label="Plan name">
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </Field>
        <Field label="Billing interval">
          <Select
            value={interval}
            onChange={(e) => setInterval(e.target.value as BillingInterval)}
          >
            {["daily", "weekly", "monthly", "yearly"].map((v) => (
              <option key={v} value={v}>
                {titleCase(v)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Recurring amount">
          <Input
            type="number"
            min="0.01"
            step="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            required
          />
        </Field>
        <Field label="Minimum quantity">
          <Input
            type="number"
            min="1"
            value={min}
            onChange={(e) => setMin(e.target.value)}
            required
          />
        </Field>
        <Field label="Available from">
          <Input
            type="date"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
          />
        </Field>
        <Field label="Available until">
          <Input
            type="date"
            value={until}
            onChange={(e) => setUntil(e.target.value)}
          />
        </Field>
      </div>
      <div style={{ marginTop: 14, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 10 }}>
        <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.875rem", cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={autoClose}
            onChange={(e) => setAutoClose(e.target.checked)}
          />
          Auto-close when expired
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.875rem", cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={allowEarlyClose}
            onChange={(e) => setAllowEarlyClose(e.target.checked)}
          />
          Allow early close
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.875rem", cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={allowPause}
            onChange={(e) => setAllowPause(e.target.checked)}
          />
          Allow pause / resume
        </label>
        <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: "0.875rem", cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={allowRenew}
            onChange={(e) => setAllowRenew(e.target.checked)}
          />
          Allow renewal
        </label>
      </div>
      <div className="form-actions" style={{ marginTop: 16 }}>
        <Button type="submit" loading={loading}>
          Save plan
        </Button>
      </div>
    </form>
  );
}
