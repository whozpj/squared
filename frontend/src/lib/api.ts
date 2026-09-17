// Thin client for the Squared backend.

export interface LineItem {
  price: number; // cents
  shares: Record<number, number>;
}

export interface AllocateResponse {
  shares: Record<number, number>;
  total: number;
}

export interface Transfer {
  debtor: number;
  creditor: number;
  amount: number;
}

export interface SettleResponse {
  transfers: Transfer[];
  baseline: number;
  simplified: number;
  reduction_pct: number;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

export function allocate(
  items: LineItem[],
  tax: number,
  tip: number,
  participants: number[],
): Promise<AllocateResponse> {
  return post("/compute/allocate", { items, tax, tip, participants });
}

export function settle(
  obligations: { debtor: number; creditor: number; amount: number }[],
): Promise<SettleResponse> {
  return post("/compute/settle", { obligations });
}
