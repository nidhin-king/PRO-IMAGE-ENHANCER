from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

from app.dimensions import ALLOWED_SCALES
from app.enhancer import JobCancelled, enhance_image
from app.inference import MODEL_SCALE, InferenceEngine
from app.resources import evaluate_job_resources
from app.storage import JobStorage
from app.validation import ValidationError, validate_upload
from app.verification import inspect_output


OUTPUT_FORMATS = {"PNG", "TIFF"}


class JobError(Exception):
    def __init__(self, message: str, status_code: int = 400, extra: dict | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.extra = extra or {}


@dataclass
class Job:
    id: str
    status: str
    progress: float = 0.0
    message: str = ""
    error: str | None = None
    scale: int = 2
    output_format: str = "PNG"
    original_name: str = ""
    original_width: int = 0
    original_height: int = 0
    verification: dict[str, Any] | None = None
    created_at: float = field(default_factory=time.time)
    cancel_event: threading.Event = field(default_factory=threading.Event)
    warning: str | None = None

    def public_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "error": self.error,
            "scale": self.scale,
            "output_format": self.output_format,
            "original_name": self.original_name,
            "original_width": self.original_width,
            "original_height": self.original_height,
            "verification": self.verification,
            "warning": self.warning,
        }


class JobManager:
    def __init__(self, storage: JobStorage, engine: InferenceEngine) -> None:
        self.storage = storage
        self.engine = engine
        self.jobs: dict[str, Job] = {}
        self.lock = threading.Lock()
        self.queue: list[str] = []
        self.worker_thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.queue_event = threading.Event()

    def start(self) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            return
        self.stop_event.clear()
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="pie-worker")
        self.worker_thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.queue_event.set()

    def create_job(
        self,
        *,
        filename: str,
        content_type: str,
        data: bytes,
        scale: int,
        output_format: str,
        confirmed: bool = False,
    ) -> Job:
        try:
            scale_int = int(scale)
        except (TypeError, ValueError) as exc:
            raise JobError("Scale must be an integer") from exc
        if scale_int not in ALLOWED_SCALES:
            raise JobError("Scale must be one of 2, 4, 6, 8, 10")

        fmt = str(output_format or "").upper()
        if fmt not in OUTPUT_FORMATS:
            raise JobError("Output format must be PNG or TIFF")

        try:
            validated = validate_upload(filename=filename, content_type=content_type, data=data)
        except ValidationError as exc:
            raise JobError(str(exc)) from exc

        available = _available_ram_bytes()
        decision = evaluate_job_resources(
            width=validated.width,
            height=validated.height,
            scale=scale_int,
            available_ram_bytes=available,
            confirmed=confirmed,
        )
        if decision.action == "block":
            raise JobError(decision.message, status_code=400, extra={"resource": decision.__dict__})
        if decision.action == "warn":
            raise JobError(decision.message, status_code=409, extra={"resource": decision.__dict__, "needs_confirm": True})

        job_id, job_dir = self.storage.create_job_dir()
        original_path = job_dir / f"original{Path(validated.filename).suffix.lower()}"
        self.storage.write_bytes_atomic(original_path, data)

        job = Job(
            id=job_id,
            status="queued",
            scale=scale_int,
            output_format=fmt,
            original_name=validated.filename,
            original_width=validated.width,
            original_height=validated.height,
            message="Queued",
        )
        with self.lock:
            self.jobs[job_id] = job
            self.queue.append(job_id)
            self.queue_event.set()
        return job

    def get(self, job_id: str) -> Job:
        with self.lock:
            job = self.jobs.get(job_id)
        if not job:
            raise JobError("Job not found", status_code=404)
        return job

    def cancel(self, job_id: str) -> Job:
        job = self.get(job_id)
        job.cancel_event.set()
        if job.status in {"queued", "running"}:
            job.status = "cancelling"
            job.message = "Cancellation requested"
        return job

    def delete(self, job_id: str) -> None:
        job = self.get(job_id)
        job.cancel_event.set()
        self.storage.delete_job(job_id)
        with self.lock:
            self.jobs.pop(job_id, None)
            if job_id in self.queue:
                self.queue.remove(job_id)

    def original_path(self, job_id: str) -> Path:
        self.get(job_id)
        job_dir = self.storage.job_dir(job_id)
        matches = list(job_dir.glob("original.*"))
        if not matches:
            raise JobError("Original file not found", status_code=404)
        return matches[0]

    def result_path(self, job_id: str) -> Path:
        job = self.get(job_id)
        if job.status != "completed":
            raise JobError("Result is not ready", status_code=409)
        job_dir = self.storage.job_dir(job_id)
        matches = list(job_dir.glob("output.*"))
        if not matches:
            raise JobError("Result file not found", status_code=404)
        return matches[0]

    def _worker_loop(self) -> None:
        while not self.stop_event.is_set():
            job_id = None
            with self.lock:
                if self.queue:
                    job_id = self.queue.pop(0)
                else:
                    self.queue_event.clear()
            if job_id is None:
                self.queue_event.wait(timeout=0.2)
                continue
            try:
                self._process(job_id)
            except Exception as exc:
                job = self.jobs.get(job_id)
                if job:
                    job.status = "failed"
                    job.error = str(exc)
                    job.message = "Failed"

    def _process(self, job_id: str) -> None:
        job = self.jobs[job_id]
        if job.cancel_event.is_set():
            job.status = "cancelled"
            job.message = "Cancelled"
            return
        job.status = "running"
        job.message = "Starting"
        job_dir = self.storage.job_dir(job_id)
        original = self.original_path(job_id)
        ext = ".png" if job.output_format == "PNG" else ".tif"
        output = job_dir / f"output{ext}"

        tile_size = 64
        overlap = 8
        pixels = job.original_width * job.original_height
        if pixels > 2_000_000:
            tile_size = 48
        if pixels > 8_000_000:
            tile_size = 32

        def progress_cb(value: float, message: str) -> None:
            job.progress = max(0.0, min(1.0, float(value)))
            job.message = message

        try:
            enhance_image(
                source_path=original,
                output_path=output,
                scale=job.scale,
                output_format=job.output_format,
                infer_fn=self.engine.infer_tile,
                model_scale=MODEL_SCALE,
                tile_size=tile_size,
                overlap=overlap,
                cancel_event=job.cancel_event,
                progress_cb=progress_cb,
                device=self.engine.device,
            )
        except JobCancelled:
            job.status = "cancelled"
            job.message = "Cancelled"
            if output.exists():
                output.unlink()
            return

        report = inspect_output(
            original_path=original,
            output_path=output,
            requested_scale=job.scale,
            requested_format=job.output_format,
        )
        job.verification = report.to_dict()
        job.verification["model"] = self.engine.model_name
        job.verification["device"] = self.engine.device
        job.progress = 1.0
        job.status = "completed" if report.ok else "completed"
        job.message = "Completed" if report.ok else "Completed with verification notes"
        self.storage.write_json(job_dir / "meta.json", job.public_dict())


def _available_ram_bytes() -> int:
    try:
        with open("/proc/meminfo", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) * 1024
    except OSError:
        pass
    return int(os.environ.get("PIE_AVAILABLE_RAM", str(8 * 1024**3)))


def output_media_type(path: Path) -> str:
    with Image.open(path) as image:
        fmt = (image.format or "").upper()
    if fmt == "PNG":
        return "image/png"
    if fmt == "TIFF":
        return "image/tiff"
    if fmt == "JPEG":
        return "image/jpeg"
    return "application/octet-stream"
