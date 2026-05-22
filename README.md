# Books to Audio

Books to Audio - инструмент для подготовки русскоязычных книг к озвучке:
загрузка PDF/TXT/EPUB/FB2/DOCX, нормализация текста, разметка глав и реплик,
нарезка на TTS-чанки, синтез через ComfyUI/Qwen3-TTS и сборка WAV/MP3.

GUI доступен на русском, английском, китайском, казахском и узбекском языках.
Пока озвучка и обработка книг рассчитаны только на русский язык.

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

`install.py` создает `.venv`, обновляет `pip`, ставит пакет в editable-режиме и проверяет импорты. Windows wrapper `install.bat` использует `.venv-windows`, чтобы не смешивать Windows GUI и Linux/WSL `.venv`. По умолчанию ставится desktop-профиль: GUI, OCR, LLM-клиент и audio helpers.

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
  tesseract-ocr tesseract-ocr-rus ffmpeg \
  libegl1 libgl1 libxcb-cursor0 libxkbcommon-x11-0
```

### Fedora

```bash
sudo dnf install python3 python3-pip tesseract tesseract-langpack-rus ffmpeg \
  libglvnd-glx libxkbcommon-x11 xcb-util-cursor
```

### Arch Linux

```bash
sudo pacman -S python python-pip tesseract tesseract-data-rus ffmpeg \
  libgl libxkbcommon-x11 xcb-util-cursor
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

Для русских книг должен быть язык `rus`. Если его нет, установите `tesseract-ocr-rus`, `tesseract-langpack-rus` или `tesseract-lang` в зависимости от OS.

## Настройка LLM через WSL Ollama

LLM используется для нормализации текста и умной разметки голосов. Команды ниже запускайте в Ubuntu WSL, чтобы модели и сервер жили в одной Linux-среде с GPU/CUDA.

Установка Ollama в WSL:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
```

Если нет `sudo`, можно поставить user-local архив Ollama в `~/.local/bin`; главное, чтобы команда `ollama --version` работала внутри WSL.

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

В коде LLM-запросы идут через `/api/chat` с `think=false`, `num_ctx=4096`, `num_parallel=1`, JSON/schema output и явной выгрузкой моделей после батчей. `gemma3:12b` не используется по умолчанию: размер модели плюс KV/cache слишком рискованны для 8 GB VRAM.

Если включить `LLM/GPU нормализация`, книга получает metadata-флаг `llm_processing_enabled`, а вкладка голосов автоматически выбирает LLM smart markup с тем же language/model profile. Если 8B не проходит validation, приложение пробует 4B; если обе модели не сохраняют текст, создается review report вместо тихого heuristic downgrade.

Ручной benchmark качества:

```bash
python scripts/quality_benchmark.py
RUN_OLLAMA_TESTS=1 python scripts/quality_benchmark.py --run-ollama
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
на практике для production-озвучки рекомендуется Linux/WSL с CUDA GPU.

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
