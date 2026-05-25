# Books to Audio

Books to Audio - инструмент для подготовки русскоязычных книг к озвучке:
загрузка PDF/TXT/EPUB/FB2/DOCX, нормализация текста, разметка глав и реплик,
нарезка на TTS-чанки, синтез через ComfyUI/Qwen3-TTS и сборка WAV/MP3.

GUI доступен на русском, английском, китайском, казахском и узбекском языках.
Нормализация, LLM-разметка голосов и chunk manifest покрывают языки
`ru/en/zh/kk/uz`; русские правила ударений и `ё` применяются только для `ru`.

## Поддерживаемые OS

| OS | Статус | Комментарий |
| --- | --- | --- |
| Windows 10/11 | Поддерживается | Есть `install.bat` и `run_gui.bat`. TTS pipeline uses `chunks_manifest_v2.json` + ComfyUI. |
| Linux | Поддерживается | Основной путь для локального GPU/CUDA TTS. GUI работает через PyQt6. |
| macOS | Поддерживается | GUI, OCR, LLM-чанкинг и работа с ComfyUI. Локальный CUDA TTS недоступен на Mac, используйте ComfyUI/remote GPU. |

Минимальная версия Python: **3.10+**. Рекомендуется Python **3.12**.

## Быстрый старт

Склонируйте репозиторий и запустите установщик.

```bash
git clone <repo-url>
cd books-to-audio
```

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

Универсальный вариант для любой OS:

```bash
python install.py
```

После установки запускайте через wrapper (`run_gui.bat` / `run_gui.sh`) или через Python из virtualenv.

Windows:

```powershell
.venv-windows\Scripts\python.exe -m book_normalizer.gui.app
```

Linux/macOS:

```bash
.venv/bin/python -m book_normalizer.gui.app
```

`install.py` создает `.venv`, обновляет `pip`, ставит пакет в editable-режиме,
проверяет импорты, спрашивает пути для моделей/Hugging Face/Ollama в
интерактивном терминале и сохраняет их в `data/local_runtime_paths.json`.
Для Ollama-моделей можно выбрать отдельную папку через
`--ollama-models-dir`; installer передает ее в native Ollama как
`OLLAMA_MODELS`, поэтому `ollama pull` не пишет модели в неожиданное место.
Windows wrapper `install.bat` использует `.venv-windows`, чтобы не смешивать
Windows GUI и Linux `.venv`. По умолчанию ставится desktop-профиль: GUI, OCR,
LLM-клиент и audio helpers. `install.log` перезаписывается при каждом запуске.

## Системные зависимости

Python-зависимости ставит `install.py`. Системные утилиты зависят от OS и нужны для отдельных функций.

### Windows

```powershell
winget install Python.Python.3.12
winget install UB-Mannheim.TesseractOCR
winget install Gyan.FFmpeg
```

После установки Tesseract перезапустите терминал, чтобы обновился `PATH`.

### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip \
  tesseract-ocr tesseract-ocr-eng tesseract-ocr-rus \
  tesseract-ocr-chi-sim tesseract-ocr-kaz tesseract-ocr-uzb \
  ffmpeg libegl1 libgl1 libxcb-cursor0 libxkbcommon-x11-0 fonts-noto-cjk
```

### Fedora

```bash
sudo dnf install python3 python3-pip tesseract \
  tesseract-langpack-eng tesseract-langpack-rus tesseract-langpack-chi_sim \
  tesseract-langpack-kaz tesseract-langpack-uzb ffmpeg \
  libglvnd-glx libxkbcommon-x11 xcb-util-cursor google-noto-sans-cjk-fonts
```

### Arch Linux

```bash
sudo pacman -S python python-pip tesseract \
  tesseract-data-eng tesseract-data-rus tesseract-data-chi_sim \
  tesseract-data-kaz tesseract-data-uzb ffmpeg \
  libgl libxkbcommon-x11 xcb-util-cursor noto-fonts-cjk
```

### macOS

```bash
brew install python tesseract tesseract-lang ffmpeg
```

Если GUI не нужен, используйте `python install.py --minimal` или уберите GUI extra:

```bash
python install.py --without-gui
```

## Профили установки

```bash
python install.py                         # desktop: GUI + OCR + LLM + audio helpers
python install.py --minimal               # только core-зависимости
python install.py --with-dev              # pytest + ruff
python install.py --with-stress           # silero-stress для ударений
python install.py --with-tts              # прямой Qwen-TTS runner, лучше Linux/CUDA
python install.py --with-sage             # Qwen-TTS + SageAttention, только Linux/CUDA
python install.py --recreate              # пересоздать .venv
python install.py --dry-run               # показать план без установки
python install.py --yes                   # не спрашивать пути, взять defaults/flags
python install.py --interactive           # явно спросить пути и optional downloads
python install.py --ollama-models-dir D:/OllamaModels
python install.py --tesseract-bin "C:/Program Files/Tesseract-OCR/tesseract.exe" --tessdata-dir "C:/Program Files/Tesseract-OCR/tessdata"
python install.py --download-ollama-models
python install.py --download-tts-models --verify-hashes
```

Старый вариант тоже работает:

```bash
pip install -r requirements.txt
```

Но для новых установок предпочтителен `install.py`, потому что он одинаково работает на Windows, Linux и macOS и дает подсказки по системным пакетам.

## Проверка окружения

После установки:

```bash
# Windows
.venv-windows\Scripts\normalize-book.exe doctor --skip-network

