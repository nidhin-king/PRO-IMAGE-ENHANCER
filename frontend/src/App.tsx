import { useEffect, useMemo, useState } from "react";
import { Download, RotateCcw, Square, Sparkles, X } from "lucide-react";
import { cancelJob, createJob, deleteJob, fetchHealth, getJob, originalUrl, resultUrl } from "./api";
import { CompareView } from "./components/CompareView";
import { DropZone } from "./components/DropZone";
import { ProgressPanel } from "./components/ProgressPanel";
import { SettingsPanel } from "./components/SettingsPanel";
import { VerificationPanel } from "./components/VerificationPanel";
import type { Health, Job, OutputFormat, Scale } from "./types";

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [dims, setDims] = useState({ width: 0, height: 0 });
  const [scale, setScale] = useState<Scale>(2);
  const [outputFormat, setOutputFormat] = useState<OutputFormat>("PNG");
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetchHealth().then(setHealth).catch((err) => setError(String(err.message || err)));
  }, []);

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    const image = new Image();
    image.onload = () => setDims({ width: image.naturalWidth, height: image.naturalHeight });
    image.src = url;
    return () => URL.revokeObjectURL(url);
  }, [file]);

  useEffect(() => {
    if (!job || (job.status !== "queued" && job.status !== "running" && job.status !== "cancelling")) {
      return;
    }
    const timer = window.setInterval(async () => {
      try {
        const next = await getJob(job.id);
        setJob(next);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to poll job");
      }
    }, 700);
    return () => window.clearInterval(timer);
  }, [job]);

  const afterUrl = useMemo(() => {
    if (job?.status === "completed") return resultUrl(job.id);
    return null;
  }, [job]);

  const beforeUrl = job ? originalUrl(job.id) : previewUrl;

  async function start(confirm = false) {
    if (!file) return;
    setError(null);
    setBusy(true);
    try {
      const created = await createJob({ file, scale, outputFormat, confirm });
      setJob(created);
    } catch (err) {
      const typed = err as Error & { needsConfirm?: boolean };
      if (typed.needsConfirm && window.confirm(`${typed.message}\n\nContinue anyway?`)) {
        await start(true);
        return;
      }
      setError(typed.message);
    } finally {
      setBusy(false);
    }
  }

  async function onCancel() {
    if (!job) return;
    setJob(await cancelJob(job.id));
  }

  async function onReset() {
    if (job) {
      try {
        await deleteJob(job.id);
      } catch {
        /* still reset UI */
      }
    }
    setFile(null);
    setJob(null);
    setError(null);
    setDims({ width: 0, height: 0 });
  }

  const processing = job?.status === "queued" || job?.status === "running" || job?.status === "cancelling";

  return (
    <div className="min-h-dvh bg-background text-foreground">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:bg-primary focus:px-3 focus:py-2">
        Skip to main content
      </a>
      <header className="border-b border-white/10 px-4 py-5 sm:px-8">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-accent">Real super-resolution</p>
            <h1 className="font-heading text-2xl sm:text-3xl">Pro Image Enhancer</h1>
          </div>
          <p className="text-sm text-white/60">
            {health ? `Model: ${health.model} · Device: ${health.device}` : "Checking engine…"}
          </p>
        </div>
      </header>
      <main id="main" className="mx-auto grid max-w-6xl gap-6 px-4 py-6 sm:px-8 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-6">
          {!file ? (
            <DropZone onFile={setFile} />
          ) : beforeUrl ? (
            <CompareView
              beforeUrl={beforeUrl}
              afterUrl={afterUrl}
              altBefore="Original uploaded image"
              altAfter="Enhanced output"
            />
          ) : null}
          {job && (processing || job.status === "completed" || job.status === "failed") ? (
            <ProgressPanel progress={job.progress} message={job.message} status={job.status} />
          ) : null}
          {job?.verification ? <VerificationPanel report={job.verification} /> : null}
        </div>
        <aside className="space-y-4">
          {file && dims.width > 0 ? (
            <SettingsPanel
              width={dims.width}
              height={dims.height}
              scale={scale}
              outputFormat={outputFormat}
              onScale={setScale}
              onFormat={setOutputFormat}
              disabled={processing}
            />
          ) : (
            <section className="rounded-2xl bg-muted p-5">
              <h2 className="font-heading text-lg">Workflow</h2>
              <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-white/75">
                <li>Upload</li>
                <li>Preview</li>
                <li>Settings</li>
                <li>Process</li>
                <li>Verify</li>
                <li>Result</li>
                <li>Download</li>
              </ol>
            </section>
          )}
          {error ? (
            <div className="rounded-2xl border border-danger/40 bg-danger/10 p-4" role="alert">
              <p className="text-sm">{error}</p>
              <button
                type="button"
                className="mt-3 inline-flex min-h-11 cursor-pointer items-center gap-2 text-sm underline"
                onClick={() => setError(null)}
              >
                <X className="h-4 w-4" aria-hidden="true" />
                Clear error
              </button>
            </div>
          ) : null}
          <div className="flex flex-col gap-2">
            <button
              type="button"
              className="inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-xl bg-primary px-4 font-semibold text-on-primary transition-opacity duration-200 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!file || busy || processing}
              onClick={() => start(false)}
            >
              <Sparkles className="h-4 w-4" aria-hidden="true" />
              Enhance
            </button>
            <button
              type="button"
              className="inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-xl bg-background px-4 font-semibold transition-opacity duration-200 disabled:cursor-not-allowed disabled:opacity-40"
              disabled={!processing}
              onClick={onCancel}
            >
              <Square className="h-4 w-4" aria-hidden="true" />
              Cancel
            </button>
            {job?.status === "completed" ? (
              <a
                className="inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-xl bg-accent px-4 font-semibold"
                href={resultUrl(job.id)}
                download={`enhanced.${outputFormat === "TIFF" ? "tif" : "png"}`}
              >
                <Download className="h-4 w-4" aria-hidden="true" />
                Download
              </a>
            ) : null}
            <button
              type="button"
              className="inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-xl border border-white/10 px-4 font-semibold"
              onClick={onReset}
            >
              <RotateCcw className="h-4 w-4" aria-hidden="true" />
              Reset
            </button>
          </div>
          <p className="text-xs leading-relaxed text-white/50">
            Conservative enhancement only. Text is not rewritten, translated, or spell-checked. Output size is the actual
            input size multiplied by the selected factor. Verification inspects the saved file, not the request.
          </p>
        </aside>
      </main>
    </div>
  );
}
