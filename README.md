# Books to Audio

Production-ready desktop and CLI pipeline for turning books into structured audiobook assets.

Books to Audio loads TXT, PDF, EPUB, FB2, and DOCX files, normalizes text, detects chapters and dialogue, prepares TTS chunks, sends them to ComfyUI/Qwen3-TTS, runs quality checks, and assembles WAV/MP3 audiobook chapters.

The app UI supports five languages: Russian, English, Chinese, Kazakh, and Uzbek. This README includes setup and operating notes in all five languages.

## Project Overview

Books to Audio is not just a text-to-speech launcher. It is an end-to-end audiobook preparation system for long-form books, especially books that need cleanup, chapter detection, dialogue handling, voice planning, chunked synthesis, and final audio assembly.

The project includes:

- **Desktop GUI** for loading books, normalizing text, reviewing chapters, assigning voices, downloading models, running synthesis, and assembling output.
- **CLI tools** for repeatable production runs, diagnostics, batch processing, QA, mastering, and packaging.
- **Book loaders** for `TXT`, `PDF`, `EPUB`, `FB2`, and `DOCX`.
- **OCR support** for scanned PDFs through Tesseract.
- **Text normalization** for punctuation, whitespace, OCR artifacts, abbreviations, numbers, Russian `ё`, stress hints, and language-aware cleanup.
- **LLM-assisted processing** through local Ollama/Qwen models for smarter normalization, segmentation, and dialogue/voice markup.
- **Chapter and dialogue pipeline** that builds a structured book representation instead of sending one giant text blob to TTS.
- **Voice and role tooling** for character inventories, speaker attribution, voice presets, and casting plans.
- **ComfyUI/Qwen3-TTS synthesis** using the v2 chunk manifest workflow.
- **Audio QA and assembly** for checking generated chunks, retrying failed items, and producing chapter-level WAV/MP3 files.
- **Production reports and manifests** so long runs can be resumed, audited, and debugged.

Typical output is a project folder in `output/` with normalized text, chapter files, Qwen/LLM chunks, `chunks_manifest_v2.json`, generated audio chunks, QA reports, and assembled chapter audio.

## Contents

