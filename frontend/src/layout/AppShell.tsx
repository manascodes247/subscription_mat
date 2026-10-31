import { useMemo, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  Package,
  BadgePercent,
  FileText,
  RefreshCcw,
  ReceiptText,
  LogOut,
  Menu,
  Bell,
  ChevronDown,
  Search,
  Sparkles,
  X,
} from "lucide-react";
import { useAuth } from "@/auth/useAuth";
import { initials, roleLabel } from "@/lib/format";
import type { Role } from "@/api/types";

const items: {
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
  roles: Role[];
}[] = [
  {
    to: "/dashboard",
    label: "Overview",
    icon: LayoutDashboard,
    roles: ["admin", "staff", "customer"],
  },
  { to: "/customers", label: "People", icon: Users, roles: ["admin", "staff"] },
  {
    to: "/catalog",
    label: "Product catalog",
    icon: Package,
    roles: ["admin", "staff"],
  },
  {
    to: "/pricing",
    label: "Pricing rules",
    icon: BadgePercent,
    roles: ["admin", "staff"],
  },
  {
    to: "/quotations",
    label: "Quotations",
    icon: FileText,
    roles: ["admin", "staff"],
  },
  {
    to: "/subscriptions",
    label: "Subscriptions",
    icon: RefreshCcw,
    roles: ["admin", "staff", "customer"],
  },
  {
    to: "/invoices",
    label: "Invoices & payments",
    icon: ReceiptText,
    roles: ["admin", "staff", "customer"],
  },
];

export function AppShell() {
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const navItems = useMemo(
    () => items.filter((item) => user && item.roles.includes(user.role)),
    [user],
  );
  const current = navItems.find((item) =>
    location.pathname.startsWith(item.to),
  );
  if (!user) return null;
  return (
    <div className="app-shell">
      {mobileOpen && (
        <button
          className="mobile-overlay"
          onClick={() => setMobileOpen(false)}
          aria-label="Close navigation"
        />
      )}
      <aside className={mobileOpen ? "sidebar sidebar--open" : "sidebar"}>
        <div className="brand">
          <div className="brand__mark">
            <Sparkles size={19} />
          </div>
          <div>
            <strong>Brightloop</strong>
            <small>Subscription OS</small>
          </div>
          <button
            className="sidebar-close"
            onClick={() => setMobileOpen(false)}
          >
            <X size={20} />
          </button>
        </div>
        <nav>
          <span className="nav-label">Workspace</span>
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) => (isActive ? "active" : "")}
            >
              <Icon size={18} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar__footer">
          <div className="support-card">
            <span>LIVE OPERATIONS</span>
            <strong>Billing engine ready</strong>
            <small>Automations are monitored continuously.</small>
          </div>
          <button className="profile-card" onClick={logout}>
            <span className="avatar">{initials(user.full_name)}</span>
            <span>
              <strong>{user.full_name}</strong>
              <small>{roleLabel[user.role]}</small>
            </span>
            <LogOut size={17} />
          </button>
        </div>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <div className="topbar__left">
            <button className="menu-button" onClick={() => setMobileOpen(true)}>
              <Menu size={20} />
            </button>
            <div>
              <small>Workspace</small>
              <strong>{current?.label || "Brightloop"}</strong>
            </div>
          </div>
          <div className="topbar__search">
            <Search size={17} />
            <input placeholder="Search workspace…" />
          </div>
          <div className="topbar__actions">
            <button className="icon-button">
              <Bell size={19} />
              <i />
            </button>
            <button className="topbar-profile">
              <span className="avatar avatar--small">
                {initials(user.full_name)}
              </span>
              <span>{user.full_name.split(" ")[0]}</span>
              <ChevronDown size={15} />
            </button>
          </div>
        </header>
        <div className="page">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
