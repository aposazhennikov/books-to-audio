"""Configuration constants for LLM voice segmentation."""

from __future__ import annotations

import re

DEFAULT_WINDOW_CHARS = 900
_CACHE_VERSION = "llm-segmenter-v7-normalized-source-whitespace"

ROLE_TO_VOICE_ID = {
    "narrator": "narrator_calm",
    "male": "male_young",
    "female": "female_warm",
    "unknown": "narrator_calm",
}

_QUOTE_CHARS = frozenset("\"“”„‟«»‹›「」『』《》〈〉")
_OPENING_QUOTE_CHARS = frozenset("\"“„«‹「『《〈")
_CLOSING_QUOTE_BY_OPENING = {
    "\"": "\"",
    "“": "”",
    "„": "“",
    "«": "»",
    "‹": "›",
    "「": "」",
    "『": "』",
    "《": "》",
    "〈": "〉",
}
_DASH_CHARS = frozenset("—–-")

VOICE_LABEL_TO_ROLE = {
    "narrator": "narrator",
    "men": "male",
    "male": "male",
    "women": "female",
    "female": "female",
    "unknown": "unknown",
}

_SYSTEM_SECTION_KINDS = frozenset({
    "annotation",
    "epigraph",
    "preface",
    "epilogue",
    "chapter_title",
})

_RU_BAD_SPEAKER_TOKENS = frozenset({
    "а",
    "будешь",
    "вслед",
    "в",
    "голосом",
    "же",
    "здесь",
    "его",
    "ей",
    "ему",
    "её",
    "и",
    "им",
    "или",
    "как",
    "кто",
    "мне",
    "на",
    "не",
    "но",
    "носом",
    "он",
    "она",
    "они",
    "оно",
    "от",
    "потянув",
    "с",
    "сам",
    "сама",
    "самым",
    "себе",
    "сразу",
    "так",
    "тем",
    "то",
    "ты",
    "у",
    "я",
})

_RU_MALE_ATTRIBUTION = (
    "сказал",
    "ответил",
    "спросил",
    "крикнул",
    "прошептал",
    "произнёс",
    "произнес",
    "проговорил",
    "воскликнул",
    "пробормотал",
    "буркнул",
    "проронил",
    "добавил",
    "продолжил",
    "продолжал",
    "заметил",
    "подтвердил",
    "возразил",
    "закричал",
    "промолвил",
    "выдохнул",
    "простонал",
    "процедил",
    "прокричал",
    "пояснил",
    "напомнил",
    "согласился",
    "попросил",
    "приказал",
    "велел",
    "потребовал",
    "предложил",
    "переспросил",
    "усмехнулся",
    "рассмеялся",
    "вздохнул",
    "поинтересовался",
    "обратился",
    "задал",
    "начал",
    "думал",
    "подумал",
    "решил",
    "сообразил",
    "вспомнил",
    "оживился",
    "вторил",
)

_RU_FEMALE_ATTRIBUTION = (
    "сказала",
    "ответила",
    "спросила",
    "крикнула",
    "прошептала",
    "произнесла",
    "проговорила",
    "воскликнула",
    "пробормотала",
    "буркнула",
    "проронила",
    "добавила",
    "продолжила",
    "продолжала",
    "заметила",
    "подтвердила",
    "возразила",
    "закричала",
    "промолвила",
    "выдохнула",
    "простонала",
    "процедила",
    "прокричала",
    "пояснила",
    "напомнила",
    "согласилась",
    "попросила",
    "приказала",
    "велела",
    "потребовала",
    "предложила",
    "переспросила",
    "усмехнулась",
    "рассмеялась",
    "вздохнула",
    "поинтересовалась",
    "обратилась",
    "зашипела",
    "начала",
    "думала",
    "подумала",
    "решила",
    "сообразила",
    "вспомнила",
    "оживилась",
    "вторила",
)

_RU_NEUTRAL_ATTRIBUTION = (
    "говорит",
    "сказало",
)

