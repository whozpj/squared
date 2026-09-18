import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const target = "http://localhost:8001";
const api = { target, changeOrigin: true };

// Some API prefixes (/groups, /bills) collide with client-side routes. For those,
// serve the SPA on HTML navigations (address bar / refresh) and proxy only data
// requests (XHR/fetch send Accept: application/json).
const spaAware = {
  ...api,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  bypass(req: any) {
    const accept = String(req.headers?.accept ?? "");
    if (req.method === "GET" && accept.includes("text/html")) return "/index.html";
    return null;
  },
};

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/health": api,
      "/compute": api,
      "/auth": api,
      "/invites": api,
      "/payments": api,
      "/notifications": api,
      "/ocr": api,
      "/groups": spaAware,
      "/bills": spaAware,
      "/ws": { target: "ws://localhost:8001", ws: true },
    },
  },
});
