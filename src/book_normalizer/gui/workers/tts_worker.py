"""Background workers for v2 TTS synthesis and voice preparation."""

from __future__ import annotations

import json
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from book_normalizer.gui.i18n import t
from book_normalizer.languages import normalize_book_language
from book_normalizer.tts.model_download import MODEL_DOWNLOAD_WARNING, install_tts_models
from book_normalizer.tts.synthesis_controller import SynthesisController, SynthesisRequest


class ExportSegmentsWorker(QThread):
    """Export voice-annotated segments from a processed book."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(
        self,
        book: object,
        output_dir: Path,
        speaker_mode: str = "heuristic",
        llm_endpoint: str = "",
        llm_model: str = "",
        llm_api_key: str = "",
        stress_mode: str = "double_vowel",
        parent=None,
    ):
        super().__init__(parent)
        self._book = book
        self._output_dir = output_dir
        self._speaker_mode = speaker_mode
        self._llm_endpoint = llm_endpoint
        self._llm_model = llm_model
        self._llm_api_key = llm_api_key
        self._stress_mode = stress_mode

    def run(self) -> None:
        try:
            from book_normalizer.chunking.llm_segmenter import LlmVoiceSegmenter
            from book_normalizer.chunking.voice_splitter import extract_segments_book
            from book_normalizer.dialogue.attribution import SpeakerMode, create_attributor
            from book_normalizer.dialogue.detector import DialogueDetector
            from book_normalizer.stress.rendering import render_annotated_chapters_for_tts

            metadata = getattr(self._book, "metadata", None)
            language = normalize_book_language(getattr(metadata, "language", "ru"))
            if self._speaker_mode == "llm":
                self.progress.emit(t("voice.attributing", mode=self._speaker_mode))
                segmenter = LlmVoiceSegmenter(
                    endpoint=self._llm_endpoint or "http://localhost:11434",
                    model=self._llm_model or "",
                    api_key=self._llm_api_key or "",
                    language=language,
                    cache_dir=self._output_dir / "speaker_cache",
                    review_report_path=self._output_dir / "llm_voice_review_report.json",
                    max_segment_chars=600,
                )

                def report(done: int, total: int, label: str) -> None:
                    self.progress.emit(f"LLM voice markup: {done}/{total} ({label})")

                manifest = segmenter.segment_book(self._book, progress_callback=report)
            else:
                self.progress.emit(t("voice.detecting_dialogue"))
                annotated = DialogueDetector().detect_book(self._book)

                if self._speaker_mode != "manual":
                    self.progress.emit(t("voice.attributing", mode=self._speaker_mode))
                    attributor = create_attributor(
                        SpeakerMode(self._speaker_mode),
                        cache_dir=self._output_dir / "speaker_cache",
                        llm_endpoint=self._llm_endpoint or "",
                        llm_model=self._llm_model or "",
                        llm_api_key=self._llm_api_key or "",
                    )
                    attributor.attribute(annotated)

                render_annotated_chapters_for_tts(annotated, self._book, self._stress_mode)
                self.progress.emit(t("voice.extracting_segments"))
                manifest = [
                    {
                        "segment_index": segment.segment_index,
                        "chapter_index": segment.chapter_index,
                        "language": language,
                        "is_dialogue": segment.is_dialogue,
                        "role": segment.role.value,
                        "voice_id": segment.voice_id,
                        "intonation": segment.intonation,
                        "text": segment.text,
                        "pause_after_ms": segment.pause_after_ms,
                        "boundary_after": segment.boundary_after,
                    }
                    for segment in extract_segments_book(annotated)
                ]

            self._output_dir.mkdir(parents=True, exist_ok=True)
            manifest_path = self._output_dir / "segments_manifest.json"
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            self.progress.emit(t("voice.exported_segments", n=len(manifest)))
            self.finished.emit(str(manifest_path))
        except Exception as exc:
            self.error.emit(str(exc))


class TTSSynthesisWorker(QThread):
    """Qt adapter for the v2 ComfyUI synthesis controller."""

    progress = pyqtSignal(int, int, str, int, int, float, int, int, int)
    status = pyqtSignal(str)
    log_line = pyqtSignal(str)
    finished = pyqtSignal(str, int, int)
    error = pyqtSignal(str)

    def __init__(
        self,
        manifest_path: Path,
        output_dir: Path,
        model: str = "",
        chapter: int | None = None,
        batch_size: int = 1,
        resume: bool = False,
        chunk_timeout: int = 300,
        use_compile: bool = False,
        clone_config: str = "",
        use_sage_attention: bool = False,
        models_dir: str = "",
        voice_library_dir: str = "",
        comfyui_url: str = "http://localhost:8188",
        workflow_path: str = "",
        failed_only: bool = False,
        temperature: float = 1.0,
        top_p: float = 0.8,
        top_k: int = 20,
        repetition_penalty: float = 1.05,
        max_new_tokens: int = 2048,
        seed: int = -1,
        speech_rate: float = 1.0,
        output_format: str = "flac",
        merge_chapters: bool = True,
        parent=None,
    ):
        super().__init__(parent)
        self._manifest_path = manifest_path
        self._output_dir = output_dir
        self._chapter = chapter
        self._chunk_timeout = chunk_timeout
        self._comfyui_url = comfyui_url
        self._workflow_path = workflow_path
        self._failed_only = failed_only
        self._merge_chapters = merge_chapters
        self._cancelled = False

        # Accepted for source compatibility with older GUI/tests. V2 synthesis
        # is driven by the manifest and ComfyUI workflow, not runner flags.
        self._unused_runner_options = {
            "model": model,
            "batch_size": batch_size,
            "resume": resume,
            "use_compile": use_compile,
            "clone_config": clone_config,
            "use_sage_attention": use_sage_attention,
            "models_dir": models_dir,
            "voice_library_dir": voice_library_dir,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "repetition_penalty": repetition_penalty,
            "max_new_tokens": max_new_tokens,
            "seed": seed,
            "speech_rate": speech_rate,
            "output_format": output_format,
        }

    def cancel(self) -> None:
        """Request cancellation before the next controller step."""
        self._cancelled = True

    def run(self) -> None:
        try:
            if self._cancelled:
                self.error.emit(t("synth.cancelled"))
                return

            workflow = Path(self._workflow_path) if self._workflow_path else (
                Path(__file__).resolve().parents[4] / "comfyui_workflows" / "qwen3_tts_template.json"
            )
            request = SynthesisRequest(
                manifest_path=self._manifest_path,
                output_dir=self._output_dir,
                workflow_path=workflow,
                comfyui_url=self._comfyui_url or "http://localhost:8188",
                chapter=self._chapter,
                chunk_timeout=float(self._chunk_timeout),
                failed_only=self._failed_only,
                merge_chapters=self._merge_chapters,
            )
            controller = SynthesisController(
                request,
                progress=self.progress.emit,
                status=self.status.emit,
                log=self.log_line.emit,
            )
            result = controller.run()
            if self._cancelled:
                self.error.emit(t("synth.cancelled"))
                return
            self.finished.emit(str(result.audio_dir), result.synthesized, result.skipped)
        except Exception as exc:
            self.error.emit(str(exc))


class TTSModelInstallWorker(QThread):
    """Download selected Hugging Face TTS models into the configured model dir."""

    status = pyqtSignal(str)
    log_line = pyqtSignal(str)
    finished = pyqtSignal(str, int, int)
    error = pyqtSignal(str)

    def __init__(self, model_ids: list[str], models_dir: Path, parent=None) -> None:
        super().__init__(parent)
        self._model_ids = model_ids
        self._models_dir = models_dir

    def run(self) -> None:
        try:
            self.status.emit(MODEL_DOWNLOAD_WARNING)
            self.log_line.emit(MODEL_DOWNLOAD_WARNING)
            results = install_tts_models(self._model_ids, self._models_dir, progress=self.log_line.emit)
            downloaded = sum(1 for result in results if not result.already_present)
            skipped = sum(1 for result in results if result.already_present)
            self.finished.emit(str(self._models_dir), downloaded, skipped)
        except Exception as exc:
            self.error.emit(str(exc))


class VoicePromptSaveWorker(QThread):
    """Save a reusable custom voice through the ComfyUI voice setup workflow."""

    status = pyqtSignal(str)
    finished = pyqtSignal(str, str)
    error = pyqtSignal(str)

    def __init__(
        self,
        audio_path: Path,
        voice_name: str,
        ref_text: str,
        voice_library_dir: Path | None = None,
        models_dir: str = "",
        speech_rate: float = 1.0,
        device: str = "",
        comfyui_url: str = "http://localhost:8188",
        workflow_path: Path | None = None,
        timeout: float = 300.0,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._audio_path = audio_path
        self._voice_name = voice_name
        self._ref_text = ref_text
        self._comfyui_url = comfyui_url
        self._workflow_path = workflow_path or (
            Path(__file__).resolve().parents[4] / "comfyui_workflows" / "voice_setup_template.json"
        )
        self._timeout = timeout
        self._voice_library_dir = voice_library_dir
        self._unused_options = {
            "models_dir": models_dir,
            "speech_rate": speech_rate,
            "device": device,
        }

    def run(self) -> None:
        try:
            from book_normalizer.comfyui.client import ComfyUIClient
            from book_normalizer.comfyui.workflow_builder import WorkflowBuilder

            if not self._audio_path.exists():
                self.error.emit(f"Audio file not found: {self._audio_path}")
                return
            if not self._voice_name.strip() or not self._ref_text.strip():
                self.error.emit(t("synth.saved_voice_missing"))
                return

            self.status.emit(t("synth.train_connecting"))
            client = ComfyUIClient(self._comfyui_url)
            if not client.is_reachable():
                self.error.emit(t("synth.train_err_comfyui", url=self._comfyui_url))
                return

            self.status.emit(t("synth.train_uploading", file=self._audio_path.name))
            uploaded_name = client.upload_audio(self._audio_path)
            self.status.emit(t("synth.train_extracting", name=self._voice_name.strip()))
            workflow = WorkflowBuilder(self._workflow_path).build_voice_setup(
                audio_filename=uploaded_name,
                voice_name=self._voice_name.strip(),
                ref_text=self._ref_text.strip(),
            )
            prompt_id = client.queue_prompt(workflow)
            client.wait_for_execution(prompt_id, timeout=self._timeout)
            self.finished.emit(self._voice_name.strip(), str(self._voice_library_dir or "comfyui"))
        except Exception as exc:
            self.error.emit(str(exc))


class ComfyVoiceSaveWorker(VoicePromptSaveWorker):
    """Backward-compatible name for the ComfyUI voice save worker."""