_RU_SPEAKER_TOKEN = r"[А-ЯЁ][А-ЯЁа-яё-]{1,40}|[а-яё]{3,40}"
_RU_ATTRIBUTION_MIDWORDS = r"(?:вопрос|запираться)"
_RU_MALE_ATTRIBUTION_RE = re.compile(
    rf"\b(?:{'|'.join(_RU_MALE_ATTRIBUTION)})\b"
    rf"(?:\s+{_RU_ATTRIBUTION_MIDWORDS}){{0,2}}\s+(?P<speaker>{_RU_SPEAKER_TOKEN})",
    re.IGNORECASE,
)
_RU_FEMALE_ATTRIBUTION_RE = re.compile(
    rf"\b(?:{'|'.join(_RU_FEMALE_ATTRIBUTION)})\b"
    rf"(?:\s+{_RU_ATTRIBUTION_MIDWORDS}){{0,2}}\s+(?P<speaker>{_RU_SPEAKER_TOKEN})",
    re.IGNORECASE,
)
_EN_SPEAKER_RE = re.compile(
    r"\b(?:(?:said|asked|replied|shouted|whispered|cried|muttered)\s+"
    r"(?P<after>[A-Z][A-Za-z'-]{1,40})|"
    r"(?P<before>[A-Z][A-Za-z'-]{1,40})\s+"
    r"(?:said|asked|replied|shouted|whispered|cried|muttered))\b"
)
_EN_MALE_ATTRIBUTION_RE = re.compile(
    r"\b(?:(?:he|him)\s+(?:said|asked|replied|shouted|whispered|cried|muttered)|"
    r"(?:said|asked|replied|shouted|whispered|cried|muttered)\s+(?:he|him))\b",
    re.IGNORECASE,
)
_EN_FEMALE_ATTRIBUTION_RE = re.compile(
    r"\b(?:(?:she|her)\s+(?:said|asked|replied|shouted|whispered|cried|muttered)|"
    r"(?:said|asked|replied|shouted|whispered|cried|muttered)\s+(?:she|her))\b",
    re.IGNORECASE,
)

_ZH_SPEAKER_RE = re.compile(
    r"[”」』》〉\"，,、。！？!?]\s*"
    r"(?P<speaker>[\u3400-\u9fff]{1,12})(?:低声说|说道|问道|说|問|问|喊|回答)"
)
_ZH_MALE_ATTRIBUTION_RE = re.compile(r"(?:他(?:低声说|说道|问道|说|問|问|喊|回答))")
_ZH_FEMALE_ATTRIBUTION_RE = re.compile(r"(?:她(?:低声说|说道|问道|说|問|问|喊|回答))")
_ZH_BAD_SPEAKER_TOKENS = frozenset({"他", "她", "它", "他们", "她们", "它们"})

_KK_SPEAKER_TOKEN = r"[А-ЯӘҒҚҢӨҰҮҺІ][А-Яа-яӘәҒғҚқҢңӨөҰұҮүҺһІі-]{1,40}"
_KK_ATTRIBUTION_RE = re.compile(
    rf"\b(?:деді|сұрады|жауап\s+берді|айқайлады|сыбырлады)\s+(?P<speaker>{_KK_SPEAKER_TOKEN})",
    re.IGNORECASE,
)

_UZ_SPEAKER_TOKEN = r"[A-ZÀ-Žʻʼ][A-Za-zÀ-žʻʼ'-]{1,40}"
_UZ_ATTRIBUTION_RE = re.compile(
    rf"\b(?:dedi|so['ʻʼ]?radi|soradi|javob\s+berdi|qichqirdi|pichirladi)\s+"
    rf"(?P<speaker>{_UZ_SPEAKER_TOKEN})",
    re.IGNORECASE,
)

