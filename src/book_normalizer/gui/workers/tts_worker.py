"""Background worker for TTS synthesis via WSL subprocess."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from book_normalizer.gui.i18n import t


class ExportSegmentsWorker(QThread):
    """Export voice-annotated segments (line-level) from a processed book."""

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
        parent=None,
    ):
        super().__init__(parent)
        self._book = book
        self._output_dir = output_dir
        self._speaker_mode = speaker_mode
        self._llm_endpoint = llm_endpoint
        self._llm_model = llm_model
        self._llm_api_key = llm_api_key

    def run(self) -> None:
        try:
            from book_normalizer.chunking.voice_splitter import (
                extract_segments_book,
            )
            from book_normalizer.dialogue.attribution import (
                SpeakerMode,
                create_attributor,
            )
            from book_normalizer.dialogue.detector import DialogueDetector

            self.progress.emit(t("voice.detecting_dialogue"))
            detector = DialogueDetector()
            annotated = detector.detect_book(self._book)

            self.progress.emit(
                t("voice.attributing", mode=self._speaker_mode),
            )
            attr_mode = SpeakerMode(self._speaker_mode)
            attributor = create_attributor(
                attr_mode,
                cache_dir=self._output_dir / "speaker_cache",
                llm_endpoint=self._llm_endpoint or "",
                llm_model=self._llm_model or "qwen3:8b",
                llm_api_key=self._llm_api_key or "",
            )
            attributor.attribute(annotated)

            self.progress.emit(t("voice.extracting_segments"))
            segments = extract_segments_book(annotated)

            manifest = []
            for seg in segments:
                manifest.append({
                    "segment_index": seg.segment_index,
                    "chapter_index": seg.chapter_index,
                    "is_dialogue": seg.is_dialogue,
                    "role": seg.role.value,
                    "voice_id": seg.voice_id,
                    "intonation": seg.intonation,
                    "text": seg.text,
                })

            self._output_dir.mkdir(parents=True, exist_ok=True)
            manifest_path = (
                self._output_dir / "segments_manifest.json"
            )
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            self.progress.emit(
                t("voice.exported_segments", n=len(manifest)),
            )
            self.finished.emit(str(manifest_path))

        except Exception as exc:
            self.error.emit(str(exc))


class ExportChunksWorker(QThread):
    """Legacy: export voice-annotated chunks from a processed book."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(
        self,
        book: object,
        output_dir: Path,
        speaker_mode: str = "heuristic",
        max_chunk_chars: int = 600,
        parent=None,
    ):
        super().__init__(parent)
        self._book = book
        self._output_dir = output_dir
        self._speaker_mode = speaker_mode
        self._max_chunk_chars = max_chunk_chars

    def run(self) -> None:
        try:
            from book_normalizer.chunking.voice_splitter import (
                chunk_annotated_book,
            )
            from book_normalizer.dialogue.attribution import (
                SpeakerMode,
                create_attributor,
            )
            from book_normalizer.dialogue.detector import DialogueDetector

            self.progress.emit(t("voice.detecting_dialogue"))
            detector = DialogueDetector()
            annotated = detector.detect_book(self._book)

            self.progress.emit(
                t("voice.attributing", mode=self._speaker_mode),
            )
            attr_mode = SpeakerMode(self._speaker_mode)
            attributor = create_attributor(
                attr_mode,
                cache_dir=self._output_dir / "speaker_cache",
            )
            attributor.attribute(annotated)

            self.progress.emit(t("voice.chunking"))
            chunked = chunk_annotated_book(
                annotated,
                max_chunk_chars=self._max_chunk_chars,
            )

            manifest = []
            for ch_idx in sorted(chunked.keys()):
                for chunk in chunked[ch_idx]:
                    manifest.append({
                        "chapter_index": chunk.chapter_index,
                        "chunk_index": chunk.index,
                        "role": chunk.role.value,
                        "voice_id": chunk.voice_id,
                        "text": chunk.text,
                    })

            self._output_dir.mkdir(parents=True, exist_ok=True)
            manifest_path = self._output_dir / "chunks_manifest.json"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            self.progress.emit(
                t("voice.exported_chunks", n=len(manifest)),
            )
            self.finished.emit(str(manifest_path))

        except Exception as exc:
            self.error.emit(str(exc))


