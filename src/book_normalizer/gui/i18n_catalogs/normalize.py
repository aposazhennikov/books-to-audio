"""Normalize GUI translations."""

# ruff: noqa: E501

from __future__ import annotations

NORMALIZE_TRANSLATIONS: dict[str, dict[str, str]] = {'norm.no_file': {'en': 'No file selected', 'ru': 'Файл не выбран'},
 'norm.browse': {'en': 'Browse…', 'ru': 'Обзор…'},
 'norm.book_language': {'en': 'Book language:', 'ru': 'Язык книги:'},
 'norm.book_language_tip': {'en': 'Controls OCR language, language-safe normalization, chunk '
                                  'metadata, and Qwen/ComfyUI synthesis language.',
                            'ru': 'Влияет на язык OCR, безопасную нормализацию, метаданные чанков '
                                  'и язык синтеза Qwen/ComfyUI.'},
 'norm.ocr_mode': {'en': 'OCR Mode:', 'ru': 'Режим OCR:'},
 'norm.ocr_mode_image': {'en': 'Image OCR', 'ru': 'OCR из картинки'},
 'norm.ocr_mode_hint': {'en': 'auto = OCR if text unreadable | image = rendered-page OCR | off = no OCR | force = always OCR | '
                              'compare = both',
                        'ru': 'auto = OCR если текст нечитаем | image = OCR из картинки | off = без OCR | force = всегда OCR '
                              '| compare = оба'},
 'norm.ocr_mode_tip': {'en': 'auto — OCR only if native text is empty or unreadable (Cyrillic < '
                             '30%)\n'
                             'image — render pages and OCR images; native PDF text is diagnostic only\n'
                             'off — use only native PDF text extraction, no OCR\n'
                             'force — always run OCR, ignore native text\n'
                             'compare — run both, save comparison report',
                       'ru': 'auto — OCR только если текст пуст или нечитаем (кириллица < 30%)\n'
                             'image — рендерить страницы и распознавать картинку; PDF text layer только для диагностики\n'
                             'off — только извлечение текста из PDF, без OCR\n'
                             'force — всегда запускать OCR, игнорировать встроенный текст\n'
                             'compare — запустить оба способа, сохранить отчёт'},
 'norm.ocr_dpi': {'en': 'OCR DPI:', 'ru': 'OCR DPI:'},
 'norm.ocr_dpi_hint': {'en': '300 = fast | 400 = recommended | 600 = best quality (slow)',
                       'ru': '300 = быстро | 400 = рекомендуется | 600 = лучшее качество '
                             '(медленно)'},
 'norm.ocr_dpi_tip': {'en': 'DPI (dots per inch) for rendering PDF pages to images before OCR.\n'
                            'Higher = better quality text recognition, but slower.\n'
                            '300 = fast, 400 = good balance (default), 600 = best quality.',
                      'ru': 'DPI (точек на дюйм) для рендера страниц PDF перед OCR.\n'
                            'Больше = лучше качество, но медленнее.\n'
                            '300 = быстро, 400 = оптимально, 600 = максимальное качество.'},
 'norm.ocr_psm': {'en': 'OCR page layout (PSM):', 'ru': 'Разметка страницы OCR (PSM):'},
 'norm.ocr_psm_hint': {'en': 'Choose the layout that best matches the rendered page.',
                       'ru': 'Выберите разметку, которая ближе всего к странице после рендера.'},
 'norm.ocr_psm_3': {'en': '3 - Auto full page: unknown book layout',
                    'ru': '3 - Авто-страница: если верстка книги непонятна'},
 'norm.ocr_psm_4': {'en': '4 - Normal book page: continuous reading order',
                    'ru': '4 - Обычная страница книги: сплошной порядок чтения'},
 'norm.ocr_psm_6': {'en': '6 - Cropped body text: one selected text block',
                    'ru': '6 - Вырезанный основной текст: один выбранный блок'},
 'norm.ocr_psm_11': {'en': '11 - Loose fragments: captions, stamps, margin notes',
                     'ru': '11 - Разбросанные фрагменты: подписи, штампы, поля'},
 'norm.ocr_psm_13': {'en': '13 - Title or one line: short strip, not a page',
                     'ru': '13 - Заголовок или одна строка: не целая страница'},
 'norm.ocr_psm_compact_3': {'en': '3 - Auto',
                            'ru': '3 - Авто',
                            'zh': '3 - 自动',
                            'kk': '3 - Авто',
                            'uz': '3 - Avto'},
 'norm.ocr_psm_compact_4': {'en': '4 - Book page',
                            'ru': '4 - Страница книги',
                            'zh': '4 - 书页',
                            'kk': '4 - Кітап беті',
                            'uz': '4 - Kitob sahifasi'},
 'norm.ocr_psm_compact_6': {'en': '6 - Cropped text',
                            'ru': '6 - Обрезанный текст',
                            'zh': '6 - 裁剪正文',
                            'kk': '6 - Қиылған мәтін',
                            'uz': '6 - Kesilgan matn'},
 'norm.ocr_psm_compact_11': {'en': '11 - Fragments',
                             'ru': '11 - Фрагменты',
                             'zh': '11 - 片段',
                             'kk': '11 - Фрагменттер',
                             'uz': "11 - Bo'laklar"},
 'norm.ocr_psm_compact_13': {'en': '13 - One line',
                             'ru': '13 - Одна строка',
                             'zh': '13 - 单行',
                             'kk': '13 - Бір жол',
                             'uz': '13 - Bir qator'},
 'norm.ocr_psm_summary_3': {'en': 'Use when page layout is uncertain; review reading order after '
                                  'OCR.',
                            'ru': 'Для сложной страницы: Tesseract сам ищет порядок, но результат '
                                  'надо проверить.',
                            'zh': '页面结构不确定时使用；OCR 后请复核阅读顺序。',
                            'kk': 'Бет құрылымы белгісіз болса; OCR-дан кейін оқу ретін '
                                  'тексеріңіз.',
                            'uz': "Sahifa tuzilmasi noaniq bo'lsa ishlating; OCRdan keyin o'qish "
                                  'tartibini tekshiring.'},
 'norm.ocr_psm_summary_4': {'en': 'Best first choice for a normal full-page book scan.',
                            'ru': 'Лучший первый выбор для обычного полного скана книжной '
                                  'страницы.',
                            'zh': '普通整页书籍扫描的首选。',
                            'kk': 'Кітаптың қалыпты толық скан беті үшін бірінші таңдау.',
                            'uz': "Oddiy to'liq skan qilingan kitob sahifasi uchun birinchi "
                                  'tanlov.'},
 'norm.ocr_psm_summary_6': {'en': 'Use only for a cropped rectangle with one main text block.',
                            'ru': 'Только для обрезанного прямоугольника с одним основным блоком '
                                  'текста.',
                            'zh': '仅用于已裁剪的单个正文矩形区域。',
                            'kk': 'Бір негізгі мәтін блогы бар қиылған тікбұрыш үшін ғана.',
                            'uz': "Faqat bitta asosiy matn bloki bor kesilgan to'rtburchak uchun."},
 'norm.ocr_psm_summary_11': {'en': 'For notes, stamps, captions, or scattered pieces; not for '
                                   'normal pages.',
                             'ru': 'Для заметок, штампов, подписей и разбросанных кусков; не для '
                                   'обычной страницы.',
                             'zh': '用于笔记、印章、图注或分散片段；不适合普通书页。',
                             'kk': 'Жазба, мөр, түсіндірме не шашыраған бөліктер үшін; қалыпты '
                                   'бетке емес.',
                             'uz': "Izoh, muhr, sarlavha yoki tarqoq bo'laklar uchun; oddiy sahifa "
                                   'uchun emas.'},
 'norm.ocr_psm_summary_13': {'en': 'For a single title/header line; do not use for full pages.',
                             'ru': 'Для одной строки или заголовка; не используйте для полной '
                                   'страницы.',
                             'zh': '用于单行标题或页眉；不要用于整页。',
                             'kk': 'Бір жол не тақырып үшін; толық бетке қолданбаңыз.',
                             'uz': "Bitta sarlavha yoki qator uchun; to'liq sahifaga ishlatmang."},
 'norm.ocr_psm_tip': {'en': 'Tesseract Page Segmentation Mode (PSM):\n'
                            '3 auto full page = use when the book page has unknown layout, several '
                            'blocks, illustrations, or mixed structure.\n'
                            '4 normal book page = use for a full scanned page whose main text can '
                            'be read from top to bottom in a stable order.\n'
                            '6 cropped body text = use only when the image is already a selected '
                            'rectangle with one main text block.\n'
                            '11 loose fragments = use for captions, stamps, margin notes, forms, '
                            'or scattered text pieces; reading order may need review.\n'
                            '13 title or one line = use for one short horizontal '
                            'title/header/line; do not use for full pages.',
                      'ru': 'Режим сегментации страницы Tesseract (PSM):\n'
                            '3 авто-страница = когда у страницы книги непонятная верстка, '
                            'несколько блоков, иллюстрации или смешанная структура.\n'
                            '4 обычная страница книги = полный скан страницы, где основной текст '
                            'читается сверху вниз в стабильном порядке.\n'
                            '6 вырезанный основной текст = только если изображение уже обрезано до '
                            'одного прямоугольного блока текста без полей и колонтитулов.\n'
                            '11 разбросанные фрагменты = подписи, штампы, заметки на полях, формы '
                            'или отдельные куски текста; порядок чтения надо проверить.\n'
                            '13 заголовок или одна строка = одна короткая горизонтальная '
                            'строка/шапка; не использовать для полной страницы.'},
 'norm.ocr_not_applicable': {'en': 'OCR settings apply only to PDF files',
                             'ru': 'Настройки OCR применимы только к PDF'},
 'norm.ocr_install_hint': {'en': 'Tesseract is not available in this OS. Install native OCR tools: '
                                 '{cmd}',
                           'ru': 'Tesseract не найден в этой ОС. Установите OCR нативным '
                                 'установщиком: {cmd}',
                           'zh': '当前系统未找到 Tesseract。请用本机安装器安装 OCR 工具：{cmd}',
                           'kk': 'Бұл ОС-та Tesseract табылмады. OCR құралдарын жергілікті '
                                 'орнатқышпен орнатыңыз: {cmd}',
                           'uz': 'Bu OSda Tesseract topilmadi. OCR vositalarini mahalliy '
                                 'o‘rnatuvchi bilan o‘rnating: {cmd}'},
 'norm.ocr_install_language_hint': {'en': "Tesseract is installed, but language data '{lang}' is "
                                          'missing. Install OCR language packs: {cmd}',
                                    'ru': "Tesseract установлен, но нет языкового пакета '{lang}'. "
                                          'Установите OCR-языки: {cmd}',
                                    'zh': "已安装 Tesseract，但缺少语言数据 '{lang}'。请安装 OCR 语言包：{cmd}",
                                    'kk': "Tesseract орнатылған, бірақ '{lang}' тіл деректері жоқ. "
                                          'OCR тіл пакеттерін орнатыңыз: {cmd}',
                                    'uz': "Tesseract o‘rnatilgan, lekin '{lang}' til maʼlumoti "
                                          'yo‘q. OCR til paketlarini o‘rnating: {cmd}'},
 'norm.ocr_install_button': {'en': 'Install OCR',
                             'ru': 'Установить OCR',
                             'zh': '安装 OCR',
                             'kk': 'OCR орнату',
                             'uz': 'OCR o‘rnatish'},
 'norm.ocr_install_started': {'en': 'Started native OCR installer: {cmd}',
                              'ru': 'Запущен нативный установщик OCR: {cmd}',
                              'zh': '已启动本机 OCR 安装器：{cmd}',
                              'kk': 'Жергілікті OCR орнатқышы іске қосылды: {cmd}',
                              'uz': 'Mahalliy OCR o‘rnatuvchisi ishga tushdi: {cmd}'},
 'norm.ocr_install_failed': {'en': 'Could not launch installer. Run manually: {cmd}',
                             'ru': 'Не удалось запустить установщик. Запустите вручную: {cmd}',
                             'zh': '无法启动安装器。请手动运行：{cmd}',
                             'kk': 'Орнатқышты іске қосу мүмкін болмады. Қолмен іске қосыңыз: '
                                   '{cmd}',
                             'uz': 'O‘rnatuvchini ishga tushirib bo‘lmadi. Qo‘lda ishga tushiring: '
                                   '{cmd}'},
 'norm.llm_normalize': {'en': 'LLM/GPU normalization:', 'ru': 'LLM/GPU нормализация:'},
 'norm.llm_normalize_check': {'en': 'Use local model after rules',
                              'ru': 'Использовать локальную модель после правил'},
 'norm.llm_normalize_check_compact': {'en': 'Local LLM',
                                      'ru': 'Локальная LLM',
                                      'zh': '本地 LLM',
                                      'kk': 'Жергілікті LLM',
                                      'uz': 'Lokal LLM'},
 'norm.llm_endpoint': {'en': 'LLM endpoint:', 'ru': 'LLM endpoint:'},
 'norm.llm_model': {'en': 'LLM model:', 'ru': 'LLM модель:'},
 'norm.llm_hint': {'en': 'Uses an OpenAI-compatible local server. GPU usage depends on that '
                         'server, e.g. Ollama with CUDA.',
                   'ru': 'Использует OpenAI-compatible локальный сервер. GPU задействуется самим '
                         'сервером, например Ollama с CUDA.'},
 'norm.llm_tip': {'en': 'Runs the existing rule-based normalizer first, then asks a local '
                        'OpenAI-compatible LLM to conservatively fix punctuation, typos, and yo '
                        'letters. The app validates every answer and keeps the original text if '
                        'the model changes too much.',
                  'ru': 'Сначала идёт быстрая нормализация правилами, затем локальная '
                        'OpenAI-compatible LLM аккуратно исправляет пунктуацию, опечатки и букву '
                        'ё. Каждый ответ проверяется; если модель слишком меняет текст, остаётся '
                        'исходный абзац.'},
 'norm.run': {'en': 'Run Normalization', 'ru': 'Запустить нормализацию'},
 'norm.starting': {'en': 'Starting…', 'ru': 'Запуск…'},
 'norm.cache_dialog_title': {'en': 'Completed normalization found',
                             'ru': 'Готовая нормализация найдена',
                             'zh': '已找到完成的标准化结果',
                             'kk': 'Дайын нормализация табылды',
                             'uz': 'Yakunlangan normalizatsiya topildi'},
 'norm.cache_dialog_text': {'en': 'A cached result exists for “{name}” with the current settings.',
                            'ru': 'Для «{name}» найден результат с текущими параметрами.',
                            'zh': '“{name}”在当前设置下已有缓存结果。',
                            'kk': '«{name}» үшін ағымдағы баптаулармен кеш нәтижесі бар.',
                            'uz': '“{name}” uchun joriy sozlamalar bilan kesh natijasi bor.'},
 'norm.cache_dialog_text_mismatch': {'en': 'A cached result exists for “{name}”, but its settings '
                                           'differ from the current ones.',
                                     'ru': 'Для «{name}» найден кеш, но его настройки отличаются '
                                           'от текущих.',
                                     'zh': '“{name}” 有缓存结果，但它的设置与当前设置不同。',
                                     'kk': '«{name}» үшін кеш нәтижесі бар, бірақ оның баптаулары '
                                           'ағымдағы баптаулардан өзгеше.',
                                     'uz': '“{name}” uchun kesh natijasi bor, lekin uning '
                                           'sozlamalari joriy sozlamalardan farq qiladi.'},
 'norm.cache_dialog_informative': {'en': 'Restore it to continue immediately with chapters and '
                                         'role extraction. Choose “Run from scratch” only if you '
                                         'want to read the source, OCR, and LLM steps again.',
                                   'ru': 'Восстановите его из кеша, чтобы сразу продолжить с '
                                         'главами и ролями. Выберите «Запустить заново», только '
                                         'если хотите повторно прочитать файл, OCR и LLM-шаги.',
                                   'zh': '从缓存恢复即可立即继续处理章节和角色。只有在想重新读取源文件、OCR 和 LLM 步骤时，才选择“重新运行”。',
                                   'kk': 'Кештен қалпына келтірсеңіз, тараулар мен рөлдерге бірден '
                                         'өтесіз. Бастапқы файлды, OCR және LLM қадамдарын қайта '
                                         'орындау керек болса ғана «Қайта іске қосу» таңдаңыз.',
                                   'uz': 'Keshdan tiklasangiz, boblar va rollar bilan darhol davom '
                                         'etasiz. Manba fayl, OCR va LLM bosqichlarini qayta '
                                         'bajarishni istasangizgina “Qayta ishga tushirish”ni '
                                         'tanlang.'},
 'norm.cache_dialog_informative_mismatch': {'en': 'Restoring uses the cached result as it was '
                                                  'built before. Choose “Run from scratch” to '
                                                  'apply the current OCR, DPI, PSM, or LLM '
                                                  'settings.',
                                            'ru': 'Восстановление возьмет уже собранный результат '
                                                  'из кеша. Выберите «Запустить заново», чтобы '
                                                  'применить текущие OCR, DPI, PSM или '
                                                  'LLM-настройки.',
                                            'zh': '恢复会使用之前生成的缓存结果。选择“重新运行”以应用当前 OCR、DPI、PSM 或 LLM '
                                                  '设置。',
                                            'kk': 'Қалпына келтіру бұрын жасалған кеш нәтижесін '
                                                  'пайдаланады. Ағымдағы OCR, DPI, PSM немесе LLM '
                                                  'баптауларын қолдану үшін «Қайта іске қосу» '
                                                  'таңдаңыз.',
                                            'uz': 'Tiklash avval yaratilgan kesh natijasidan '
                                                  'foydalanadi. Joriy OCR, DPI, PSM yoki LLM '
                                                  "sozlamalarini qo'llash uchun “Qayta ishga "
                                                  'tushirish”ni tanlang.'},
 'norm.cache_restore_button': {'en': 'Restore from cache',
                               'ru': 'Восстановить из кеша',
                               'zh': '从缓存恢复',
                               'kk': 'Кештен қалпына келтіру',
                               'uz': 'Keshdan tiklash'},
 'norm.cache_run_fresh_button': {'en': 'Run from scratch',
                                 'ru': 'Запустить заново',
                                 'zh': '重新运行',
                                 'kk': 'Қайта іске қосу',
                                 'uz': 'Qayta ishga tushirish'},
 'norm.cache_cancel_button': {'en': 'Cancel',
                              'ru': 'Отмена',
                              'zh': '取消',
                              'kk': 'Болдырмау',
                              'uz': 'Bekor qilish'},
 'norm.cache_restored': {'en': 'Restored from cache. Chapters: {n}.',
                         'ru': 'Восстановлено из кеша. Глав: {n}.',
                         'zh': '已从缓存恢复。章节数：{n}。',
                         'kk': 'Кештен қалпына келтірілді. Тараулар: {n}.',
                         'uz': 'Keshdan tiklandi. Boblar: {n}.'},
 'norm.cache_restore_failed': {'en': 'Could not restore cached normalization: {msg}',
                               'ru': 'Не удалось восстановить нормализацию из кеша: {msg}',
                               'zh': '无法恢复缓存的标准化结果：{msg}',
                               'kk': 'Кештегі нормализацияны қалпына келтіру мүмкін болмады: {msg}',
                               'uz': "Keshlangan normalizatsiyani tiklab bo'lmadi: {msg}"},
 'norm.loading': {'en': 'Loading book…', 'ru': 'Загрузка книги…'},
 'norm.pdf_checking': {'en': 'Checking PDF and OCR settings...',
                       'ru': 'Проверяю PDF и OCR-настройки...',
                       'zh': '正在检查 PDF 和 OCR 设置...',
                       'kk': 'PDF және OCR баптаулары тексерілуде...',
                       'uz': 'PDF va OCR sozlamalari tekshirilmoqda...'},
 'norm.pdf_native_extracting': {'en': 'Checking the embedded PDF text layer...',
                                'ru': 'Проверяю встроенный текстовый слой PDF...',
                                'zh': '正在检查 PDF 内置文本层...',
                                'kk': 'PDF ішіндегі мәтін қабаты тексерілуде...',
                                'uz': 'PDF ichidagi matn qatlami tekshirilmoqda...'},
 'norm.ocr_prepare': {'en': 'Preparing OCR (DPI={dpi}, PSM={psm})...',
                      'ru': 'Готовлю OCR (DPI={dpi}, PSM={psm})...',
                      'zh': '正在准备 OCR (DPI={dpi}, PSM={psm})...',
                      'kk': 'OCR дайындалуда (DPI={dpi}, PSM={psm})...',
                      'uz': 'OCR tayyorlanmoqda (DPI={dpi}, PSM={psm})...'},
 'norm.ocr_pages_start': {'en': 'OCR will process {total} page(s) at {dpi} DPI, PSM {psm}. The '
                                'first page can take a while; ETA appears after it finishes.',
                          'ru': 'OCR обработает {total} стр. при {dpi} DPI, PSM {psm}. Первая '
                                'страница может идти долго; ETA появится после неё.',
                          'zh': 'OCR 将处理 {total} 页，{dpi} DPI，PSM {psm}。第一页可能较慢；完成后会显示 ETA。',
                          'kk': 'OCR {total} бетті {dpi} DPI, PSM {psm} режимінде өңдейді. Бірінші '
                                'бет ұзақ жүруі мүмкін; ETA содан кейін шығады.',
                          'uz': 'OCR {total} sahifani {dpi} DPI, PSM {psm} bilan qayta ishlaydi. '
                                'Birinchi sahifa uzoqroq ketishi mumkin; ETA undan keyin chiqadi.'},
 'norm.ocr_page_rendering': {'en': 'OCR: rendering page {page}/{total} at {dpi} DPI...',
                             'ru': 'OCR: рендер страницы {page}/{total} при {dpi} DPI...',
                             'zh': 'OCR：正在渲染第 {page}/{total} 页，{dpi} DPI...',
                             'kk': 'OCR: {page}/{total} бет {dpi} DPI-да рендерленуде...',
                             'uz': 'OCR: {page}/{total} sahifa {dpi} DPI da render qilinmoqda...'},
 'norm.ocr_page_recognizing': {'en': 'OCR: recognizing page {page}/{total}, segment '
                                     '{segment}/{segments}...',
                               'ru': 'OCR: распознаю страницу {page}/{total}, сегмент '
                                     '{segment}/{segments}...',
                               'zh': 'OCR：正在识别第 {page}/{total} 页，片段 {segment}/{segments}...',
                               'kk': 'OCR: {page}/{total} бет танылуда, сегмент '
                                     '{segment}/{segments}...',
                               'uz': 'OCR: {page}/{total} sahifa tanilmoqda, segment '
                                     '{segment}/{segments}...'},
 'norm.ocr_page_done': {'en': 'OCR: {done}/{total} page(s) done - ETA: {eta}',
                        'ru': 'OCR: готово {done}/{total} стр. - Осталось: {eta}',
                        'zh': 'OCR：已完成 {done}/{total} 页 - ETA：{eta}',
                        'kk': 'OCR: {done}/{total} бет дайын - ETA: {eta}',
                        'uz': 'OCR: {done}/{total} sahifa tayyor - ETA: {eta}'},
 'norm.ocr_unavailable_native': {'en': 'Tesseract is not installed; using native PDF text '
                                       'extraction. Run: {hint}',
                                 'ru': 'Tesseract не установлен; использую встроенное извлечение '
                                       'текста PDF. Запустите: {hint}'},
 'norm.err_tesseract_missing_force': {'en': 'Tesseract is not installed. Run: {hint}. Or switch '
                                            'OCR mode to auto/off.',
                                      'ru': 'Tesseract не установлен. Запустите: {hint}. Или '
                                            'переключите OCR в auto/off.'},
 'norm.err_tesseract_missing_scanned': {'en': 'The PDF text layer is missing or unreadable, and '
                                              'Tesseract is not installed. Run: {hint}. Then run '
                                              'normalization again.',
                                        'ru': 'Текстовый слой PDF отсутствует или нечитаем, а '
                                              'Tesseract не установлен. Запустите: {hint}. Затем '
                                              'запустите нормализацию снова.'},
 'norm.err_ocr_failed_unreadable': {'en': 'The PDF text layer is unreadable, and OCR did not '
                                          'produce readable Russian text. Check the Tesseract '
                                          'Russian language pack or try another DPI/PSM setting.',
                                    'ru': 'Текстовый слой PDF нечитаем, и OCR не дал читаемый '
                                          'русский текст. Проверьте русский языковой пакет '
                                          'Tesseract или попробуйте другие DPI/PSM.'},
 'norm.err_ocr_failed_force': {'en': 'OCR did not produce readable Russian text. Check the '
                                     'Tesseract Russian language pack or try another DPI/PSM '
                                     'setting.',
                               'ru': 'OCR не дал читаемый русский текст. Проверьте русский '
                                     'языковой пакет Tesseract или попробуйте другие DPI/PSM.'},
 'norm.normalizing': {'en': 'Normalizing: {stage} ({cur}/{total}) — ETA: {eta}',
                      'ru': 'Нормализация: {stage} ({cur}/{total}) — Осталось: {eta}'},
 'norm.norm_paragraphs': {'en': 'Normalizing: {done}/{total} paragraphs — ETA: {eta}',
                          'ru': 'Нормализация: {done}/{total} абзацев — Осталось: {eta}'},
 'norm.llm_start': {'en': 'LLM normalization: model {model}',
                    'ru': 'LLM-нормализация: модель {model}'},
 'norm.llm_progress': {'en': 'LLM normalization: {done}/{total} paragraphs, accepted {accepted}, '
                             'rejected {rejected} — ETA: {eta}',
                       'ru': 'LLM-нормализация: {done}/{total} абзацев, принято {accepted}, '
                             'отклонено {rejected} — Осталось: {eta}'},
 'norm.llm_done': {'en': 'LLM normalization complete: accepted {accepted}, rejected {rejected}',
                   'ru': 'LLM-нормализация готова: принято {accepted}, отклонено {rejected}'},
 'norm.llm_review_required': {'en': 'LLM left {rejected} paragraph(s) unchanged. Review report: '
                                    '{path}',
                              'ru': 'LLM оставила {rejected} абзац(ев) без правки. Review-report: '
                                    '{path}'},
 'norm.detecting_chapters': {'en': 'Detecting chapters…', 'ru': 'Определение глав…'},
 'norm.annotating_stress': {'en': 'Annotating stress marks…', 'ru': 'Расстановка ударений…'},
 'norm.done': {'en': 'Done: {n} chapters, {time} total', 'ru': 'Готово: {n} глав, {time} всего'},
 'norm.raw_placeholder': {'en': 'Original text', 'ru': 'Оригинал из файла'},
 'norm.norm_placeholder': {'en': 'After normalization', 'ru': 'После нормализации'},
 'norm.apply_manual_edits': {'en': 'Apply edits',
                             'ru': 'Применить правки',
                             'zh': '应用编辑',
                             'kk': 'Өңдеуді қолдану',
                             'uz': 'Tahrirlarni qoʻlash'},
 'norm.apply_manual_edits_compact': {'en': 'Apply',
                                     'ru': 'Применить',
                                     'zh': '应用',
                                     'kk': 'Қолдану',
                                     'uz': "Qo'llash"},
 'norm.apply_manual_edits_tip': {'en': 'Write the edited normalized text back into the book before '
                                       'role/chunk markup.',
                                 'ru': 'Записать ручные правки в книгу перед разметкой ролей и '
                                       'чанков.',
                                 'zh': '在角色和分块标注前，将已编辑的规范化文本写回书稿。',
                                 'kk': 'Рөлдер мен чанктарды белгілеуден бұрын өңделген мәтінді '
                                       'кітапқа қайта жазу.',
                                 'uz': 'Rol va boʻak belgilashdan oldin tahrirlangan '
                                       'normallashtirilgan matnni kitobga yozish.'},
 'norm.manual_edit_applied': {'en': 'Applied manual edits to {n} paragraph(s).',
                              'ru': 'Ручные правки применены к {n} абзац(ам).',
                              'zh': '已将手动编辑应用到 {n} 个段落。',
                              'kk': 'Қолмен өңдеу {n} абзацқа қолданылды.',
                              'uz': 'Qoʻlanma tahrirlar {n} paragrafga qoʻllandi.'},
 'norm.manual_edit_mismatch': {'en': 'Cannot apply edits: {edited} edited blocks for {paragraphs} '
                                     'book paragraph(s). Keep blank-line paragraph boundaries.',
                               'ru': 'Не могу применить правки: {edited} блок(а) на {paragraphs} '
                                     'абзац(ев) книги. Сохраните границы абзацев пустыми строками.',
                               'zh': '无法应用编辑：{edited} 个编辑块对应 {paragraphs} 个书稿段落。请保留空行段落边界。',
                               'kk': 'Өңдеуді қолдану мүмкін емес: {paragraphs} абзац үшін '
                                     '{edited} өңделген блок. Абзац шекараларын бос жолдармен '
                                     'сақтаңыз.',
                               'uz': 'Tahrirlarni qoʻlab boʻlmadi: {paragraphs} kitob paragrafi '
                                     'uchun {edited} tahrirlangan blok. Paragraf chegaralarini '
                                     'boʻsh qatorlar bilan saqlang.'},
 'norm.select_file': {'en': 'Select Book File', 'ru': 'Выбрать файл книги'}}
