// Typed client for the Squared backend. Token is held in memory + localStorage.

// In dev this is empty (Vite proxies /auth, /groups, … to the backend). In prod set
// VITE_API_BASE to the deployed backend origin, e.g. https://squared-api.onrender.com
export const API_BASE = (import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "");

let token: string | null = null;
try {
  token = localStorage.getItem("squared_token");
} catch {
  token = null;
}

export function setToken(t: string | null) {
  token = t;
  try {
    if (t) localStorage.setItem("squared_token", t);
    else localStorage.removeItem("squared_token");
  } catch {
    /* private mode: keep in memory only */
  }
}

export function getToken() {
  return token;
}

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = `${res.status}`;
    try {
      const j = await res.json();
      detail = j.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, String(detail));
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

// ---- types ----
export interface User {
  id: number;
  email: string;
  name: string;
  venmo_handle?: string | null;
  paypal_handle?: string | null;
  cashapp_cashtag?: string | null;
}
export interface ProfileUpdate {
  name?: string;
  venmo_handle?: string;
  paypal_handle?: string;
  cashapp_cashtag?: string;
}
export interface Group {
  id: number;
  name: string;
  currency: string;
  role?: string | null;
}
export interface Member {
  user_id: number;
  name: string;
  email: string;
  role: string;
  venmo_handle?: string | null;
  paypal_handle?: string | null;
  cashapp_cashtag?: string | null;
}
export interface ShareOut {
  user_id: number;
  amount: number;
}
export interface LineItemOut {
  id: number;
  name: string;
  price: number;
  quantity: number;
  shares: Record<number, number>;
}
export interface Bill {
  id: number;
  title: string;
  payer_id: number;
  subtotal: number;
  tax: number;
  tip: number;
  total: number;
  currency: string;
  version: number;
  line_items: LineItemOut[];
  shares: ShareOut[];
}
export interface Transfer {
  debtor: number;
  creditor: number;
  amount: number;
}
export interface Balances {
  balances: Record<number, number>;
  transfers: Transfer[];
  baseline: number;
  simplified: number;
  reduction_pct: number;
}
export interface Payment {
  id: number;
  from_user: number;
  to_user: number;
  amount: number;
  method: string | null;
  status: string;
}
export interface Notification {
  id: number;
  type: string;
  payload: Record<string, unknown> | null;
  read: boolean;
}
export interface OcrJob {
  id: number;
  bill_id: number;
  status: string;
  confidence: number | null;
  error: string | null;
  parsed: {
    items: { name: string; price: number }[];
    subtotal: number | null;
    tax: number | null;
    tip: number | null;
    total: number | null;
    reconciled: boolean;
    issues: string[];
  } | null;
}
export interface ItemInput {
  name: string;
  price: number;
  quantity?: number;
  shares: Record<number, number>;
}

// ---- endpoints ----
export const api = {
  devLogin: (email: string, name: string) =>
    req<{ access_token: string; user_id: number }>("POST", "/auth/dev-login", { email, name }),
  me: () => req<User>("GET", "/auth/me"),
  updateProfile: (payload: ProfileUpdate) => req<User>("PATCH", "/auth/me", payload),

  groups: () => req<Group[]>("GET", "/groups"),
  createGroup: (name: string, currency = "USD") =>
    req<Group>("POST", "/groups", { name, currency }),
  members: (gid: number) => req<Member[]>("GET", `/groups/${gid}/members`),
  createInvite: (gid: number, email?: string) =>
    req<{ id: number; token: string; status: string }>("POST", `/groups/${gid}/invites`, { email }),
  acceptInvite: (token: string) => req<Group>("POST", `/invites/${token}/accept`),

  balances: (gid: number) => req<Balances>("GET", `/groups/${gid}/balances`),
  createBill: (gid: number, payload: { title: string; payer_id: number; tax: number; tip: number; items: ItemInput[] }) =>
    req<Bill>("POST", `/groups/${gid}/bills`, payload),
  bills: (gid: number) => req<Bill[]>("GET", `/groups/${gid}/bills`),
  getBill: (id: number) => req<Bill>("GET", `/bills/${id}`),
  replaceItems: (id: number, payload: { tax: number; tip: number; items: ItemInput[]; version?: number }) =>
    req<Bill>("PUT", `/bills/${id}/items`, payload),

  payments: (gid: number) => req<Payment[]>("GET", `/groups/${gid}/payments`),
  claimPayment: (gid: number, to_user: number, amount: number, method?: string) =>
    req<Payment>("POST", `/groups/${gid}/payments`, { to_user, amount, method }),
  confirmPayment: (id: number) => req<Payment>("POST", `/payments/${id}/confirm`),
  remind: (gid: number, to_user: number, amount: number) =>
    req<{ emailed: boolean; notified: boolean }>("POST", `/groups/${gid}/settle/remind`, {
      to_user,
      amount,
    }),

  notifications: () => req<Notification[]>("GET", "/notifications"),
  markRead: (id: number) => req<Notification>("POST", `/notifications/${id}/read`),

  getJob: (id: number) => req<OcrJob>("GET", `/ocr/${id}`),
  uploadReceipt: async (billId: number, file: File): Promise<OcrJob> => {
    const fd = new FormData();
    fd.append("file", file);
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(`${API_BASE}/bills/${billId}/ocr`, { method: "POST", headers, body: fd });
    if (!res.ok) throw new ApiError(res.status, await res.text());
    return (await res.json()) as OcrJob;
  },
};

export const money = (cents: number) => {
  const v = (Math.abs(cents) / 100).toFixed(2);
  return `${cents < 0 ? "-" : ""}$${v}`;
};
