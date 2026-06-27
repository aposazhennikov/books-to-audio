"""Synthesis runtime GUI translations."""

# ruff: noqa: E501

from __future__ import annotations

SYNTHESIS_RUNTIME_TRANSLATIONS: dict[str, dict[str, str]] = {'synth.chapter': {'en': 'Chapter:', 'ru': 'Глава:'},
 'synth.all_chapters': {'en': 'All chapters', 'ru': 'Все главы'},
 'synth.chapter_item': {'en': 'Chapter {num}  ({chunks} chunks)',
                        'ru': 'Глава {num}  ({chunks} чанков)'},
 'synth.chapter_info': {'en': '{chapters} chapters, {chunks} chunks total',
                        'ru': '{chapters} глав, {chunks} чанков всего'},
 'synth.chunks_word': {'en': 'chunks', 'ru': 'чанков'},
 'synth.test_source_title': {'en': 'Test fragment source', 'ru': 'Источник тестового фрагмента'},
 'synth.test_source_desc': {'en': 'Pick one book chunk for a quick preview before running the '
                                  'whole book, or switch to custom text.',
                            'ru': 'Выберите один чанк для быстрой проверки перед полной озвучкой '
                                  'или переключитесь на свой текст.'},
 'synth.test_source': {'en': 'Test from:', 'ru': 'Тест из:'},
 'synth.test_source_chunk': {'en': 'Book chunk', 'ru': 'Чанк книги'},
 'synth.test_source_custom': {'en': 'Custom text', 'ru': 'Свой текст'},
 'synth.test_source_help': {'en': 'Book chunk uses the selected chunk exactly as it appears in the '
                                  'manifest. Custom text creates a one-off preview chunk.',
                            'ru': 'Чанк книги берется ровно из манифеста. Свой текст создает '
                                  'разовый preview-чанк.'},
 'synth.test_chunk': {'en': 'Book chunk:', 'ru': 'Чанк книги:'},
 'synth.test_chunk_item': {'en': 'Chunk {num} (will use: {voice}, {chars} chars): {preview}',
                           'ru': 'Чанк {num} (озвучит: {voice}, {chars} симв.): {preview}'},
 'synth.test_voice_custom_sample': {'en': 'CustomVoice sample', 'ru': 'CustomVoice sample'},
 'synth.test_voice_saved': {'en': 'CustomVoice: {voice}', 'ru': 'CustomVoice: {voice}'},
 'synth.test_voice_builtin': {'en': 'built-in preset: {voice}', 'ru': 'встроенный preset: {voice}'},
 'synth.test_voice': {'en': 'Voice for custom text:', 'ru': 'Голос для своего текста:'},
 'synth.test_chunk_text': {'en': 'Selected chunk text:', 'ru': 'Текст выбранного чанка:'},
 'synth.test_custom_text': {'en': 'Custom text:', 'ru': 'Свой текст:'},
 'synth.test_custom_placeholder': {'en': 'Paste any text you want to test with the current voice '
                                         'settings.',
                                   'ru': 'Вставьте любой текст, который нужно прогнать с текущими '
                                         'настройками голоса.'},
 'synth.test_custom_missing': {'en': 'Enter custom text for the test fragment.',
                               'ru': 'Введите свой текст для тестового фрагмента.'},
 'synth.chunk_editor_placeholder': {'en': 'Edit the selected chunk here, then save it back to the '
                                          'manifest before synthesis.',
                                    'ru': 'Правьте выбранный чанк здесь и сохраните в manifest '
                                          'перед синтезом.'},
 'synth.chunk_editor_save': {'en': 'Save chunk text', 'ru': 'Сохранить чанк'},
 'synth.compact_chunk_editor_save': {'en': 'Save',
                                     'ru': 'Сохр. чанк',
                                     'zh': '保存',
                                     'kk': 'Сақт.',
                                     'uz': 'Saql.'},
 'synth.chunk_editor_split': {'en': 'Split',
                              'ru': 'Разделить',
                              'zh': '分割',
                              'kk': 'Бөлу',
                              'uz': "Bo'lish"},
 'synth.chunk_editor_split_tip': {'en': 'Split the selected chunk at the cursor.',
                                  'ru': 'Разделить выбранный чанк в месте курсора.',
                                  'zh': '在光标处分割选中的分块。',
                                  'kk': 'Таңдалған чанкты курсор тұрған жерден бөлу.',
                                  'uz': "Tanlangan bo'lakni kursor turgan joydan bo'lish."},
 'synth.chunk_editor_merge': {'en': 'Merge next', 'ru': 'Склеить со след.'},
 'synth.compact_chunk_editor_merge': {'en': 'Merge',
                                      'ru': 'Склеить',
                                      'zh': '合并',
                                      'kk': 'Бірік.',
                                      'uz': 'Birlasht.'},
 'synth.chunk_editor_saved': {'en': 'Chunk manifest saved. Synthesis will use the edited text.',
                              'ru': 'Манифест чанков сохранен. Синтез возьмет отредактированный '
                                    'текст.'},
 'synth.no_test_chunks': {'en': 'No chunks loaded', 'ru': 'Чанки не загружены'},
 'synth.start': {'en': 'Start Synthesis', 'ru': 'Запустить синтез'},
 'synth.test_start': {'en': 'Test Fragment', 'ru': 'Тестовый фрагмент'},
 'synth.test_play': {'en': 'Play Test', 'ru': 'Прослушать тест'},
 'synth.test_pause': {'en': 'Pause Test', 'ru': 'Пауза'},
 'synth.test_help': {'en': 'Render one short chunk from the selected chapter with the current '
                           'voice and generation settings. The preview is saved separately and '
                           'does not mark the book as synthesized.',
                     'ru': 'Озвучит один короткий чанк из выбранной главы с текущим голосом и '
                           'параметрами. Превью сохраняется отдельно и не помечает книгу как '
                           'синтезированную.'},
 'synth.stop': {'en': 'Stop', 'ru': 'Стоп'},
 'synth.waiting': {'en': 'Waiting for manifest…', 'ru': 'Ожидание манифеста…'},
 'synth.in_progress': {'en': 'Synthesis in progress… (each chunk may take 1–2 min)',
                       'ru': 'Синтез в процессе… (каждый чанк может занять 1–2 мин)'},
 'synth.test_in_progress': {'en': 'Rendering a short test fragment with current settings...',
                            'ru': 'Озвучиваю короткий тестовый фрагмент с текущими настройками...'},
 'synth.test_no_chunk': {'en': 'No non-empty chunk found for a test fragment.',
                         'ru': 'Не нашелся непустой чанк для теста.'},
 'synth.progress_status': {'en': 'Chunk {current}/{total} • ETA: {eta}',
                           'ru': 'Чанк {current}/{total} • Осталось: {eta}'},
 'synth.progress_status_no_eta': {'en': 'Chunk {current}/{total}', 'ru': 'Чанк {current}/{total}'},
 'synth.progress_chapter': {'en': 'Ch. {chapter} • Chunk {current}/{total} • ETA: {eta}',
                            'ru': 'Гл. {chapter} • Чанк {current}/{total} • Осталось: {eta}'},
 'synth.progress_chapter_no_eta': {'en': 'Ch. {chapter} • Chunk {current}/{total}',
                                   'ru': 'Гл. {chapter} • Чанк {current}/{total}'},
 'synth.progress_done': {'en': 'Processed {current}/{total} chunks',
                         'ru': 'Обработано {current}/{total} чанков'},
 'synth.progress_remaining': {'en': '{n} left', 'ru': 'осталось {n}'},
 'synth.progress_last_chunk': {'en': 'last: {chars} chars in {sec:.1f}s',
                               'ru': 'последний: {chars} симв. за {sec:.1f} с'},
 'synth.progress_chars': {'en': '{done}/{total} chars ({left} left)',
                          'ru': '{done}/{total} симв. (ост. {left})'},
 'synth.progress_eta': {'en': 'ETA: {eta}', 'ru': 'Осталось: {eta}'},
 'synth.log_placeholder': {'en': 'Log will appear here when synthesis runs…',
                           'ru': 'Лог появится при запуске синтеза…'},
 'synth.log_path': {'en': 'Log file: {path}', 'ru': 'Лог: {path}'},
 'synth.test_log_path': {'en': 'Test preview folder: {path}',
                         'ru': 'Папка тестового превью: {path}'},
 'synth.resume': {'en': 'Resume mode:', 'ru': 'Продолжить:'},
 'synth.resume_note': {'en': 'Automatic: chunks with synthesized=true and an existing audio_file '
                             'are skipped. Use Resynthesize failed/warning for QA retries.',
                       'ru': 'Автоматически: чанки с synthesized=true и существующим audio_file '
                             'пропускаются. Для QA-повторов используйте пересинтез '
                             'ошибок/предупреждений.',
                       'zh': '自动：跳过 synthesized=true 且已有 audio_file 的块。QA 重试请使用重新合成失败/警告。',
                       'kk': 'Автоматты түрде: synthesized=true және audio_file бар бөліктер '
                             'өткізіледі. QA қайталаулары үшін сәтсіз/ескерту бөліктерін қайта '
                             'синтездеуді қолданыңыз.',
                       'uz': "Avtomatik: synthesized=true va mavjud audio_file bo'lgan bo'laklar "
                             "o'tkazib yuboriladi. QA qayta urinishlari uchun xato/ogohlantirish "
                             "bo'laklarini qayta sintez qiling."},
 'synth.resume_check': {'en': 'Skip already synthesized chunks',
                        'ru': 'Пропустить уже синтезированные чанки'},
 'synth.resume_hint': {'en': 'If checked, chunks that already have WAV files will be skipped. '
                             'Useful to continue after interruption.',
                       'ru': 'Если включено, чанки с уже готовыми WAV-файлами будут пропущены. '
                             'Полезно для продолжения после обрыва.'},
 'synth.retry_failed': {'en': 'Retry:', 'ru': 'Повтор:'},
 'synth.retry_failed_check': {'en': 'Retry failed chunks only',
                              'ru': 'Повторить только упавшие чанки'},
 'synth.retry_failed_hint': {'en': 'For ComfyUI v2 manifests, run only chunks marked failed=true. '
                                   'Leave off for normal resume.',
                             'ru': 'Для ComfyUI v2-манифестов запускает только чанки с '
                                   'failed=true. Для обычного продолжения оставьте выключенным.'},
 'synth.compile': {'en': 'torch.compile:', 'ru': 'torch.compile:'},
 'synth.compile_check': {'en': 'Enable JIT compilation (+20–40% speed)',
                         'ru': 'Включить JIT-компиляцию (+20–40% скорости)'},
 'synth.compile_hint': {'en': 'Compiles model with torch.compile(). First chunk will be slower '
                              '(JIT warmup), all subsequent chunks will run faster. Requires '
                              'PyTorch 2.0+.',
                        'ru': 'Компилирует модель через torch.compile(). Первый чанк будет '
                              'медленнее (прогрев JIT), все последующие — быстрее. Требует PyTorch '
                              '2.0+.'},
 'synth.sage_attention': {'en': 'SageAttention:', 'ru': 'SageAttention:'},
 'synth.sage_check': {'en': 'Enable SageAttention (~2-3x faster attention)',
                      'ru': 'Включить SageAttention (~2-3x быстрее attention)'},
 'synth.sage_hint': {'en': 'SageAttention replaces SDPA with quantized attention kernels.\n'
                           'Requires SageAttention in the local TTS Python environment; GitHub v2 '
                           'is preferred:\n'
                           '  pip install git+https://github.com/thu-ml/SageAttention.git\n'
                           'If enabled and unavailable, synthesis stops with an explicit error.',
                     'ru': 'SageAttention заменяет SDPA квантованными attention-ядрами.\n'
                           'Нужен SageAttention в локальном TTS Python; GitHub v2 '
                           'предпочтительнее:\n'
                           '  pip install git+https://github.com/thu-ml/SageAttention.git\n'
                           'Если включено, но пакет недоступен, синтез остановится с явной '
                           'ошибкой.'},
 'synth.clone_enable': {'en': 'Voice Cloning — use a real audio sample as voice',
                        'ru': 'Клонирование голоса — использовать реальный аудио-образец'},
 'synth.clone_title': {'en': '🎤  Voice Cloning', 'ru': '🎤  Клонирование голоса'},
 'synth.clone_desc': {'en': 'Load a short audio clip (5–15 sec) of any voice + its transcript. The '
                            'model will synthesize the entire book in that voice. You can add '
                            'multiple voices for narrator / characters.',
                      'ru': 'Загрузите короткий аудио-фрагмент (5–15 сек) любого голоса + '
                            'транскрипт. Модель озвучит всю книгу этим голосом. Можно добавить '
                            'несколько голосов для диктора и персонажей.'},
 'synth.clone_add_voice': {'en': '+ Add voice', 'ru': '+ Добавить голос'},
 'synth.clone_col_role': {'en': 'Voice role', 'ru': 'Роль голоса'},
 'synth.clone_col_wav': {'en': 'Audio file (WAV/MP3/FLAC)', 'ru': 'Аудиофайл (WAV/MP3/FLAC)'},
 'synth.clone_col_transcript': {'en': '↳ Transcript: exactly what is said in the audio clip',
                                'ru': '↳ Транскрипт: точный текст, который произносится в '
                                      'аудиофрагменте'},
 'synth.clone_transcript_ph': {'en': 'Type the exact words spoken in the audio file…',
                               'ru': 'Введите точный текст, который произносится в аудиофайле…'},
 'synth.train_title': {'en': 'ComfyUI Saved Voice', 'ru': 'Сохранение голоса ComfyUI'},
 'synth.train_desc': {'en': 'Extract a reusable custom voice through ComfyUI. The saved name will '
                            'appear in FB_Qwen3TTSLoadSpeaker and can be used by ComfyUI dialogue '
                            'workflows.',
                      'ru': 'Извлекает reusable custom voice через ComfyUI. Сохраненное имя '
                            'появится в FB_Qwen3TTSLoadSpeaker и подойдет для ComfyUI dialogue '
                            'workflows.'},
 'synth.train_url': {'en': 'ComfyUI URL:', 'ru': 'ComfyUI URL:'},
 'synth.train_name': {'en': 'Save as:', 'ru': 'Сохранить как:'},
 'synth.train_audio': {'en': 'Reference audio:', 'ru': 'Аудио-образец:'},
 'synth.train_transcript': {'en': 'Transcript:', 'ru': 'Транскрипт:'},
 'synth.browse_audio': {'en': 'Browse...', 'ru': 'Обзор...'},
 'synth.train_start': {'en': 'Save Voice', 'ru': 'Сохранить голос'},
 'synth.train_idle': {'en': 'ComfyUI voice save is idle.',
                      'ru': 'Сохранение голоса в ComfyUI ожидает запуска.'},
 'synth.train_missing': {'en': 'Choose an audio file and voice name first.',
                         'ru': 'Сначала выберите аудио и имя голоса.'},
 'synth.train_starting': {'en': 'Starting voice save...', 'ru': 'Запуск сохранения голоса...'},
 'synth.train_connecting': {'en': 'Connecting to ComfyUI...', 'ru': 'Подключение к ComfyUI...'},
 'synth.train_uploading': {'en': 'Uploading {file} to ComfyUI...',
                           'ru': 'Загрузка {file} в ComfyUI...'},
 'synth.train_extracting': {'en': "Extracting and saving voice '{name}'...",
                            'ru': "Извлечение и сохранение голоса '{name}'..."},
 'synth.train_done': {'en': "Saved '{name}'. Available speakers: {speakers}",
                      'ru': "Голос '{name}' сохранен. Доступные голоса: {speakers}"},
 'synth.train_error': {'en': 'Voice save failed: {msg}', 'ru': 'Не удалось сохранить голос: {msg}'},
 'synth.train_err_comfyui': {'en': 'ComfyUI is not reachable at {url}.',
                             'ru': 'ComfyUI недоступен по адресу {url}.'},
 'synth.train_none': {'en': '(none)', 'ru': '(нет)'},
 'synth.loading_model': {'en': 'Loading TTS model… (may take 1–2 min)',
                         'ru': 'Загрузка TTS модели… (может занять 1–2 мин)'},
 'synth.test_loading_model': {'en': 'Loading TTS model for test fragment...',
                              'ru': 'Загрузка TTS-модели для тестового фрагмента...'},
 'synth.loading_model_elapsed': {'en': 'Loading TTS model… {sec}s elapsed',
                                 'ru': 'Загрузка TTS модели… {sec} сек'},
 'synth.model_ready': {'en': '✔ Model loaded in {sec}s. Synthesizing…',
                       'ru': '✔ Модель загружена за {sec} сек. Синтез…'},
 'synth.test_model_ready': {'en': '✔ Model loaded in {sec}s. Rendering test fragment...',
                            'ru': '✔ Модель загружена за {sec} сек. Рендер теста...'},
 'synth.synthesizing': {'en': 'Synthesizing first chunk…', 'ru': 'Синтез первого чанка…'},
 'synth.test_synthesizing': {'en': 'Synthesizing test fragment...',
                             'ru': 'Синтез тестового фрагмента...'},
 'synth.err_no_chunks': {'en': 'No chunks in manifest to synthesize.',
                         'ru': 'В манифесте нет чанков для синтеза.'},
 'synth.cancelled': {'en': 'Synthesis cancelled by user.', 'ru': 'Синтез отменён пользователем.'},
 'synth.err_exit_code': {'en': 'TTS process exited with code {code}.',
                         'ru': 'TTS-процесс завершился с кодом {code}.'},
 'synth.complete': {'en': 'Synthesis complete!', 'ru': 'Синтез завершён!'},
 'synth.test_done': {'en': 'Test fragment is ready. Output: {path}',
                     'ru': 'Тестовый фрагмент готов. Файл: {path}'},
 'synth.test_done_no_file': {'en': 'Test run finished, but no audio file was found in {path}. '
                                   'Check the log above.',
                             'ru': 'Тест завершился, но аудиофайл не найден в {path}. Проверьте '
                                   'лог выше.'},
 'synth.test_next_step': {'en': 'If the test sounds right, save the voice; the app will switch to '
                                'that saved voice for the full synthesis.',
                          'ru': 'Если тест звучит хорошо, сохраните голос; приложение само '
                                'переключит полный синтез на этот сохраненный голос.'},
 'synth.done_detail': {'en': '✔ Synthesis complete!\n'
                             'Synthesized: {synthesized} chunks, skipped: {skipped}\n'
                             'Output: {path}',
                       'ru': '✔ Синтез завершён!\n'
                             'Синтезировано: {synthesized} чанков, пропущено: {skipped}\n'
                             'Папка: {path}'}}
