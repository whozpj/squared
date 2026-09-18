import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Badge, Button, Card, Icon, Input, Spinner } from "../components/ui";
import { api, money, type Member } from "../lib/api";

interface Row {
  name: string;
  cents: number;
  members: Set<number>;
}

export default function BillEditor() {
  const { gid, bid } = useParams();
  const groupId = Number(gid);
  const billId = Number(bid);
  const nav = useNavigate();

  const [members, setMembers] = useState<Member[]>([]);
  const [title, setTitle] = useState("");
  const [rows, setRows] = useState<Row[]>([]);
  const [tax, setTax] = useState(0);
  const [tip, setTip] = useState(0);
  const [version, setVersion] = useState<number | undefined>(undefined);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [ocrBusy, setOcrBusy] = useState(false);
  const [ocrNote, setOcrNote] = useState<{ reconciled: boolean; issues: string[] } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    Promise.all([api.members(groupId), api.getBill(billId)]).then(([ms, bill]) => {
      setMembers(ms);
      setTitle(bill.title);
      setTax(bill.tax);
      setTip(bill.tip);
      setVersion(bill.version);
      setRows(
        bill.line_items.map((li) => ({
          name: li.name,
          cents: li.price,
          members: new Set(Object.keys(li.shares).map(Number)),
        })),
      );
      setLoading(false);
    });
  }, [groupId, billId]);

  const allIds = members.map((m) => m.user_id);

  const setRow = (i: number, patch: Partial<Row>) =>
    setRows((rs) => rs.map((r, j) => (j === i ? { ...r, ...patch } : r)));
  const toggle = (i: number, uid: number) =>
    setRows((rs) =>
      rs.map((r, j) => {
        if (j !== i) return r;
        const s = new Set(r.members);
        s.has(uid) ? s.delete(uid) : s.add(uid);
        return { ...r, members: s };
      }),
    );
  const addRow = () =>
    setRows((rs) => [...rs, { name: "", cents: 0, members: new Set(allIds) }]);
  const removeRow = (i: number) => setRows((rs) => rs.filter((_, j) => j !== i));

  const pollJob = useCallback(async (jobId: number) => {
    for (let i = 0; i < 20; i++) {
      const job = await api.getJob(jobId);
      if (job.status === "done" || job.status === "failed") return job;
      await new Promise((r) => setTimeout(r, 700));
    }
    return api.getJob(jobId);
  }, []);

  const onFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setOcrBusy(true);
    setOcrNote(null);
    try {
      const started = await api.uploadReceipt(billId, file);
      const job = await pollJob(started.id);
      if (job.status === "done" && job.parsed) {
        const p = job.parsed;
        setRows(
          p.items.map((it) => ({ name: it.name, cents: it.price, members: new Set(allIds) })),
        );
        if (p.tax != null) setTax(p.tax);
        if (p.tip != null) setTip(p.tip);
        setOcrNote({ reconciled: p.reconciled, issues: p.issues });
      } else {
        setOcrNote({ reconciled: false, issues: [job.error || "Couldn't read the receipt"] });
      }
    } finally {
      setOcrBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const subtotal = rows.reduce((s, r) => s + r.cents, 0);
  const total = subtotal + tax + tip;
  const unassigned = rows.some((r) => r.members.size === 0);

  const save = async () => {
    setSaving(true);
    try {
      await api.replaceItems(billId, {
        tax,
        tip,
        version,
        items: rows.map((r) => ({
          name: r.name || "Item",
          price: r.cents,
          shares: Object.fromEntries([...r.members].map((u) => [u, 1])),
        })),
      });
      nav(`/groups/${groupId}`);
    } finally {
      setSaving(false);
    }
  };

  if (loading)
    return (
      <div style={{ display: "grid", placeItems: "center", padding: 48 }}>
        <Spinner />
      </div>
    );

  return (
    <>
      <div className="page-head">
        <span className="link small" onClick={() => nav(`/groups/${groupId}`)}>
          ← {title || "Bill"}
        </span>
        <h1 style={{ marginTop: 8 }}>{title || "Bill"}</h1>
      </div>

      {/* Receipt upload */}
      <Card>
        <div className="row between">
          <div>
            <h3>Scan a receipt</h3>
            <p className="small muted" style={{ marginTop: 4 }}>
              We'll read the line items — you review before splitting.
            </p>
          </div>
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            hidden
            onChange={onFile}
          />
          <Button onClick={() => fileRef.current?.click()} loading={ocrBusy}>
            <Icon name="camera" size={16} /> Upload
          </Button>
        </div>
        {ocrNote && (
          <div style={{ marginTop: 14 }}>
            {ocrNote.reconciled ? (
              <Badge tone="pos">
                <Icon name="check" size={14} /> Reads add up
              </Badge>
            ) : (
              <Badge tone="neg">Needs review</Badge>
            )}
            {!ocrNote.reconciled &&
              ocrNote.issues.map((iss, i) => (
                <p key={i} className="small muted" style={{ marginTop: 6 }}>
                  {iss}
                </p>
              ))}
          </div>
        )}
      </Card>

      {/* Items */}
      <Card>
        <div className="row between" style={{ marginBottom: 8 }}>
          <h3>Items</h3>
          <span className="link small" onClick={addRow}>
            + Add item
          </span>
        </div>
        {rows.length === 0 && (
          <p className="small muted" style={{ padding: "12px 0" }}>
            Add items manually, or upload a receipt above.
          </p>
        )}
        <div className="stack-4">
          {rows.map((r, i) => (
            <div key={i} style={{ borderTop: i ? "1px solid var(--border)" : "none", paddingTop: i ? 16 : 0 }}>
              <div className="row" style={{ gap: 8 }}>
                <Input
                  placeholder="Item"
                  value={r.name}
                  onChange={(e) => setRow(i, { name: e.target.value })}
                  style={{ flex: 1 }}
                />
                <Input
                  className="num"
                  type="number"
                  step="0.01"
                  style={{ width: 110 }}
                  value={r.cents ? (r.cents / 100).toString() : ""}
                  onChange={(e) =>
                    setRow(i, { cents: Math.round(parseFloat(e.target.value || "0") * 100) })
                  }
                  placeholder="0.00"
                />
                <button className="icon-btn" onClick={() => removeRow(i)} aria-label="Remove item">
                  <Icon name="x" size={16} />
                </button>
              </div>
              <div className="row" style={{ gap: 6, marginTop: 8, flexWrap: "wrap" }}>
                {members.map((m) => {
                  const on = r.members.has(m.user_id);
                  return (
                    <button
                      key={m.user_id}
                      onClick={() => toggle(i, m.user_id)}
                      className="badge"
                      style={{
                        cursor: "pointer",
                        background: on ? "var(--ink)" : "var(--surface-2)",
                        color: on ? "var(--paper)" : "var(--muted)",
                        borderColor: "transparent",
                      }}
                    >
                      {m.name.split(" ")[0]}
                    </button>
                  );
                })}
                {r.members.size > 0 && (
                  <span className="small faint num" style={{ marginLeft: 4 }}>
                    {money(Math.round(r.cents / r.members.size))} each
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Tax / tip / total */}
      <Card>
        <div className="row between" style={{ marginBottom: 12 }}>
          <span className="muted">Subtotal</span>
          <span className="num">{money(subtotal)}</span>
        </div>
        <div className="row between" style={{ marginBottom: 12 }}>
          <span className="muted">Tax</span>
          <Input
            className="num"
            type="number"
            step="0.01"
            style={{ width: 110 }}
            value={tax ? (tax / 100).toString() : ""}
            onChange={(e) => setTax(Math.round(parseFloat(e.target.value || "0") * 100))}
            placeholder="0.00"
          />
        </div>
        <div className="row between" style={{ marginBottom: 12 }}>
          <span className="muted">Tip</span>
          <Input
            className="num"
            type="number"
            step="0.01"
            style={{ width: 110 }}
            value={tip ? (tip / 100).toString() : ""}
            onChange={(e) => setTip(Math.round(parseFloat(e.target.value || "0") * 100))}
            placeholder="0.00"
          />
        </div>
        <div className="divider" />
        <div className="row between">
          <span style={{ fontWeight: 700 }}>Total</span>
          <span className="num" style={{ fontWeight: 700, fontSize: 18 }}>
            {money(total)}
          </span>
        </div>
        <p className="small faint" style={{ marginTop: 10 }}>
          Tax &amp; tip are split in proportion to what each person ordered.
        </p>
      </Card>

      <div className="row" style={{ marginTop: 20, justifyContent: "flex-end" }}>
        {unassigned && (
          <span className="small" style={{ color: "var(--negative)" }}>
            Assign every item to someone first
          </span>
        )}
        <Button variant="secondary" onClick={() => nav(`/groups/${groupId}`)}>
          Cancel
        </Button>
        <Button
          variant="primary"
          onClick={save}
          loading={saving}
          disabled={rows.length === 0 || unassigned}
        >
          Save bill
        </Button>
      </div>
    </>
  );
}