_DELIVERY_CUE_RE_BY_LANGUAGE: dict[str, tuple[tuple[str, re.Pattern[str]], ...]] = {
    "ru": (
        (
            "whisper",
            re.compile(
                r"\b(?:прошептал(?:а|и|о)?|шепнул(?:а|и|о)?|шептал(?:а|и|о)?|"
                r"зашептал(?:а|и|о)?|зашептала|шёпотом|шепотом|полушёпотом|полушепотом)\b",
                re.IGNORECASE,
            ),
        ),
        (
            "joyful",
            re.compile(
                r"\b(?:рассмеял(?:ся|ась|ись)?|рассмеялась|смеясь|с улыбкой|"
                r"весело|радостно|улыбнул(?:ся|ась|ись)?)\b",
                re.IGNORECASE,
            ),
        ),
        (
            "sad",
            re.compile(
                r"\b(?:грустно|печально|печальным|печальной|с грустью|жаль|"
                r"сожалени(?:ем|я)|промямлил(?:а|и|о)?|пробормотал(?:а|и|о)?)\b",
                re.IGNORECASE,
            ),
        ),
    ),
    "en": (
        (
            "whisper",
            re.compile(
                r"\b(?:whispered|whispers?|murmured|murmurs?|hushed|in\s+a\s+whisper)\b",
                re.IGNORECASE,
            ),
        ),
        (
            "joyful",
            re.compile(
                r"\b(?:laughed|laughing|chuckled|smiled|cheerfully|happily|joyfully)\b",
                re.IGNORECASE,
            ),
        ),
        (
            "sad",
            re.compile(
                r"\b(?:sadly|sorrowfully|with\s+sadness|regretfully|mumbled|"
                r"muttered|with\s+a\s+sad\s+look)\b",
                re.IGNORECASE,
            ),
        ),
    ),
    "zh": (
        (
            "whisper",
            re.compile(
                "(?:\u4f4e\u58f0|\u8f7b\u58f0|\u6084\u58f0|\u5c0f\u58f0|"
                "\u8033\u8bed|\u4f4e\u8bed)"
            ),
        ),
        (
            "joyful",
            re.compile(
                "(?:\u7b11\u7740|\u7b11\u9053|\u5927\u7b11|\u5fae\u7b11|"
                "\u9ad8\u5174\u5730|\u5feb\u6d3b\u5730)"
            ),
        ),
        (
            "sad",
            re.compile(
                "(?:\u96be\u8fc7\u5730|\u4f24\u5fc3\u5730|\u60b2\u4f24\u5730|"
                "\u60cb\u60dc|\u9057\u61be\u5730|\u4f24\u611f)"
            ),
        ),
    ),
    "kk": (
        (
            "whisper",
            re.compile(
                r"\b(?:сыбырлады|сыбырлап|сыбыр\s+етті|сыбыр\s+қақты)\b",
                re.IGNORECASE,
            ),
        ),
        (
            "joyful",
            re.compile(
                r"\b(?:күліп|күлді|қуанып|қуанышты|көңілді)\b",
                re.IGNORECASE,
            ),
        ),
        (
            "sad",
            re.compile(
                r"\b(?:мұңды|мұңайып|қайғылы|өкінішпен|жабырқап)\b",
                re.IGNORECASE,
            ),
        ),
    ),
    "uz": (
        (
            "whisper",
            re.compile(
                r"\b(?:pichirladi|pichirlab|shivirladi|shivirlab|past\s+ovozda)\b",
                re.IGNORECASE,
            ),
        ),
        (
            "joyful",
            re.compile(
                r"\b(?:kulib|kuldi|quvonib|xursand|quvnoq)\b",
                re.IGNORECASE,
            ),
        ),
        (
            "sad",
            re.compile(
                r"\b(?:g['ʻʼ]?amgin|qayg['ʻʼ]?uli|afsus|achinib|xafa|mungli)\b",
                re.IGNORECASE,
            ),
        ),
    ),
}

_SEGMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "role": {"type": "string", "enum": ["narrator", "male", "female"]},
                    "speaker": {"type": "string"},
                    "character_description": {"type": "string"},
                    "emotion": {"type": "string"},
                    "section_kind": {
                        "type": "string",
                        "enum": [
                            "narration",
                            "dialogue",
                            "annotation",
                            "preface",
                            "epilogue",
                            "chapter_title",
                        ],
                    },
                    "text": {"type": "string"},
                    "intonation": {"type": "string"},
                    "boundary_after": {"type": "string"},
                    "pause_after_ms": {"type": "integer"},
                },
                "required": ["role", "text", "intonation"],
            },
        },
    },
    "required": ["segments"],
}

