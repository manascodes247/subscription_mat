import { lazy, Suspense, type ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { LoaderCircle } from "lucide-react";
import { useAuth } from "@/auth/useAuth";
import type { Role } from "@/api/types";
import { AppShell } from "@/layout/AppShell";
import { LoginPage } from "@/pages/LoginPage";
import { PasswordResetPage } from "@/pages/PasswordResetPage";

const DashboardPage = lazy(() =>
  import("@/pages/DashboardPage").then((module) => ({
    default: module.DashboardPage,
  })),
);
const PeoplePage = lazy(() =>
  import("@/pages/PeoplePage").then((module) => ({
    default: module.PeoplePage,
  })),
);
const CatalogPage = lazy(() =>
  import("@/pages/CatalogPage").then((module) => ({
    default: module.CatalogPage,
  })),
);
const PricingPage = lazy(() =>
  import("@/pages/PricingPage").then((module) => ({
    default: module.PricingPage,
  })),
);
const QuotationsPage = lazy(() =>
  import("@/pages/QuotationsPage").then((module) => ({
    default: module.QuotationsPage,
  })),
);
const SubscriptionsPage = lazy(() =>
  import("@/pages/SubscriptionsPage").then((module) => ({
    default: module.SubscriptionsPage,
  })),
);
const InvoicesPage = lazy(() =>
  import("@/pages/InvoicesPage").then((module) => ({
    default: module.InvoicesPage,
  })),
);

const deferred = (page: ReactNode) => (
  <Suspense
    fallback={
      <div className="loading-state">
        <LoaderCircle className="spin" />
        <span>Loading workspace…</span>
      </div>
    }
  >
    {page}
  </Suspense>
);

function Protected({ roles }: { roles?: Role[] }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading)
    return (
      <div className="loading-state" style={{ minHeight: "100vh" }}>
        <LoaderCircle className="spin" />
        <span>Opening your workspace…</span>
      </div>
    );
  if (!user)
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (roles && !roles.includes(user.role))
    return <Navigate to="/dashboard" replace />;
  return <AppShell />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<PasswordResetPage />} />
      <Route path="/reset-password" element={<PasswordResetPage />} />
      <Route element={<Protected />}>
        <Route path="/dashboard" element={deferred(<DashboardPage />)} />
        <Route
          path="/subscriptions"
          element={deferred(<SubscriptionsPage />)}
        />
        <Route path="/invoices" element={deferred(<InvoicesPage />)} />
      </Route>
      <Route element={<Protected roles={["admin", "staff"]} />}>
        <Route path="/customers" element={deferred(<PeoplePage />)} />
        <Route path="/catalog" element={deferred(<CatalogPage />)} />
        <Route path="/pricing" element={deferred(<PricingPage />)} />
        <Route path="/quotations" element={deferred(<QuotationsPage />)} />
      </Route>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
