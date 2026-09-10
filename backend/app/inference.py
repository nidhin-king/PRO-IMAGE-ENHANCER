from __future__ import annotations

import os
import urllib.request
from pathlib import Path

import numpy as np

ONNX_CANDIDATES = [
    os.environ.get("PIE_MODEL_URL", ""),
]

MODEL_SCALE = 4


class InferenceEngine:
    def __init__(self, models_dir: Path, use_stub: bool = False) -> None:
        self.models_dir = Path(models_dir)
        # Vercel's project bundle is read-only. The bundled model already exists
        # in data/models, so never try to mkdir it during function startup.
        if not self.models_dir.exists() and self.models_dir != Path(os.environ.get("PIE_MODELS_DIR", str(self.models_dir))):
            self.models_dir = Path("/tmp/pie/models")
        if not self.models_dir.exists():
            try:
                self.models_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                self.models_dir = Path("/tmp/pie/models")
                self.models_dir.mkdir(parents=True, exist_ok=True)
        self.use_stub = use_stub
        self.session = None
        self.device = "cpu"
        self.model_name = "stub-nearest" if use_stub else "pending"
        self.input_name = None
        self.output_name = None
        self.input_channels = 3
        self.input_layout = "NCHW"
        self.load_error: str | None = None
        if not use_stub:
            try:
                self._load()
            except Exception as exc:
                self.load_error = str(exc)
                self.model_name = "unavailable"

    def _providers(self) -> list[str]:
        try:
            import onnxruntime as ort
        except ImportError:
            return []
        available = ort.get_available_providers()
        preferred = []
        for name in ("CUDAExecutionProvider", "DmlExecutionProvider", "CPUExecutionProvider"):
            if name in available:
                preferred.append(name)
        return preferred or ["CPUExecutionProvider"]

    def _load(self) -> None:
        import onnxruntime as ort

        model_path = self._ensure_model()
        providers = self._providers()
        if not providers:
            raise RuntimeError("onnxruntime is not available in this deployment")
        so = ort.SessionOptions()
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        intra = max(1, min(4, os.cpu_count() or 2))
        so.intra_op_num_threads = intra
        so.inter_op_num_threads = 1
        self.session = ort.InferenceSession(str(model_path), sess_options=so, providers=providers)
        inp = self.session.get_inputs()[0]
        self.input_name = inp.name
        self.output_name = self.session.get_outputs()[0].name
        shape = list(inp.shape)
        if len(shape) == 4:
            if shape[1] in (1, 3) or shape[1] is None:
                self.input_layout = "NCHW"
                self.input_channels = 3 if shape[1] in (3, None) else 1
                if shape[1] == 1:
                    self.input_channels = 1
            elif shape[-1] in (1, 3):
                self.input_layout = "NHWC"
                self.input_channels = 1 if shape[-1] == 1 else 3
        self.model_name = model_path.name
        provider = self.session.get_providers()[0]
        self.device = "cuda" if "CUDA" in provider else "dml" if "Dml" in provider else "cpu"
        self.load_error = None

    def _ensure_model(self) -> Path:
        env_path = os.environ.get("PIE_MODEL_PATH")
        if env_path and Path(env_path).exists():
            return Path(env_path)

        existing = sorted(self.models_dir.glob("*.onnx"))
        for path in existing:
            if path.stat().st_size > 10_000:
                return path

        last_error = "No model URL configured"
        target = self.models_dir / "super-resolution-x4.onnx"
        for url in ONNX_CANDIDATES:
            if not url:
                continue
            try:
                tmp = target.with_suffix(".onnx.part")
                urllib.request.urlretrieve(url, tmp)
                if tmp.exists() and tmp.stat().st_size > 10_000:
                    tmp.replace(target)
                    return target
                if tmp.exists():
                    tmp.unlink()
            except Exception as exc:
                last_error = str(exc)
        raise RuntimeError(f"Failed to obtain a super-resolution ONNX model: {last_error}")

    def infer_tile(self, tile: np.ndarray) -> np.ndarray:
        if self.use_stub or self.session is None:
            if not self.use_stub:
                raise RuntimeError(
                    self.load_error
                    or "Super-resolution model is not loaded. Place an ONNX model at PIE_MODEL_PATH."
                )
            return np.repeat(np.repeat(tile, MODEL_SCALE, axis=0), MODEL_SCALE, axis=1)

        rgb = tile[:, :, :3].astype(np.float32) / 255.0
        if self.input_channels == 1:
            y = _rgb_to_y(rgb)
            tensor = y[None, None, ...] if self.input_layout == "NCHW" else y[None, ..., None]
            outputs = self.session.run([self.output_name], {self.input_name: tensor})[0]
            y_up = outputs[0, 0] if outputs.ndim == 4 and outputs.shape[1] == 1 else outputs.squeeze()
            y_up = np.clip(y_up, 0, 1)
            cbcr = _downsample_chroma(rgb, y_up.shape[1], y_up.shape[0])
            out = _ycbcr_to_rgb(y_up, cbcr[..., 0], cbcr[..., 1])
        else:
            if self.input_layout == "NCHW":
                tensor = np.transpose(rgb, (2, 0, 1))[None, ...]
            else:
                tensor = rgb[None, ...]
            outputs = self.session.run([self.output_name], {self.input_name: tensor})[0]
            if outputs.ndim == 4:
                if outputs.shape[1] in (1, 3):
                    out = np.transpose(outputs[0], (1, 2, 0))
                else:
                    out = outputs[0]
            else:
                out = outputs
            if out.shape[-1] == 1:
                out = np.repeat(out, 3, axis=-1)
            out = np.clip(out, 0, 1)

        out = np.clip(out * 255.0, 0, 255).astype(np.uint8)
        h, w = tile.shape[0] * MODEL_SCALE, tile.shape[1] * MODEL_SCALE
        if out.shape[0] != h or out.shape[1] != w:
            from PIL import Image

            out = np.array(Image.fromarray(out).resize((w, h), Image.Resampling.LANCZOS))
        return out

    def health(self) -> dict:
        return {
            "model": self.model_name,
            "device": self.device,
            "stub": self.use_stub,
            "model_scale": MODEL_SCALE,
            "load_error": self.load_error,
            "input_channels": self.input_channels,
        }


def _rgb_to_y(rgb: np.ndarray) -> np.ndarray:
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def _downsample_chroma(rgb: np.ndarray, width: int, height: int) -> np.ndarray:
    from PIL import Image

    y = _rgb_to_y(rgb)
    cb = (rgb[..., 2] - y) * 0.564 + 0.5
    cr = (rgb[..., 0] - y) * 0.713 + 0.5
    chroma = np.stack([cb, cr], axis=-1)
    img = Image.fromarray(np.clip(chroma * 255.0, 0, 255).astype(np.uint8), mode="LA")
    resized = np.array(img.resize((width, height), Image.Resampling.BICUBIC)).astype(np.float32) / 255.0
    return resized


def _ycbcr_to_rgb(y: np.ndarray, cb: np.ndarray, cr: np.ndarray) -> np.ndarray:
    r = y + 1.403 * (cr - 0.5)
    g = y - 0.344 * (cb - 0.5) - 0.714 * (cr - 0.5)
    b = y + 1.773 * (cb - 0.5)
    return np.stack([r, g, b], axis=-1)
