import type { Verification } from "../types";

export function VerificationPanel({ report }: { report: Verification }) {
  const rows = [
    ["Image format", report.actual_format ?? "unknown"],
    ["Resolution", report.actual_width && report.actual_height ? `${report.actual_width} x ${report.actual_height} px` : "unavailable"],
    [
      "Upscale",
      report.scale_x && report.scale_y
        ? `${report.original_width} x ${report.original_height} → ${report.actual_width} x ${report.actual_height} = ${report.scale_x}x / ${report.scale_y}x`
        : "unavailable",
    ],
    ["Original resolution", `${report.original_width} x ${report.original_height} px`],
    ["Orientation", report.orientation],
    ["Matches requested scale", report.matches_requested_scale ? "Yes" : "No"],
    ["Format matches request", report.format_matches_request ? "Yes" : "No"],
    ["Crop detected", report.cropped ? "Yes" : "No"],
    ["Model", report.model ?? "n/a"],
    ["Device", report.device ?? "n/a"],
  ];
  return (
    <section className="rounded-2xl bg-muted p-5" aria-labelledby="verify-heading">
      <h2 id="verify-heading" className="font-heading text-lg">
        Verify
      </h2>
      <p className="mt-2 text-sm text-white/70">{report.message}</p>
      <dl className="mt-4 space-y-2">
        {rows.map(([label, value]) => (
          <div key={label} className="grid grid-cols-1 gap-1 sm:grid-cols-3">
            <dt className="text-sm text-white/60">{label}</dt>
            <dd className="font-mono text-sm sm:col-span-2">{value}</dd>
          </div>
        ))}
      </dl>
      <pre className="mt-4 overflow-x-auto whitespace-pre-wrap rounded-xl bg-background p-3 text-xs text-white/80">
        {report.summary}
      </pre>
    </section>
  );
}
