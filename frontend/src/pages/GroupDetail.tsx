import React, { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Avatar,
  Badge,
  Button,
  Card,
  EmptyState,
  Field,
  Icon,
  Input,
  Modal,
  Spinner,
} from "../components/ui";
import {
  api,
  money,
  type Balances,
  type Bill,
  type Group,
  type Member,
  type Payment,
} from "../lib/api";
import { useAuth } from "../lib/auth";
import { connectGroup } from "../lib/ws";
import { getToken } from "../lib/api";

export default function GroupDetail() {
  const { gid } = useParams();
  const groupId = Number(gid);
  const { user } = useAuth();
  const nav = useNavigate();

  const [group, setGroup] = useState<Group | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [balances, setBalances] = useState<Balances | null>(null);
  const [bills, setBills] = useState<Bill[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [showNewBill, setShowNewBill] = useState(false);
  const [showInvite, setShowInvite] = useState(false);

  const nameOf = useCallback(
    (id: number) => members.find((m) => m.user_id === id)?.name ?? `User ${id}`,
    [members],
  );
  const memberOf = useCallback(
    (id: number) => members.find((m) => m.user_id === id),
    [members],
  );

  const refresh = useCallback(() => {
    api.groups().then((gs) => setGroup(gs.find((g) => g.id === groupId) ?? null));
    api.members(groupId).then(setMembers);
    api.balances(groupId).then(setBalances);
    api.bills(groupId).then(setBills);
    api.payments(groupId).then(setPayments);
  }, [groupId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Live updates: refetch on balances / payment / ocr events.
  useEffect(() => {
    const tok = getToken();
    if (!tok) return;
    const sock = connectGroup(tok, groupId, (e) => {
      if (["balances.updated", "notification.new", "ocr.status"].includes(e.type)) refresh();
    });
    return () => sock.close();
  }, [groupId, refresh]);

  const myBalance = balances?.balances[user!.id] ?? 0;
  const pendingForMe = payments.filter((p) => p.to_user === user!.id && p.status === "claimed");

  const markPaid = async (toUser: number, amount: number) => {
    await api.claimPayment(groupId, toUser, amount);
    refresh();
  };
  const confirm = async (id: number) => {
    await api.confirmPayment(id);
    refresh();
  };

  if (!balances) {
    return (
      <div style={{ display: "grid", placeItems: "center", padding: 48 }}>
        <Spinner />
      </div>
    );
  }

  return (
    <>
      <div className="page-head">
        <div className="row" style={{ marginBottom: 8 }}>
          <span className="link small" onClick={() => nav("/")}>
            ← Groups
          </span>
        </div>
        <div className="row between">
          <h1>{group?.name ?? "Group"}</h1>
          <Button variant="primary" size="sm" onClick={() => setShowNewBill(true)}>
            <Icon name="plus" size={16} /> Add bill
          </Button>
        </div>
        <div className="row" style={{ marginTop: 12, gap: 6 }}>
          {members.map((m) => (
            <span key={m.user_id} title={m.name}>
              <Avatar name={m.name} />
            </span>
          ))}
          <button className="icon-btn" onClick={() => setShowInvite(true)} aria-label="Invite">
            <Icon name="plus" size={16} />
          </button>
        </div>
      </div>

      {/* Your balance */}
      <Card>
        <div className="row between">
          <div>
            <div className="small muted">Your balance</div>
            <div
              className={`num ${myBalance > 0 ? "money-pos" : myBalance < 0 ? "money-neg" : ""}`}
              style={{ fontSize: 30, fontWeight: 700, marginTop: 2 }}
            >
              {money(myBalance)}
            </div>
          </div>
          <div className="small muted" style={{ textAlign: "right", maxWidth: 180 }}>
            {myBalance > 0
              ? "you're owed overall"
              : myBalance < 0
                ? "you owe overall"
                : "you're all settled"}
          </div>
        </div>
      </Card>

      {/* Settle up */}
      <Card>
        <div className="row between" style={{ marginBottom: 16 }}>
          <h2>Settle up</h2>
          {balances.baseline > 0 && (
            <Badge tone={balances.reduction_pct > 0 ? "pos" : undefined}>
              {balances.baseline} → {balances.simplified} payments
              {balances.reduction_pct > 0 ? ` · ${balances.reduction_pct}% fewer` : ""}
            </Badge>
          )}
        </div>
        {balances.transfers.length === 0 ? (
          <EmptyState title="Everyone's settled up" hint="No payments needed right now." />
        ) : (
          <div className="stack-2">
            {balances.transfers.map((t, i) => (
              <div key={i} className="row between transfer-row" style={{ padding: "8px 0" }}>
                <div className="row">
                  <Avatar name={nameOf(t.debtor)} />
                  <Icon name="arrow" size={16} />
                  <Avatar name={nameOf(t.creditor)} />
                  <span className="small muted">
                    {t.debtor === user!.id ? "You" : nameOf(t.debtor)} → {nameOf(t.creditor)}
                  </span>
                </div>
                <div className="row" style={{ flexWrap: "wrap", justifyContent: "flex-end" }}>
                  <span className="num" style={{ fontWeight: 600 }}>
                    {money(t.amount)}
                  </span>
                  {t.debtor === user!.id && (
                    <PayLinks
                      creditor={memberOf(t.creditor)}
                      amount={t.amount}
                      groupName={group?.name ?? "Squared"}
                    />
                  )}
                  {t.debtor === user!.id && (
                    <Button size="sm" variant="secondary" onClick={() => markPaid(t.creditor, t.amount)}>
                      I paid
                    </Button>
                  )}
                  {t.creditor === user!.id && (
                    <RemindButton groupId={groupId} debtor={t.debtor} amount={t.amount} />
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {pendingForMe.length > 0 && (
          <>
            <div className="divider" />
            <div className="small muted" style={{ marginBottom: 8 }}>
              Confirm payments sent to you
            </div>
            <div className="stack-2">
              {pendingForMe.map((p) => (
                <div key={p.id} className="row between">
                  <span className="small">
                    {nameOf(p.from_user)} paid you{" "}
                    <span className="num" style={{ fontWeight: 600 }}>
                      {money(p.amount)}
                    </span>
                  </span>
                  <Button size="sm" variant="primary" onClick={() => confirm(p.id)}>
                    <Icon name="check" size={16} /> Confirm
                  </Button>
                </div>
              ))}
            </div>
          </>
        )}
      </Card>

      {/* Bills */}
      <h2 style={{ margin: "28px 0 12px" }}>Bills</h2>
      {bills.length === 0 ? (
        <Card>
          <EmptyState title="No bills yet" hint="Add a bill or snap a receipt to get started." />
        </Card>
      ) : (
        <Card flush>
          {bills.map((b) => (
            <div
              key={b.id}
              className="list-row clickable"
              onClick={() => nav(`/groups/${groupId}/bills/${b.id}`)}
            >
              <span className="avatar">
                <Icon name="receipt" size={16} />
              </span>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600 }}>{b.title || "Untitled bill"}</div>
                <div className="small muted">{nameOf(b.payer_id)} paid</div>
              </div>
              <span className="num" style={{ fontWeight: 600 }}>
                {money(b.total)}
              </span>
              <Icon name="chevron" size={18} />
            </div>
          ))}
        </Card>
      )}

      {showNewBill && (
        <NewBillModal
          groupId={groupId}
          members={members}
          defaultPayer={user!.id}
          onClose={() => setShowNewBill(false)}
          onCreated={(id) => nav(`/groups/${groupId}/bills/${id}`)}
        />
      )}
      {showInvite && <InviteModal groupId={groupId} onClose={() => setShowInvite(false)} />}
    </>
  );
}

function PayLinks({
  creditor,
  amount,
  groupName,
}: {
  creditor?: Member;
  amount: number;
  groupName: string;
}) {
  const amt = (amount / 100).toFixed(2);
  const note = encodeURIComponent(`${groupName} settle up`);
  const links: { label: string; href: string }[] = [
    {
      label: "Venmo",
      href: creditor?.venmo_handle
        ? `https://venmo.com/${creditor.venmo_handle}?txn=pay&amount=${amt}&note=${note}`
        : `https://venmo.com/?txn=pay&amount=${amt}&note=${note}`,
    },
  ];
  if (creditor?.paypal_handle)
    links.push({ label: "PayPal", href: `https://paypal.me/${creditor.paypal_handle}/${amt}` });
  if (creditor?.cashapp_cashtag)
    links.push({ label: "Cash App", href: `https://cash.app/$${creditor.cashapp_cashtag}/${amt}` });
  if (creditor?.email)
    links.push({
      label: "Email",
      href: `mailto:${creditor.email}?subject=${encodeURIComponent(
        `Settling up: ${groupName}`,
      )}&body=${encodeURIComponent(
        `Hi ${creditor.name}, sending you $${amt} for ${groupName} on Squared.`,
      )}`,
    });
  return (
    <>
      {links.map((l) => (
        <a key={l.label} className="btn btn-ghost btn-sm" href={l.href} target="_blank" rel="noreferrer">
          {l.label}
        </a>
      ))}
    </>
  );
}

function RemindButton({
  groupId,
  debtor,
  amount,
}: {
  groupId: number;
  debtor: number;
  amount: number;
}) {
  const [state, setState] = useState<"idle" | "busy" | "done">("idle");
  const send = async () => {
    setState("busy");
    try {
      await api.remind(groupId, debtor, amount);
      setState("done");
    } catch {
      setState("idle");
    }
  };
  return (
    <Button size="sm" variant="secondary" onClick={send} disabled={state !== "idle"}>
      {state === "done" ? "Reminded ✓" : state === "busy" ? "…" : "Remind"}
    </Button>
  );
}

function NewBillModal({
  groupId,
  members,
  defaultPayer,
  onClose,
  onCreated,
}: {
  groupId: number;
  members: Member[];
  defaultPayer: number;
  onClose: () => void;
  onCreated: (id: number) => void;
}) {
  const [title, setTitle] = useState("");
  const [payer, setPayer] = useState(defaultPayer);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const bill = await api.createBill(groupId, {
        title: title.trim() || "New bill",
        payer_id: payer,
        tax: 0,
        tip: 0,
        items: [],
      });
      onCreated(bill.id);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title="Add a bill" onClose={onClose}>
      <form onSubmit={submit}>
        <Field label="What's it for?">
          <Input
            autoFocus
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Dinner, groceries…"
          />
        </Field>
        <Field label="Who paid?">
          <select
            className="input"
            value={payer}
            onChange={(e) => setPayer(Number(e.target.value))}
          >
            {members.map((m) => (
              <option key={m.user_id} value={m.user_id}>
                {m.name}
              </option>
            ))}
          </select>
        </Field>
        <Button variant="primary" block type="submit" loading={busy}>
          Continue to items
        </Button>
      </form>
    </Modal>
  );
}

function InviteModal({ groupId, onClose }: { groupId: number; onClose: () => void }) {
  const [code, setCode] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const gen = async () => {
    setBusy(true);
    try {
      const inv = await api.createInvite(groupId);
      setCode(inv.token);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal title="Invite someone" onClose={onClose}>
      <p className="small muted" style={{ marginBottom: 16 }}>
        Generate a code and share it. They enter it under “Join” to hop into this group.
      </p>
      {code ? (
        <div className="card" style={{ background: "var(--surface-2)", wordBreak: "break-all" }}>
          <code>{code}</code>
        </div>
      ) : (
        <Button variant="primary" block loading={busy} onClick={gen}>
          Generate invite code
        </Button>
      )}
    </Modal>
  );
}
