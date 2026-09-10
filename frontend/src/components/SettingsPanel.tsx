import { SCALES, expectedOutputSize, type OutputFormat, type Scale } from "../types";

interface Props {
  width: number;
  height: number;
  scale: Scale;
  outputFormat: OutputFormat;
  onScale: (scale: Scale) => void;
  onFormat: (format: OutputFormat) => void;
  disabled?: boolean;
}

export function SettingsPanel({
  width,
  height,
  scale,
  outputFormat,
  onScale,
  onFormat,
  disabled,
}: Props) {
  const out = expectedOutputSize(width, height, scale);
  return (
    <section className="rounded-2xl bg-muted p-5" aria-labelledby="settings-heading">
      <h2 id="settings-heading" className="font-heading text-lg">
        Settings
      </h2>
      <fieldset className="mt-4" disabled={disabled}>
        <legend className="text-sm text-white/70">Upscale factor</legend>
        <div className="mt-3 grid grid-cols-5 gap-2">
          {SCALES.map((value) => {
            const selected = value === scale;
            return (
              <button
                key={value}
                type="button"
                className={`min-h-11 cursor-pointer rounded-xl px-2 py-2 text-sm font-semibold transition-colors duration-200 ${
                  selected ? "bg-primary text-on-primary shadow-glow" : "bg-background/60 text-white hover:bg-background"
                }`}
                aria-pressed={selected}
                onClick={() => onScale(value)}
              >
                {value}x
              </button>
            );
          })}
        </div>
      </fieldset>
      <fieldset className="mt-5" disabled={disabled}>
        <legend className="text-sm text-white/70">Lossless output format</legend>
        <div className="mt-3 grid grid-cols-2 gap-2">
          {(["PNG", "TIFF"] as OutputFormat[]).map((fmt) => {
            const selected = fmt === outputFormat;
            return (
              <button
                key={fmt}
                type="button"
                className={`min-h-11 cursor-pointer rounded-xl px-3 py-2 text-sm font-semibold transition-colors duration-200 ${
                  selected ? "bg-accent text-white" : "bg-background/60 text-white hover:bg-background"
                }`}
                aria-pressed={selected}
                onClick={() => onFormat(fmt)}
              >
                {fmt}
              </button>
            );
          })}
        </div>
      </fieldset>
      <p className="mt-4 font-mono text-sm text-white/80" aria-live="polite">
        {width} x {height} → {out.width} x {out.height} px
      </p>
    </section>
  );
}