# Linux/macOS
.venv/bin/normalize-book doctor --skip-network
```

Полная проверка с Ollama и ComfyUI:

```bash
normalize-book doctor
```

Если команда `normalize-book` не найдена, активируйте виртуальное окружение.

Windows:

```powershell
.venv-windows\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

## Настройка OCR

OCR нужен только для сканов PDF. Для обычных EPUB/FB2/TXT/DOCX можно работать без Tesseract.

Проверьте:

```bash
tesseract --version
tesseract --list-langs
```

Для книг на поддерживаемых языках должны быть доступны коды `eng`, `rus`,
`chi_sim`, `kaz`, `uzb`. Если их нет, запустите native installer:

```bash
# Windows
install.bat --interactive --install-system-tools

# Linux/macOS
./install.sh --interactive --install-system-tools
```

## Настройка LLM через нативную Ollama

LLM используется для нормализации текста и умной разметки голосов. Ollama должна
работать нативно в той OS, где запускается приложение, либо быть доступной по
HTTP endpoint. Важно не держать одновременно несколько больших моделей:
приложение отправляет запросы через native `/api/chat`, использует
`num_parallel=1`, `num_ctx=4096`, `think=false`, `keep_alive` и выгружает модели
после батчей.

Установка Ollama:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
```

На Windows можно поставить Ollama Desktop или указать полный путь к `ollama.exe`
в `install.py --ollama-bin`. Главное, чтобы `http://localhost:11434` отвечал из
приложения; в dev shell должен быть доступен тот же endpoint.
Если модели должны лежать на другом диске, запускайте installer с
`--ollama-models-dir` или укажите путь в interactive-режиме; он сохранится в
`data/local_runtime_paths.json` и `.env`, а `ollama pull` получит `OLLAMA_MODELS`.

Рекомендуемые модели для 8 GB VRAM / 16 GB RAM:

```bash
ollama pull hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M
ollama pull hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M
```

Маршрутизация языков:

```text
ru/en/zh/kk/uz -> hf.co/Qwen/Qwen3-8B-GGUF:Q4_K_M
fallback       -> hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M
```

По умолчанию приложение использует native Ollama endpoint:

```text
http://localhost:11434
```

`gemma3:12b` не используется по умолчанию: размер модели плюс KV/cache слишком
рискованны для 8 GB VRAM.

Если включить `LLM/GPU нормализация`, книга получает metadata-флаг
`llm_processing_enabled`, а вкладка голосов автоматически выбирает LLM smart
markup с тем же language/model profile. Если 8B не проходит validation,
приложение пробует 4B; если модели не сохраняют текст, создается review report
с проблемными окнами вместо тихого downgrade.

Ручной benchmark качества:

```bash
python scripts/quality_benchmark.py
RUN_OLLAMA_TESTS=1 python scripts/quality_benchmark.py --run-ollama
RUN_OLLAMA_TESTS=1 python scripts/quality_benchmark.py --run-ollama --ollama-lightweight --languages en --max-chars 300
RUN_OLLAMA_TESTS=1 python scripts/quality_benchmark.py --run-ollama --languages ru --book-glob "*.fb2" --limit-books 1 --max-chars 350
python scripts/quality_benchmark.py --skip-synthetic --book-glob "*.pdf" --limit-books 1
```

Воспроизводимый public corpus для `en/zh/kk/uz` можно скачать без коммита самих
текстов:

```bash
python scripts/fetch_quality_corpus.py --out-dir output/public_quality_corpus
python scripts/quality_benchmark.py \
  --skip-synthetic \
  --books-dir output/public_quality_corpus \
  --languages en,zh,kk,uz \
  --book-language-map output/public_quality_corpus/languages.json \
  --out-dir output/quality_reports_public_corpus
```

Для реального многоязычного корпуса задавайте язык на файл через JSON-карту,
иначе TXT/DOCX/PDF без метаданных будут проверяться с общим `--book-language`.
Пример `books/languages.json`:

```json
{
  "english/*.txt": "en",
  "china/*.epub": "zh",
  "kazakh/*.fb2": "kk",
  "uzbek/*.pdf": "uz"
}
```

Запуск:

```bash
python scripts/quality_benchmark.py \
  --skip-synthetic \
  --books-dir books \
  --languages en,zh,kk,uz \
  --book-language-map books/languages.json

RUN_OLLAMA_TESTS=1 python scripts/quality_benchmark.py \
  --run-ollama \
  --books-dir books \
  --languages en,zh,kk,uz \
  --book-language-map books/languages.json \
  --limit-books 4 \
  --max-chars 600
```

Отчеты пишутся в `output/quality_reports`. Локальные книги из `books/` используются только для проверки и не коммитятся.