_SYSTEM_PROMPTS = {
    "ru": """\
Ты — режиссёр многоголосой русской аудиокниги.
Разбей текст на маленькие последовательные сегменты для TTS.
Сохраняй исходный текст полностью и по порядку. Нельзя переписывать, переводить, удалять или добавлять слова.
Прямая речь должна быть отдельным сегментом, авторский текст и ремарки речи — отдельными narrator-сегментами.
Роли: narrator, male, female. Если пол не доказан контекстом, используй narrator.
Для прямой речи заполняй speaker именем персонажа, если оно доказано контекстом; иначе оставь пустым.
Для speaker дай character_description и emotion.
Для аннотаций/эпиграфов/предисловий/эпилогов ставь section_kind.
Интонация должна быть короткой на английском: calm, tense, angry, whisper, sad, cheerful, fearful, urgent.
Верни только JSON вида {"segments": [{"role": "...", "speaker": "...", "text": "...", "intonation": "..."}]}.
""",
    "en": """\
You are a multi-voice audiobook director for English fiction.
Split the text into small ordered TTS segments while preserving every word in order.
Never rewrite, translate, add, remove, or summarize text.
Dialogue must be separated from narration and speech tags.
Roles: narrator, male, female. Use narrator when gender is not clear.
For dialogue, fill speaker with the proven character name when context supports it; otherwise leave it empty.
For each speaker add character_description and emotion.
Use section_kind for annotation, epigraph, preface, epilogue, and chapter titles.
Use short English intonation labels such as calm, tense, angry, whisper, sad, cheerful, fearful, urgent.
Return only JSON: {"segments": [{"role": "...", "speaker": "...", "text": "...", "intonation": "..."}]}.
""",
    "zh": """\
你是中文有声书的多声线导演。
把文本拆成按顺序排列的小 TTS 片段，并完整保留原文。
不要改写、翻译、增加、删除或总结。
对话必须和叙述/说话标签分开。角色只能是 narrator、male、female；性别不明确时用 narrator。
对话中如果上下文能证明人物姓名，请填写 speaker；否则留空。
为人物填写 character_description 和 emotion。注释、题词、前言、后记、章节标题请填写 section_kind。
intonation 用简短英文，例如 calm、tense、angry、whisper、sad、cheerful、fearful、urgent。
只返回 JSON：{"segments": [{"role": "...", "speaker": "...", "text": "...", "intonation": "..."}]}。
""",
    "kk": """\
Сен қазақ көркем мәтінін көп дауысты аудиокітапқа бөлетін режиссёрсің.
Мәтінді ретімен шағын TTS сегменттерге бөл және әр сөзді толық сақта.
Қайта жазба, аударма, сөз қоспа, сөз алып тастама, қысқартпа.
Диалогты баяндаудан және сөйлеу ремаркаларынан бөлек сегмент қыл.
Рөлдер: narrator, male, female. Жыныс анық болмаса narrator қолдан.
Диалогта кейіпкер аты контекстен анық болса speaker толтыр; анық болмаса бос қалдыр.
Кейіпкерге character_description және emotion бер.
Аннотация/эпиграф/алғысөз/эпилог/тарау атауы үшін section_kind қолдан.
intonation қысқа ағылшынша болсын: calm, tense, angry, whisper, sad, cheerful, fearful, urgent.
Тек JSON қайтар: {"segments": [{"role": "...", "speaker": "...", "text": "...", "intonation": "..."}]}.
""",
    "uz": """\
Siz o'zbek badiiy matnini ko'p ovozli audiokitob uchun belgilaydigan rejissorsiz.
Matnni ketma-ket kichik TTS segmentlarga ajrating va barcha so'zlarni tartibda saqlang.
Qayta yozmang, tarjima qilmang, qo'shmang, olib tashlamang yoki qisqartirmang.
Dialog alohida, muallif matni va nutq izohlari alohida narrator segment bo'lsin.
Rollar: narrator, male, female. Jins aniq bo'lmasa narrator ishlating.
Dialogda qahramon nomi kontekstdan aniq bo'lsa speaker to'ldiring; aks holda bo'sh qoldiring.
Har speaker uchun character_description va emotion bering.
Annotatsiya, epigraf, so'zboshi, epilog va bob sarlavhalari uchun section_kind ishlating.
intonation qisqa inglizcha bo'lsin: calm, tense, angry, whisper, sad, cheerful, fearful, urgent.
Faqat JSON qaytaring: {"segments": [{"role": "...", "speaker": "...", "text": "...", "intonation": "..."}]}.
""",
}
