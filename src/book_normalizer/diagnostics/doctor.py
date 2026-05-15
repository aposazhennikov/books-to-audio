"""Preflight checks for local audiobook generation dependencies."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from book_normalizer.comfyui.client import ComfyUIClient
from book_normalizer.comfyui.workflow_builder import WorkflowBuilder, WorkflowBuilderError
from book_normalizer.tts.model_paths import default_comfyui_models_dir
from book_normalizer.tts.wsl_runtime import build_wsl_tts_activation_script


@dataclass
class DoctorCheck:
    """One preflight check result."""

    name: str
    status: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "status": self.status, "detail": self.detail}


def run_doctor(
    *,
    comfyui_url: str = "http://localhost:8188",
    llm_endpoint: str = "http://localhost:11434/v1",
    workflow_path: Path | None = None,
    models_dir: Path | None = None,
    skip_network: bool = False,
) -> list[DoctorCheck]:
    """Run local dependency checks."""
    workflow_path = workflow_path or Path("comfyui_workflows/qwen3_tts_template.json")
    models_dir = models_dir or default_comfyui_models_dir()

    checks = [
        _check_python(),
        _check_tesseract(),
        _check_wsl_venv(),
        _check_cuda_wsl(),
        _check_models_dir(models_dir),
        _check_workflow(workflow_path),
    ]

    if skip_network:
        checks.append(DoctorCheck("Ollama / LLM endpoint", "skip", "Skipped by --skip-network."))
        checks.append(DoctorCheck("ComfyUI", "skip", "Skipped by --skip-network."))
    else:
        checks.append(_check_llm_endpoint(llm_endpoint))
        checks.extend(_check_comfyui(comfyui_url))

    return checks


def checks_to_json(checks: list[DoctorCheck]) -> str:
    """Serialize checks as JSON."""
    return json.dumps([check.to_dict() for check in checks], ensure_ascii=False, indent=2)


def _check_python() -> DoctorCheck:
    version = ".".join(str(part) for part in sys.version_info[:3])
    return DoctorCheck("Python", "ok", version)


def _check_tesseract() -> DoctorCheck:
    try:
        import pytesseract

        version = pytesseract.get_tesseract_version()
        return DoctorCheck("Tesseract", "ok", f"Available via pytesseract: {version}")
    except Exception as exc:
        exe = shutil.which("tesseract")
        if exe:
            return DoctorCheck("Tesseract", "warn", f"Binary found at {exe}, pytesseract check failed: {exc}")
        return DoctorCheck("Tesseract", "warn", "Not found. OCR for scanned PDFs will be unavailable.")


def _check_wsl_venv() -> DoctorCheck:
    if not shutil.which("wsl"):
        return DoctorCheck("WSL TTS venv", "warn", "wsl.exe not found on PATH.")
    script = build_wsl_tts_activation_script() + "\npython - <<'PY'\nimport sys\nprint(sys.executable)\nPY"
    try:
        result = subprocess.run(
            ["wsl", "-e", "bash", "-lc", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
        )
    except Exception as exc:
        return DoctorCheck("WSL TTS venv", "warn", f"Could not inspect WSL venv: {exc}")
    if result.returncode != 0:
        return DoctorCheck("WSL TTS venv", "warn", (result.stderr or result.stdout).strip())
    return DoctorCheck("WSL TTS venv", "ok", result.stdout.strip().splitlines()[-1])


def _check_cuda_wsl() -> DoctorCheck:
    if not shutil.which("wsl"):
        return DoctorCheck("CUDA in WSL", "warn", "wsl.exe not found on PATH.")
    try:
        result = subprocess.run(
            ["wsl", "-e", "bash", "-lc", "command -v nvidia-smi >/dev/null && nvidia-smi -L"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
        )
    except Exception as exc:
        return DoctorCheck("CUDA in WSL", "warn", f"Could not run nvidia-smi: {exc}")
    if result.returncode != 0:
        return DoctorCheck("CUDA in WSL", "warn", "nvidia-smi is not available inside WSL.")
    return DoctorCheck("CUDA in WSL", "ok", result.stdout.strip() or "nvidia-smi succeeded.")


def _check_models_dir(models_dir: Path) -> DoctorCheck:
    expected = [
        "Qwen3-TTS-12Hz-1.7B-Base",
        "Qwen3-TTS-12Hz-1.7B-CustomVoice",
        "Qwen3-TTS-Tokenizer-12Hz",
    ]
    root = Path(models_dir)
    audio_encoders = root / "audio_encoders"
    if not root.exists():
        return DoctorCheck("Models dir", "warn", f"{root} does not exist.")
    missing = [name for name in expected if not (audio_encoders / name).exists()]
    if missing:
        return DoctorCheck("Models dir", "warn", f"{root}; missing in audio_encoders: {', '.join(missing)}")
    return DoctorCheck("Models dir", "ok", str(root))


def _check_workflow(workflow_path: Path) -> DoctorCheck:
    try:
        builder = WorkflowBuilder(workflow_path)
    except WorkflowBuilderError as exc:
        return DoctorCheck("ComfyUI workflow", "fail", str(exc))
    missing = builder.missing_placeholders()
    if missing:
        return DoctorCheck("ComfyUI workflow", "warn", f"Missing placeholders: {', '.join(missing)}")
    return DoctorCheck("ComfyUI workflow", "ok", str(workflow_path))


def _check_llm_endpoint(endpoint: str) -> DoctorCheck:
    try:
        import httpx

        resp = httpx.get(f"{endpoint.rstrip('/')}/models", timeout=5.0)
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        models = data.get("data", [])
        detail = f"{endpoint}; {len(models)} model(s)" if isinstance(models, list) else endpoint
        return DoctorCheck("Ollama / LLM endpoint", "ok", detail)
    except Exception as exc:
        return DoctorCheck("Ollama / LLM endpoint", "warn", f"{endpoint} is not reachable: {exc}")


def _check_comfyui(url: str) -> list[DoctorCheck]:
    client = ComfyUIClient(url)
    if not client.is_reachable():
        return [DoctorCheck("ComfyUI", "warn", f"{url} is not reachable.")]
    checks = [DoctorCheck("ComfyUI", "ok", url)]
    speakers = client.list_saved_speakers()
    if speakers:
        checks.append(DoctorCheck("ComfyUI saved speakers", "ok", ", ".join(speakers)))
    else:
        checks.append(
            DoctorCheck(
                "ComfyUI saved speakers",
                "warn",
                "No saved speakers reported by FB_Qwen3TTSLoadSpeaker.",
            )
        )
    return checks