- [English](#english)
- [Русский](#русский)
- [中文](#中文)
- [Қазақша](#қазақша)
- [O'zbekcha](#ozbekcha)

---

## English

### What The App Does

Books to Audio is a local-first audiobook production tool:

1. Imports books from `TXT`, `PDF`, `EPUB`, `FB2`, or `DOCX`.
2. Extracts text; scanned PDFs can use Tesseract OCR.
3. Normalizes punctuation, whitespace, numbers, OCR artifacts, and language-specific text issues.
4. Detects chapters, dialogue, speakers, roles, and voice assignments.
5. Creates a v2 chunk manifest: `chunks_manifest_v2.json`.
6. Sends chunks to ComfyUI with Qwen3-TTS workflows.
7. Saves chunk audio, retries failures, runs artifact/ASR quality checks, and assembles final chapters.

Core capabilities:

| Area | What it does |
| --- | --- |
| Book import | Reads TXT, PDF, EPUB, FB2, and DOCX sources. |
| OCR | Uses Tesseract for scanned PDFs when native text extraction is not enough. |
| Normalization | Cleans punctuation, whitespace, OCR artifacts, numbers, abbreviations, and language-specific text issues. |
| LLM processing | Uses local Ollama/Qwen models for normalization, chunking, dialogue analysis, and voice markup. |
| Structure | Detects chapters, dialogue, speakers, roles, and production metadata. |
| TTS preparation | Creates `chunks_manifest_v2.json` with chapter-aware, voice-aware synthesis chunks. |
| Synthesis | Sends chunks to ComfyUI/Qwen3-TTS workflows and records per-chunk status. |
| QA and assembly | Checks audio artifacts/ASR, retries failed chunks, and assembles WAV/MP3 chapter files. |

The supported production path is:

```text
Book file -> text extraction/OCR -> normalization -> chaptering -> role markup
-> chunks_manifest_v2.json -> ComfyUI/Qwen3-TTS -> audio chunks
-> QA -> assembled WAV/MP3 chapters
```

### Supported Platforms

| OS | Status | Notes |
| --- | --- | --- |
| Windows 10/11 | Supported | Use `install.bat` and `run_gui.bat`. |
| Linux | Supported | Best target for local CUDA/GPU TTS and ComfyUI. |
| macOS | Supported | GUI, OCR, LLM, and remote/local ComfyUI endpoints work. CUDA-only direct TTS is not a production path on macOS. |

Python requirement: **Python 3.10+**. Python **3.12** is recommended.

### Clone The Repository

```bash
git clone <repo-url>
cd books-to-audio
```

Replace `<repo-url>` with your GitHub repository URL, for example:

```bash
git clone https://github.com/<owner>/<repo>.git
cd books-to-audio
```

### Install

Windows:

```powershell
install.bat
run_gui.bat
```

Linux/macOS:

```bash
chmod +x install.sh run_gui.sh
./install.sh
./run_gui.sh
```

Cross-platform installer:

```bash
python install.py
```

Useful installer profiles:

```bash
python install.py                         # desktop profile: GUI + OCR + LLM + audio helpers
python install.py --minimal               # core dependencies only
python install.py --with-dev              # pytest + ruff
python install.py --with-asr              # ASR QA dependencies
python install.py --with-stress           # optional Silero stress support
python install.py --with-tts              # direct Qwen-TTS runtime
python install.py --with-sage             # Qwen-TTS + SageAttention, Linux/CUDA oriented
python install.py --recreate              # recreate virtual environment
python install.py --dry-run               # show install plan without changing files
python install.py --yes                   # use defaults without prompts
python install.py --interactive           # ask for paths and optional downloads
python install.py --install-system-tools  # install native Tesseract/FFmpeg/GUI packages where supported
python install.py --install-ollama        # install native Ollama if missing
python install.py --install-comfyui       # prepare local ComfyUI + Qwen3-TTS custom nodes
python install.py --tessdata-dir /path/to/tessdata
```

Manual fallback:

```bash
pip install -r requirements.txt
```

For new production installs, prefer `install.py` because it writes runtime paths, configures local model locations, and works consistently across Windows, Linux, and macOS.

### System Dependencies

Windows:

```powershell
winget install Python.Python.3.12
winget install -e --silent --disable-interactivity --accept-package-agreements --accept-source-agreements --id UB-Mannheim.TesseractOCR
winget install -e --silent --disable-interactivity --accept-package-agreements --accept-source-agreements --id Gyan.FFmpeg
```

Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip \
  tesseract-ocr tesseract-ocr-eng tesseract-ocr-rus \
  tesseract-ocr-chi-sim tesseract-ocr-kaz tesseract-ocr-uzb \
  ffmpeg libegl1 libgl1 libxcb-cursor0 libxkbcommon-x11-0 fonts-noto-cjk
```

macOS:

```bash
brew install python tesseract tesseract-lang ffmpeg
```

### Where Models Are Downloaded

The installer writes local runtime settings to:

```text
data/local_runtime_paths.json
```

The same values are also written to `.env` for local runs.

Default model/cache locations:

| Asset | Default / Config | Environment variable |
| --- | --- | --- |
| Qwen3-TTS / ComfyUI models | Windows: `D:/ComfyUI-external/models`; Linux/WSL: `/mnt/d/ComfyUI-external/models`; or `--models-dir` | `BOOKS_TO_AUDIO_MODELS_DIR`, `COMFYUI_MODELS_DIR` |
| TTS model subfolder | `<models-dir>/audio_encoders/` | same as above |
| Hugging Face cache | `--hf-cache-dir` or installer-selected folder | `HF_HOME` |
| Ollama models | `<repo>/ollama-models` by default or `--ollama-models-dir` | `BOOKS_TO_AUDIO_OLLAMA_MODELS_DIR`, `OLLAMA_MODELS` |
| Local Tesseract language data | `<repo>/data/tessdata` when using `--download-tessdata` | `BOOKS_TO_AUDIO_TESSDATA_DIR`, `TESSDATA_PREFIX` |

Expected Qwen3-TTS structure:

```text
models/
  audio_encoders/
    Qwen3-TTS-12Hz-1.7B-Base/
    Qwen3-TTS-12Hz-1.7B-CustomVoice/
    Qwen3-TTS-Tokenizer-12Hz/
```

Download TTS models:

```bash
python install.py --download-tts-models
```

or:

```bash
normalize-book install-tts-models --models-dir /path/to/models \
  --model Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice --with-base
```

If Hugging Face requires authentication:

```bash
export HF_TOKEN="<your-token>"
```

Windows PowerShell:

```powershell
$env:HF_TOKEN="<your-token>"
```

Download Ollama models:

```bash
python install.py --download-ollama-models
```

or manually:

```bash
ollama pull hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M
ollama pull hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M
```

Prepare a full local runtime on a new machine:

```bash
python install.py --interactive \
  --install-system-tools \
  --install-ollama \
  --download-ollama-models \
  --download-tts-models \
  --install-comfyui
```

The installer asks whether to install Ollama and ComfyUI in interactive mode. If they are already installed, it reports the existing path and skips reinstalling. Use `--ollama-bin`, `--comfyui-root`, and `--models-dir` to provide custom locations.

### Resource Requirements

Minimum for text normalization and GUI:

| Resource | Minimum | Recommended |
| --- | --- | --- |
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16-32 GB |
| Disk | 10 GB free | 50+ GB free for models, books, and output |
| GPU | Not required for text-only workflow | NVIDIA GPU for production TTS |
| VRAM | Not required for text-only workflow | 8 GB minimum for the recommended local Qwen/Ollama setup; 12-24 GB preferred for heavier TTS/QA workloads |

Production audiobook generation with ComfyUI/Qwen3-TTS needs a GPU host with enough VRAM for the selected TTS workflow. Model downloads can consume many gigabytes and should be placed on a fast SSD.

### Start The App

Windows:

```powershell
run_gui.bat
```

Linux/macOS:

```bash
./run_gui.sh
```

Direct module run:

```bash
python -m book_normalizer.gui.app
```

CLI health check:

```bash
normalize-book doctor --skip-network
normalize-book doctor
```

### Production CLI Workflow

Normalize and prepare a book:

```bash
normalize-book pipeline books/mybook.pdf --out output --llm-normalize
```

Run ComfyUI synthesis and assemble chapters:

```bash
normalize-book pipeline books/mybook.pdf \
  --out output \
  --llm-normalize \
  --synthesize \
  --workflow comfyui_workflows/qwen3_tts_template.json \
  --assemble
```

Assemble already synthesized chunks:

```bash
python scripts/assemble_chapter.py \
  --manifest output/mybook_pdf/chunks_manifest_v2.json \
  --out output/mybook_pdf \
  --all
```

### Output Structure

```text
output/mybook_pdf/
  000_full_book.txt
  001_chapter_01.txt
  qwen_full.txt
  qwen_chunks/
  chunks_manifest_v2.json
  audio_chunks/
  chapter_001.wav
  audit_log.json
```

### Development

```bash
python install.py --with-dev
python -m ruff check .
python -m pytest
```

---

## Русский

### Что делает приложение

Books to Audio - локальный production-инструмент для подготовки аудиокниг из длинных текстов. Он не просто запускает TTS, а готовит книгу к озвучке: достает текст, чистит его, разбивает на главы и реплики, помогает разметить роли и голоса, синтезирует чанки через ComfyUI/Qwen3-TTS, проверяет результат и собирает финальные аудиофайлы.

1. Загружает книги из `TXT`, `PDF`, `EPUB`, `FB2`, `DOCX`.
2. Извлекает текст; для сканированных PDF может использовать Tesseract OCR.
3. Нормализует пунктуацию, пробелы, числа, OCR-ошибки и языковые особенности.
4. Определяет главы, диалоги, говорящих, роли и распределение голосов.
5. Создает v2-манифест чанков: `chunks_manifest_v2.json`.
6. Отправляет чанки в ComfyUI через Qwen3-TTS workflow.
7. Сохраняет аудио чанков, повторяет ошибки, запускает QA и собирает финальные главы.

Основные возможности:

| Зона | Что делает |
| --- | --- |
| Импорт книг | Читает TXT, PDF, EPUB, FB2 и DOCX. |
| OCR | Обрабатывает сканированные PDF через Tesseract, если обычного извлечения текста недостаточно. |
| Нормализация | Исправляет пунктуацию, пробелы, OCR-артефакты, числа, сокращения, `ё`, ударения и языковые особенности. |
| LLM-обработка | Использует локальные Ollama/Qwen модели для нормализации, чанкинга, диалогов и разметки голосов. |
| Структура книги | Находит главы, диалоги, говорящих, роли и production metadata. |
| Подготовка к TTS | Создает `chunks_manifest_v2.json` с чанками, привязанными к главам и голосам. |
| Синтез | Отправляет чанки в ComfyUI/Qwen3-TTS и сохраняет статус каждого аудиофрагмента. |
| QA и сборка | Проверяет аудио, повторяет неудачные чанки и собирает WAV/MP3 главы. |

Production-путь:

```text
Файл книги -> извлечение/OCR -> нормализация -> главы -> роли
-> chunks_manifest_v2.json -> ComfyUI/Qwen3-TTS -> audio chunks
-> QA -> WAV/MP3 главы
```

### Поддерживаемые платформы

| OS | Статус | Комментарий |
| --- | --- | --- |
| Windows 10/11 | Поддерживается | Используйте `install.bat` и `run_gui.bat`. |
| Linux | Поддерживается | Лучший вариант для локального CUDA/GPU TTS и ComfyUI. |
| macOS | Поддерживается | GUI, OCR, LLM и ComfyUI endpoint работают. CUDA-only runner не является production-путем на macOS. |

Требование: **Python 3.10+**. Рекомендуется **Python 3.12**.

### Клонирование репозитория

```bash
git clone <repo-url>
cd books-to-audio
```

Пример:

```bash
git clone https://github.com/<owner>/<repo>.git
cd books-to-audio
```

### Установка

Windows:

```powershell
install.bat
run_gui.bat
```

Linux/macOS:

```bash
chmod +x install.sh run_gui.sh
./install.sh
./run_gui.sh
```

Универсально:

```bash
python install.py
```

Полезные профили:

```bash
python install.py                         # desktop: GUI + OCR + LLM + audio helpers
python install.py --minimal               # только базовые зависимости
python install.py --with-dev              # pytest + ruff
python install.py --with-asr              # зависимости для ASR QA
python install.py --with-stress           # Silero stress
python install.py --with-tts              # прямой Qwen-TTS runtime
python install.py --with-sage             # Qwen-TTS + SageAttention, Linux/CUDA
python install.py --recreate              # пересоздать virtualenv
python install.py --dry-run               # показать план установки
python install.py --yes                   # использовать значения по умолчанию
python install.py --interactive           # спросить пути и загрузки
python install.py --install-system-tools  # установить системные Tesseract/FFmpeg/GUI пакеты где поддерживается
python install.py --install-ollama        # установить Ollama, если ее нет
python install.py --install-comfyui       # подготовить локальный ComfyUI + Qwen3-TTS custom nodes
```

### Куда скачиваются модели

Installer сохраняет пути в:

```text
data/local_runtime_paths.json
```

и дублирует их в `.env`.

| Что хранится | Путь / настройка | Переменная окружения |
| --- | --- | --- |
| Qwen3-TTS / ComfyUI модели | Windows: `D:/ComfyUI-external/models`; Linux/WSL: `/mnt/d/ComfyUI-external/models`; или `--models-dir` | `BOOKS_TO_AUDIO_MODELS_DIR`, `COMFYUI_MODELS_DIR` |
| Папка TTS-моделей | `<models-dir>/audio_encoders/` | те же |
| Hugging Face cache | `--hf-cache-dir` или выбранная папка | `HF_HOME` |
| Ollama модели | по умолчанию `<repo>/ollama-models` или `--ollama-models-dir` | `BOOKS_TO_AUDIO_OLLAMA_MODELS_DIR`, `OLLAMA_MODELS` |
| Tesseract языки | `<repo>/data/tessdata` при `--download-tessdata` | `BOOKS_TO_AUDIO_TESSDATA_DIR`, `TESSDATA_PREFIX` |

Ожидаемая структура:

```text
models/
  audio_encoders/
    Qwen3-TTS-12Hz-1.7B-Base/
    Qwen3-TTS-12Hz-1.7B-CustomVoice/
    Qwen3-TTS-Tokenizer-12Hz/
```

Скачать TTS-модели:

```bash
python install.py --download-tts-models
```

Скачать Ollama-модели:

```bash
python install.py --download-ollama-models
```

или вручную:

```bash
ollama pull hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M
ollama pull hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M
```

Полная подготовка нового компьютера:

```bash
python install.py --interactive \
  --install-system-tools \
  --install-ollama \
  --download-ollama-models \
  --download-tts-models \
  --install-comfyui
```

В интерактивном режиме installer спрашивает, устанавливать ли Ollama и ComfyUI. Если они уже установлены, он сообщает текущий путь и не переустанавливает. Для кастомных путей используйте `--ollama-bin`, `--comfyui-root` и `--models-dir`.

### Требования к ресурсам

| Ресурс | Минимум | Рекомендуется |
| --- | --- | --- |
| CPU | 4 ядра | 8+ ядер |
| RAM | 8 GB | 16-32 GB |
| Диск | 10 GB свободно | 50+ GB для моделей, книг и output |
| GPU | Не нужен для text-only workflow | NVIDIA GPU для production TTS |
| VRAM | Не нужен для text-only workflow | 8 GB минимум; 12-24 GB лучше для тяжелого TTS/QA |

Для production-синтеза через ComfyUI/Qwen3-TTS нужен GPU-хост. Модели большие, лучше хранить их на быстром SSD.

### Запуск

Windows:

```powershell
run_gui.bat
```

Linux/macOS:

```bash
./run_gui.sh
```

Проверка окружения:

```bash
normalize-book doctor --skip-network
normalize-book doctor
```

### Production CLI

```bash
normalize-book pipeline books/mybook.pdf --out output --llm-normalize
```

С синтезом и сборкой:

```bash
normalize-book pipeline books/mybook.pdf \
  --out output \
  --llm-normalize \
  --synthesize \
  --workflow comfyui_workflows/qwen3_tts_template.json \
  --assemble
```

---

## 中文

### 应用功能

Books to Audio 是一个本地优先的有声书生产工具。它不只是启动 TTS，而是完成长篇书籍生产流程：文本提取、清理、章节和对话结构化、角色/语音规划、分块合成、质量检查和最终音频组装。

1. 导入 `TXT`、`PDF`、`EPUB`、`FB2`、`DOCX`。
2. 提取文本；扫描版 PDF 可使用 Tesseract OCR。
3. 清理标点、空白、数字、OCR 错误和语言相关问题。
4. 识别章节、对话、说话人、角色和语音分配。
5. 生成 v2 分块清单：`chunks_manifest_v2.json`。
6. 通过 ComfyUI/Qwen3-TTS 合成音频。
7. 保存音频分块、重试失败项、执行 QA，并合成最终章节音频。

核心能力：

| 模块 | 功能 |
| --- | --- |
| 书籍导入 | 读取 TXT、PDF、EPUB、FB2、DOCX。 |
| OCR | 使用 Tesseract 处理扫描版 PDF。 |
| 文本清理 | 修复标点、空白、OCR 错误、数字、缩写和语言相关问题。 |
| LLM 处理 | 通过本地 Ollama/Qwen 进行规范化、分块、对话分析和语音标注。 |
| 结构化 | 识别章节、对话、说话人、角色和 production metadata。 |
| TTS 准备 | 生成按章节和语音组织的 `chunks_manifest_v2.json`。 |
| 音频合成 | 将分块发送到 ComfyUI/Qwen3-TTS，并记录每个分块状态。 |
| QA 和组装 | 检查音频、重试失败分块，并生成 WAV/MP3 章节文件。 |

Production 流程：

```text
Book file -> extraction/OCR -> normalization -> chapters -> roles
-> chunks_manifest_v2.json -> ComfyUI/Qwen3-TTS -> audio chunks
-> QA -> WAV/MP3 chapters
```

### 支持平台

| OS | 状态 | 说明 |
| --- | --- | --- |
| Windows 10/11 | 支持 | 使用 `install.bat` 和 `run_gui.bat`。 |
| Linux | 支持 | 推荐用于本地 CUDA/GPU TTS 和 ComfyUI。 |
| macOS | 支持 | 支持 GUI、OCR、LLM 和 ComfyUI endpoint；CUDA-only TTS 不适合作为 macOS production 路径。 |

要求：**Python 3.10+**，推荐 **Python 3.12**。

### 克隆仓库

```bash
git clone <repo-url>
cd books-to-audio
```

示例：

```bash
git clone https://github.com/<owner>/<repo>.git
cd books-to-audio
```

### 安装

Windows:

```powershell
install.bat
run_gui.bat
```

Linux/macOS:

```bash
chmod +x install.sh run_gui.sh
./install.sh
./run_gui.sh
```

跨平台：

```bash
python install.py
```

常用参数：

```bash
python install.py --minimal
python install.py --with-dev
python install.py --with-asr
python install.py --with-stress
python install.py --with-tts
python install.py --with-sage
python install.py --interactive
python install.py --download-tts-models
python install.py --download-ollama-models
```

### 模型下载位置

安装器将运行时路径写入：

```text
data/local_runtime_paths.json
```

并写入 `.env`。

| 资源 | 路径 / 配置 | 环境变量 |
| --- | --- | --- |
| Qwen3-TTS / ComfyUI 模型 | Windows: `D:/ComfyUI-external/models`; Linux/WSL: `/mnt/d/ComfyUI-external/models`; 或 `--models-dir` | `BOOKS_TO_AUDIO_MODELS_DIR`, `COMFYUI_MODELS_DIR` |
| TTS 子目录 | `<models-dir>/audio_encoders/` | 同上 |
| Hugging Face 缓存 | `--hf-cache-dir` | `HF_HOME` |
| Ollama 模型 | 默认 `<repo>/ollama-models` 或 `--ollama-models-dir` | `BOOKS_TO_AUDIO_OLLAMA_MODELS_DIR`, `OLLAMA_MODELS` |
| Tesseract 语言数据 | `<repo>/data/tessdata` | `BOOKS_TO_AUDIO_TESSDATA_DIR`, `TESSDATA_PREFIX` |

下载模型：

```bash
python install.py --download-tts-models
python install.py --download-ollama-models
```

### 资源要求

| 资源 | 最低 | 推荐 |
| --- | --- | --- |
| CPU | 4 核 | 8+ 核 |
| RAM | 8 GB | 16-32 GB |
| 磁盘 | 10 GB 可用 | 50+ GB |
| GPU | 纯文本流程不需要 | production TTS 推荐 NVIDIA GPU |
| VRAM | 纯文本流程不需要 | 至少 8 GB；12-24 GB 更好 |

### 启动和 CLI

```bash
python -m book_normalizer.gui.app
normalize-book doctor
normalize-book pipeline books/mybook.pdf --out output --llm-normalize
normalize-book pipeline books/mybook.pdf --out output --llm-normalize --synthesize --workflow comfyui_workflows/qwen3_tts_template.json --assemble
```

---

## Қазақша

### Қолданба не істейді

Books to Audio - ұзақ кітаптарды аудиокітап өндірісіне дайындайтын жергілікті құрал. Ол тек TTS іске қоспайды: мәтінді шығарады, тазалайды, тараулар мен диалогтарды құрылымдайды, рөлдер мен дауыстарды жоспарлайды, чанктарды синтездейді, сапаны тексереді және финалдық аудионы жинайды.

1. `TXT`, `PDF`, `EPUB`, `FB2`, `DOCX` файлдарын ашады.
2. Мәтінді шығарады; сканерленген PDF үшін Tesseract OCR қолдана алады.
3. Пунктуацияны, бос орындарды, сандарды, OCR қателерін және тілдік ерекшеліктерді түзетеді.
4. Тарауларды, диалогтарды, кейіпкерлерді, рөлдерді және дауыстарды анықтайды.
5. `chunks_manifest_v2.json` манифесін жасайды.
6. Чанктарды ComfyUI/Qwen3-TTS workflow арқылы синтездейді.
7. Аудио чанктарды сақтайды, қателерді қайта өңдейді, QA жүргізеді және финалдық тарауларды жинайды.

Негізгі мүмкіндіктер:

| Бөлім | Қызметі |
| --- | --- |
| Кітап импорты | TXT, PDF, EPUB, FB2 және DOCX оқиды. |
| OCR | Сканерленген PDF файлдарын Tesseract арқылы өңдейді. |
| Мәтінді тазалау | Пунктуацияны, бос орындарды, OCR қателерін, сандарды және тілдік ерекшеліктерді түзетеді. |
| LLM өңдеу | Жергілікті Ollama/Qwen арқылы нормализация, чанкинг, диалог және дауыс белгілеу жасайды. |
| Құрылым | Тарауларды, диалогтарды, сөйлеушілерді, рөлдерді және production metadata анықтайды. |
| TTS дайындау | Тараулар мен дауыстарға байланыстырылған `chunks_manifest_v2.json` жасайды. |
| Синтез | Чанктарды ComfyUI/Qwen3-TTS жүйесіне жібереді және статусын сақтайды. |
| QA және жинау | Аудионы тексереді, сәтсіз чанктарды қайталайды және WAV/MP3 тарауларын жинайды. |

Production ағымы:

```text
Кітап файлы -> мәтін/OCR -> нормализация -> тараулар -> рөлдер
-> chunks_manifest_v2.json -> ComfyUI/Qwen3-TTS -> audio chunks
-> QA -> WAV/MP3 тараулар
```

### Платформалар

| OS | Күйі | Ескерту |
| --- | --- | --- |
| Windows 10/11 | Қолдау бар | `install.bat`, `run_gui.bat`. |
| Linux | Қолдау бар | CUDA/GPU TTS және ComfyUI үшін ең ыңғайлы. |
| macOS | Қолдау бар | GUI, OCR, LLM және ComfyUI endpoint жұмыс істейді. |

Талап: **Python 3.10+**, ұсынылады **Python 3.12**.

### Репозиторийді көшіру

```bash
git clone <repo-url>
cd books-to-audio
```

Мысал:

```bash
git clone https://github.com/<owner>/<repo>.git
cd books-to-audio
```

### Орнату

Windows:

```powershell
install.bat
run_gui.bat
```

Linux/macOS:

```bash
chmod +x install.sh run_gui.sh
./install.sh
./run_gui.sh
```

Барлық жүйелер үшін:

```bash
python install.py
```

Қосымша параметрлер:

```bash
python install.py --minimal
python install.py --with-dev
python install.py --with-asr
python install.py --with-stress
python install.py --with-tts
python install.py --with-sage
python install.py --interactive
python install.py --download-tts-models
python install.py --download-ollama-models
```

### Модельдер қайда сақталады

Орнатушы жолдарды мына файлға жазады:

```text
data/local_runtime_paths.json
```

| Ресурс | Жол / баптау | Environment variable |
| --- | --- | --- |
| Qwen3-TTS / ComfyUI models | Windows: `D:/ComfyUI-external/models`; Linux/WSL: `/mnt/d/ComfyUI-external/models`; немесе `--models-dir` | `BOOKS_TO_AUDIO_MODELS_DIR`, `COMFYUI_MODELS_DIR` |
| TTS ішкі папкасы | `<models-dir>/audio_encoders/` | сол айнымалылар |
| Hugging Face cache | `--hf-cache-dir` | `HF_HOME` |
| Ollama models | әдетте `<repo>/ollama-models` немесе `--ollama-models-dir` | `BOOKS_TO_AUDIO_OLLAMA_MODELS_DIR`, `OLLAMA_MODELS` |
| Tesseract тіл деректері | `<repo>/data/tessdata` | `BOOKS_TO_AUDIO_TESSDATA_DIR`, `TESSDATA_PREFIX` |

Модельдерді жүктеу:

```bash
python install.py --download-tts-models
python install.py --download-ollama-models
```

### Ресурс талаптары

| Ресурс | Минимум | Ұсынылады |
| --- | --- | --- |
| CPU | 4 core | 8+ core |
| RAM | 8 GB | 16-32 GB |
| Disk | 10 GB бос орын | 50+ GB |
| GPU | text-only үшін қажет емес | production TTS үшін NVIDIA GPU |
| VRAM | text-only үшін қажет емес | кемінде 8 GB; 12-24 GB жақсырақ |

### Іске қосу

```bash
python -m book_normalizer.gui.app
normalize-book doctor
normalize-book pipeline books/mybook.pdf --out output --llm-normalize
normalize-book pipeline books/mybook.pdf --out output --llm-normalize --synthesize --workflow comfyui_workflows/qwen3_tts_template.json --assemble
```

---

## O'zbekcha

### Ilova nima qiladi

Books to Audio - uzun kitoblarni audiokitob ishlab chiqarishga tayyorlaydigan lokal vosita. U faqat TTS ishga tushirmaydi: matnni ajratadi, tozalaydi, boblar va dialoglarni tuzadi, rollar va ovozlarni rejalashtiradi, chanklarni sintez qiladi, sifatni tekshiradi va yakuniy audioni yig'adi.

1. `TXT`, `PDF`, `EPUB`, `FB2`, `DOCX` fayllarini yuklaydi.
2. Matnni ajratadi; skanerlangan PDF uchun Tesseract OCR ishlatilishi mumkin.
3. Tinish belgilari, bo'shliqlar, raqamlar, OCR xatolari va tilga xos muammolarni normallashtiradi.
4. Boblar, dialoglar, personajlar, rollar va ovozlarni aniqlaydi.
5. `chunks_manifest_v2.json` manifestini yaratadi.
6. Chanklarni ComfyUI/Qwen3-TTS workflow orqali sintez qiladi.
7. Audio chanklarni saqlaydi, xatolarni qayta ishlaydi, QA bajaradi va yakuniy boblarni yig'adi.

Asosiy imkoniyatlar:

| Bo'lim | Vazifasi |
| --- | --- |
| Kitob importi | TXT, PDF, EPUB, FB2 va DOCX o'qiydi. |
| OCR | Skanerlangan PDF fayllarini Tesseract orqali qayta ishlaydi. |
| Matnni tozalash | Tinish belgilari, bo'shliqlar, OCR xatolari, raqamlar va tilga xos muammolarni tuzatadi. |
| LLM ishlovi | Lokal Ollama/Qwen orqali normalizatsiya, chanking, dialog va ovoz belgilashni bajaradi. |
| Tuzilma | Boblar, dialoglar, gapiruvchilar, rollar va production metadata ni aniqlaydi. |
| TTS tayyorlash | Boblar va ovozlarga bog'langan `chunks_manifest_v2.json` yaratadi. |
| Sintez | Chanklarni ComfyUI/Qwen3-TTS ga yuboradi va har bir chank statusini saqlaydi. |
| QA va yig'ish | Audioni tekshiradi, muvaffaqiyatsiz chanklarni qayta ishlaydi va WAV/MP3 boblarini yig'adi. |

Production oqimi:

```text
Kitob fayli -> matn/OCR -> normalizatsiya -> boblar -> rollar
-> chunks_manifest_v2.json -> ComfyUI/Qwen3-TTS -> audio chunks
-> QA -> WAV/MP3 boblar
```

### Platformalar

| OS | Holat | Izoh |
| --- | --- | --- |
| Windows 10/11 | Qo'llab-quvvatlanadi | `install.bat`, `run_gui.bat`. |
| Linux | Qo'llab-quvvatlanadi | CUDA/GPU TTS va ComfyUI uchun eng yaxshi yo'l. |
| macOS | Qo'llab-quvvatlanadi | GUI, OCR, LLM va ComfyUI endpoint ishlaydi. |

Talab: **Python 3.10+**, tavsiya etiladi **Python 3.12**.

### Repozitoriyni klonlash

```bash
git clone <repo-url>
cd books-to-audio
```

Misol:

```bash
git clone https://github.com/<owner>/<repo>.git
cd books-to-audio
```

### O'rnatish

Windows:

```powershell
install.bat
run_gui.bat
```

Linux/macOS:

```bash
chmod +x install.sh run_gui.sh
./install.sh
./run_gui.sh
```

Universal:

```bash
python install.py
```

Foydali parametrlar:

```bash
python install.py --minimal
python install.py --with-dev
python install.py --with-asr
python install.py --with-stress
python install.py --with-tts
python install.py --with-sage
python install.py --interactive
python install.py --download-tts-models
python install.py --download-ollama-models
```

### Modellar qayerga yuklanadi

Installer yo'llarni shu faylga yozadi:

```text
data/local_runtime_paths.json
```

| Resurs | Yo'l / sozlama | Environment variable |
| --- | --- | --- |
| Qwen3-TTS / ComfyUI models | Windows: `D:/ComfyUI-external/models`; Linux/WSL: `/mnt/d/ComfyUI-external/models`; yoki `--models-dir` | `BOOKS_TO_AUDIO_MODELS_DIR`, `COMFYUI_MODELS_DIR` |
| TTS ichki papkasi | `<models-dir>/audio_encoders/` | yuqoridagi |
| Hugging Face cache | `--hf-cache-dir` | `HF_HOME` |
| Ollama models | odatda `<repo>/ollama-models` yoki `--ollama-models-dir` | `BOOKS_TO_AUDIO_OLLAMA_MODELS_DIR`, `OLLAMA_MODELS` |
| Tesseract til fayllari | `<repo>/data/tessdata` | `BOOKS_TO_AUDIO_TESSDATA_DIR`, `TESSDATA_PREFIX` |

Modellarni yuklash:

```bash
python install.py --download-tts-models
python install.py --download-ollama-models
```

### Resurs talablari

| Resurs | Minimum | Tavsiya |
| --- | --- | --- |
| CPU | 4 core | 8+ core |
| RAM | 8 GB | 16-32 GB |
| Disk | 10 GB bo'sh joy | 50+ GB |
| GPU | text-only uchun shart emas | production TTS uchun NVIDIA GPU |
| VRAM | text-only uchun shart emas | kamida 8 GB; 12-24 GB yaxshiroq |

### Ishga tushirish

```bash
python -m book_normalizer.gui.app
normalize-book doctor
normalize-book pipeline books/mybook.pdf --out output --llm-normalize
normalize-book pipeline books/mybook.pdf --out output --llm-normalize --synthesize --workflow comfyui_workflows/qwen3_tts_template.json --assemble
```

---

## Runtime Notes

- Use `normalize-book doctor` before a production run.
- Use the v2 manifest path only. Legacy v1/direct runner flows are removed.
- ComfyUI must expose its API, usually at `http://localhost:8188`.
- Ollama must expose its API, usually at `http://localhost:11434`.
