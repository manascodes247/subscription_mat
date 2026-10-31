import type { Role } from "@/api/types";

const currency = import.meta.env.VITE_CURRENCY || "USD";
export const money = (value?: number | string | null) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(Number(value || 0));
export const shortDate = (value?: string | null) =>
  value
    ? new Intl.DateTimeFormat("en-US", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      }).format(new Date(`${value}T00:00:00`))
    : "—";
export const titleCase = (value?: string | null) =>
  value
    ? value
        .replaceAll("_", " ")
        .replace(/\b\w/g, (letter) => letter.toUpperCase())
    : "—";
export const initials = (name?: string) =>
  (name || "User")
    .split(" ")
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
export const today = () => new Date().toISOString().slice(0, 10);
export const roleLabel: Record<Role, string> = {
  admin: "Administrator",
  staff: "Operations staff",
  customer: "Customer",
};
