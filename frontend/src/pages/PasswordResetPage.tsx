import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowLeft, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { authApi } from "@/api/services";
import { apiMessage } from "@/api/client";
import { Button, Field, Input } from "@/components/ui";

export function PasswordResetPage() {
  const [params] = useSearchParams();
  const token = params.get("token");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    try {
      if (token) {
        await authApi.confirmReset(token, password);
        toast.success("Password updated. You can sign in now.");
      } else {
        await authApi.requestReset(email);
        setSent(true);
      }
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
          <strong>Brightloop</strong>
        </div>
        <div className="auth-copy">
          <span>ACCOUNT RECOVERY</span>
          <h1>Secure access, without the friction.</h1>
          <p>We’ll help you safely recover your workspace access.</p>
        </div>
      </section>
      <section className="auth-form-side">
        <div className="auth-form">
          <span className="eyebrow">Account security</span>
          <h2>{token ? "Choose a new password" : "Reset your password"}</h2>
          <p>
            {sent
              ? "If an account exists for that email, a secure reset link has been sent."
              : token
                ? "Use at least 12 characters with uppercase, lowercase, number and symbol."
                : "Enter your work email and we’ll send a secure reset link."}
          </p>
          {!sent && (
            <form onSubmit={submit}>
              <Field label={token ? "New password" : "Work email"}>
                <Input
                  type={token ? "password" : "email"}
                  value={token ? password : email}
                  onChange={(event) =>
                    token
                      ? setPassword(event.target.value)
                      : setEmail(event.target.value)
                  }
                  required
                  minLength={token ? 12 : undefined}
                />
              </Field>
              <Button type="submit" loading={loading}>
                {token ? "Update password" : "Send reset link"}
              </Button>
            </form>
          )}
          <p style={{ marginTop: 24 }}>
            <Link className="text-link" to="/login">
              <ArrowLeft
                size={14}
                style={{ verticalAlign: "middle", marginRight: 6 }}
              />
              Back to sign in
            </Link>
          </p>
        </div>
      </section>
    </main>
  );
}
