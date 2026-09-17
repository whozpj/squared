import { useState } from "react";
import { allocate, settle, type SettleResponse } from "./lib/api";

const fmt = (cents: number) => `$${(cents / 100).toFixed(2)}`;

export default function App() {
  const [alloc, setAlloc] = useState<Record<number, number> | null>(null);
  const [result, setResult] = useState<SettleResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // A tiny hardcoded demo exercising the two core endpoints. The real
  // group/bill UI is built in later steps (DESIGN.md §13).
  async function runDemo() {
    setError(null);
    try {
      const a = await allocate(
        [
          { price: 3000, shares: { 1: 1 } }, // Alice's $30
          { price: 1000, shares: { 2: 1 } }, // Bob's $10
        ],
        400, // $4 tax
        800, // $8 tip
        [1, 2],
      );
      setAlloc(a.shares);

      const s = await settle([
        { debtor: 1, creditor: 3, amount: 1000 },
        { debtor: 2, creditor: 3, amount: 1000 },
        { debtor: 3, creditor: 1, amount: 600 },
      ]);
      setResult(s);
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <main style={{ fontFamily: "system-ui", maxWidth: 640, margin: "3rem auto", padding: "0 1rem" }}>
      <h1>Squared</h1>
      <p style={{ color: "#555" }}>
        Split bills fairly — exact tax &amp; tip per person, minimal settle-up transfers.
      </p>
      <button onClick={runDemo} style={{ padding: "0.5rem 1rem", fontSize: 16, cursor: "pointer" }}>
        Run core demo
      </button>

      {error && <pre style={{ color: "crimson" }}>{error}</pre>}

      {alloc && (
        <section>
          <h2>Allocation (exact tax &amp; tip)</h2>
          <ul>
            {Object.entries(alloc).map(([user, cents]) => (
              <li key={user}>
                User {user} owes <strong>{fmt(cents)}</strong>
              </li>
            ))}
          </ul>
        </section>
      )}

      {result && (
        <section>
          <h2>Settle up (greedy simplification)</h2>
          <p>
            Reduced <strong>{result.baseline}</strong> → <strong>{result.simplified}</strong>{" "}
            transactions ({result.reduction_pct}% fewer).
          </p>
          <ul>
            {result.transfers.map((t, i) => (
              <li key={i}>
                User {t.debtor} pays User {t.creditor} <strong>{fmt(t.amount)}</strong>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}
