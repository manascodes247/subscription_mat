import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  Activity,
  ArrowUpRight,
  BadgeDollarSign,
  CircleDollarSign,
  Clock3,
  FilePlus2,
  FileText,
  Play,
  ReceiptText,
  RefreshCcw,
  Users,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { financeApi, invoiceApi, subscriptionApi } from "@/api/services";
import { useAuth } from "@/auth/useAuth";
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  KpiCard,
  LoadingState,
  PageHeader,
  StatusBadge,
} from "@/components/ui";
import { money, shortDate } from "@/lib/format";

const chart = [
  { name: "May", value: 12400 },
  { name: "Jun", value: 15750 },
  { name: "Jul", value: 14800 },
  { name: "Aug", value: 18900 },
  { name: "Sep", value: 21300 },
  { name: "Oct", value: 24750 },
];
export function DashboardPage() {
  const { user } = useAuth();
  const internal = user?.role !== "customer";
  const finance = useQuery({
    queryKey: ["finance"],
    queryFn: financeApi.dashboard,
    enabled: internal,
  });
  const invoices = useQuery({
    queryKey: ["invoices", "recent"],
    queryFn: () => invoiceApi.list({ limit: 5 }),
  });
  const subscriptions = useQuery({
    queryKey: ["subscriptions", "recent"],
    queryFn: () => subscriptionApi.list({ limit: 5 }),
  });
  if (
    invoices.isLoading ||
    subscriptions.isLoading ||
    (internal && finance.isLoading)
  )
    return <LoadingState />;
  if (
    invoices.isError ||
    subscriptions.isError ||
    (internal && finance.isError)
  )
    return (
      <ErrorState
        message="Check that the backend is running and try again."
        retry={() => {
          void invoices.refetch();
          void subscriptions.refetch();
          void finance.refetch();
        }}
      />
    );
  const active = internal
    ? finance.data?.active_subscriptions || 0
    : subscriptions.data?.filter((item) => item.status === "active").length ||
      0;
  return (
    <>
      <PageHeader
        eyebrow={internal ? "Revenue command center" : "Customer portal"}
        title={`Good ${new Date().getHours() < 12 ? "morning" : "afternoon"}, ${user?.full_name.split(" ")[0]}`}
        description={
          internal
            ? "Here’s the operational pulse of your subscription business."
            : "Your subscriptions, invoices and upcoming billing—all in one place."
        }
        action={
          internal ? (
            <>
              <Button variant="secondary">
                <Activity size={16} />
                View reports
              </Button>
              <Link to="/quotations">
                <Button>
                  <FilePlus2 size={16} />
                  New quotation
                </Button>
              </Link>
            </>
          ) : undefined
        }
      />
      <div className="kpi-grid">
        <KpiCard
          label="Active subscriptions"
          value={String(active)}
          note="Currently generating recurring revenue"
          icon={RefreshCcw}
          tone="blue"
        />
        <KpiCard
          label={internal ? "Total revenue" : "Total invoiced"}
          value={money(
            internal
              ? finance.data?.revenue
              : invoices.data?.reduce(
                  (sum, item) => sum + Number(item.amount),
                  0,
                ),
          )}
          note={
            internal
              ? "Confirmed and paid invoices"
              : "Across your visible invoices"
          }
          icon={CircleDollarSign}
          tone="teal"
        />
        <KpiCard
          label={internal ? "Payments collected" : "Outstanding"}
          value={money(
            internal
              ? finance.data?.payments
              : invoices.data?.reduce(
                  (sum, item) => sum + Number(item.outstanding_balance),
                  0,
                ),
          )}
          note={
            internal ? "Successful payment records" : "Amount currently due"
          }
          icon={BadgeDollarSign}
          tone="purple"
        />
        <KpiCard
          label="Overdue invoices"
          value={String(
            internal
              ? finance.data?.overdue_invoices || 0
              : invoices.data?.filter((item) => item.status === "overdue")
                  .length || 0,
          )}
          note="Requires collection attention"
          icon={Clock3}
          tone="amber"
        />
      </div>
      <div className="content-grid">
        <Card>
          <div className="section-header">
            <div>
              <h2>{internal ? "Revenue performance" : "Invoice activity"}</h2>
              <p>
                {internal
                  ? "Six-month recurring revenue trend"
                  : "Your five most recent invoices"}
              </p>
            </div>
            <Link className="text-link" to="/invoices">
              View all <ArrowUpRight size={12} />
            </Link>
          </div>
          <div className="section-body">
            {internal ? (
              <div className="chart-wrap">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chart}>
                    <defs>
                      <linearGradient id="revenue" x1="0" y1="0" x2="0" y2="1">
                        <stop
                          offset="5%"
                          stopColor="#2f6bff"
                          stopOpacity={0.25}
                        />
                        <stop
                          offset="95%"
                          stopColor="#2f6bff"
                          stopOpacity={0}
                        />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="#edf1f6" vertical={false} />
                    <XAxis
                      dataKey="name"
                      axisLine={false}
                      tickLine={false}
                      tick={{ fontSize: 10, fill: "#8490a5" }}
                    />
                    <YAxis
                      axisLine={false}
                      tickLine={false}
                      tick={{ fontSize: 10, fill: "#8490a5" }}
                      tickFormatter={(value) => `$${value / 1000}k`}
                    />
                    <Tooltip formatter={(value) => money(Number(value))} />
                    <Area
                      type="monotone"
                      dataKey="value"
                      stroke="#2f6bff"
                      strokeWidth={2.5}
                      fill="url(#revenue)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <InvoiceActivity invoices={invoices.data || []} />
            )}
          </div>
        </Card>
        <div style={{ display: "grid", gap: 18, alignContent: "start" }}>
          <Card>
            <div className="section-header">
              <div>
                <h2>Quick actions</h2>
                <p>Common workspace tasks</p>
              </div>
            </div>
            <div className="section-body quick-actions">
              {internal ? (
                <>
                  <Link to="/quotations" className="quick-action">
                    <FileText size={19} />
                    <strong>Create quotation</strong>
                    <small>Prepare a commercial offer</small>
                  </Link>
                  <Link to="/customers" className="quick-action">
                    <Users size={19} />
                    <strong>Add customer</strong>
                    <small>Grow your account base</small>
                  </Link>
                  <Link to="/subscriptions" className="quick-action">
                    <RefreshCcw size={19} />
                    <strong>Subscriptions</strong>
                    <small>Review active agreements</small>
                  </Link>
                  <Link to="/invoices" className="quick-action">
                    <Play size={19} />
                    <strong>Collections</strong>
                    <small>Track outstanding balances</small>
                  </Link>
                </>
              ) : (
                <>
                  <Link to="/subscriptions" className="quick-action">
                    <RefreshCcw size={19} />
                    <strong>My subscriptions</strong>
                    <small>Review your agreements</small>
                  </Link>
                  <Link to="/invoices" className="quick-action">
                    <ReceiptText size={19} />
                    <strong>My invoices</strong>
                    <small>View balances and PDFs</small>
                  </Link>
                </>
              )}
            </div>
          </Card>
        </div>
      </div>
      {internal && (
        <Card className="table-card">
          <div className="section-header">
            <div>
              <h2>Recent invoices</h2>
              <p>Latest billing activity across customers</p>
            </div>
            <Link className="text-link" to="/invoices">
              View all
            </Link>
          </div>
          <InvoiceActivity invoices={invoices.data || []} />
        </Card>
      )}
    </>
  );
}
function InvoiceActivity({
  invoices,
}: {
  invoices: Awaited<ReturnType<typeof invoiceApi.list>>;
}) {
  if (!invoices.length)
    return (
      <EmptyState
        title="No invoices yet"
        text="Invoices will appear here after the first billing run."
      />
    );
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Invoice</th>
            <th>Customer</th>
            <th>Due date</th>
            <th>Status</th>
            <th style={{ textAlign: "right" }}>Amount</th>
          </tr>
        </thead>
        <tbody>
          {invoices.map((invoice) => (
            <tr key={invoice.id}>
              <td className="primary-cell">
                <strong>INV-{String(invoice.id).padStart(5, "0")}</strong>
                <small>
                  {invoice.period_start} – {invoice.period_end}
                </small>
              </td>
              <td>
                {invoice.customer_name_snapshot ||
                  invoice.customer_email_snapshot ||
                  "Customer"}
              </td>
              <td>{shortDate(invoice.due_on)}</td>
              <td>
                <StatusBadge value={invoice.status} />
              </td>
              <td className="amount" style={{ textAlign: "right" }}>
                {money(invoice.amount)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
