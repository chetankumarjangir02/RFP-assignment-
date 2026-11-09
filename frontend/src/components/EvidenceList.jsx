// Renders ranked evidence passages with citations + metadata badges.
export default function EvidenceList({ items }) {
  if (!items || items.length === 0) {
    return <p className="text-sm text-slate-500">No passages returned.</p>;
  }
  return (
    <div className="space-y-3">
      {items.map((ev, i) => {
        const m = ev.metadata || {};
        return (
          <div key={ev.chunk_id || i} className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
              <span className="font-semibold text-slate-700">
                {m.file_name || "?"} · p.{m.page_number ?? "?"}
              </span>
              {m.bid_id && <Badge>{m.bid_id}</Badge>}
              {m.doc_type && <Badge tone="violet">{m.doc_type}</Badge>}
              {m.addendum_number != null && <Badge tone="amber">add. {m.addendum_number}</Badge>}
              {typeof ev.score === "number" && (
                <span className="ml-auto text-slate-400">score {ev.score.toFixed(3)}</span>
              )}
            </div>
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-600">
              {ev.text}
            </p>
          </div>
        );
      })}
    </div>
  );
}

function Badge({ children, tone = "slate" }) {
  const tones = {
    slate: "bg-slate-100 text-slate-600",
    violet: "bg-violet-100 text-violet-700",
    amber: "bg-amber-100 text-amber-700",
  };
  return <span className={`rounded px-1.5 py-0.5 font-medium ${tones[tone]}`}>{children}</span>;
}
