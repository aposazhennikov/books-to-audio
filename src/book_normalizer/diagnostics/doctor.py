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
from book_normalizer.llm.model_router import FALLBACK_QWEN3_MODEL, PRIMARY_QWEN3_MODEL
from book_normalizer.loaders.pdf_ocr_engine import available_tesseract_languages, tesseract_available
from book_normalizer.tts.local_runtime import check_tts_python
from book_normalizer.tts.model_paths import effective_comfyui_models_dir

WINDOWS_OCR_INSTALL_HINT = "install.bat --interactive --install-system-tools --download-tessdata"
POSIX_OCR_INSTALL_HINT = "./install.sh --interactive --install-system-tools --download-tessdata"
REQUIRED_TESSERACT_LANGS = ("eng", "rus", "chi_sim", "kaz", "uzb")


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
    llm_endpoint: str = "http://localhost:11434",
    workflow_path: Path | None = None,
    models_dir: Path | None = None,
    skip_network: bool = False,
) -> list[DoctorCheck]:
    """Run local dependency checks."""
    workflow_path = workflow_path or Path("comfyui_workflows/qwen3_tts_template.json")
    models_dir = models_dir or effective_comfyui_models_dir()

    checks = [
        _check_python(),
        _check_tesseract(),
        _check_tts_python(),
        _check_cuda_native(),
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
        available = tesseract_available()
    except Exception as exc:
        return DoctorCheck(
            "Tesseract",
            "warn",
            f"Runtime check failed: {exc}. Install native OCR tools: {_ocr_install_hint()}",
        )
    if not available:
        return DoctorCheck(
            "Tesseract",
            "warn",
            (
                "Not found in this OS. OCR for scanned PDFs is unavailable. "
                f"Install native OCR tools: {_ocr_install_hint()}"
            ),
        )

    languages = available_tesseract_languages()
    if not languages:
        return DoctorCheck(
            "Tesseract",
            "warn",
            f"Available, but language data could not be listed. Verify tessdata with: {_ocr_install_hint()}",
        )

    missing = [lang for lang in REQUIRED_TESSERACT_LANGS if lang not in languages]
    if missing:
        return DoctorCheck(
            "Tesseract",
            "warn",
            (
                f"Available, but missing OCR language data: {', '.join(missing)}. "
                f"Install/update tessdata: {_ocr_install_hint()}"
            ),
        )

    return DoctorCheck("Tesseract", "ok", f"Available with OCR languages: {', '.join(REQUIRED_TESSERACT_LANGS)}")


def _ocr_install_hint() -> str:
    return f"`{WINDOWS_OCR_INSTALL_HINT}` on Windows or `{POSIX_OCR_INSTALL_HINT}` on Linux/macOS"


def _check_tts_python() -> DoctorCheck:
    ok, detail = check_tts_python()
    if ok:
        return DoctorCheck("Local TTS Python", "ok", detail)
    return DoctorCheck("Local TTS Python", "warn", detail)


def _check_cuda_native() -> DoctorCheck:
    if not shutil.which("nvidia-smi"):
        return DoctorCheck("CUDA", "warn", "nvidia-smi not found on PATH.")
    try:
        result = subprocess.run(
            ["nvidia-smi", "-L"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            check=False,
        )
    except Exception as exc:
        return DoctorCheck("CUDA", "warn", f"Could not run nvidia-smi: {exc}")
    if result.returncode != 0:
        return DoctorCheck("CUDA", "warn", (result.stderr or result.stdout).strip() or "nvidia-smi failed.")
    return DoctorCheck("CUDA", "ok", result.stdout.strip() or "nvidia-smi succeeded.")


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
    base_url = endpoint.rstrip("/")
    try:
        import httpx

        version_resp = httpx.get(f"{base_url}/api/version", timeout=5.0)
        version_resp.raise_for_status()
        version_data: dict[str, Any] = version_resp.json()
        tags_resp = httpx.get(f"{base_url}/api/tags", timeout=5.0)
        tags_resp.raise_for_status()
        tags_data: dict[str, Any] = tags_resp.json()
        models = tags_data.get("models", [])
        version = str(version_data.get("version") or "unknown")
        if isinstance(models, list):
            model_names = _ollama_model_names(models)
            preview = ", ".join(model_names[:3])
            suffix = f": {preview}" if preview else ""
            detail = f"{base_url}; native Ollama {version}; {len(models)} model(s){suffix}"
            missing = _missing_default_ollama_models(model_names)
            if missing:
                return DoctorCheck(
                    "Ollama / LLM endpoint",
                    "warn",
                    (
                        f"{detail}. Missing default Qwen3 model(s): {', '.join(missing)}. "
                        "Install natively with `install.bat --interactive --download-ollama-models` "
                        "on Windows or `./install.sh --interactive --download-ollama-models` "
                        "on Linux/macOS."
                    ),
                )
        else:
            detail = f"{base_url}; native Ollama {version}"
        return DoctorCheck("Ollama / LLM endpoint", "ok", detail)
    except Exception as exc:
        return DoctorCheck(
            "Ollama / LLM endpoint",
            "warn",
            (
                f"{base_url} native Ollama API is not reachable: {exc}. "
                "Start Ollama Desktop on Windows, or run `ollama serve` in a native Linux/macOS terminal."
            ),
        )


def _ollama_model_names(models: list[Any]) -> list[str]:
    """Return model names from Ollama /api/tags response records."""
    names: list[str] = []
    for model in models:
        if not isinstance(model, dict):
            continue
        name = model.get("name") or model.get("model")
        if name:
            names.append(str(name))
    return names


def _missing_default_ollama_models(model_names: list[str]) -> list[str]:
    """Return default Qwen3 models that are not installed in native Ollama."""
    installed = {name.lower() for name in model_names}
    required = [PRIMARY_QWEN3_MODEL, FALLBACK_QWEN3_MODEL]
    return [model for model in required if model.lower() not in installed]


def _check_comfyui(url: str) -> list[DoctorCheck]:
    client = ComfyUIClient(url)
    if not client.is_reachable():
        return [
            DoctorCheck(
                "ComfyUI",
                "warn",
                (
                    f"{url} is not reachable. Start ComfyUI, then run "
                    f"`python scripts/live_tts_smoke.py --comfyui-url {url} "
                    "--workflow comfyui_workflows/qwen3_tts_template.json` "
                    "to verify one small synthesis before a full book run."
                ),
            )
        ]
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
