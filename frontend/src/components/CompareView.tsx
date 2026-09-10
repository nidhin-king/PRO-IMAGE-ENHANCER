import { useEffect, useRef, useState, type PointerEvent } from "react";

interface Props {
  beforeUrl: string;
  afterUrl: string | null;
  altBefore: string;
  altAfter: string;
}

export function CompareView({ beforeUrl, afterUrl, altBefore, altAfter }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [split, setSplit] = useState(50);
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number } | null>(null);

  useEffect(() => {
    setOffset({ x: 0, y: 0 });
    setZoom(1);
  }, [beforeUrl, afterUrl]);

  function onPointerMove(event: PointerEvent<HTMLDivElement>) {
    if (drag.current) {
      setOffset((prev) => ({
        x: prev.x + (event.clientX - drag.current!.x),
        y: prev.y + (event.clientY - drag.current!.y),
      }));
      drag.current = { x: event.clientX, y: event.clientY };
      return;
    }
    const box = containerRef.current?.getBoundingClientRect();
    if (!box) return;
    const next = ((event.clientX - box.left) / box.width) * 100;
    setSplit(Math.min(100, Math.max(0, next)));
  }

  return (
    <section className="rounded-2xl bg-muted p-4" aria-label="Before and after comparison">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-heading text-lg">Preview</h2>
        <div className="flex gap-2">
          <button
            type="button"
            className="min-h-11 cursor-pointer rounded-lg bg-background px-3 text-sm hover:bg-background/80"
            onClick={() => setZoom((z) => Math.min(8, z * 1.25))}
          >
            Zoom in
          </button>
          <button
            type="button"
            className="min-h-11 cursor-pointer rounded-lg bg-background px-3 text-sm hover:bg-background/80"
            onClick={() => setZoom((z) => Math.max(0.25, z / 1.25))}
          >
            Zoom out
          </button>
          <button
            type="button"
            className="min-h-11 cursor-pointer rounded-lg bg-background px-3 text-sm hover:bg-background/80"
            onClick={() => {
              setZoom(1);
              setOffset({ x: 0, y: 0 });
            }}
          >
            100%
          </button>
        </div>
      </div>
      <div
        ref={containerRef}
        className="relative h-[min(70dvh,640px)] overflow-hidden rounded-xl bg-black"
        onPointerMove={onPointerMove}
        onPointerDown={(event) => {
          if (event.shiftKey) {
            drag.current = { x: event.clientX, y: event.clientY };
            (event.currentTarget as HTMLDivElement).setPointerCapture(event.pointerId);
          }
        }}
        onPointerUp={() => {
          drag.current = null;
        }}
      >
        <div
          className="absolute inset-0"
          style={{ transform: `translate(${offset.x}px, ${offset.y}px) scale(${zoom})`, transformOrigin: "center center" }}
        >
          <img src={beforeUrl} alt={altBefore} className="absolute inset-0 h-full w-full object-contain" />
          {afterUrl ? (
            <img
              src={afterUrl}
              alt={altAfter}
              className="absolute inset-0 h-full w-full object-contain"
              style={{ clipPath: `inset(0 ${100 - split}% 0 0)` }}
            />
          ) : null}
        </div>
        {afterUrl ? (
          <div className="pointer-events-none absolute inset-y-0 w-0.5 bg-accent" style={{ left: `${split}%` }} />
        ) : null}
      </div>
      {afterUrl ? (
        <label className="mt-3 flex items-center gap-3 text-sm text-white/70">
          Before / after slider
          <input
            type="range"
            min={0}
            max={100}
            value={split}
            onChange={(event) => setSplit(Number(event.target.value))}
            className="w-full accent-accent"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(split)}
          />
        </label>
      ) : (
        <p className="mt-3 text-sm text-white/60">Hold Shift and drag to pan. Process the image to unlock the comparison slider.</p>
      )}
    </section>
  );
}
