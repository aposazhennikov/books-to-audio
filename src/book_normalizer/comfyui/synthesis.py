"""ComfyUI synthesis loop for v2 chunk manifests."""

from __future__ import annotations

import json
import logging
import time
import wave
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from book_normalizer.chunking.manifest_v2 import (
    DEFAULT_MANIFEST_NAME,
    chunk_is_excluded,
    ensure_v2_manifest,
)
from book_normalizer.comfyui.client import ComfyUICancelledError, ComfyUIClient, ComfyUIError
from book_normalizer.comfyui.generation_options import (
    GenerationOptions,
    generation_options_from_mapping,
)
from book_normalizer.comfyui.workflow_builder import WorkflowBuilder
from book_normalizer.runtime_paths import configured_ffmpeg_bin
from book_normalizer.tts.audio_smoothing import smooth_wav_silence
from book_normalizer.tts.compatible_audio import export_compatible_mp3
from book_normalizer.tts.voice_mapping import voice_mapping_candidates

ProgressCallback = Callable[[str], None]
RecoveryCallback = Callable[[ComfyUIError, int], ComfyUIClient | None]
CancelRequested = Callable[[], bool]

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SynthesisSummary:
    """Final counters from a ComfyUI synthesis run."""

    total: int
    synthesized: int
    skipped: int
    failed: int
    status: str = "completed"

    @property
    def cancelled(self) -> bool:
        """Return true when synthesis stopped by cooperative cancellation."""
        return self.status == "cancelled"


_LOG_LANGS = {"en", "ru", "zh", "kk", "uz"}

_LOG_MESSAGES: dict[str, dict[str, str]] = {
    "already_done": {
        "en": "All {total} chunks already synthesized. Nothing to do.",
        "ru": "Все {total} чанков уже синтезированы. Делать нечего.",
        "zh": "全部 {total} 个分块已合成，无需处理。",
        "kk": "{total} чанктың бәрі синтезделген. Істеу қажет емес.",
        "uz": "{total} bo'lakning barchasi sintez qilingan. Hech narsa qilish kerak emas.",
    },
    "chunks": {
        "en": "Chunks: {total} total, {done} already done, {pending} to synthesize.",
        "ru": "Чанки: всего {total}, уже готово {done}, синтезировать {pending}.",
        "zh": "分块：共 {total}，已完成 {done}，待合成 {pending}。",
        "kk": "Чанктар: барлығы {total}, дайын {done}, синтезге {pending}.",
        "uz": "Bo'laklar: jami {total}, tayyor {done}, sintez uchun {pending}.",
    },
    "skip_empty": {
        "en": "  Skipping empty chunk ch{chapter}/chunk{chunk}",
        "ru": "  Пропуск пустого чанка гл{chapter}/чанк{chunk}",
        "zh": "  跳过空分块 第{chapter}章/分块{chunk}",
        "kk": "  Бос чанк өткізіледі {chapter}-тарау/чанк{chunk}",
        "uz": "  Bo'sh bo'lak o'tkazib yuborildi {chapter}-bob/bo'lak{chunk}",
    },
    "synthesizing": {
        "en": "  Synthesizing ch{chapter}/chunk{chunk} [{role}/{voice}/{tone}] {chars} chars -> {file}",
        "ru": "  Синтез гл{chapter}/чанк{chunk} [{role}/{voice}/{tone}] {chars} симв. -> {file}",
        "zh": "  合成 第{chapter}章/分块{chunk} [{role}/{voice}/{tone}] {chars} 字符 -> {file}",
        "kk": "  Синтез {chapter}-тарау/чанк{chunk} [{role}/{voice}/{tone}] {chars} таңба -> {file}",
        "uz": "  Sintez {chapter}-bob/bo'lak{chunk} [{role}/{voice}/{tone}] {chars} belgi -> {file}",
    },
    "error": {
        "en": "  ERROR: {error}",
        "ru": "  ОШИБКА: {error}",
        "zh": "  错误：{error}",
        "kk": "  ҚАТЕ: {error}",
        "uz": "  XATO: {error}",
    },
    "recovery": {
        "en": "  Recovery: restarting/checking ComfyUI (attempt {attempt}/{limit})...",
        "ru": "  Восстановление: перезапуск/проверка ComfyUI (попытка {attempt}/{limit})...",
        "zh": "  恢复：重启/检查 ComfyUI（尝试 {attempt}/{limit}）...",
        "kk": "  Қалпына келтіру: ComfyUI қайта іске қосу/тексеру ({attempt}/{limit})...",
        "uz": "  Tiklash: ComfyUI qayta ishga tushirish/tekshirish ({attempt}/{limit})...",
    },
    "done": {
        "en": "    Done in {seconds:.1f}s -> {size_kb} KB",
        "ru": "    Готово за {seconds:.1f}с -> {size_kb} КБ",
        "zh": "    完成：{seconds:.1f} 秒 -> {size_kb} KB",
        "kk": "    Дайын: {seconds:.1f}с -> {size_kb} КБ",
        "uz": "    Tayyor: {seconds:.1f}s -> {size_kb} KB",
    },
    "smoothed": {
        "en": "    Smoothed silence: removed {removed}ms, max gap was {max_gap}ms",
        "ru": "    Сглажена тишина: удалено {removed} мс, максимум паузы был {max_gap} мс",
        "zh": "    已平滑静音：移除 {removed}ms，最大间隔 {max_gap}ms",
        "kk": "    Тыныштық тегістелді: {removed}мс жойылды, ең үлкен үзіліс {max_gap}мс",
        "uz": "    Jimlik tekislandi: {removed}ms olib tashlandi, eng katta pauza {max_gap}ms",
    },
    "complete": {
        "en": "Synthesis complete: {new} new chunks synthesized ({done}/{total} total done, {failed} failed).",
        "ru": "Синтез завершён: новых чанков {new} ({done}/{total} всего готово, ошибок {failed}).",
        "zh": "合成完成：新合成 {new} 个分块（共完成 {done}/{total}，失败 {failed}）。",
        "kk": "Синтез аяқталды: жаңа чанк {new} ({done}/{total} дайын, қате {failed}).",
        "uz": "Sintez tugadi: {new} yangi bo'lak ({done}/{total} tayyor, {failed} xato).",
    },
}

