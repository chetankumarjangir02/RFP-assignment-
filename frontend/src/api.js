// Thin API client. All calls go through the Vite /api proxy to the FastAPI backend.
const BASE = "/api";

async function handle(res) {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}${text ? ` — ${text}` : ""}`);
  }
  return res.json();
}

export async function health() {
  const res = await fetch(`${BASE}/health`);
  return handle(res);
}

// List the bid_ids currently indexed (for the shared bid selector).
export async function listBids() {
  const res = await fetch(`${BASE}/bids`);
  return handle(res);
}

// Upload a folder's files (from <input webkitdirectory>) under a bid_id, then index.
export async function uploadBid(bidId, files) {
  const form = new FormData();
  form.append("bid_id", bidId);
  for (const f of files) form.append("files", f, f.name);
  const res = await fetch(`${BASE}/upload`, { method: "POST", body: form });
  return handle(res);
}

export async function search({ q, bidId, docType, topK, mode }) {
  const params = new URLSearchParams({ q });
  if (bidId) params.set("bid_id", bidId);
  if (docType) params.set("doc_type", docType);
  if (topK) params.set("top_k", String(topK));
  if (mode) params.set("mode", mode);
  const res = await fetch(`${BASE}/search?${params.toString()}`);
  return handle(res);
}

export async function ask(question, bidId) {
  const res = await fetch(`${BASE}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, bid_id: bidId || null }),
  });
  return handle(res);
}

export async function extract(bidId) {
  const res = await fetch(`${BASE}/extract`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ bid_id: bidId }),
  });
  return handle(res);
}
