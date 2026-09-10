# Pro Image Enhancer

Real AI image enhancement and upscaling for screenshots, long scrolling captures, documents, and photos.

This is not a mock. The backend runs tiled Real-ESRGAN (ONNX Runtime) on CPU by default, writes lossless PNG or TIFF, and independently verifies the actual output file.

## Architecture

```
React + Vite + Tailwind  (port 5173, exposed)
        |
        |  /api  reverse proxy
        v
FastAPI  (port 8000, localhost)
        |
        +-- validation, resource checks, job queue
        +-- in-process worker
              +-- image classifier (screenshot vs photo)
              +-- tiled ONNX Real-ESRGAN x4
              +-- Lanczos to exact requested N (2/4/6/8/10)
              +-- lossless PNG or TIFF
              +-- independent verification of the saved file
```

Redis and PostgreSQL are intentionally not used. They would consume RAM on the 8 GB target machine. Job metadata lives in memory and on disk under `data/jobs/{uuid}/`.

## Priorities

1. Preserve visible information and text
2. Maximum genuine image quality
3. Preserve composition, layout, colors, and aspect ratio
4. No cropping, rearranging, adding, removing, or inventing content
5. Real super-resolution
6. Accurate format and resolution verification

The original file is never overwritten.

## Upscale math

Output size is always `input_width * N` by `input_height * N`.

Example for 1080 x 2340:

- 2x = 2160 x 4680
- 4x = 4320 x 9360
- 6x = 6480 x 14040
- 8x = 8640 x 18720
- 10x = 10800 x 23400

## Installation

### Backend

```bash
# Python 3.11+
pip3 install --break-system-packages -r backend/requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

### AI model

Export the official compact Real-ESRGAN x4v3 weights to ONNX (CPU):

```bash
pip3 install --break-system-packages torch onnx --index-url https://download.pytorch.org/whl/cpu
python3 backend/scripts/export_realesrgan_onnx.py
```

This writes `data/models/realesr-general-x4v3.onnx`. You can also set `PIE_MODEL_PATH` to any compatible x4 ONNX file.

For tests only, set `PIE_USE_STUB_INFER=1` to use a nearest-neighbor x4 stand-in. Do not use the stub in production.

## Environment variables

| Name | Meaning |
|------|---------|
| `PIE_DATA_DIR` | Job storage directory (default `data/jobs`) |
| `PIE_MODELS_DIR` | Model directory (default `data/models`) |
| `PIE_MODEL_PATH` | Explicit ONNX model path |
| `PIE_MODEL_URL` | Download URL if the model is absent |
| `PIE_USE_STUB_INFER` | `1` to skip ONNX (tests only) |
| `PIE_AVAILABLE_RAM` | Override RAM bytes used by the safety check |

## CPU / GPU

- Default device is CPU via ONNX Runtime.
- CUDA or DirectML is used only if ONNX Runtime actually reports that provider.
- Intel Iris Xe is not assumed. There is no fake GPU path.
- Target hardware: Windows 11, Intel Core i5-1235U, 8 GB RAM, Iris Xe. Large 8x/10x jobs are warned or blocked instead of crashing.

## Run

```bash
# both services (frontend is the exposed port)
bash start.sh
```

Or separately:

```bash
# backend
cd backend
python3 -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000

# frontend
cd frontend
npm run dev
```

Frontend proxies `/api` to `http://127.0.0.1:8000`.

## Vercel (frontend only)

Vercel can host the React UI. It cannot run the FastAPI Real-ESRGAN worker (long CPU jobs, ONNX, tiled inference).

```bash
# from repo root
npx vercel --prod --yes
```

Root Directory is the repo root. `vercel.json` builds `frontend` and publishes `frontend/dist`.

To point the deployed UI at a separately hosted API, set:

```text
VITE_API_BASE_URL=https://your-api-host.example
```

in the Vercel project environment, then redeploy. Leave it empty for local Vite proxy use.

## Testing

```bash
cd backend && python3 -m pytest tests -q
cd frontend && npm test && npm run build
```

Acceptance tests cover upload validation, PNG/TIFF, every scale factor, dimension math, long screenshots, cancellation, security, and API jobs.

Full 1080 x 2340 at 10x is 252 megapixels. CI uses smaller images plus exact scale math. The resource guard warns or blocks unsafe jobs on 8 GB machines.

## API

- `GET /api/health`
- `POST /api/jobs` multipart: `file`, `scale`, `output_format`, `confirm`
- `GET /api/jobs/{id}`
- `POST /api/jobs/{id}/cancel`
- `GET /api/jobs/{id}/original`
- `GET /api/jobs/{id}/result`
- `DELETE /api/jobs/{id}`

## Supported formats

Input: PNG, JPEG, WebP, BMP, TIFF

Output: lossless PNG or TIFF (verified from file magic, not the request)

## Limitations

- Real-ESRGAN does not guarantee pixel-perfect or 100% text preservation.
- OCR is not used to rewrite the image.
- 6x/8x/10x use 4x neural SR plus Lanczos to the exact requested size (Real-ESRGAN official outscale pattern).
- CPU inference of tall screenshots at 8x/10x can take many minutes and a lot of RAM.
- If TIFF encoding fails, the API reports the limitation instead of labeling a PNG as TIFF.

## Troubleshooting

- `model: unavailable` — download or copy a Real-ESRGAN x4 ONNX file into `data/models/`.
- 409 on create — the job needs explicit confirm because of the memory estimate.
- 400 "exceeds the safe memory budget" — reduce scale or image size.
- Slow jobs — lower scale, use a smaller tile automatically selected by the worker, or run on a machine with more RAM.