_ROLE_LABELS: dict[str, dict[str, str]] = {
    "narrator": {"en": "narrator", "ru": "автор", "zh": "旁白", "kk": "автор", "uz": "muallif"},
    "men": {"en": "male", "ru": "мужской", "zh": "男声", "kk": "ер", "uz": "erkak"},
    "women": {"en": "female", "ru": "женский", "zh": "女声", "kk": "әйел", "uz": "ayol"},
}

_TONE_LABELS: dict[str, dict[str, str]] = {
    "neutral": {"en": "neutral", "ru": "нейтральная", "zh": "中性", "kk": "бейтарап", "uz": "neytral"},
    "calm": {"en": "calm", "ru": "спокойная", "zh": "平静", "kk": "тыныш", "uz": "tinch"},
    "excited": {"en": "excited", "ru": "взволнованная", "zh": "激动", "kk": "толқыған", "uz": "hayajonli"},
    "joyful": {"en": "joyful", "ru": "радостная", "zh": "欢快", "kk": "қуанышты", "uz": "quvonchli"},
    "sad": {"en": "sad", "ru": "грустная", "zh": "悲伤", "kk": "мұңды", "uz": "g'amgin"},
    "angry": {"en": "angry", "ru": "злая", "zh": "愤怒", "kk": "ашулы", "uz": "jahldor"},
    "whisper": {"en": "whisper", "ru": "шёпот", "zh": "耳语", "kk": "сыбыр", "uz": "shivir"},
}

