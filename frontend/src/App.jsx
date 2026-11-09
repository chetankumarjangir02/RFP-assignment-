import { useEffect, useState, useCallback } from "react";
import { health, listBids } from "./api.js";
import UploadPanel from "./components/UploadPanel.jsx";
import SearchPanel from "./components/SearchPanel.jsx";
import AskPanel from "./components/AskPanel.jsx";
import ExtractPanel from "./components/ExtractPanel.jsx";
import { Icon } from "./components/ui.jsx";

const TABS = [
  { id: "upload", label: "Upload", icon: "upload", Comp: UploadPanel, blurb: "Ingest & index a bid folder" },
  { id: "search", label: "Search", icon: "search", Comp: SearchPanel, blurb: "Hybrid retrieval over chunks" },
  { id: "ask", label: "Ask", icon: "chat", Comp: AskPanel, blurb: "Cited Q&A over the corpus" },
  { id: "extract", label: "Extract", icon: "extract", Comp: ExtractPanel, blurb: "20-field structured record" },
];

export default function App() {
  const [tab, setTab] = useState("upload");
  const [online, setOnline] = useState(null);
  const [bid, setBid] = useState(""); // shared active bid across every tab
  const [bids, setBids] = useState([]); // indexed bids for the switcher

  const refreshBids = useCallback(async () => {
    try {
      const { bids } = await listBids();
      setBids(bids || []);
      // Auto-select the first indexed bid if none is active yet.
      setBid((cur) => cur || (bids && bids[0]) || "");
    } catch {
      /* backend offline — leave as-is */
    }
  }, []);

  useEffect(() => {
    let alive = true;
    const check = () =>
      health()
        .then(() => {
          if (!alive) return;
          const was = online;
          setOnline(true);
          if (was !== true) refreshBids();
        })
        .catch(() => alive && setOnline(false));
    check();
    const t = setInterval(check, 8000);
    return () => {
      alive = false;
      clearInterval(t);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshBids]);

  const active = TABS.find((t) => t.id === tab);
  const Active = active.Comp;

  // After an upload, adopt the new bid everywhere and refresh the list.
  function handleIndexed(res) {
    if (res?.bid_id) setBid(res.bid_id);
    refreshBids();
  }

  const panelProps = {
    bid,
    onIndexed: handleIndexed,
    refreshBids,
    goToUpload: () => setTab("upload"),
  };

  return (
    <div className="relative flex min-h-screen flex-col">
      <div
        className="pointer-events-none fixed inset-0 bg-grid-faint opacity-60"
        style={{ backgroundSize: "44px 44px", maskImage: "radial-gradient(ellipse at 50% 0%, black, transparent 75%)" }}
      />

      <div className="relative mx-auto flex w-full max-w-7xl flex-1 flex-col gap-6 px-4 py-6 lg:flex-row lg:gap-8 lg:px-8 lg:py-10">
        {/* ---------- Sidebar ---------- */}
        <aside className="lg:w-72 lg:shrink-0">
          <div className="lg:sticky lg:top-10 space-y-5">
            <Brand />
            <StatusCard online={online} bid={bid} />
            <nav className="glass hidden p-2 lg:block">
              {TABS.map((t) => (
                <NavItem key={t.id} {...t} active={tab === t.id} onClick={() => setTab(t.id)} />
              ))}
            </nav>
            <p className="hidden px-2 text-xs leading-relaxed text-slate-600 lg:block">
              Hybrid RAG · multi-agent extraction · every answer grounded in cited passages.
            </p>
          </div>

          {/* mobile tabs */}
          <nav className="glass mt-4 flex gap-1 p-1.5 lg:hidden">
            {TABS.map((t) => (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg px-2 py-2 text-xs font-semibold transition ${
                  tab === t.id ? "bg-brand-gradient text-white shadow-glow-sm" : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <Icon name={t.icon} className="h-4 w-4" />
                {t.label}
              </button>
            ))}
          </nav>
        </aside>

        {/* ---------- Main canvas ---------- */}
        <main className="min-w-0 flex-1">
          <div key={tab} className="glass animate-fade-up p-6 sm:p-8">
            <Active {...panelProps} />
          </div>
        </main>
      </div>

      {/* Footer — centered across the full screen width */}
      <footer className="relative flex items-center justify-center gap-2 px-4 pb-8 text-center text-base text-slate-400">
        Submitted by <span className="font-semibold text-slate-200">Chetan Kumar Jangir</span>
        <span className="text-slate-500">· AI Engineer</span>
      </footer>
    </div>
  );
}

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <div className="relative grid h-11 w-11 place-items-center rounded-2xl bg-brand-gradient shadow-glow">
        <Icon name="bolt" className="h-5 w-5 text-white" />
        <span className="absolute -inset-1 -z-10 rounded-2xl bg-brand-gradient opacity-40 blur-lg" />
      </div>
      <div className="leading-tight">
        <h1 className="font-display text-base font-bold tracking-tight text-white">
          RFP <span className="gradient-text">Intelligence</span>
        </h1>
        <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-slate-500">Platform</p>
      </div>
    </div>
  );
}

function StatusCard({ online, bid }) {
  const state =
    online === null
      ? { dot: "bg-slate-500", ring: "", label: "Connecting…", text: "text-slate-400" }
      : online
        ? { dot: "bg-emerald-400", ring: "animate-pulse-ring", label: "Backend online", text: "text-emerald-300" }
        : { dot: "bg-rose-500", ring: "", label: "Backend offline", text: "text-rose-300" };
  return (
    <div className="glass flex items-center gap-3 px-4 py-3">
      <span className={`h-2.5 w-2.5 rounded-full ${state.dot} ${state.ring}`} />
      <div className="min-w-0 flex-1">
        <p className={`text-sm font-semibold ${state.text}`}>{state.label}</p>
        <p className="truncate text-xs text-slate-500">
          {bid ? <>active bid · <span className="font-mono text-slate-400">{bid}</span></> : "no bid uploaded yet"}
        </p>
      </div>
    </div>
  );
}

function NavItem({ icon, label, blurb, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-all duration-200 ${
        active ? "bg-white/[0.07] shadow-inner" : "hover:bg-white/[0.04]"
      }`}
    >
      <span
        className={`grid h-9 w-9 place-items-center rounded-lg transition-all duration-200 ${
          active
            ? "bg-brand-gradient text-white shadow-glow-sm"
            : "border border-white/10 bg-white/5 text-slate-400 group-hover:text-slate-200"
        }`}
      >
        <Icon name={icon} className="h-[18px] w-[18px]" />
      </span>
      <span className="min-w-0">
        <span className={`block text-sm font-semibold ${active ? "text-white" : "text-slate-300"}`}>{label}</span>
        <span className="block truncate text-xs text-slate-500">{blurb}</span>
      </span>
      {active && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-brand-400" />}
    </button>
  );
}
