interface Props {
  progress: number;
  message: string;
  status: string;
}

export function ProgressPanel({ progress, message, status }: Props) {
  const pct = Math.round(progress * 100);
  return (
    <section className="rounded-2xl bg-muted p-5" aria-live="polite">
      <h2 className="font-heading text-lg">Process</h2>
      <p className="mt-2 text-sm capitalize text-white/70">{status}</p>
      <div className="mt-3 h-3 overflow-hidden rounded-full bg-background">
        <div className="h-full bg-primary transition-[width] duration-200" style={{ width: `${pct}%` }} />
      </div>
      <p className="mt-2 text-sm">{message || "Working"} — {pct}%</p>
    </section>
  );
}
