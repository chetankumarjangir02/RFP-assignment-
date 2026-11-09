import { useState } from "react";
import { search } from "../api.js";
import EvidenceList from "./EvidenceList.jsx";
import { PanelHeader, Field, Alert, Spinner, EmptyState, NeedBid, Icon } from "./ui.jsx";

const DOC_TYPES = ["", "bid_page", "rfp", "addendum", "specs", "affidavit"];
const MODES = ["hybrid_rerank", "hybrid", "vector", "keyword"];

export default function SearchPanel({ bid = "", goToUpload }) {
  const [q, setQ] = useState("");
  const bidId = bid;
  const [docType, setDocType] = useState("");
  const [topK, setTopK] = useState(5);
  const [mode, setMode] = useState("hybrid_rerank");
  const [results, setResults] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    if (!q) return;
    setBusy(true);
    setError("");
    try {
      setResults(await search({ q, bidId, docType, topK, mode }));
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  }

  if (!bid) {
    return (
      <div className="space-y-6">
        <PanelHeader
          icon="search"
          title="Search the bid"
          subtitle="Dense + sparse retrieval fused with RRF, metadata filtering, and optional cross-encoder re-ranking."
        />
        <NeedBid onUpload={goToUpload} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PanelHeader
        icon="search"
        title="Search the bid"
        subtitle={
          <>
            Hybrid retrieval scoped to <span className="font-mono text-brand-300">{bid}</span> — RRF fusion, metadata
            filtering, optional re-ranking.
          </>
        }
      />

      {/* Query bar */}
      <div className="flex gap-2.5">
        <div className="relative flex-1">
          <Icon name="search" className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && run()}
            placeholder="e.g. bid bond requirement amount"
            className="input pl-10"
          />
        </div>
        <button onClick={run} disabled={busy || !q} className="btn btn-primary shrink-0">
          {busy ? <Spinner /> : <Icon name="search" className="h-4 w-4" />}
          {busy ? "Searching…" : "Search"}
        </button>
      </div>

      {/* Filters */}
      <div className="grid grid-cols-2 gap-3 rounded-2xl border border-white/8 bg-white/[0.02] p-4 sm:grid-cols-3">
        <Field label="doc_type">
          <select value={docType} onChange={(e) => setDocType(e.target.value)} className="select">
            {DOC_TYPES.map((d) => (
              <option key={d} value={d}>
                {d || "any"}
              </option>
            ))}
          </select>
        </Field>
        <Field label="top_k">
          <input
            type="number"
            min={1}
            max={50}
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
            className="input"
          />
        </Field>
        <Field label="mode">
          <select value={mode} onChange={(e) => setMode(e.target.value)} className="select">
            {MODES.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </Field>
      </div>

      {error && <Alert tone="error">{error}</Alert>}

      {results && (
        <div className="animate-fade-up space-y-3">
          {results.length > 0 && (
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              {results.length} passage{results.length === 1 ? "" : "s"}
            </p>
          )}
          <EvidenceList items={results} />
        </div>
      )}
      {!results && !busy && (
        <EmptyState icon="search" title="No search yet" hint="Enter a query to retrieve ranked, cited passages from the index." />
      )}
    </div>
  );
}
