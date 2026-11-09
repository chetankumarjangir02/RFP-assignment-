// Shared UI primitives + inline SVG icon set for the RFP Intelligence Platform.
// Keeps panel components declarative and visually consistent.

export function Spinner({ className = "h-4 w-4" }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none">
      <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3.5" />
      <path
        className="opacity-90"
        d="M22 12a10 10 0 0 1-10 10"
        stroke="currentColor"
        strokeWidth="3.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

// Section heading used at the top of each panel.
export function PanelHeader({ icon, title, subtitle }) {
  return (
    <div className="flex items-start gap-3.5">
      {icon && (
        <div className="grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-white/10 bg-white/5 text-brand-300 shadow-inner">
          <Icon name={icon} className="h-5 w-5" />
        </div>
      )}
      <div>
        <h2 className="font-display text-lg font-semibold text-white">{title}</h2>
        {subtitle && <p className="mt-0.5 max-w-xl text-sm leading-relaxed text-slate-400">{subtitle}</p>}
      </div>
    </div>
  );
}

export function Field({ label, children }) {
  return (
    <label className="block">
      <span className="field-label">{label}</span>
      {children}
    </label>
  );
}

// Dismissible-style alert used for errors/info.
export function Alert({ tone = "error", children }) {
  const tones = {
    error: "border-rose-500/25 bg-rose-500/10 text-rose-200",
    success: "border-emerald-500/25 bg-emerald-500/10 text-emerald-200",
    info: "border-brand-400/25 bg-brand-500/10 text-brand-100",
  };
  const icon = { error: "alert", success: "check", info: "info" }[tone];
  return (
    <div className={`flex items-start gap-2.5 rounded-xl border px-3.5 py-3 text-sm ${tones[tone]} animate-fade-in`}>
      <Icon name={icon} className="mt-0.5 h-4 w-4 shrink-0 opacity-80" />
      <div className="leading-relaxed">{children}</div>
    </div>
  );
}

// Shown on Search/Ask/Extract when no bid has been uploaded/indexed yet.
export function NeedBid({ onUpload }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-white/10 bg-white/[0.015] px-6 py-14 text-center">
      <div className="mb-4 grid h-14 w-14 place-items-center rounded-2xl border border-white/10 bg-white/5 text-brand-300">
        <Icon name="upload" className="h-6 w-6" />
      </div>
      <p className="font-medium text-slate-300">No bid uploaded yet</p>
      <p className="mt-1 max-w-sm text-sm text-slate-500">
        Upload a bid folder first — every tab then works on that bid automatically.
      </p>
      {onUpload && (
        <button onClick={onUpload} className="btn btn-primary mt-5">
          <Icon name="upload" className="h-4 w-4" />
          Go to Upload
        </button>
      )}
    </div>
  );
}

export function EmptyState({ icon = "sparkles", title, hint }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-white/10 bg-white/[0.015] px-6 py-14 text-center">
      <div className="mb-4 grid h-14 w-14 place-items-center rounded-2xl border border-white/10 bg-white/5 text-slate-500">
        <Icon name={icon} className="h-6 w-6" />
      </div>
      <p className="font-medium text-slate-300">{title}</p>
      {hint && <p className="mt-1 max-w-sm text-sm text-slate-500">{hint}</p>}
    </div>
  );
}

// Minimal dependency-free icon set (Lucide-style strokes).
const PATHS = {
  upload: <><path d="M12 15V3" /><path d="m7 8 5-5 5 5" /><path d="M5 21h14a2 2 0 0 0 2-2v-3" /><path d="M3 16v3a2 2 0 0 0 2 2" /></>,
  search: <><circle cx="11" cy="11" r="7" /><path d="m21 21-4.3-4.3" /></>,
  chat: <><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></>,
  extract: <><path d="M14 3v4a2 2 0 0 0 2 2h4" /><path d="M5 3h9l5 5v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z" /><path d="M9 13h6" /><path d="M9 17h4" /></>,
  folder: <><path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2z" /></>,
  download: <><path d="M12 3v12" /><path d="m7 10 5 5 5-5" /><path d="M5 21h14" /></>,
  check: <path d="M20 6 9 17l-5-5" />,
  alert: <><path d="M12 9v4" /><path d="M12 17h.01" /><path d="M10.3 3.9 2 18a2 2 0 0 0 1.7 3h16.6a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" /></>,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5" /><path d="M12 8h.01" /></>,
  sparkles: <><path d="M12 3v4M12 17v4M3 12h4M17 12h4" /><path d="m6.3 6.3 2.4 2.4M15.3 15.3l2.4 2.4M17.7 6.3l-2.4 2.4M8.7 15.3l-2.4 2.4" /></>,
  bolt: <path d="M13 2 3 14h8l-1 8 10-12h-8z" />,
  doc: <><path d="M14 3v4a2 2 0 0 0 2 2h4" /><path d="M5 3h9l5 5v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z" /></>,
  layers: <><path d="m12 2 9 5-9 5-9-5 9-5z" /><path d="m3 12 9 5 9-5" /><path d="m3 17 9 5 9-5" /></>,
};

export function Icon({ name, className = "h-5 w-5" }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {PATHS[name] || PATHS.doc}
    </svg>
  );
}