_VOICE_LABELS: dict[str, dict[str, str]] = {
    "narrator_calm": {
        "en": "Narrator - Calm",
        "ru": "Диктор - Спокойный",
        "zh": "旁白 - 平静",
        "kk": "Диктор - Сабырлы",
        "uz": "Hikoyachi - Vazmin",
    },
    "narrator_energetic": {
        "en": "Narrator - Energetic",
        "ru": "Диктор - Энергичный",
        "zh": "旁白 - 充满活力",
        "kk": "Диктор - Қуатты",
        "uz": "Hikoyachi - Jo'shqin",
    },
    "narrator_wise": {
        "en": "Narrator - Wise",
        "ru": "Диктор - Мудрый",
        "zh": "旁白 - 睿智",
        "kk": "Диктор - Дана",
        "uz": "Hikoyachi - Dono",
    },
    "male_young": {
        "en": "Male - Young",
        "ru": "Мужской - Молодой",
        "zh": "男声 - 年轻",
        "kk": "Ер дауысы - Жас",
        "uz": "Erkak ovozi - Yosh",
    },
    "male_confident": {
        "en": "Male - Confident",
        "ru": "Мужской - Уверенный",
        "zh": "男声 - 自信",
        "kk": "Ер дауысы - Сенімді",
        "uz": "Erkak ovozi - Ishonchli",
    },
    "male_deep": {
        "en": "Male - Deep",
        "ru": "Мужской - Глубокий",
        "zh": "男声 - 低沉",
        "kk": "Ер дауысы - Терең",
        "uz": "Erkak ovozi - Chuqur",
    },
    "male_lively": {
        "en": "Male - Lively",
        "ru": "Мужской - Живой",
        "zh": "男声 - 活泼",
        "kk": "Ер дауысы - Ширақ",
        "uz": "Erkak ovozi - Tetik",
    },
    "male_regional": {
        "en": "Male - Expressive",
        "ru": "Мужской - Экспрессивный",
        "zh": "男声 - 富有表现力",
        "kk": "Ер дауысы - Әсерлі",
        "uz": "Erkak ovozi - Ifodali",
    },
    "female_warm": {
        "en": "Female - Warm",
        "ru": "Женский - Тёплый",
        "zh": "女声 - 温暖",
        "kk": "Әйел дауысы - Жылы",
        "uz": "Ayol ovozi - Iliq",
    },
    "female_bright": {
        "en": "Female - Bright",
        "ru": "Женский - Яркий",
        "zh": "女声 - 明亮",
        "kk": "Әйел дауысы - Жарқын",
        "uz": "Ayol ovozi - Yorqin",
    },
    "female_playful": {
        "en": "Female - Playful",
        "ru": "Женский - Игривый",
        "zh": "女声 - 俏皮",
        "kk": "Әйел дауысы - Ойнақы",
        "uz": "Ayol ovozi - O'ynoqi",
    },
    "female_gentle": {
        "en": "Female - Gentle",
        "ru": "Женский - Нежный",
        "zh": "女声 - 轻柔",
        "kk": "Әйел дауысы - Нәзік",
        "uz": "Ayol ovozi - Muloyim",
    },
}


def _log_lang(language: str) -> str:
    normalized = (language or "").strip().lower()
    return normalized if normalized in _LOG_LANGS else "en"


def _localized(mapping: dict[str, dict[str, str]], key: str, language: str, fallback: str = "") -> str:
    labels = mapping.get(key, {})
    return labels.get(_log_lang(language), labels.get("en", fallback or key))


def _log_text(language: str, key: str, **kwargs: Any) -> str:
    entry = _LOG_MESSAGES[key]
    return entry.get(_log_lang(language), entry["en"]).format(**kwargs)


def localized_synthesis_line(
    *,
    language: str,
    chapter: int,
    chunk: int,
    voice_label: str,
    voice_id: str,
    voice_tone: str,
    chars: int,
    file_name: str,
) -> str:
    """Return a localized per-chunk synthesis log line."""
    return _log_text(
        language,
        "synthesizing",
        chapter=f"{chapter:03d}",
        chunk=f"{chunk:03d}",
        role=_localized(_ROLE_LABELS, voice_label, language, voice_label),
        voice=_localized(_VOICE_LABELS, voice_id, language, voice_id or "-"),
        tone=_localized(_TONE_LABELS, voice_tone, language, voice_tone),
        chars=chars,
        file=file_name,
    )


