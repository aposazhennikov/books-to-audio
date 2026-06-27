"""Assembly GUI translations."""

# ruff: noqa: E501

from __future__ import annotations

ASSEMBLY_TRANSLATIONS: dict[str, dict[str, str]] = {'asm.no_dir': {'en': 'No audio directory selected', 'ru': 'Папка аудио не выбрана'},
 'asm.select_dir': {'en': 'Select Audio Dir', 'ru': 'Выбрать папку аудио'},
 'asm.pause_same': {'en': 'Pause (same voice):', 'ru': 'Пауза (тот же голос):'},
 'asm.pause_same_help': {'en': 'Pause inserted between adjacent chunks with the same voice. Small '
                               'values keep narration tight; larger values add breathing room.',
                         'ru': 'Пауза между соседними чанками с тем же голосом. Малые значения '
                               'делают чтение плотнее, большие добавляют воздуха.'},
 'asm.pause_change': {'en': 'Pause (voice change):', 'ru': 'Пауза (смена голоса):'},
 'asm.pause_change_help': {'en': 'Pause inserted when the next chunk uses another voice. Usually a '
                                 'bit longer than the same-voice pause so dialogue transitions are '
                                 'clearer.',
                           'ru': 'Пауза при смене голоса между чанками. Обычно чуть длиннее '
                                 'обычной паузы, чтобы переходы в диалогах были понятнее.'},
 'asm.run': {'en': 'Assemble All Chapters', 'ru': 'Собрать все главы'},
 'asm.assembling': {'en': 'Assembling…', 'ru': 'Сборка…'},
 'asm.complete': {'en': 'Assembly complete!', 'ru': 'Сборка завершена!'},
 'asm.no_wav_found': {'en': 'No WAV files found — run synthesis first.',
                      'ru': 'WAV-файлы не найдены — сначала запустите синтез.'},
 'asm.no_wav_in': {'en': 'No WAV chunks in', 'ru': 'Нет WAV чанков в'},
 'asm.no_chapters_in': {'en': 'No chapter dirs found in', 'ru': 'Папки глав не найдены в'},
 'asm.chunk_stats': {'en': '{chunks} chunks -> {duration}s',
                     'ru': '{chunks} чанков → {duration} сек'},
 'asm.production_title': {'en': 'Production preflight',
                          'ru': 'Production-проверка',
                          'zh': '制作预检',
                          'kk': 'Production алдын ала тексеру',
                          'uz': 'Production tekshiruvi'},
 'asm.production_desc': {'en': 'Build character bible, casting plan, director score, production '
                               'QA, and optional package metadata from the current v2 manifest.',
                         'ru': 'Создаёт character bible, кастинг, режиссёрскую партитуру, '
                               'production QA и метаданные пакета из текущего v2-манифеста.',
                         'zh': '从当前 v2 清单生成角色档案、配音方案、导演标注、制作 QA 和可选包元数据。',
                         'kk': 'Ағымдағы v2 манифестінен character bible, кастинг жоспарын, '
                               'режиссерлік партитураны, production QA және пакет метадеректерін '
                               'жасайды.',
                         'uz': 'Joriy v2 manifestdan character bible, kasting rejasi, rejissyor '
                               "partiturasi, production QA va ixtiyoriy paket metama'lumotlarini "
                               'yaratadi.'},
 'asm.production_preflight': {'en': 'Run production preflight',
                              'ru': 'Запустить production preflight',
                              'zh': '运行制作预检',
                              'kk': 'Production preflight іске қосу',
                              'uz': 'Production preflight ishga tushirish'},
 'asm.production_package': {'en': 'Prepare package',
                            'ru': 'Подготовить пакет',
                            'zh': '准备包',
                            'kk': 'Пакетті дайындау',
                            'uz': 'Paketni tayyorlash'},
 'asm.production_gate_no_manifest': {'en': 'Package locked: select a v2 manifest first.',
                                     'ru': 'Пакет заблокирован: сначала выберите v2-манифест.',
                                     'zh': '打包已锁定：请先选择 v2 清单。',
                                     'kk': 'Пакет бұғатталған: алдымен v2 манифестін таңдаңыз.',
                                     'uz': 'Paket bloklangan: avval v2 manifestni tanlang.'},
 'asm.production_gate_manifest_error': {'en': 'Package locked: manifest cannot be read.',
                                        'ru': 'Пакет заблокирован: манифест не читается.',
                                        'zh': '打包已锁定：无法读取清单。',
                                        'kk': 'Пакет бұғатталған: манифест оқылмайды.',
                                        'uz': "Paket bloklangan: manifestni o'qib bo'lmadi."},
 'asm.production_gate_no_chunks': {'en': 'Package locked: manifest has no production chunks.',
                                   'ru': 'Пакет заблокирован: в манифесте нет production-чанков.',
                                   'zh': '打包已锁定：清单中没有生产块。',
                                   'kk': 'Пакет бұғатталған: манифестте production бөліктері жоқ.',
                                   'uz': "Paket bloklangan: manifestda production bo'laklari "
                                         "yo'q."},
 'asm.production_gate_audio_not_synthesized': {'en': 'Package locked: synthesize all included '
                                                     'chunks first.',
                                               'ru': 'Пакет заблокирован: сначала синтезируйте все '
                                                     'включённые чанки.',
                                               'zh': '打包已锁定：请先合成所有包含的块。',
                                               'kk': 'Пакет бұғатталған: алдымен барлық қосылған '
                                                     'бөліктерді синтездеңіз.',
                                               'uz': 'Paket bloklangan: avval barcha kiritilgan '
                                                     "bo'laklarni sintez qiling."},
 'asm.production_gate_audio_missing': {'en': 'Package locked: synthesized chunk audio is missing '
                                             'on disk.',
                                       'ru': 'Пакет заблокирован: аудио синтезированного чанка '
                                             'отсутствует на диске.',
                                       'zh': '打包已锁定：磁盘上缺少已合成块的音频。',
                                       'kk': 'Пакет бұғатталған: синтезделген бөліктің аудиосы '
                                             'дискте жоқ.',
                                       'uz': "Paket bloklangan: sintez qilingan bo'lak audiosi "
                                             "diskda yo'q."},
 'asm.production_gate_asr': {'en': 'Package locked: ASR QA must pass for every included chunk.',
                             'ru': 'Пакет заблокирован: ASR QA должен пройти для каждого '
                                   'включённого чанка.',
                             'zh': '打包已锁定：每个包含的块都必须通过 ASR QA。',
                             'kk': 'Пакет бұғатталған: әр қосылған бөлік ASR QA тексеруінен өтуі '
                                   'керек.',
                             'uz': "Paket bloklangan: har bir kiritilgan bo'lak ASR QA dan o'tishi "
                                   'kerak.'},
 'asm.production_gate_qa': {'en': 'Package locked: run production preflight and resolve '
                                  'review/resynthesis items.',
                            'ru': 'Пакет заблокирован: запустите production preflight и закройте '
                                  'review/пересинтез.',
                            'zh': '打包已锁定：运行生产预检并处理复核/重合成项。',
                            'kk': 'Пакет бұғатталған: production preflight іске қосып, '
                                  'review/қайта синтез тармақтарын жабыңыз.',
                            'uz': 'Paket bloklangan: production preflight ishga tushiring va '
                                  'review/qayta sintez bandlarini yoping.'},
 'asm.production_gate_not_assembled': {'en': 'Package locked: assemble chapter audio before '
                                             'packaging.',
                                       'ru': 'Пакет заблокирован: перед упаковкой соберите аудио '
                                             'глав.',
                                       'zh': '打包已锁定：打包前请先组装章节音频。',
                                       'kk': 'Пакет бұғатталған: ораудан бұрын тарау аудиосын '
                                             'жинаңыз.',
                                       'uz': 'Paket bloklangan: qadoqlashdan oldin bob audiosini '
                                             "yig'ing."},
 'asm.production_gate_manual_review': {'en': 'Package locked: listen to the assembled chapters and '
                                             'explicitly accept the release package.',
                                       'ru': 'Пакет заблокирован: прослушайте собранные главы и '
                                             'явно подтвердите релизный пакет.',
                                       'zh': '打包已锁定：请试听已组装的章节，并明确接受发布包。',
                                       'kk': 'Пакет бұғатталған: жиналған тарауларды тыңдап, релиз '
                                             'пакетін нақты қабылдаңыз.',
                                       'uz': "Paket bloklangan: yig'ilgan boblarni tinglang va "
                                             'reliz paketini aniq tasdiqlang.'},
 'asm.production_manual_review_check': {'en': 'I listened to the assembled chapters and accept '
                                              'this package for production.',
                                        'ru': 'Я прослушал(а) собранные главы и подтверждаю этот '
                                              'пакет для продакшена.',
                                        'zh': '我已试听已组装的章节，并接受此生产包。',
                                        'kk': 'Жиналған тарауларды тыңдадым және бұл пакетті '
                                              'production үшін қабылдаймын.',
                                        'uz': "Yig'ilgan boblarni tingladim va bu paketni "
                                              'production uchun tasdiqlayman.'},
 'asm.production_gate_ready': {'en': 'Package ready: ASR passed, production QA passed, review is '
                                     'clear, and chapter audio is assembled.',
                               'ru': 'Пакет готов: ASR и production QA пройдены, review чистый, '
                                     'аудио глав собрано.',
                               'zh': '打包就绪：ASR 和生产 QA 已通过，复核已清空，章节音频已组装。',
                               'kk': 'Пакет дайын: ASR және production QA өтті, review таза, тарау '
                                     'аудиосы жиналды.',
                               'uz': "Paket tayyor: ASR va production QA o'tdi, review toza, bob "
                                     "audiosi yig'ilgan."},
 'asm.production_running': {'en': 'Running production preflight...',
                            'ru': 'Выполняется production preflight...',
                            'zh': '正在运行制作预检...',
                            'kk': 'Production preflight орындалуда...',
                            'uz': 'Production preflight bajarilmoqda...'},
 'asm.production_complete': {'en': 'Production preflight complete.',
                             'ru': 'Production preflight завершён.',
                             'zh': '制作预检完成。',
                             'kk': 'Production preflight аяқталды.',
                             'uz': 'Production preflight tugadi.'},
 'asm.production_done': {'en': 'Production report: {path}',
                         'ru': 'Production-отчёт: {path}',
                         'zh': '制作报告：{path}',
                         'kk': 'Production есебі: {path}',
                         'uz': 'Production hisoboti: {path}'},
 'asm.production_package_done': {'en': 'Production report: {run}\n'
                                       'Package report: {package}\n'
                                       'Audiobook: {book}',
                                 'ru': 'Production-отчёт: {run}\n'
                                       'Отчёт пакета: {package}\n'
                                       'Аудиокнига: {book}',
                                 'zh': '制作报告：{run}\n包报告：{package}\n有声书：{book}',
                                 'kk': 'Production есебі: {run}\n'
                                       'Пакет есебі: {package}\n'
                                       'Аудиокітап: {book}',
                                 'uz': 'Production hisoboti: {run}\n'
                                       'Paket hisoboti: {package}\n'
                                       'Audiokitob: {book}'}}
