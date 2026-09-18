import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, money, type Notification } from "../lib/api";
import { useAuth } from "../lib/auth";
import { Avatar, Icon } from "./ui";

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
  const { user, logout } = useAuth();
  const nav = useNavigate();
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
                title={`${user.name} — sign out`}
                aria-label="Sign out"
                onClick={() => {
                  logout();
                  nav("/login");
                }}
                style={{ width: "auto", padding: "0 8px", gap: 8 }}
              >
                <Avatar name={user.name} />
              </button>
            </>
          )}
        </div>
      </header>
      <main className="container page">{children}</main>
    </>
  );
}