## Настройка TTS

Рекомендуемый production-путь - ComfyUI с Qwen3-TTS nodes.

1. Запустите ComfyUI.
2. Убедитесь, что API доступен на `http://localhost:8188`.
3. Положите или настройте workflow в `comfyui_workflows/qwen3_tts_template.json`.
4. В workflow должны быть placeholders:
   - `{{TEXT}}`
   - `{{VOICE_ID}}`
   - `{{INSTRUCT}}`
   - `{{OUTPUT_FILENAME}}`

Модели можно хранить в общем каталоге и указать его через переменную:

```bash
export BOOKS_TO_AUDIO_MODELS_DIR="/path/to/ComfyUI/models"
```

Windows PowerShell:

```powershell
$env:BOOKS_TO_AUDIO_MODELS_DIR="D:\ComfyUI-external\models"
```

Ожидаемая структура:

```text
models/
  audio_encoders/
    Qwen3-TTS-12Hz-1.7B-Base/
    Qwen3-TTS-12Hz-1.7B-CustomVoice/
    Qwen3-TTS-Tokenizer-12Hz/
```

### Установка TTS-моделей из Hugging Face

В GUI откройте вкладку **Синтез**, заранее выберите папку **Models dir** и нажмите
**Скачать модели**. Приложение скачает нужные Qwen3-TTS репозитории с Hugging Face
в выбранную папку, например:

```text
models/
  audio_encoders/
    Qwen3-TTS-12Hz-1.7B-CustomVoice/
    Qwen3-TTS-12Hz-1.7B-Base/
    Qwen3-TTS-Tokenizer-12Hz/
```

CLI-вариант:

```bash
normalize-book install-tts-models --models-dir /path/to/models \
  --model Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice --with-base
```

Предупреждение: модели большие, скачивание может занять много времени и потребовать
несколько гигабайт свободного места. Нужен доступ в интернет к Hugging Face; если
репозиторий требует авторизации, задайте `HF_TOKEN` или передайте `--token`.
Python-зависимость для скачивания: `huggingface-hub` (ставится через `install.py`).
Для прямого Qwen-TTS runner также нужны `qwen-tts`, `torch`, `soundfile`, `numpy`;
на практике для production-озвучки рекомендуется нативный CUDA GPU-хост или
ComfyUI endpoint с достаточной VRAM.

Direct `scripts/tts_runner.py` legacy flow has been removed. Use `chunks_manifest_v2.json` + ComfyUI synthesis.

```bash
python install.py --with-tts
```

SageAttention:

```bash
python install.py --with-sage
```

На macOS прямой CUDA runner не является production-путем. Используйте ComfyUI на другом GPU-хосте или внешний endpoint.

## Запуск GUI

Windows:

```powershell
run_gui.bat
```

Linux/macOS:

```bash
./run_gui.sh
```

Или напрямую:

```bash
python -m book_normalizer.gui.app
```

Визуальный аудит GUI с PNG-скриншотами и JSON-summary:

```bash
python scripts/gui_visual_audit.py --out-dir output/gui_visual_audit
```

## CLI workflow

Нормализовать книгу:

```bash
normalize-book process books/mybook.pdf --out output --ocr-mode auto
```

Рекомендуемый pipeline без синтеза:

```bash
normalize-book pipeline books/mybook.pdf --out output --llm-normalize
```

Pipeline с ComfyUI-синтезом и сборкой глав:

```bash
normalize-book pipeline books/mybook.pdf \
  --out output \
  --llm-normalize \
  --synthesize \
  --workflow comfyui_workflows/qwen3_tts_template.json \
  --assemble
```

Собрать уже синтезированные chunks:

```bash
python scripts/assemble_chapter.py \
  --manifest output/mybook_pdf/chunks_manifest_v2.json \
  --out output/mybook_pdf \
  --all
```

## Структура output

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

## Что хранить в репозитории

В git должны попадать только код, тесты, документация, workflow templates и маленькие ассеты.

Не коммитим:

- `.venv/`, `.venv-windows/`, `venv/`, `env/`
- `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.coverage`
- `books/`
- `output/`
- `data/`
- временные файлы редакторов и OS

`books/` и `output/` специально добавлены в `.gitignore`: локальные книги и результаты работы остаются у пользователя и не засоряют репозиторий.

## Разработка

```bash
python install.py --with-dev
python -m ruff check .
python -m pytest
```

CI запускается на Windows, Ubuntu и macOS.

## Troubleshooting

`No module named book_normalizer`:

```bash
python install.py
```

OCR не работает:

```bash
tesseract --version
tesseract --list-langs
```

Проверьте, что установлен русский language pack.

GUI не стартует на Linux:

```bash
sudo apt-get install -y libegl1 libgl1 libxcb-cursor0 libxkbcommon-x11-0
```

MP3 не создается:

```bash
ffmpeg -version
```

ComfyUI недоступен:

```bash
normalize-book doctor
```

Проверьте, что ComfyUI запущен и API доступен по `http://localhost:8188`.
