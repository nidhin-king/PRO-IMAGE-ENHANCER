# Pro Image Enhancer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a real FastAPI + React image enhancer that runs Real-ESRGAN ONNX (CPU fallback), writes lossless PNG/TIFF, and reports independently verified dimensions and formats.

**Architecture:** Vite frontend proxies `/api` to FastAPI. Jobs run on an in-process worker with tiled ONNX inference, exact N× dimension targeting, resource warnings, cancellation, and post-process verification that re-opens the output file.

**Tech Stack:** React, Vite, TypeScript, Tailwind CSS, Python, FastAPI, Pillow, NumPy, ONNX Runtime, pytest.

## Global Constraints

- Output size is always `input_width * N` × `input_height * N` for N in {2,4,6,8,10}; never hard-code dimensions.
- Never overwrite the original file.
- Report actual format/size from the output file, never the requested values.
- CPU-only must work; do not assume NVIDIA CUDA.
- Conservative enhancement only: no generative rewrite of text or content.
- Vite `server.proxy['/api']` → `http://localhost:8000` and `allowedHosts: ['.monkeycode-ai.live']`.
- No Redis/PostgreSQL (8 GB RAM target).
- Honest limitations if a provider/model is unavailable.

## File map

- `backend/app/dimensions.py` — scale math
- `backend/app/validation.py` — upload safety
- `backend/app/resources.py` — RAM/pixel guards
- `backend/app/classifier.py` — screenshot vs photo heuristic
- `backend/app/tiling.py` — tile grid + overlap blend
- `backend/app/inference.py` — ONNX Real-ESRGAN session
- `backend/app/enhancer.py` — pipeline orchestration
- `backend/app/verification.py` — independent inspect
- `backend/app/storage.py` / `jobs.py` / `main.py` — API
- `frontend/` — React UI
- `start.sh` — both services
