import { useState } from "react";
import { ask } from "../api.js";
import EvidenceList from "./EvidenceList.jsx";
import { PanelHeader, Alert, Spinner, EmptyState, NeedBid, Icon } from "./ui.jsx";

const SAMPLES = [
  "What is the submission deadline after all addendums?",
  "What changed in Addendum 1?",
  "Compare the bid bond requirements across bids.",
];

export default function AskPanel({ bid = "", goToUpload }) {
  const [question, setQuestion] = useState("");
  const bidId = bid;
  const [answer, setAnswer] = useState(null);
  const [evidence, setEvidence] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    if (!question) return;
    setBusy(true);
    setError("");
    setAnswer(null);
    try {
      const res = await ask(question, bidId);
      setAnswer(res.answer);
      setEvidence(res.evidence || []);
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
          icon="chat"
          title="Ask a question"
          subtitle="Natural-language answers grounded in — and cited back to — the uploaded documents."
        />
        <NeedBid onUpload={goToUpload} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PanelHeader
        icon="chat"
        title="Ask a question"
        subtitle={
          <>
            Cited answers grounded in <span className="font-mono text-brand-300">{bid}</span> — addendum-aware, never
            guessed.
          </>
        }
      />

      <div className="relative">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => (e.key === "Enter" && (e.metaKey || e.ctrlKey) ? run() : null)}
          rows={3}
          placeholder="What is the submission deadline for Bid1 after all addendums?"
          className="textarea resize-none"
        />
        <span className="pointer-events-none absolute bottom-2.5 right-3 text-[10px] font-medium text-slate-600">
          ⌘ + ↵ to ask
        </span>
      </div>

      {/* Sample prompts */}
      <div className="flex flex-wrap gap-2">
        {SAMPLES.map((s) => (
          <button
            key={s}
            onClick={() => setQuestion(s)}
            className="chip border border-white/10 bg-white/5 text-slate-400 transition hover:border-brand-400/40 hover:text-slate-200"
          >
            <Icon name="sparkles" className="h-3 w-3 opacity-70" />
            {s}
          </button>
        ))}
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <button onClick={run} disabled={busy || !question} className="btn btn-primary sm:ml-auto">
          {busy ? (
            <>
              <Spinner /> Thinking…
            </>
          ) : (
            <>
              <Icon name="bolt" className="h-4 w-4" /> Ask
            </>
          )}
        </button>
      </div>

      {error && <Alert tone="error">{error}</Alert>}

      {answer != null && (
        <div className="animate-fade-up space-y-5">
          <div className="relative overflow-hidden rounded-2xl border border-brand-400/20 bg-brand-500/[0.06] p-5">
            <span className="absolute inset-y-0 left-0 w-1 bg-brand-gradient" />
            <div className="mb-2 flex items-center gap-2">
              <Icon name="sparkles" className="h-4 w-4 text-brand-300" />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-brand-200">Answer</h3>
            </div>
            <p className="whitespace-pre-wrap text-[15px] leading-relaxed text-slate-100">{answer}</p>
          </div>

          <div>
            <h3 className="mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
              <Icon name="layers" className="h-3.5 w-3.5" /> Evidence
            </h3>
            <EvidenceList items={evidence} />
          </div>
        </div>
      )}
      {answer == null && !busy && !error && (
        <EmptyState icon="chat" title="Ask anything about the bids" hint="Answers always come with the passages they were grounded in." />
      )}
    </div>
  );
}