def load_manifest(path: Path) -> dict[str, Any]:
    """Load and validate a v2 manifest JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    try:
        return ensure_v2_manifest(data).to_record()
    except ValueError as exc:
        raise ValueError(
            f"ComfyUI synthesis requires a v2 manifest ({DEFAULT_MANIFEST_NAME}). "
            "Generate it with export_chunks.py or the GUI Voices tab."
        ) from exc


def save_manifest(path: Path, data: dict[str, Any]) -> None:
    """Atomically write manifest data back to disk."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def iter_manifest_chunks(
    manifest: dict[str, Any],
    chapter_filter: int | None = None,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Return ``(chapter, chunk)`` pairs matching an optional 1-based chapter."""
    ensure_v2_manifest(manifest)
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for chapter in manifest.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chapter_index = int(chapter.get("chapter_index", 0))
        if chapter_filter is not None and chapter_index != chapter_filter - 1:
            continue
        for chunk in chapter.get("chunks", []):
            if isinstance(chunk, dict):
                pairs.append((chapter, chunk))
    return pairs


def collect_pending_chunks(
    manifest: dict[str, Any],
    chapter_filter: int | None = None,
    *,
    failed_only: bool = False,
    manifest_path: Path | None = None,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Return chunk pairs that should be synthesized."""
    pending: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for chapter, chunk in iter_manifest_chunks(manifest, chapter_filter):
        if chunk_is_excluded(chunk):
            continue
        if _chunk_is_done(chunk, manifest_path):
            continue
        if failed_only and not chunk.get("failed", False):
            continue
        pending.append((chapter, chunk))
    return pending


def count_done_chunks(
    manifest: dict[str, Any],
    chapter_filter: int | None = None,
    *,
    manifest_path: Path | None = None,
) -> int:
    """Count synthesized chunks matching an optional chapter filter."""
    return sum(
        1
        for _chapter, chunk in iter_manifest_chunks(manifest, chapter_filter)
        if not chunk_is_excluded(chunk) and _chunk_is_done(chunk, manifest_path)
    )


def _chunk_is_done(chunk: dict[str, Any], manifest_path: Path | None = None) -> bool:
    """Return True when a chunk has no work left for synthesis."""
    if not chunk.get("synthesized", False):
        return False
    if not _chunk_text(chunk).strip():
        return True
    audio_file = str(chunk.get("audio_file") or "")
    audio_path = _resolve_manifest_audio_path(audio_file, manifest_path)
    return audio_path is not None and audio_path.exists()


def _resolve_manifest_audio_path(audio_file: str, manifest_path: Path | None) -> Path | None:
    """Resolve an audio_file value stored in a chunk manifest."""
    if not audio_file:
        return None
    path = Path(audio_file)
    if not path.is_absolute() and manifest_path is not None:
        path = manifest_path.parent / path
    return path


def _manifest_audio_file(output_path: Path, manifest_path: Path) -> str:
    """Return the portable path value to store in a manifest chunk."""
    try:
        return output_path.resolve().relative_to(manifest_path.parent.resolve()).as_posix()
    except ValueError:
        return str(output_path)


def _chunk_text(chunk: dict[str, Any]) -> str:
    voice_label = str(chunk.get("voice_label") or "")
    return str(chunk.get("text") or (chunk.get(voice_label) if voice_label else "") or "")


def build_output_path(
    out_dir: Path,
    chapter_index: int,
    chunk_index: int,
    voice_label: str,
) -> Path:
    """Return the local WAV path for a chunk."""
    chapter_dir = out_dir / f"chapter_{chapter_index + 1:03d}"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    safe_voice = "".join(ch for ch in voice_label if ch.isalnum() or ch in ("_", "-")) or "voice"
    return chapter_dir / f"chunk_{chunk_index + 1:03d}_{safe_voice}.wav"


def load_speaker_overrides(path: Path | str | None) -> dict[str, str]:
    """Load saved CustomVoice speaker overrides from a GUI clone config."""
    if not path:
        return {}
    config_path = Path(path)
    if not config_path.exists():
        return {}
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}

    overrides: dict[str, str] = {}
    for raw_key, raw_value in data.items():
        key = str(raw_key).strip()
        speaker = ""
        if isinstance(raw_value, str):
            speaker = raw_value.strip()
        elif isinstance(raw_value, dict):
            speaker = str(
                raw_value.get("speaker")
                or raw_value.get("saved_voice")
                or raw_value.get("voice_id")
                or "",
            ).strip()
        if key and speaker:
            overrides[key] = speaker
    return overrides


