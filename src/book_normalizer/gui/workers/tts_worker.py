"""Background worker for TTS synthesis via WSL subprocess."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal


class ExportChunksWorker(QThread):
    """Export voice-annotated chunks from a processed book."""

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
            from book_normalizer.chunking.voice_splitter import chunk_annotated_book
            from book_normalizer.dialogue.attribution import SpeakerMode, create_attributor
            from book_normalizer.dialogue.detector import DialogueDetector

            self.progress.emit("Detecting dialogue...")
            detector = DialogueDetector()
            annotated = detector.detect_book(self._book)

            self.progress.emit(f"Speaker attribution ({self._speaker_mode})...")
            attr_mode = SpeakerMode(self._speaker_mode)
            attributor = create_attributor(
                attr_mode, cache_dir=self._output_dir / "speaker_cache",
            )
            attributor.attribute(annotated)

            self.progress.emit("Chunking...")
            chunked = chunk_annotated_book(annotated, max_chunk_chars=self._max_chunk_chars)

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
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8",
            )

            self.progress.emit(f"Exported {len(manifest)} chunks")
            self.finished.emit(str(manifest_path))

        except Exception as exc:
            self.error.emit(str(exc))


class TTSSynthesisWorker(QThread):
    """Run TTS synthesis via WSL subprocess and monitor progress."""

    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(
        self,
        manifest_path: Path,
        output_dir: Path,
        model: str = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        chapter: int | None = None,
        batch_size: int = 1,
        parent=None,
    ):
        super().__init__(parent)
        self._manifest_path = manifest_path
        self._output_dir = output_dir
        self._model = model
        self._chapter = chapter
        self._batch_size = batch_size
        self._process: subprocess.Popen | None = None
        self._cancelled = False

    def cancel(self) -> None:
        """Request cancellation of synthesis."""
        self._cancelled = True
        if self._process:
            self._process.terminate()

    def run(self) -> None:
        try:
            manifest = json.loads(self._manifest_path.read_text(encoding="utf-8"))
            total = len(manifest)
            if self._chapter is not None:
                total = sum(1 for c in manifest if c["chapter_index"] == self._chapter - 1)

            script_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "scripts" / "tts_runner.py"

            cmd = [
                "wsl", "-e", "bash", "-c",
                f"source ~/venvs/qwen3tts/bin/activate && "
                f"python {self._wsl_path(script_path)} "
                f"--chunks-json {self._wsl_path(self._manifest_path)} "
                f"--out {self._wsl_path(self._output_dir)} "
                f"--model {self._model} "
                f"--batch-size {self._batch_size} "
                f"--resume"
                + (f" --chapter {self._chapter}" if self._chapter else ""),
            ]

            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            done = 0
            for line in iter(self._process.stdout.readline, ""):
                if self._cancelled:
                    break
                line = line.strip()
                if not line:
                    continue

                if line.startswith("  ["):
                    try:
                        parts = line.split("]")[0].replace("[", "").strip()
                        current, tot = parts.split("/")
                        done = int(current)
                        eta_part = line.split("ETA:")[1].strip() if "ETA:" in line else ""
                        self.progress.emit(done, total, eta_part)
                    except (ValueError, IndexError):
                        pass

                if line.startswith("Done:"):
                    self.progress.emit(total, total, "0s")

            self._process.wait()
            if not self._cancelled:
                self.finished.emit(str(self._output_dir / "synthesis_manifest.json"))
            else:
                self.error.emit("Cancelled by user")

        except Exception as exc:
            self.error.emit(str(exc))

    @staticmethod
    def _wsl_path(path: Path) -> str:
        """Convert Windows path to WSL path."""
        p = str(path.resolve()).replace("\\", "/")
        if len(p) >= 2 and p[1] == ":":
            drive = p[0].lower()
            p = f"/mnt/{drive}{p[2:]}"
        return p
