# Pro Image Enhancer — Design Spec

Date: 2026-09-10

## Purpose

A real, production-quality web application that upscales and enhances images with open-source super-resolution. It is an enhancement tool, not a generative editor. Visible information and text are preserved; composition, layout, colors, and aspect ratio are unchanged. No cropping, rearranging, adding, removing, or inventing content.

## Priorities

1. Preserve visible information and text
2. Maximum genuine image quality
3. Preserve original composition, layout, colors, aspect ratio
4. No cropping / rearranging / inventing
5. Real AI super-resolution
6. Accurate output-format and resolution verification

## Architecture

```
browser (React + Vite + Tailwind)
  POST/GET /api/*  (Vite reverse proxy)
FastAPI API process :8000
  validation, jobs, storage, verification
background worker thread (in-process)
  classifier -> tiled ONNX Real-ESRGAN -> lossless encode -> independent verify
disk: data/jobs/{uuid}/original.*, output.*, meta.json
```

Redis and PostgreSQL are not used. They would consume RAM on the 8 GB target machine and are unnecessary for a single-node enhancer. Job state lives in memory with metadata mirrored to disk.

## Components

| Unit | Responsibility |
|------|----------------|
| `validation` | MIME, extension, size, dimensions, corruption, path safety |
| `dimensions` | Exact `width * scale`, `height * scale` for 2/4/6/8/10 |
| `resources` | Estimate output RAM/pixels; warn or block unsafe jobs |
| `classifier` | Heuristic screenshot/text vs photo (drives conservative settings) |
| `inference` | Real-ESRGAN ONNX via ONNX Runtime (CPU; CUDA if present) |
| `enhancer` | Tiled inference, overlap blend, exact spatial reconstruction |
| `verification` | Re-open output; magic bytes; actual WxH; actual scale; actual format |
| `jobs` | Create, progress, cancel, cleanup; never overwrite original |
| `storage` | UUID directories; delete temps on reset/TTL |

## Upscale

Output size is always `input_w * N` by `input_h * N` with N in {2,4,6,8,10}. Never hard-coded.

Real-ESRGAN x4 is the SR backbone (official `outscale` pattern): run 4x SR, then Lanczos only as needed to hit the exact requested N. This is genuine neural upscaling plus exact dimension targeting, not CSS or browser resize.

Screenshots / text: anime/video Real-ESRGAN variant when available (sharper edges, conservative). Photos: general x4plus variant when available. If only one model is present, it is used for all types; the classifier still records the detected type.

## Long screenshots

Very tall images are processed as tiles with overlap. Tiles are written back in original spatial order. Overlap is blended to avoid seams. Top, middle, and bottom are all processed; no skip, duplicate, or reorder.

## Output

User selects PNG or TIFF. Both are written lossless via Pillow (`PNG` RGB/RGBA, `TIFF` with compression=None or DEFLATE lossless). Format is verified from file magic, not the requested name. If TIFF write fails, the API reports the limitation and does not claim TIFF.

## Verification report (actual values only)

After processing the server re-opens the output file and reports:

- Actual format (from magic + decoder)
- Actual width and height
- Actual scale = actual/original on each axis
- Aspect ratio original vs output
- Orientation
- Crop check: scale_x ≈ scale_y and equals requested N
- Model name and device (cpu/cuda)

Never report requested values as actual values.

## Resource safety (8 GB / Intel i5 / Iris Xe)

- GPU is used only if ONNX Runtime reports a usable CUDA or DirectML provider. Intel Iris Xe is not assumed. CPU is the default.
- Estimate `out_w * out_h * 3` plus tile workspace. If estimated peak > 40% of available RAM, return a warning requiring explicit confirm. If > 70%, reject.
- Tile size adapts downward under memory pressure (128 → 64 → 32).
- Jobs can be cancelled between tiles. Temp files are deleted on cancel/reset.

## API

- `GET /api/health` — process, model loaded, device
- `POST /api/jobs` — multipart image + scale + format + confirm
- `GET /api/jobs/{id}` — status, progress, error, verification
- `POST /api/jobs/{id}/cancel`
- `GET /api/jobs/{id}/original` — original bytes (not overwritten)
- `GET /api/jobs/{id}/result` — processed bytes
- `DELETE /api/jobs/{id}` — cleanup

## Security

- Allowlisted extensions and decoded formats only: PNG, JPEG, WEBP, BMP, TIFF
- Content sniffed via Pillow + magic bytes; extension/MIME mismatch rejected
- Reject SVG, HTML, PDF, XML, polyglots, path traversal (`..`, absolute paths)
- Max upload 40 MB; max input pixels 40 MP unless confirmed
- UUID storage names only; no shell, no user path in commands
- Do not log pixels or filenames that could leak content
- No secrets in the frontend

## UI

OLED dark tool UI (violet primary `#7C3AED`, cyan accent `#0891B2`, background `#0F172A`). Poppins headings, Open Sans body. Lucide icons, no emoji icons.

Workflow: Upload → Preview → Settings → Process → Verify → Result → Download.

Includes drag-and-drop, file picker, before/after slider, zoom/pan/100% view, scale and format selectors, progress, cancel, reset, verification panel, resource warnings. Keyboard accessible, labeled controls, visible focus, `prefers-reduced-motion`.

## Testing

TDD for dimensions, validation, security, verification, tiling reconstruction, API, cancellation, and frontend production build. Acceptance math for 1080×2340 at every N. Integration inference on small real images with the actual ONNX model. Full 1080×2340 10× is a resource-warning case, not a CI default (252 MP).

## Limitations (honest)

- CPU inference is slow; 8×/10× of tall screenshots can take many minutes
- Iris Xe is not used unless a Vulkan/DirectML provider is actually present
- Real-ESRGAN does not guarantee pixel-perfect or 100% text preservation
- OCR is not used to rewrite the image
- 6×/10× use 4× SR + Lanczos to the exact target (Real-ESRGAN official outscale pattern)
