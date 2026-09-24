import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Field, Input } from "../components/ui";
import { FloatingSquares, WelcomeShow } from "../components/WelcomeShow";
import { useAuth } from "../lib/auth";

export default function Login() {
  const { login, user } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (user) nav("/");
  }, [user, nav]);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

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
      <FloatingSquares />
      <header className="topbar">
        <div className="topbar-inner">
          <div className="wordmark">
            <span className="glyph" />
            Squared
          </div>
          <div className="spacer" />
          <div ref={menuRef} style={{ position: "relative" }}>
            <Button variant="primary" size="sm" onClick={() => setOpen((o) => !o)}>
              Sign in
            </Button>
            {open && (
              <div className="panel signin-panel">
                <form onSubmit={submit}>
                  <div className="signin-mini-title">Welcome</div>
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
            )}
          </div>
        </div>
      </header>

      <div className="welcome-center">
        <WelcomeShow />
      </div>
    </div>
  );
}
