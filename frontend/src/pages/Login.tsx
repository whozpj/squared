import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Field, Input } from "../components/ui";
import { useAuth } from "../lib/auth";

export default function Login() {
  const { login, user } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (user) nav("/");
  }, [user, nav]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      await login(email.trim(), name.trim() || email.split("@")[0]);
      nav("/");
    } catch {
      setErr("Couldn't sign in. Check the backend is running.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ display: "grid", placeItems: "center", minHeight: "100dvh", padding: 16 }}>
      <div style={{ width: "100%", maxWidth: 380 }}>
        <div className="wordmark" style={{ fontSize: 24, marginBottom: 8, justifyContent: "center" }}>
          <span className="glyph" style={{ width: 26, height: 26 }} />
          Squared
        </div>
        <p className="muted" style={{ textAlign: "center", marginBottom: 28 }}>
          Split bills fairly. Settle up in the fewest payments.
        </p>
        <div className="card">
          <form onSubmit={submit}>
            <Field label="Email">
              <Input
                type="email"
                required
                autoFocus
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
              />
            </Field>
            <Field label="Name">
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
              />
            </Field>
            {err && (
              <p className="small" style={{ color: "var(--negative)", marginBottom: 12 }}>
                {err}
              </p>
            )}
            <Button variant="primary" block type="submit" loading={busy}>
              Continue
            </Button>
          </form>
        </div>
        <p className="small faint" style={{ textAlign: "center", marginTop: 16 }}>
          Sign in with Google coming soon.
        </p>
      </div>
    </div>
  );
}