def resolve_speaker_override(
    chunk: dict[str, Any],
    voice_label: str,
    speaker_overrides: dict[str, str] | None,
) -> str:
    """Resolve a concrete CustomVoice speaker for one chunk if configured."""
    if not speaker_overrides:
        return ""
    enriched = dict(chunk)
    enriched.setdefault("voice_label", voice_label)
    for key in voice_mapping_candidates(enriched):
        speaker = speaker_overrides.get(key)
        if speaker:
            return speaker
    return ""


def synthesize_manifest(
    *,
    manifest: dict[str, Any],
    manifest_path: Path,
    client: ComfyUIClient,
    builder: WorkflowBuilder,
    out_dir: Path,
    chapter_filter: int | None = None,
    chunk_timeout: float = 300.0,
    failed_only: bool = False,
    speaker_overrides: dict[str, str] | None = None,
    generation_options: GenerationOptions | dict[str, Any] | None = None,
    progress: ProgressCallback | None = None,
    recovery: RecoveryCallback | None = None,
    max_recovery_retries: int = 0,
    log_language: str = "en",
    cancel_requested: CancelRequested | None = None,
) -> SynthesisSummary:
    """Synthesize all pending chunks and update the manifest after each chunk."""
    is_cancelled = cancel_requested or (lambda: False)
    out_dir.mkdir(parents=True, exist_ok=True)
    all_pairs = [
        pair for pair in iter_manifest_chunks(manifest, chapter_filter)
        if not chunk_is_excluded(pair[1])
    ]
    pending = collect_pending_chunks(
        manifest,
        chapter_filter,
        failed_only=failed_only,
        manifest_path=manifest_path,
    )
    total = len(all_pairs)
    done_start = count_done_chunks(manifest, chapter_filter, manifest_path=manifest_path)
    skipped = done_start
    failed = 0

    def emit(line: str) -> None:
        if progress:
            progress(line)

    if not pending:
        emit(_log_text(log_language, "already_done", total=total))
        return SynthesisSummary(total=total, synthesized=0, skipped=skipped, failed=0)

    emit(_log_text(log_language, "chunks", total=total, done=done_start, pending=len(pending)))
    done = done_start
    synthesized_now = 0
    manifest_language = str(manifest.get("language") or "ru")
    base_generation_options = generation_options_from_mapping(generation_options)

    for chapter_entry, chunk in pending:
        if is_cancelled():
            return SynthesisSummary(
                total=total,
                synthesized=synthesized_now,
                skipped=skipped,
                failed=failed,
                status="cancelled",
            )
        chapter_index = int(chapter_entry.get("chapter_index", 0))
        chunk_index = int(chunk.get("chunk_index", 0))
        voice_label = str(chunk.get("voice_label") or "narrator")
        voice_id = str(chunk.get("voice_id") or "")
        voice_tone = str(chunk.get("voice_tone") or "calm").strip().lower()
        text = str(chunk.get("text") or chunk.get(voice_label) or "")
        language = str(chunk.get("language") or manifest_language)
        attempt = int(chunk.get("resynthesis_attempt") or 0)
        effective_options = base_generation_options.for_attempt(
            attempt,
            chapter_index=chapter_index,
            chunk_index=chunk_index,
        )

        chunk["failed"] = False
        chunk["error"] = ""

        if not text.strip():
            emit(
                _log_text(
                    log_language,
                    "skip_empty",
                    chapter=f"{chapter_index + 1:03d}",
                    chunk=f"{chunk_index + 1:03d}",
                )
            )
            chunk["synthesized"] = True
            chunk["audio_file"] = ""
            done += 1
            skipped += 1
            emit(f"PROGRESS {done}/{total}")
            save_manifest(manifest_path, manifest)
            continue

        output_path = build_output_path(out_dir, chapter_index, chunk_index, voice_label)
        output_filename = output_path.with_suffix("").name
        emit(
            localized_synthesis_line(
                language=log_language,
                chapter=chapter_index + 1,
                chunk=chunk_index + 1,
                voice_label=voice_label,
                voice_id=voice_id,
                voice_tone=voice_tone,
                chars=len(text),
                file_name=output_path.name,
            )
        )

        started = time.monotonic()
        smoothing = None
        chunk_done = False
        recovery_limit = max(0, int(max_recovery_retries))
        for recovery_attempt in range(recovery_limit + 1):
            try:
                workflow = builder.build(
                    text=text,
                    voice_label=voice_label,
                    voice_tone=voice_tone,
                    output_filename=output_filename,
                    language=language,
                    speaker_override=resolve_speaker_override(
                        chunk,
                        voice_label,
                        speaker_overrides,
                    ),
                    generation_options=effective_options,
                    speaker=str(chunk.get("speaker") or ""),
                    emotion=str(chunk.get("emotion") or ""),
                    section_kind=str(chunk.get("section_kind") or ""),
                    director=chunk.get("director") if isinstance(chunk.get("director"), dict) else None,
                    resynthesis_attempt=attempt,
                )
                client.synthesize_chunk(
                    workflow,
                    output_path,
                    timeout=chunk_timeout,
                    cancel_requested=is_cancelled,
                )
                try:
                    smoothing = smooth_wav_silence(output_path)
                except (OSError, ValueError, wave.Error, EOFError):
                    smoothing = None
                chunk_done = True
                break
            except ComfyUICancelledError:
                return SynthesisSummary(
                    total=total,
                    synthesized=synthesized_now,
                    skipped=skipped,
                    failed=failed,
                    status="cancelled",
                )
            except ComfyUIError as exc:
                chunk["failed"] = True
                chunk["error"] = str(exc)
                emit(_log_text(log_language, "error", error=exc))
                save_manifest(manifest_path, manifest)
                if recovery is None or recovery_attempt >= recovery_limit:
                    failed += 1
                    break
                next_attempt = recovery_attempt + 1
                emit(
                    _log_text(
                        log_language,
                        "recovery",
                        attempt=next_attempt,
                        limit=recovery_limit,
                    )
                )
                recovered_client = recovery(exc, next_attempt)
                if recovered_client is not None:
                    client = recovered_client
                chunk["failed"] = False
                chunk["error"] = ""
                save_manifest(manifest_path, manifest)

        if not chunk_done:
            continue

        elapsed = time.monotonic() - started
        size_kb = output_path.stat().st_size // 1024 if output_path.exists() else 0
        emit(_log_text(log_language, "done", seconds=elapsed, size_kb=size_kb))

        chunk["synthesized"] = True
        chunk["failed"] = False
        chunk["error"] = ""
        chunk["audio_file"] = _manifest_audio_file(output_path, manifest_path)
        _write_compatible_chunk_audio(chunk, output_path, manifest_path)
        chunk["last_generation_options"] = effective_options
        if smoothing is not None:
            chunk["audio_postprocess"] = {"silence_smoothing": smoothing.to_dict()}
            if smoothing.changed:
                emit(
                    _log_text(
                        log_language,
                        "smoothed",
                        removed=smoothing.removed_silence_ms,
                        max_gap=smoothing.max_silence_ms,
                    )
                )
        done += 1
        synthesized_now += 1
        emit(f"PROGRESS {done}/{total}")
        save_manifest(manifest_path, manifest)

    emit(_log_text(log_language, "complete", new=synthesized_now, done=done, total=total, failed=failed))
    return SynthesisSummary(
        total=total,
        synthesized=synthesized_now,
        skipped=skipped,
        failed=failed,
    )


def _write_compatible_chunk_audio(chunk: dict[str, Any], output_path: Path, manifest_path: Path) -> None:
    """Best-effort compatible MP3 sidecar for synthesized chunk audio."""
    try:
        compatible_path = export_compatible_mp3(
            output_path,
            ffmpeg=str(configured_ffmpeg_bin() or "ffmpeg"),
        )
    except Exception as exc:  # pragma: no cover - depends on local ffmpeg/runtime media
        logger.warning("Compatible chunk MP3 export failed for %s: %s", output_path, exc)
        chunk["compatible_audio_error"] = str(exc)
        return
    chunk["compatible_audio_file"] = _manifest_audio_file(compatible_path, manifest_path)
    chunk.pop("compatible_audio_error", None)
