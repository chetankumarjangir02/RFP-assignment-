import { useRef, useState } from "react";
import { uploadBid } from "../api.js";
import { PanelHeader, Field, Alert, Spinner, Icon } from "./ui.jsx";

// Folder upload via <input webkitdirectory>. The chosen folder's name becomes bid_id.
export default function UploadPanel({ onIndexed }) {
  const inputRef = useRef(null);
  const [bidId, setBidId] = useState("");
  const [files, setFiles] = useState([]);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  function ingest(picked) {
    setFiles(picked);
    setError("");
    setResult(null);
    const first = picked[0];
    if (first && first.webkitRelativePath) {
      setBidId(first.webkitRelativePath.split("/")[0]);
    }
  }

  function onPick(e) {
    ingest(Array.from(e.target.files || []));
  }

  async function submit() {
    if (!bidId || files.length === 0) {
      setError("Pick a folder (it must contain the bid's PDF/HTML files).");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const res = await uploadBid(bidId, files);
      setResult(res);
      onIndexed?.(res);
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setBusy(false);
    }
  }

  const supported = files.filter((f) => /\.(pdf|html?)$/i.test(f.name));

  return (
    <div className="space-y-6">
      <PanelHeader
        icon="upload"
        title="Upload a bid folder"
        subtitle="Select the folder with the bid's documents (PDF / HTML). Files are saved on the server and indexed incrementally. The first upload downloads the embedding model."
      />

      {/* Dropzone */}
      <div className="group relative overflow-hidden rounded-2xl border-2 border-dashed border-white/12 bg-white/[0.02] px-6 py-10 text-center transition-all duration-300 hover:border-brand-400/40 hover:bg-brand-500/[0.04]">
        <input
          ref={inputRef}
          type="file"
          multiple
          webkitdirectory=""
          directory=""
          onChange={onPick}
          className="hidden"
        />
        <div className="mx-auto mb-4 grid h-16 w-16 place-items-center rounded-2xl border border-white/10 bg-white/5 text-brand-300 transition-transform duration-300 group-hover:scale-105 group-hover:animate-float">
          <Icon name="folder" className="h-7 w-7" />
        </div>
        <button onClick={() => inputRef.current?.click()} className="btn btn-primary">
          <Icon name="upload" className="h-4 w-4" />
          Choose folder…
        </button>
        <p className="mt-3 text-xs text-slate-500">PDF & HTML · RFP, addendums, specs, affidavits</p>

        {files.length > 0 && (
          <div className="mx-auto mt-6 max-w-md animate-fade-up rounded-xl border border-white/10 bg-base-900/50 px-4 py-3 text-left">
            <div className="flex items-center gap-2 text-sm">
              <Icon name="folder" className="h-4 w-4 text-brand-300" />
              <span className="font-semibold text-white">{bidId}</span>
              <span className="ml-auto font-mono text-xs text-slate-400">
                {supported.length}/{files.length} supported
              </span>
            </div>
            <div className="mt-2 max-h-28 space-y-1 overflow-y-auto pr-1">
              {files.slice(0, 20).map((f, i) => {
                const ok = /\.(pdf|html?)$/i.test(f.name);
                return (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <Icon
                      name={ok ? "doc" : "alert"}
                      className={`h-3.5 w-3.5 shrink-0 ${ok ? "text-slate-500" : "text-amber-400/70"}`}
                    />
                    <span className={`truncate ${ok ? "text-slate-400" : "text-slate-600 line-through"}`}>
                      {f.name}
                    </span>
                  </div>
                );
              })}
              {files.length > 20 && <p className="pl-5 text-xs text-slate-600">+{files.length - 20} more…</p>}
            </div>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
        <div className="sm:w-52">
          <Field label="bid_id">
            <input value={bidId} onChange={(e) => setBidId(e.target.value)} placeholder="Bid1" className="input" />
          </Field>
        </div>
        <button onClick={submit} disabled={busy} className="btn btn-primary sm:ml-auto sm:w-auto">
          {busy ? (
            <>
              <Spinner /> Uploading & indexing…
            </>
          ) : (
            <>
              <Icon name="bolt" className="h-4 w-4" /> Upload & index
            </>
          )}
        </button>
      </div>

      {error && <Alert tone="error">{error}</Alert>}
      {result && (
        <Alert tone="success">
          Indexed <b>{result.indexed_chunks}</b> chunks from <b>{result.saved?.length || 0}</b> file(s) into{" "}
          <b className="font-mono">{result.bid_id}</b>.
          {result.skipped?.length > 0 && <> Skipped {result.skipped.length} unsupported file(s).</>}
        </Alert>
      )}
    </div>
  );
}
