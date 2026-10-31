import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import {
  Eye,
  EyeOff,
  LockKeyhole,
  Mail,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/auth/useAuth";
import { apiMessage } from "@/api/client";
import { Button, Field, Input } from "@/components/ui";

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  if (user) return <Navigate to="/dashboard" replace />;
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      toast.success("Welcome back to Brightloop");
      navigate((location.state as { from?: string })?.from || "/dashboard", {
        replace: true,
      });
    } catch (error) {
      toast.error(apiMessage(error));
    } finally {
      setLoading(false);
    }
  };
  return (
    <main className="auth-page">
      <section className="auth-visual">
        <div className="auth-brand">
          <div className="brand__mark">
            <Sparkles size={19} />
          </div>
          <div>
            <strong>Brightloop</strong>
            <small>Subscription OS</small>
          </div>
        </div>
        <div className="auth-copy">
          <span>SUBSCRIPTION OPERATIONS, UNIFIED</span>
          <h1>Revenue operations that move at your speed.</h1>
          <p>
            Manage customers, quotations, recurring contracts, billing and
            collections from one precise operational workspace.
          </p>
          <div className="auth-proof">
            <div>
              <strong>Secure</strong>
              <small>Role-based access</small>
            </div>
            <div>
              <strong>Reliable</strong>
              <small>Duplicate-safe billing</small>
            </div>
            <div>
              <strong>Visible</strong>
              <small>Real-time finance</small>
            </div>
          </div>
        </div>
      </section>
      <section className="auth-form-side">
        <div className="auth-form">
          <span className="eyebrow">Secure workspace</span>
          <h2>Welcome back</h2>
          <p>Enter your account details to continue to Brightloop.</p>
          <form onSubmit={submit}>
            <Field label="Work email">
              <div className="password-wrap">
                <Mail
                  size={16}
                  style={{
                    position: "absolute",
                    left: 12,
                    top: 12,
                    color: "#8994a7",
                  }}
                />
                <Input
                  style={{ paddingLeft: 38 }}
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@company.com"
                  required
                />
              </div>
            </Field>
            <Field label="Password">
              <div className="password-wrap">
                <LockKeyhole
                  size={16}
                  style={{
                    position: "absolute",
                    left: 12,
                    top: 12,
                    color: "#8994a7",
                  }}
                />
                <Input
                  style={{ paddingLeft: 38 }}
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Enter your password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </Field>
            <div className="auth-links">
              <label className="checkbox-row">
                <input type="checkbox" /> Keep me signed in
              </label>
              <button
                className="text-link"
                type="button"
                onClick={() => navigate("/forgot-password")}
              >
                Forgot password?
              </button>
            </div>
            <Button type="submit" loading={loading}>
              Sign in to workspace
            </Button>
          </form>
          <div className="auth-footer">
            <ShieldCheck
              size={13}
              style={{ verticalAlign: "middle", marginRight: 5 }}
            />
            Protected by encrypted authentication and role-based access.
          </div>
        </div>
      </section>
    </main>
  );
}
