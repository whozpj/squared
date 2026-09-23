import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Field, Input } from "../components/ui";
import { WelcomeShow } from "../components/WelcomeShow";
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
    <div className="welcome-full">
      <header className="welcome-top">
        <div className="wordmark anim-1">
          <span className="glyph" />
          Squared
        </div>
        <div className="signin-mini anim-2">
          <form onSubmit={submit}>
            <div className="signin-mini-title">Sign in</div>
            <Field label="Email">
              <Input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
              />
            </Field>
            <Field label="Name">
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name" />
            </Field>
            {err && (
              <p className="small" style={{ color: "var(--negative)", marginBottom: 10 }}>
                {err}
              </p>
            )}
            <Button variant="primary" block type="submit" loading={busy}>
              Continue
            </Button>
            <p className="small faint" style={{ textAlign: "center", marginTop: 10 }}>
              Google sign-in coming soon.
            </p>
          </form>
        </div>
      </header>

      <div className="welcome-center anim-3">
        <WelcomeShow />
      </div>
    </div>
  );
}