class TTSSynthesisWorker(QThread):
    """Run TTS synthesis via WSL subprocess and monitor progress."""

    progress = pyqtSignal(
        int, int, str, int,
        int, float, int, int, int,
    )
    status = pyqtSignal(str)
    log_line = pyqtSignal(str)
    finished = pyqtSignal(str, int, int)
    error = pyqtSignal(str)

    def __init__(
        self,
        manifest_path: Path,
        output_dir: Path,
        model: str = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        chapter: int | None = None,
        batch_size: int = 1,
        resume: bool = False,
        chunk_timeout: int = 300,
        use_compile: bool = False,
        clone_config: str = "",
        use_sage_attention: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self._manifest_path = manifest_path
        self._output_dir = output_dir
        self._model = model
        self._chapter = chapter
        self._batch_size = batch_size
        self._resume = resume
        self._chunk_timeout = chunk_timeout
        self._use_compile = use_compile
        self._clone_config = clone_config
        self._use_sage_attention = use_sage_attention
        self._process: subprocess.Popen | None = None
        self._cancelled = False

    def cancel(self) -> None:
        """Request cancellation of synthesis."""
        self._cancelled = True
        if self._process:
            self._process.terminate()

    def run(self) -> None:
        try:
            manifest = json.loads(
                self._manifest_path.read_text(encoding="utf-8"),
            )
            total = len(manifest)
            if self._chapter is not None:
                total = sum(
                    1 for c in manifest
                    if c.get("chapter_index") == self._chapter - 1
                )

            if total == 0:
                self.error.emit(t("synth.err_no_chunks"))
                return

            script_path = (
                Path(__file__).resolve().parent.parent.parent.parent.parent
                / "scripts" / "tts_runner.py"
            )

            resume_flag = " --resume" if self._resume else ""
            chapter_flag = (
                f" --chapter {self._chapter}" if self._chapter else ""
            )
            log_path = self._output_dir / "synthesis_log.txt"
            log_flag = f" --log-file {self._wsl_path(log_path)}"
            timeout_flag = f" --chunk-timeout {self._chunk_timeout}"
            compile_flag = " --compile" if self._use_compile else ""
            clone_flag = ""
            if self._clone_config:
                clone_flag = (
                    f" --clone-config {self._wsl_path(Path(self._clone_config))}"
                )
            sage_flag = " --sage-attention" if self._use_sage_attention else ""
            cmd = [
                "wsl", "-e", "bash", "-c",
                f"source ~/venvs/qwen3tts/bin/activate && "
                f"PYTHONUNBUFFERED=1 python -u "
                f"{self._wsl_path(script_path)} "
                f"--chunks-json {self._wsl_path(self._manifest_path)} "
                f"--out {self._wsl_path(self._output_dir)} "
                f"--model {self._model} "
                f"--batch-size {self._batch_size}"
                f"{resume_flag}{chapter_flag}{log_flag}"
                f"{timeout_flag}{compile_flag}{clone_flag}{sage_flag}",
            ]

            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            self.status.emit("__loading__")

            synthesized = 0
            skipped = 0
            last_lines: list[str] = []
            for line in iter(self._process.stdout.readline, ""):
                if self._cancelled:
                    break
                line = line.strip()
                if not line:
                    continue

                self.log_line.emit(line)
                last_lines.append(line)
                if len(last_lines) > 50:
                    last_lines.pop(0)

                if "Model loaded" in line:
                    self.status.emit("__model_ready__")

                if line.startswith("PROGRESS "):
                    try:
                        kv = dict(
                            re.findall(r"(\w+)=([\d.]+)", line),
                        )
                        done_val = int(kv.get("done", 0))
                        total_val = int(kv.get("total", total))
                        remaining = int(kv.get("remaining", 0))
                        chunk_chars = int(kv.get("chunk_chars", 0))
                        chunk_sec = float(kv.get("chunk_sec", 0))
                        remaining_chars = int(kv.get("remaining_chars", 0))
                        total_chars = int(kv.get("total_chars", 0))
                        eta_sec = int(kv.get("eta_sec", 0))
                        ch_num = int(kv.get("ch", 0))
                        eta_str = self._format_eta(eta_sec)
                        self.progress.emit(
                            done_val, total_val, eta_str, ch_num,
                            chunk_chars, chunk_sec,
                            remaining, remaining_chars, total_chars,
                        )
                    except (ValueError, KeyError, TypeError):
                        pass
                elif line.startswith("["):
                    try:
                        parts = line.split("]")[0].replace("[", "").strip()
                        current, _tot = parts.split("/")
                        synthesized = int(current)
                        eta_part = ""
                        if "ETA:" in line:
                            eta_part = line.split("ETA:")[1].strip().rstrip(")")
                        ch_match = re.search(r"\bch(\d+)\b", line)
                        chapter = int(ch_match.group(1)) if ch_match else 0
                        self.progress.emit(
                            synthesized, total, eta_part, chapter,
                            0, 0.0, total - synthesized, 0, 0,
                        )
                    except (ValueError, IndexError):
                        pass

                if line.startswith("Done:"):
                    try:
                        parts = line.split(",")
                        for p in parts:
                            p = p.strip()
                            if "synthesized" in p:
                                synthesized = int(p.split()[0].replace("Done:", "").strip())
                            elif "skipped" in p:
                                skipped = int(p.split()[0])
                    except (ValueError, IndexError):
                        pass
                    self.progress.emit(
                        total, total, "0s", 0,
                        0, 0.0, 0, 0, 0,
                    )

            self._process.wait()
            rc = self._process.returncode

            if self._cancelled:
                self.error.emit(t("synth.cancelled"))
            elif rc != 0:
                tail = "\n".join(last_lines[-10:])
                self.error.emit(
                    t("synth.err_exit_code", code=rc) + f"\n{tail}",
                )
            else:
                out_path = str(
                    self._output_dir / "audio_chunks",
                )
                self.finished.emit(out_path, synthesized, skipped)

        except Exception as exc:
            self.error.emit(str(exc))

    @staticmethod
    def _format_eta(seconds: int) -> str:
        """Format seconds to HH:MM:SS or MmSs."""
        if seconds <= 0:
            return "0s"
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 0:
            return f"{h}h{m:02d}m{s:02d}s"
        if m > 0:
            return f"{m}m{s:02d}s"
        return f"{s}s"

    @staticmethod
    def _wsl_path(path: Path) -> str:
        """Convert Windows path to WSL path."""
        p = str(path.resolve()).replace("\\", "/")
        if len(p) >= 2 and p[1] == ":":
            drive = p[0].lower()
            p = f"/mnt/{drive}{p[2:]}"
        return p
