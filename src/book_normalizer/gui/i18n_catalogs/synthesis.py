"""Synthesis GUI translations."""

# ruff: noqa: E501

from __future__ import annotations

SYNTHESIS_TRANSLATIONS: dict[str, dict[str, str]] = {'synth.no_manifest': {'en': 'No manifest loaded', 'ru': 'Манифест не загружен'},
 'synth.load_manifest': {'en': 'Load',
                         'ru': 'Загрузить',
                         'zh': '加载',
                         'kk': 'Жүктеу',
                         'uz': 'Yuklash'},
 'synth.load_manifest_tip': {'en': 'Load a chunk manifest for synthesis.',
                             'ru': 'Загрузить manifest чанков для синтеза.',
                             'zh': '加载用于合成的分块清单。',
                             'kk': 'Синтезге арналған чанк manifest файлын жүктеу.',
                             'uz': 'Sintez uchun chunk manifestini yuklash.'},
 'synth.compact_load_manifest': {'en': 'Open', 'ru': 'Откр.', 'zh': '打开', 'kk': 'Ашу', 'uz': 'Och'},
 'synth.mode_custom_voice': {'en': 'Custom Voice',
                             'ru': 'Свой голос',
                             'zh': '自定义声音',
                             'kk': 'Өз дауысы',
                             'uz': "O'z ovozi"},
 'synth.mode_preset_speakers': {'en': 'From Step 3',
                                'ru': 'Из шага 3',
                                'zh': '来自第 3 步',
                                'kk': '3-қадамнан',
                                'uz': '3-bosqichdan'},
 'synth.mode_advanced': {'en': 'Advanced',
                         'ru': 'Дополнительно',
                         'zh': '高级',
                         'kk': 'Қосымша',
                         'uz': "Qo'shimcha"},
 'synth.preset_title': {'en': 'Voices from Step 3',
                        'ru': 'Голоса из шага 3',
                        'zh': '第 3 步的声音',
                        'kk': '3-қадамдағы дауыстар',
                        'uz': '3-bosqichdagi ovozlar'},
 'synth.preset_desc': {'en': 'Uses the voice assignments from 3. Chunks -> Voice presets. Choose, '
                             'preview, and save voices there; this step only renders audio.',
                       'ru': 'Использует назначения из «3. Чанки -> Пресеты голосов». Выбор, '
                             'прослушивание и сохранение голосов теперь там; здесь только синтез '
                             'аудио.',
                       'zh': '使用“3. 分块 -> 声音预设”中的声音分配。选择、试听和保存声音都在那里；此步骤只合成音频。',
                       'kk': '«3. Чанктар -> Дауыс пресеттері» ішіндегі дауыс тағайындауларын '
                             'қолданады. Дауысты таңдау, тыңдау және сақтау сонда; бұл қадам тек '
                             'аудио синтездейді.',
                       'uz': '“3. Bo‘laklar -> Ovoz presetlari”dagi ovoz tayinlovlaridan '
                             'foydalanadi. Ovoz tanlash, tinglash va saqlash o‘sha yerda; bu '
                             'bosqich faqat audio sintez qiladi.'},
 'synth.open_voice_presets': {'en': 'Open voice presets',
                              'ru': 'Открыть пресеты голосов',
                              'zh': '打开声音预设',
                              'kk': 'Дауыс пресеттерін ашу',
                              'uz': 'Ovoz presetlarini ochish'},
 'synth.open_voice_presets_tip': {'en': 'Go to 3. Chunks -> Voice presets to choose, preview, or '
                                        'save voices.',
                                  'ru': 'Перейти в «3. Чанки -> Пресеты голосов», чтобы выбрать, '
                                        'прослушать или сохранить голоса.',
                                  'zh': '前往“3. 分块 -> 声音预设”选择、试听或保存声音。',
                                  'kk': 'Дауысты таңдау, тыңдау немесе сақтау үшін «3. Чанктар -> '
                                        'Дауыс пресеттері» бөліміне өту.',
                                  'uz': 'Ovoz tanlash, tinglash yoki saqlash uchun “3. Bo‘laklar '
                                        '-> Ovoz presetlari”ga o‘tish.'},
 'synth.advanced_title': {'en': 'Advanced run settings', 'ru': 'Дополнительные настройки запуска'},
 'synth.advanced_desc': {'en': 'These settings affect speed, file layout, and recovery after '
                               'interruption.',
                         'ru': 'Эти параметры влияют на скорость, файлы на выходе и продолжение '
                               'после обрыва.'},
 'synth.comfyui_url': {'en': 'ComfyUI URL:', 'ru': 'ComfyUI URL:'},
 'synth.workflow': {'en': 'Workflow:', 'ru': 'Workflow:'},
 'synth.choose_file': {'en': 'Choose...', 'ru': 'Выбрать...'},
 'synth.workflow_hint': {'en': 'Recommended path: v2 manifests are synthesized through ComfyUI. '
                               'The template must contain {{TEXT}}, {{SPEAKER}}, {{INSTRUCT}}, and '
                               '{{OUTPUT_FILENAME}} placeholders.',
                         'ru': 'Рекомендуемый путь: v2-манифесты синтезируются через ComfyUI. '
                               'Шаблон должен содержать {{TEXT}}, {{SPEAKER}}, {{INSTRUCT}} и '
                               '{{OUTPUT_FILENAME}}.'},
 'synth.model': {'en': 'Model:', 'ru': 'Модель:'},
 'synth.model_hint': {'en': '1.7B — best quality, 18% fewer errors (WER) vs 0.6B. Needs ~4 GB '
                            'VRAM. ~80–120 s per chunk.\n'
                            '0.6B — faster, needs ~2 GB VRAM. ~30–60 s per chunk. Good for drafts '
                            'and previews.',
                      'ru': '1.7B — лучшее качество, на 18% меньше ошибок (WER). Нужно ~4 ГБ VRAM. '
                            '~80–120 сек/чанк.\n'
                            '0.6B — быстрее, нужно ~2 ГБ VRAM. ~30–60 сек/чанк. Подходит для '
                            'черновиков и превью.'},
 'synth.models_dir': {'en': 'Model install dir:', 'ru': 'Папка моделей:'},
 'synth.voice_library_dir': {'en': 'Voice library:', 'ru': 'Библиотека голосов:'},
 'synth.output_dir': {'en': 'Save files to:', 'ru': 'Сохранять файлы в:'},
 'synth.models_dir_hint': {'en': 'ComfyUI/model setup uses this shared folder. Default points to '
                                 'D:\\ComfyUI-external\\models and expects Qwen folders in '
                                 'audio_encoders.',
                           'ru': 'ComfyUI/model setup использует эту общую папку моделей. По '
                                 'умолчанию: D:\\ComfyUI-external\\models; Qwen ожидается в '
                                 'audio_encoders.'},
 'synth.choose_dir': {'en': 'Choose...', 'ru': 'Выбрать...'},
 'synth.install_models': {'en': 'Install models', 'ru': 'Скачать модели'},
 'synth.install_models_help': {'en': 'Download the TTS model required by the current synthesis '
                                     'mode from Hugging Face into the selected models folder. '
                                     'Downloads are large.',
                               'ru': 'Скачивает TTS-модели для текущего режима синтеза из Hugging '
                                     'Face в выбранную папку моделей. Файлы большие.'},
 'synth.models_installing': {'en': 'Installing TTS models into {dir}. This may take a long time.',
                             'ru': 'Скачивание TTS-моделей в {dir}. Это может занять много '
                                   'времени.'},
 'synth.models_installed': {'en': 'TTS models ready: downloaded {downloaded}, already present '
                                  '{skipped}. Folder: {dir}',
                            'ru': 'TTS-модели готовы: скачано {downloaded}, уже было {skipped}. '
                                  'Папка: {dir}'},
 'synth.models_present': {'en': 'Required TTS models are already present in {dir}.',
                          'ru': 'Нужные TTS-модели уже есть в {dir}.'},
 'synth.models_install_error': {'en': 'TTS model installation failed: {msg}',
                                'ru': 'Не удалось скачать TTS-модели: {msg}'},
 'synth.batch_size': {'en': 'Batch Size:', 'ru': 'Размер батча:'},
 'synth.batch_hint': {'en': 'How many chunks are synthesized at once.\n'
                            '1 — sequential, minimal VRAM (~4 GB for 1.7B). Most stable.\n'
                            '2–4 — moderate speedup, needs 6–10 GB VRAM.\n'
                            '5–8 — max throughput, needs 12+ GB VRAM. Risk of OOM errors on '
                            'smaller GPUs.',
                      'ru': 'Сколько чанков синтезируются одновременно.\n'
                            '1 — последовательно, минимум VRAM (~4 ГБ для 1.7B). Самый '
                            'стабильный.\n'
                            '2–4 — умеренное ускорение, нужно 6–10 ГБ VRAM.\n'
                            '5–8 — макс. скорость, нужно 12+ ГБ VRAM. Риск ошибок нехватки памяти '
                            'на слабых GPU.'},
 'synth.chunk_timeout': {'en': 'Chunk timeout:', 'ru': 'Таймаут чанка:'},
 'synth.chunk_timeout_hint': {'en': 'Max seconds to wait for a single chunk before skipping it.\n'
                                    'Useful when corrupted text causes the model to hang.\n'
                                    'Default: 300 s (5 min). Increase for very long chunks.',
                              'ru': 'Максимальное время ожидания одного чанка перед пропуском.\n'
                                    'Помогает, когда поврежденный текст вешает модель.\n'
                                    'По умолчанию: 300 с (5 мин). Увеличьте для очень длинных '
                                    'чанков.'},
 'synth.output_format': {'en': 'Output format:', 'ru': 'Формат аудио:'},
 'synth.merge_chapters': {'en': 'Chapters:', 'ru': 'Главы:'},
 'synth.merge_chapters_check': {'en': 'Merge chunks into chapter files',
                                'ru': 'Собрать чанки в файлы глав'},
 'synth.sample_enable': {'en': 'Use sample voice for this book',
                         'ru': 'Использовать sample voice для этой книги'},
 'synth.sample_title': {'en': 'CustomVoice Sample', 'ru': 'CustomVoice Sample'},
 'synth.sample_desc': {'en': 'Use this only when the whole book should sound like your own sample '
                             'or a reusable saved voice.',
                       'ru': 'Нужно только если вся книга должна звучать как ваш образец или '
                             'сохраненный голос.'},
 'synth.custom_strategy': {'en': 'Voice source:', 'ru': 'Источник голоса:'},
 'synth.strategy_sample_all': {'en': 'New sample for whole book',
                               'ru': 'Новый sample на всю книгу'},
 'synth.strategy_saved_all': {'en': 'Saved voice for whole book',
                              'ru': 'Сохраненный голос на всю книгу'},
 'synth.strategy_saved_roles': {'en': 'Saved voices by role', 'ru': 'Сохраненные голоса по ролям'},
 'synth.saved_voice': {'en': 'Saved voice:', 'ru': 'Сохраненный голос:'},
 'synth.refresh_saved_voices': {'en': 'Refresh', 'ru': 'Обновить'},
 'synth.no_saved_voices': {'en': 'No saved voices yet', 'ru': 'Сохраненных голосов пока нет'},
 'synth.role_builtin': {'en': 'Use built-in speaker', 'ru': 'Готовый Qwen-спикер'},
 'synth.role_narrator': {'en': 'Narrator:', 'ru': 'Диктор:'},
 'synth.role_male': {'en': 'Male roles:', 'ru': 'Мужские роли:'},
 'synth.role_female': {'en': 'Female roles:', 'ru': 'Женские роли:'},
 'synth.saved_voice_name': {'en': 'Save as:', 'ru': 'Сохранить как:'},
 'synth.save_local_voice': {'en': 'Save Voice', 'ru': 'Сохранить голос'},
 'synth.compact_save_local_voice': {'en': 'Save',
                                    'ru': 'Сохр.',
                                    'zh': '保存',
                                    'kk': 'Сақт.',
                                    'uz': 'Saql.'},
 'synth.saved_voice_all_hint': {'en': 'The selected saved voice will be used for every chunk; '
                                      'previous voice markup stays in the manifest but does not '
                                      'affect timbre.',
                                'ru': 'Выбранный сохраненный голос будет использован для всех '
                                      'чанков; разметка голосов останется в манифесте, но не '
                                      'повлияет на тембр.'},
 'synth.saved_voice_roles_hint': {'en': 'Mapped roles use saved voices. Roles left on built-in '
                                        'speaker keep their Qwen preset from the Voices step.',
                                  'ru': 'Назначенные роли используют сохраненные голоса. Роли с '
                                        'готовым спикером сохраняют Qwen-пресет из шага «Голоса».'},
 'synth.saved_voice_missing': {'en': 'Choose a saved voice, or fill sample audio, transcript, and '
                                     'voice name.',
                               'ru': 'Выберите сохраненный голос или заполните sample audio, текст '
                                     'и имя голоса.'},
 'synth.saved_voice_saving': {'en': "Saving reusable voice '{name}'...",
                              'ru': "Сохраняю reusable voice '{name}'..."},
 'synth.saved_voice_saved': {'en': "Saved reusable voice '{name}'.",
                             'ru': "Голос '{name}' сохранен для повторного использования."},
 'synth.saved_voice_error': {'en': 'Could not save voice: {msg}',
                             'ru': 'Не удалось сохранить голос: {msg}'},
 'synth.voice_tuning_show': {'en': 'Show fine voice settings',
                             'ru': 'Показать тонкую настройку голоса'},
 'synth.voice_tuning_hide': {'en': 'Hide fine voice settings',
                             'ru': 'Скрыть тонкую настройку голоса'},
 'synth.sample_audio': {'en': 'Sample audio:', 'ru': 'Sample audio:'},
 'synth.sample_preview': {'en': 'Preview:', 'ru': 'Прослушать:'},
 'synth.sample_play': {'en': 'Play', 'ru': 'Play'},
 'synth.sample_pause': {'en': 'Pause', 'ru': 'Pause'},
 'synth.sample_transcript': {'en': 'Sample text:', 'ru': 'Текст sample voice:'},
 'synth.sample_idle': {'en': 'Sample voice is optional; when enabled, prompt extraction runs '
                             'before chunks.',
                       'ru': 'Образец голоса необязателен; если он включен, извлечение голосового '
                             'промпта выполнится перед фрагментами.'},
 'synth.sample_ready': {'en': 'Sample audio loaded. Enter the exact transcript before synthesis.',
                        'ru': 'Sample audio загружен. Перед синтезом введите точный текст '
                              'образца.'},
 'synth.sample_duration': {'en': 'Sample length: {sec}s. Prompt extraction estimate: {eta}.',
                           'ru': 'Длина образца: {sec} с. Оценка извлечения промпта: {eta}.'},
 'synth.sample_missing': {'en': 'Choose sample audio and enter the exact sample text.',
                          'ru': 'Выберите sample audio и введите точный текст образца.'},
 'synth.sample_extracting': {'en': 'Extracting voice prompt from sample audio...',
                             'ru': 'Извлекаю голосовой промпт из аудио образца...'},
 'synth.sample_extracted': {'en': 'Voice prompt {done}/{total} ready in {sec:.1f}s.',
                            'ru': 'Голосовой промпт {done}/{total} готов за {sec:.1f} с.'},
 'synth.temperature': {'en': 'Temperature (0.10-2.00):', 'ru': 'Temperature (0.10-2.00):'},
 'synth.top_p': {'en': 'Top-p (0.10-1.00):', 'ru': 'Top-p (0.10-1.00):'},
 'synth.top_k': {'en': 'Top-k (1-200):', 'ru': 'Top-k (1-200):'},
 'synth.repetition_penalty': {'en': 'Repetition penalty (0.80-2.00):',
                              'ru': 'Repetition penalty (0.80-2.00):'},
 'synth.max_new_tokens': {'en': 'Max new tokens (128-8192):', 'ru': 'Max new tokens (128-8192):'},
 'synth.speech_rate': {'en': 'Speech speed:', 'ru': 'Скорость речи:'},
 'synth.speech_rate_slow': {'en': 'slower', 'ru': 'медленнее'},
 'synth.speech_rate_normal': {'en': 'normal', 'ru': 'средне'},
 'synth.speech_rate_fast': {'en': 'faster', 'ru': 'быстрее'},
 'synth.seed': {'en': 'Seed (fixed=stable):', 'ru': 'Seed (fixed=stable):'},
 'synth.model_help': {'en': 'Choose the Qwen CustomVoice model for rendering voices assigned in '
                            'Step 3. 1.7B is better quality; 0.6B is faster and lighter.',
                      'ru': 'Модель Qwen CustomVoice для синтеза голосов, назначенных на шаге 3. '
                            '1.7B качественнее; 0.6B быстрее и легче.'},
 'synth.models_dir_help': {'en': 'Folder used by this app to check and install TTS model files. If '
                                 'ComfyUI is already running, its own model paths must point here '
                                 'too.',
                           'ru': 'Папка с уже скачанными моделями для v2 ComfyUI synthesis '
                                 'workflow.'},
 'synth.voice_library_dir_help': {'en': 'Shared folder for reusable .voice.pt prompts. Saved '
                                        'voices can be reused across books without prompt '
                                        'extraction.',
                                  'ru': "Общая папка для reusable .voice.pt prompt'ов. Сохраненные "
                                        'голоса можно переиспользовать в разных книгах без prompt '
                                        'extraction.'},
 'synth.output_dir_help': {'en': 'Folder where v2 synthesis files are written: audio_chunks, '
                                 'tts_test_preview, synthesis_log.txt, and merged chapters.',
                           'ru': 'Папка, куда пишутся файлы синтеза: audio_chunks, '
                                 'tts_test_preview, synthesis_log.txt, synthesis_manifest.json и '
                                 'собранные главы.'},
 'synth.batch_help': {'en': 'How many chunks to render at once. 1 is safest; larger values can be '
                            'faster but need more VRAM.',
                      'ru': 'Сколько чанков рендерить одновременно. 1 — самый стабильный вариант; '
                            'больше — быстрее, но требует больше VRAM.'},
 'synth.chunk_timeout_help': {'en': 'Maximum time for one chunk. If the model hangs on bad text, '
                                    'the chunk is skipped instead of blocking the whole book.',
                              'ru': 'Максимальное время на один чанк. Если модель зависнет на '
                                    'проблемном тексте, чанк будет пропущен, а книга продолжит '
                                    'рендериться.'},
 'synth.output_format_help': {'en': 'Audio format for generated chunks and merged chapter files. '
                                    'FLAC is compact and lossless; WAV is most compatible.',
                              'ru': 'Формат чанков и собранных глав. FLAC компактный и без потерь; '
                                    'WAV максимально совместимый.'},
 'synth.merge_chapters_help': {'en': 'Also create one merged audio file per chapter while keeping '
                                     'individual chunk files.',
                               'ru': 'Дополнительно собирать один аудиофайл на главу, сохраняя '
                                     'отдельные чанки.'},
 'synth.chapter_help': {'en': 'Render the whole book or only one selected chapter.',
                        'ru': 'Рендерить всю книгу или только выбранную главу.'},
 'synth.resume_help': {'en': 'v2 synthesis always resumes from manifest state by skipping chunks '
                             'that already have an existing audio_file.',
                       'ru': 'Пропускать чанки, для которых уже есть аудио. Полезно после '
                             'остановки или сбоя.'},
 'synth.compile_help': {'en': 'torch.compile can speed up later chunks after a slower warm-up. '
                              'Leave it off if you want the most predictable run.',
                        'ru': 'torch.compile может ускорить следующие чанки после более медленного '
                              'прогрева. Оставьте выключенным для максимально предсказуемого '
                              'запуска.'},
 'synth.sage_help': {'en': 'SageAttention is an optional faster attention kernel for the local TTS '
                           'Python environment. Enable only if it is installed and tested on your '
                           'GPU.',
                     'ru': 'SageAttention — опциональное ускорение attention для локального TTS '
                           'Python. Включайте только если оно установлено и проверено на вашей '
                           'GPU.'},
 'synth.sample_audio_help': {'en': 'A short clean recording of the target voice. WAV/FLAC is best; '
                                   'noisy audio gives worse cloning.',
                             'ru': 'Короткая чистая запись нужного голоса. Лучше WAV/FLAC; шумный '
                                   'файл ухудшит клонирование.'},
 'synth.sample_preview_help': {'en': 'Play the selected sample so you can verify it is the right '
                                     'voice and text.',
                               'ru': 'Прослушивание выбранного sample, чтобы проверить голос и '
                                     'соответствие тексту.'},
 'synth.sample_transcript_help': {'en': 'Exact text spoken in the sample audio. The closer it '
                                        'matches, the better the voice prompt.',
                                  'ru': 'Точный текст, произнесенный в sample audio. Чем точнее '
                                        'совпадение, тем лучше voice prompt.'},
 'synth.temperature_help': {'en': 'Range: 0.10-2.00. Default: 0.65.\n'
                                  'Lower values make pronunciation steadier and more predictable.\n'
                                  'Higher values add variation and expression, but can increase '
                                  'artifacts, odd pauses, or unstable speech.\n'
                                  'Use 0.55-0.75 for stable audiobooks; raise it only when a voice '
                                  'sounds too flat.',
                            'ru': 'Диапазон: 0.10-2.00. По умолчанию: 1.00.\n'
                                  'Ниже - речь ровнее и предсказуемее.\n'
                                  'Выше - больше вариативности и эмоции, но выше риск артефактов, '
                                  'странных пауз и нестабильной речи.\n'
                                  'Для пробы: 0.80-0.95 для стабильности, 1.05-1.15 если голос '
                                  'слишком ровный.'},
 'synth.top_p_help': {'en': 'Range: 0.10-1.00. Default: 0.70.\n'
                            'Top-p keeps only the smallest group of likely choices whose total '
                            'probability reaches this value.\n'
                            'Lower values are stricter and can reduce strange phrasing. Higher '
                            'values allow more alternatives.\n'
                            'Try 0.70-0.85 for audiobooks; 0.90+ only if the voice sounds too '
                            'constrained.',
                      'ru': 'Диапазон: 0.10-1.00. По умолчанию: 0.80.\n'
                            'Top-p оставляет только наиболее вероятные варианты, пока их суммарный '
                            'шанс не достигнет этого числа.\n'
                            'Ниже - строже и меньше странных фраз. Выше - больше альтернатив.\n'
                            'Для книг обычно 0.70-0.85; 0.90+ имеет смысл, если голос слишком '
                            'зажат.'},
 'synth.top_k_help': {'en': 'Range: 1-200. Default: 15.\n'
                            'At each generation step the model can choose only from the top K most '
                            'likely audio tokens.\n'
                            '1 is almost deterministic and can sound flat or stuck. 10-30 is a '
                            'safe audiobook range.\n'
                            '50-100 gives more variety, but can add pronunciation drift. 100+ is '
                            'experimental.',
                      'ru': 'Диапазон: 1-200. По умолчанию: 20.\n'
                            'На каждом шаге модель выбирает только из K самых вероятных '
                            'аудио-токенов.\n'
                            '1 - почти без случайности; может звучать плоско или застревать. 10-30 '
                            '- спокойный диапазон для аудиокниг.\n'
                            '50-100 - больше разнообразия, но выше риск съезда произношения. 100+ '
                            '- эксперимент.'},
 'synth.repetition_penalty_help': {'en': 'Range: 0.80-2.00. Default: 1.05. 1.00 means no penalty.\n'
                                         'This penalizes recently generated audio/text tokens, so '
                                         'it can stop loops like repeated syllables, words, '
                                         'breaths, or stuck sounds.\n'
                                         '1.03-1.10 is usually safe. Try 1.12-1.20 if speech '
                                         'repeats. Above 1.30 can make speech choppy or skip '
                                         'natural repeated words.',
                                   'ru': 'Диапазон: 0.80-2.00. По умолчанию: 1.05. 1.00 - без '
                                         'штрафа.\n'
                                         'Штрафует то, что модель только что сгенерировала: '
                                         'аудио-токены, слоги, слова, дыхание, зацикленные звуки.\n'
                                         '1.03-1.10 обычно безопасно. 1.12-1.20 - если речь '
                                         'повторяется. Выше 1.30 может сделать речь рубленой или '
                                         'выкидывать естественные повторы.'},
 'synth.max_new_tokens_help': {'en': 'Range: 128-8192. Default: 2048.\n'
                                     'Hard cap for generated audio tokens in one chunk. It is a '
                                     'safety limit, not a quality knob.\n'
                                     'Too low can cut the phrase off. Increase only when long '
                                     'chunks end early; otherwise keep the default.',
                               'ru': 'Диапазон: 128-8192. По умолчанию: 2048.\n'
                                     'Жесткий лимит аудио-токенов на один чанк; это защитный '
                                     'предел, а не ручка качества.\n'
                                     'Слишком низко - фраза может обрезаться. Повышайте только '
                                     'если длинные чанки заканчиваются раньше текста.'},
 'synth.speech_rate_help': {'en': 'Post-process tempo for generated speech. 1.00x keeps the model '
                                  'output, 0.85-0.95x is useful for slower narration, and '
                                  '1.05-1.15x makes it faster. When you save a custom voice, this '
                                  'value is stored with that voice.',
                            'ru': 'Темп готовой речи после генерации. 1.00x оставляет выход модели '
                                  'как есть; 0.85-0.95x удобно для более медленного диктора; '
                                  '1.05-1.15x ускоряет. При сохранении custom voice это значение '
                                  'запишется в голос.'},
 'synth.seed_help': {'en': 'Range: -1 or 0-2147483647. Default: 42.\n'
                           'A fixed number keeps previews and full reruns repeatable.\n'
                           '-1 means random every run, so the same text/settings can sound '
                           'different.\n'
                           'Changing the seed is useful when settings are good but one fragment '
                           'came out unlucky.',
                     'ru': 'Диапазон: -1 или 0-2147483647. По умолчанию: -1.\n'
                           '-1 - новая случайная версия при каждом запуске: тот же текст и '
                           'настройки могут звучать чуть иначе.\n'
                           'Любое фиксированное число, например 42, делает превью и повторный '
                           'рендер более повторяемыми.\n'
                           'Меняйте seed, если настройки уже нормальные, но конкретный фрагмент '
                           'получился неудачно.'}}
