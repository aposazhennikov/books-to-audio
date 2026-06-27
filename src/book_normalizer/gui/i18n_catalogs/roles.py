"""Roles GUI translations."""

# ruff: noqa: E501

from __future__ import annotations

ROLES_TRANSLATIONS: dict[str, dict[str, str]] = {'roles.llm_endpoint': {'en': 'Local LLM endpoint',
                        'ru': 'Адрес локальной LLM',
                        'zh': '本地 LLM 端点',
                        'kk': 'Жергілікті LLM endpoint',
                        'uz': 'Lokal LLM endpoint'},
 'roles.llm_model': {'en': 'Model profile',
                     'ru': 'Профиль модели',
                     'zh': '模型配置',
                     'kk': 'Модель профилі',
                     'uz': 'Model profili'},
 'roles.extract': {'en': 'Extract roles and chunks',
                   'ru': 'Извлечь роли и чанки',
                   'zh': '提取角色和分块',
                   'kk': 'Рөлдер мен чанктарды алу',
                   'uz': 'Rollar va boʻlaklarni ajratish'},
 'roles.special_sections': {'en': 'Book has annotations/epigraphs',
                            'ru': 'В книге есть аннотации/эпиграфы',
                            'zh': '书中有注释/题词',
                            'kk': 'Кітапта аннотация/эпиграф бар',
                            'uz': 'Kitobda annotatsiya/epigraf bor'},
 'roles.special_sections_tip': {'en': 'Marks short annotation or epigraph blocks near chapter '
                                      'titles for a separate narration voice.',
                                'ru': 'Помечает короткие аннотации или эпиграфы рядом с '
                                      'заголовками глав для отдельного голоса.',
                                'zh': '将章节标题附近的短注释或题词标记为单独的叙述声音。',
                                'kk': 'Тарау атауы жанындағы қысқа аннотация/эпиграфты бөлек '
                                      'дауысқа белгілейді.',
                                'uz': 'Bob sarlavhalari yaqinidagi qisqa annotatsiya yoki '
                                      'epigraflarni alohida ovoz uchun belgilaydi.'},
 'roles.empty': {'en': 'Normalize a book, then extract roles for audiobook casting.',
                 'ru': 'Сначала нормализуйте книгу, затем извлеките роли для аудиоспектакля.',
                 'zh': '先规范化书稿，再为有声剧提取角色。',
                 'kk': 'Алдымен кітапты нормалдаңыз, содан кейін аудиоқойылым үшін рөлдерді '
                       'алыңыз.',
                 'uz': 'Avval kitobni normallashtiring, keyin audiospektakl uchun rollarni '
                       'ajrating.'},
 'roles.ready': {'en': 'Book is ready. Local LLM will build character roles and segment manifest.',
                 'ru': 'Книга готова. Локальная LLM соберёт роли и segment manifest.',
                 'zh': '书稿已就绪。本地 LLM 将构建角色和片段清单。',
                 'kk': 'Кітап дайын. Жергілікті LLM рөлдер мен segment manifest құрады.',
                 'uz': 'Kitob tayyor. Lokal LLM rollar va segment manifestini yaratadi.'},
 'roles.extracting': {'en': 'Extracting roles and smart segments with local LLM...',
                      'ru': 'Извлекаем роли и умные сегменты локальной LLM...',
                      'zh': '正在用本地 LLM 提取角色和智能片段...',
                      'kk': 'Жергілікті LLM арқылы рөлдер мен ақылды сегменттер алынып жатыр...',
                      'uz': 'Lokal LLM bilan rollar va aqlli segmentlar ajratilmoqda...'},
 'roles.cache_dialog_title': {'en': 'Completed role extraction found',
                              'ru': 'Готовые роли найдены',
                              'zh': '已找到完成的角色提取',
                              'kk': 'Дайын рөлдер табылды',
                              'uz': 'Yakunlangan rollar topildi'},
 'roles.cache_dialog_text': {'en': 'Cached roles and chunks already exist for this book and the '
                                   'current settings.',
                             'ru': 'Для этой книги и текущих настроек уже есть извлечённые роли и '
                                   'чанки.',
                             'zh': '当前书稿和设置已有缓存的角色与分块。',
                             'kk': 'Осы кітап пен ағымдағы баптаулар үшін алынған рөлдер мен '
                                   'чанктар кеште бар.',
                             'uz': "Bu kitob va joriy sozlamalar uchun rollar va bo'laklar keshda "
                                   'bor.'},
 'roles.cache_dialog_informative': {'en': 'Restore them from cache to continue immediately with '
                                          'chunk review. Choose "Extract again" only if you want '
                                          'to rerun LLM role markup.',
                                    'ru': 'Восстановите их из кеша, чтобы сразу перейти к проверке '
                                          'чанков. Выберите "Извлечь заново", только если хотите '
                                          'повторно прогнать LLM-разметку ролей.',
                                    'zh': '从缓存恢复即可立即进入分块检查。只有想重新运行 LLM 角色标注时，才选择“重新提取”。',
                                    'kk': 'Кештен қалпына келтірсеңіз, чанктарды тексеруге бірден '
                                          'өтесіз. LLM арқылы рөлдерді қайта белгілеу қажет болса '
                                          'ғана "Қайта алу" таңдаңыз.',
                                    'uz': "Keshdan tiklasangiz, bo'laklarni tekshirishga darhol "
                                          "o'tasiz. LLM orqali rollarni qayta belgilash kerak "
                                          'bo\'lsagina "Qayta ajratish"ni tanlang.'},
 'roles.cache_restore_button': {'en': 'Restore roles',
                                'ru': 'Восстановить роли',
                                'zh': '恢复角色',
                                'kk': 'Рөлдерді қалпына келтіру',
                                'uz': 'Rollarni tiklash'},
 'roles.cache_run_fresh_button': {'en': 'Extract again',
                                  'ru': 'Извлечь заново',
                                  'zh': '重新提取',
                                  'kk': 'Қайта алу',
                                  'uz': 'Qayta ajratish'},
 'roles.cache_cancel_button': {'en': 'Cancel',
                               'ru': 'Отмена',
                               'zh': '取消',
                               'kk': 'Болдырмау',
                               'uz': 'Bekor qilish'},
 'roles.cache_restored': {'en': 'Restored roles from cache. Roles: {n}.',
                          'ru': 'Роли восстановлены из кеша. Ролей: {n}.',
                          'zh': '已从缓存恢复角色。角色数：{n}。',
                          'kk': 'Рөлдер кештен қалпына келтірілді. Рөлдер: {n}.',
                          'uz': 'Rollar keshdan tiklandi. Rollar: {n}.'},
 'roles.cache_restore_failed': {'en': 'Could not restore cached roles: {msg}',
                                'ru': 'Не удалось восстановить роли из кеша: {msg}',
                                'zh': '无法恢复缓存角色：{msg}',
                                'kk': 'Кештегі рөлдерді қалпына келтіру мүмкін болмады: {msg}',
                                'uz': "Keshlangan rollarni tiklab bo'lmadi: {msg}"},
 'roles.done': {'en': 'Role inventory ready: {n} role(s).',
                'ru': 'Список ролей готов: {n}.',
                'zh': '角色清单已就绪：{n} 个角色。',
                'kk': 'Рөлдер тізімі дайын: {n}.',
                'uz': 'Rollar roʻyxati tayyor: {n}.'},
 'roles.done_with_review': {'en': 'Role inventory ready: {n} role(s). Some windows used safe '
                                  'source fallback; review report: {path}',
                            'ru': 'Список ролей готов: {n}. Некоторые окна сохранены исходным '
                                  'текстом; отчёт: {path}',
                            'zh': '角色清单已就绪：{n} 个角色。部分窗口使用安全原文回退；报告：{path}',
                            'kk': 'Рөлдер тізімі дайын: {n}. Кейбір терезелер бастапқы мәтінмен '
                                  'сақталды; есеп: {path}',
                            'uz': 'Rollar roʻyxati tayyor: {n}. Ayrim oynalar asl matn bilan '
                                  'saqlandi; hisobot: {path}'},
 'roles.summary': {'en': '{roles} role(s), {speech} direct-speech segment(s), {segments} total '
                         'segment(s).',
                   'ru': '{roles} ролей, {speech} сегментов прямой речи, {segments} сегментов '
                         'всего.',
                   'zh': '{roles} 个角色，{speech} 个直接语音片段，共 {segments} 个片段。',
                   'kk': '{roles} рөл, {speech} тікелей сөз сегменті, барлығы {segments} сегмент.',
                   'uz': '{roles} rol, {speech} toʻgʻridan-toʻgʻri nutq segmenti, jami {segments} '
                         'segment.'},
 'roles.error': {'en': 'Role extraction failed: {msg}',
                 'ru': 'Извлечение ролей не удалось: {msg}',
                 'zh': '角色提取失败：{msg}',
                 'kk': 'Рөлдерді алу сәтсіз: {msg}',
                 'uz': 'Rollarni ajratib boʻlmadi: {msg}'},
 'roles.col_role': {'en': 'Role', 'ru': 'Роль', 'zh': '角色', 'kk': 'Рөл', 'uz': 'Rol'},
 'roles.col_description': {'en': 'Description',
                           'ru': 'Описание',
                           'zh': '描述',
                           'kk': 'Сипаттама',
                           'uz': 'Tavsif'},
 'roles.col_description_short': {'en': 'Desc.',
                                 'ru': 'Опис.',
                                 'zh': '描述',
                                 'kk': 'Сип.',
                                 'uz': 'Tavs.'},
 'roles.col_speech': {'en': 'Direct speech',
                      'ru': 'Прямая речь',
                      'zh': '直接对话',
                      'kk': 'Тікелей сөз',
                      'uz': 'Bevosita nutq'},
 'roles.col_speech_short': {'en': 'Speech', 'ru': 'Речь', 'zh': '台词', 'kk': 'Сөз', 'uz': 'Nutq'},
 'roles.col_emotions': {'en': 'Emotion spectrum',
                        'ru': 'Эмоции',
                        'zh': '情绪频谱',
                        'kk': 'Эмоциялар',
                        'uz': 'Hissiyotlar'},
 'roles.col_emotions_short': {'en': 'Emotions',
                              'ru': 'Эмоции',
                              'zh': '情绪',
                              'kk': 'Эмоц.',
                              'uz': 'Hiss.'},
 'roles.col_segments': {'en': 'Segments',
                        'ru': 'Сегменты',
                        'zh': '片段',
                        'kk': 'Сегменттер',
                        'uz': 'Segmentlar'},
 'roles.col_segments_short': {'en': 'Seg.', 'ru': 'Сегм.', 'zh': '片段', 'kk': 'Сегм.', 'uz': 'Seg.'}}
