from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.inference import InferenceEngine
from app.jobs import JobError, JobManager, output_media_type
from app.storage import JobStorage

REPO_ROOT = Path(__file__).resolve().parents[2]
# Render and Vercel provide writable temporary storage at /tmp. Keep the
# bundled ONNX model in the repository and store per-job files in /tmp.
DATA_DIR = Path(os.environ.get("PIE_DATA_DIR", "/tmp/pie/jobs"))
MODELS_DIR = Path(os.environ.get("PIE_MODELS_DIR", str(REPO_ROOT / "data" / "models")))


def _use_stub() -> bool:
    return os.environ.get("PIE_USE_STUB_INFER", "0") in {"1", "true", "TRUE", "yes"}


def create_app() -> FastAPI:
    storage = JobStorage(DATA_DIR)
    engine = InferenceEngine(MODELS_DIR, use_stub=_use_stub())
    manager = JobManager(storage, engine)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        manager.start()
        yield
        manager.stop()

    app = FastAPI(title="Pro Image Enhancer", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.manager = manager
    app.state.engine = engine

    @app.exception_handler(JobError)
    async def job_error_handler(_request, exc: JobError):
        payload = {"detail": str(exc), **exc.extra}
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.get("/")
    def root():
        return {
            "name": "Pro Image Enhancer API",
            "status": "ok",
            "health": "/api/health",
            "docs": "/docs",
            "api": "/api",
        }

    @app.get("/api/health")
    def health():
        info = engine.health()
        return {"ok": True, **info}

    @app.post("/api/jobs", status_code=202)
    async def create_job(
        file: UploadFile = File(...),
        scale: int = Form(...),
        output_format: str = Form("PNG"),
        confirm: bool = Form(False),
    ):
        data = await file.read()
        job = manager.create_job(
            filename=file.filename or "upload.png",
            content_type=file.content_type or "",
            data=data,
            scale=scale,
            output_format=output_format,
            confirmed=confirm,
        )
        return job.public_dict()

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str):
        return manager.get(job_id).public_dict()

    @app.post("/api/jobs/{job_id}/cancel")
    def cancel_job(job_id: str):
        return manager.cancel(job_id).public_dict()

    @app.delete("/api/jobs/{job_id}")
    def delete_job(job_id: str):
        manager.delete(job_id)
        return {"ok": True}

    @app.get("/api/jobs/{job_id}/original")
    def download_original(job_id: str):
        path = manager.original_path(job_id)
        return FileResponse(path, media_type=output_media_type(path), filename=path.name)

    @app.get("/api/jobs/{job_id}/result")
    def download_result(job_id: str):
        path = manager.result_path(job_id)
        return FileResponse(path, media_type=output_media_type(path), filename=path.name)

    return app


# uvicorn app.main:create_app --factory
