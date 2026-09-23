import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, money, type Notification } from "../lib/api";
import { useAuth } from "../lib/auth";
import { Avatar, Button, Field, Icon, Input, Modal } from "./ui";

function ProfileSheet({ onClose }: { onClose: () => void }) {
  const { user, updateProfile, logout } = useAuth();
  const nav = useNavigate();
  const [name, setName] = useState(user?.name ?? "");
  const [venmo, setVenmo] = useState(user?.venmo_handle ?? "");
  const [paypal, setPaypal] = useState(user?.paypal_handle ?? "");
  const [cashapp, setCashapp] = useState(user?.cashapp_cashtag ?? "");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);

  const save = async () => {
    setBusy(true);
    setSaved(false);
    try {
      await updateProfile({
        name,
        venmo_handle: venmo,
        paypal_handle: paypal,
        cashapp_cashtag: cashapp,
      });
      setSaved(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="Your profile" onClose={onClose}>
      <Field label="Name">
        <Input value={name} onChange={(e) => setName(e.target.value)} />
      </Field>
      <p className="small muted" style={{ margin: "4px 0 12px" }}>
        Add your payment handles so friends can pay you in one tap.
      </p>
      <Field label="Venmo username">
        <Input value={venmo} onChange={(e) => setVenmo(e.target.value)} placeholder="e.g. jane-doe" />
      </Field>
      <Field label="PayPal.me username">
        <Input value={paypal} onChange={(e) => setPaypal(e.target.value)} placeholder="e.g. janedoe" />
      </Field>
      <Field label="Cash App $cashtag">
        <Input value={cashapp} onChange={(e) => setCashapp(e.target.value)} placeholder="e.g. janedoe" />
      </Field>
      <Button variant="primary" block onClick={save} loading={busy}>
        {saved ? "Saved ✓" : "Save"}
      </Button>
      <div className="divider" />
      <Button
        variant="danger"
        block
        onClick={() => {
          logout();
          nav("/login");
        }}
      >
        Sign out
      </Button>
    </Modal>
  );
}

function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Notification[]>([]);
  const ref = useRef<HTMLDivElement>(null);

  const load = () => api.notifications().then(setItems).catch(() => {});
  useEffect(() => {
    load();
  }, []);
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const unread = items.filter((n) => !n.read).length;

  const markRead = async (n: Notification) => {
    if (n.read) return;
    await api.markRead(n.id);
    load();
  };

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        className="icon-btn"
        onClick={() => setOpen((v) => !v)}
        aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`}
      >
        <Icon name="bell" />
        {unread > 0 && <span className="dot" />}
      </button>
      {open && (
        <div className="panel">
          <div className="list-row" style={{ fontWeight: 700 }}>
            Notifications
          </div>
          {items.length === 0 && (
            <div className="list-row muted small">You're all caught up.</div>
          )}
          {items.map((n) => {
            const owed = (n.payload?.owed_cents as number) ?? 0;
            return (
              <div
                key={n.id}
                className="list-row clickable"
                onClick={() => markRead(n)}
                style={{ opacity: n.read ? 0.55 : 1 }}
              >
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>Payment reminder</div>
                  <div className="small muted num">
                    You owe {money(owed)} this week
                  </div>
                </div>
                {!n.read && <span className="dot" style={{ position: "static" }} />}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [showProfile, setShowProfile] = useState(false);
  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <Link to="/" className="wordmark">
            <span className="glyph" />
            Squared
          </Link>
          <div className="spacer" />
          {user && (
            <>
              <NotificationBell />
              <button
                className="icon-btn"
                title={`${user.name} — profile`}
                aria-label="Profile"
                onClick={() => setShowProfile(true)}
                style={{ width: "auto", padding: "0 8px", gap: 8 }}
              >
                <Avatar name={user.name} />
              </button>
            </>
          )}
        </div>
      </header>
      <main className="container page">{children}</main>
      {showProfile && <ProfileSheet onClose={() => setShowProfile(false)} />}
    </>
  );
}
