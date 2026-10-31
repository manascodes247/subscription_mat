import { Plus, Trash2 } from "lucide-react";
import type { CommercialLine, Product } from "@/api/types";
import { Button, Field, Input, Select } from "./ui";
import { money } from "@/lib/format";

type DraftLine = Omit<CommercialLine, "id">;
export function CommercialLines({
  lines,
  products,
  onChange,
}: {
  lines: DraftLine[];
  products: Product[];
  onChange: (lines: DraftLine[]) => void;
}) {
  const update = (index: number, patch: Partial<DraftLine>) =>
    onChange(
      lines.map((line, lineIndex) =>
        lineIndex === index ? { ...line, ...patch } : line,
      ),
    );
  const add = () =>
    onChange([...lines, { product_name: "", quantity: 1, unit_price: 0 }]);
  const remove = (index: number) =>
    onChange(lines.filter((_, lineIndex) => lineIndex !== index));
  return (
    <div style={{ display: "grid", gap: 12 }}>
      <div className="section-header" style={{ padding: "0 0 10px" }}>
        <div>
          <h2>Commercial lines</h2>
          <p>Products, quantities and agreed unit prices.</p>
        </div>
        <Button type="button" variant="secondary" onClick={add}>
          <Plus size={14} />
          Add line
        </Button>
      </div>
      {lines.map((line, index) => (
        <div
          className="card section-body"
          key={index}
          style={{ position: "relative" }}
        >
          <div className="form-grid">
            <Field label="Product">
              <Select
                value={line.product_id || ""}
                onChange={(event) => {
                  const product = products.find(
                    (item) => item.id === Number(event.target.value),
                  );
                  update(index, {
                    product_id: product?.id,
                    product_name: product?.name || "",
                    unit_price: Number(product?.sales_price || 0),
                  });
                }}
                required
              >
                <option value="">Select product</option>
                {products
                  .filter((item) => item.active)
                  .map((product) => (
                    <option value={product.id} key={product.id}>
                      {product.name}
                    </option>
                  ))}
              </Select>
            </Field>
            <Field label="Line description">
              <Input
                value={line.product_name}
                onChange={(event) =>
                  update(index, { product_name: event.target.value })
                }
                required
              />
            </Field>
            <Field label="Quantity">
              <Input
                type="number"
                min="1"
                value={line.quantity}
                onChange={(event) =>
                  update(index, { quantity: Number(event.target.value) })
                }
                required
              />
            </Field>
            <Field label="Unit price">
              <Input
                type="number"
                min="0"
                step="0.01"
                value={line.unit_price}
                onChange={(event) =>
                  update(index, { unit_price: Number(event.target.value) })
                }
                required
              />
            </Field>
          </div>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginTop: 12,
              alignItems: "center",
            }}
          >
            <span className="amount">
              Line total: {money(line.quantity * line.unit_price)}
            </span>
            {lines.length > 1 && (
              <Button
                type="button"
                variant="ghost"
                onClick={() => remove(index)}
              >
                <Trash2 size={14} />
                Remove
              </Button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
