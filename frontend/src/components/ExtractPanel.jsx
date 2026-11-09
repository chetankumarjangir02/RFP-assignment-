import { useState } from "react";
import { extract } from "../api.js";
import { PanelHeader, Alert, Spinner, EmptyState, NeedBid, Icon } from "./ui.jsx";

export default function ExtractPanel({ bid = "", goToUpload }) {
  const [record, setRecord] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    if (!bid) return;
    setBusy(true);
    setError("");
    setRecord(null);
    try {
      setRecord(await extract(bid));
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  }

  function download() {
    const blob = new Blob([JSON.stringify(record, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${record.bid_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const v = record?.validation || {};
  const total = (v.passed ?? 0) + (v.failed ?? 0) + (v.not_found ?? 0);

  if (!bid) {
    return (
      <div className="space-y-6">
        <PanelHeader
          icon="extract"
          title="Extract structured record"
          subtitle="Runs the orchestrated multi-agent pipeline and returns the 20-field JSON — each value cited, scored, and noted."
        />
        <NeedBid onUpload={goToUpload} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PanelHeader
        icon="extract"
        title="Extract structured record"
        subtitle={
          <>
            Runs the multi-agent pipeline over <span className="font-mono text-brand-300">{bid}</span> → the 20-field
            JSON, each value cited, scored, and noted.
          </>
        }
      />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-base-900/50 px-3.5 py-2.5 text-sm">
          <Icon name="folder" className="h-4 w-4 text-brand-300" />
          <span className="text-slate-400">bid</span>
          <span className="font-mono font-semibold text-white">{bid}</span>
        </div>
        <button onClick={run} disabled={busy} className="btn btn-primary sm:ml-auto">
          {busy ? (
            <>
              <Spinner /> Running agents…
            </>
          ) : (
            <>
              <Icon name="bolt" className="h-4 w-4" /> Run extraction
            </>
          )}
        </button>
      </div>

      {error && <Alert tone="error">{error}</Alert>}

      {busy && !record && (
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="skeleton h-20" />
            ))}
          </div>
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="skeleton h-12" />
          ))}
        </div>
      )}

      {record && (
        <div className="animate-fade-up space-y-6">
          {/* Summary strip */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Metric label="Passed" value={v.passed ?? 0} total={total} tone="emerald" icon="check" />
            <Metric label="Failed" value={v.failed ?? 0} total={total} tone="rose" icon="alert" />
            <Metric label="Not found" value={v.not_found ?? 0} total={total} tone="slate" icon="info" />
            <button
              onClick={download}
              className="group flex flex-col items-start justify-center rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-left transition hover:border-brand-400/40 hover:bg-brand-500/[0.06]"
            >
              <Icon name="download" className="mb-1 h-5 w-5 text-brand-300 transition group-hover:scale-110" />
              <span className="text-sm font-semibold text-white">Download</span>
              <span className="font-mono text-xs text-slate-500">{record.bid_id}.json</span>
            </button>
          </div>

          {record.addendum_changes?.length > 0 && (
            <Alert tone="info">
              <b>{record.addendum_changes.length}</b> field(s) updated by addendums — latest valid change applied.
            </Alert>
          )}

          {/* Field list */}
          <div className="space-y-2.5">
            {Object.entries(record.fields || {}).map(([name, fv]) => (
              <FieldCard key={name} name={name} fv={fv} />
            ))}
          </div>
        </div>
      )}

      {!record && !busy && !error && (
        <EmptyState
          icon="extract"
          title="No extraction yet"
          hint="Enter an indexed bid_id and run the pipeline to produce the structured 20-field record."
        />
      )}
    </div>
  );
}

function FieldCard({ name, fv }) {
  const found = fv.value !== null && fv.value !== undefined && String(fv.value).length > 0;
  const conf = typeof fv.confidence === "number" ? fv.confidence : 0;
  const sources = (fv.sources || []).filter(Boolean);

  const status = found
    ? { label: "found", cls: "bg-emerald-500/15 text-emerald-300" }
    : { label: "not found", cls: "bg-slate-500/15 text-slate-400" };

  return (
    <details className="group rounded-xl border border-white/8 bg-white/[0.02] transition-colors hover:border-white/15 open:border-brand-400/25 open:bg-white/[0.035]">
      <summary className="flex cursor-pointer list-none items-center gap-3 px-4 py-3">
        <Icon
          name="extract"
          className="h-4 w-4 shrink-0 text-slate-500 transition-transform group-open:rotate-0"
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-slate-200">{name}</span>
            <span className={`chip ${status.cls}`}>{status.label}</span>
          </div>
          <p className={`mt-0.5 truncate text-sm ${found ? "text-slate-400" : "italic text-slate-600"}`}>
            {found ? String(fv.value) : "—"}
          </p>
        </div>
        {found && <ConfidenceGauge value={conf} />}
        <Icon name="info" className="h-4 w-4 shrink-0 text-slate-600 transition-transform group-open:rotate-180" />
      </summary>

      <div className="space-y-3 border-t border-white/5 px-4 py-3.5 text-sm">
        {found && (
          <p className="whitespace-pre-wrap leading-relaxed text-slate-300">{String(fv.value)}</p>
        )}
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-xs">
          <div className="flex items-center gap-2">
            <span className="font-semibold uppercase tracking-wider text-slate-500">Confidence</span>
            <ConfidenceBar value={conf} />
            <span className="font-mono text-slate-400">{conf.toFixed(2)}</span>
          </div>
        </div>
        <div className="text-xs">
          <span className="font-semibold uppercase tracking-wider text-slate-500">Sources</span>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {sources.length > 0 ? (
              sources.map((s, i) => (
                <span key={i} className="chip border border-white/10 bg-base-900/60 font-mono text-slate-400">
                  <Icon name="doc" className="h-3 w-3 opacity-60" />
                  {s.file} · p.{s.page ?? "?"}
                </span>
              ))
            ) : (
              <span className="text-slate-600">—</span>
            )}
          </div>
        </div>
        {fv.notes && (
          <p className="rounded-lg border border-white/5 bg-base-900/40 px-3 py-2 text-xs leading-relaxed text-slate-400">
            <span className="font-semibold text-slate-500">Notes · </span>
            {fv.notes}
          </p>
        )}
      </div>
    </details>
  );
}

function confColor(v) {
  if (v >= 0.75) return "text-emerald-400";
  if (v >= 0.4) return "text-amber-400";
  return "text-slate-500";
}

function ConfidenceGauge({ value }) {
  const pct = Math.round(Math.min(Math.max(value, 0), 1) * 100);
  return (
    <span className={`hidden shrink-0 font-mono text-xs font-semibold sm:inline ${confColor(value)}`}>{pct}%</span>
  );
}

function ConfidenceBar({ value }) {
  const pct = Math.min(Math.max(value, 0), 1) * 100;
  const bar = value >= 0.75 ? "bg-emerald-400" : value >= 0.4 ? "bg-amber-400" : "bg-slate-500";
  return (
    <span className="h-1.5 w-24 overflow-hidden rounded-full bg-white/10">
      <span className={`block h-full rounded-full ${bar} transition-all duration-500`} style={{ width: `${pct}%` }} />
    </span>
  );
}

function Metric({ label, value, total, tone, icon }) {
  const tones = {
    emerald: { text: "text-emerald-300", bar: "bg-emerald-400", glow: "from-emerald-500/10" },
    rose: { text: "text-rose-300", bar: "bg-rose-400", glow: "from-rose-500/10" },
    slate: { text: "text-slate-300", bar: "bg-slate-400", glow: "from-slate-500/10" },
  };
  const t = tones[tone];
  const pct = total ? Math.round((value / total) * 100) : 0;
  return (
    <div className={`relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-b ${t.glow} to-transparent p-4`}>
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">{label}</span>
        <Icon name={icon} className={`h-4 w-4 ${t.text} opacity-70`} />
      </div>
      <div className={`mt-1 font-display text-3xl font-bold ${t.text}`}>{value}</div>
      <div className="mt-2.5 h-1 w-full overflow-hidden rounded-full bg-white/10">
        <div className={`h-full rounded-full ${t.bar}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
