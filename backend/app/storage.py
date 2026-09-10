from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from pathlib import Path


class JobStorage:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def create_job_dir(self) -> tuple[str, Path]:
        job_id = str(uuid.uuid4())
        path = self.root / job_id
        path.mkdir(parents=True, exist_ok=False)
        return job_id, path

    def job_dir(self, job_id: str) -> Path:
        path = (self.root / job_id).resolve()
        if self.root.resolve() not in path.parents and path != self.root.resolve():
            raise ValueError("Invalid job id")
        return path

    def write_bytes_atomic(self, path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
            Path(tmp_name).replace(path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    def write_json(self, path: Path, payload: dict) -> None:
        self.write_bytes_atomic(path, json.dumps(payload, indent=2).encode("utf-8"))

    def delete_job(self, job_id: str) -> None:
        path = self.job_dir(job_id)
        if path.exists():
            shutil.rmtree(path)
