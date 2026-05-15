"""Yoficator — restores the Russian letter ё (yo) in texts where е was used instead.

Uses a built-in dictionary of unambiguous Russian words containing ё.
Only replaces words where the ё variant is the ONLY valid form (no е/ё ambiguity).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from book_normalizer.normalization.morphology import is_likely_plural_head

logger = logging.getLogger(__name__)

# Unambiguous ё-words: words where ё is the only correct spelling.
# Includes common literary vocabulary with declensions and conjugations.
# Format: lowercase form -> replacement with ё.
_YO_DICT: dict[str, str] = {}

# Raw word list — each word is the ё-form; the е-form is derived automatically.
_YO_WORDS = (
    # Common words.
    "её,ещё,всё,моё,своё,твоё,о нём,при нём,над нём,"
    "вёл,вёз,вёсла,берёза,берёзка,берёзовый,берёт,"
    "вёдра,вёдро,ведёрко,"
    "зелёный,зелёная,зелёное,зелёные,зелёного,зелёной,зелёным,зелёных,"
    "весёлый,весёлая,весёлое,весёлые,весёлого,весёлой,весёлым,весёлых,весело,"
    "тёплый,тёплая,тёплое,тёплые,тёплого,тёплой,тёплым,тёплых,тепло,"
    "тёмный,тёмная,тёмное,тёмные,тёмного,тёмной,тёмным,тёмных,"
    "чёрный,чёрная,чёрное,чёрные,чёрного,чёрной,чёрным,чёрных,"
    "жёлтый,жёлтая,жёлтое,жёлтые,жёлтого,жёлтой,жёлтым,жёлтых,"
    "тяжёлый,тяжёлая,тяжёлое,тяжёлые,тяжёлого,тяжёлой,тяжёлым,тяжёлых,"
    # Nouns.
    "ёж,ёжик,ёлка,ёлочка,ёмкость,"
    "жёны,жёнушка,"
    "звёзды,звёздный,звёздная,звёздное,звёздочка,"
    "гнёзда,гнёздышко,"
    "ребёнок,ребёнка,ребёнку,ребёнком,"
    "котёнок,котёнка,телёнок,телёнка,жеребёнок,козлёнок,львёнок,тигрёнок,"
    "орёл,орла,"
    "лёд,льда,льду,льдом,ледяной,"
    "мёд,мёда,мёду,мёдом,медовый,"
    "лён,льна,"
    "клён,клёна,клёнов,клёновый,"
    "огонёк,уголёк,мотылёк,фитилёк,стебелёк,василёк,"
    "посёлок,посёлка,"
    "ручёёк,"
    "костёр,костра,"
    "актёр,актёра,актёры,актёров,"
    "шофёр,шофёра,шофёры,шофёров,"
    "ковёр,ковра,"
    "пёс,пса,"
    "овёс,"
    "учёт,учёта,"
    "расчёт,расчёта,"
    "счёт,счёта,счётчик,"
    "зачёт,зачёта,"
    "отчёт,отчёта,"
    "щёлк,щёлка,щёлочь,"
    "щётка,щётки,"
    "чёлка,чёлки,"
    "чёрт,чёрта,черти,чертей,"
    "пчёлы,пчёлка,пчёл,"
    "шёлк,шёлка,шёлковый,"
    "жёлудь,жёлуди,"
    "жёлоб,жёлоба,"
    "жёрнов,жёрнова,"
    "жёсткий,жёсткая,жёсткое,жёсткие,жёстко,"
    "шёпот,шёпотом,"
    "дёготь,дёгтя,"
    "гарём,гарёма,"
    "приём,приёма,приёмник,приёмный,"
    "подъём,подъёма,подъёмник,подъёмный,"
    "объём,объёма,объёмный,"
    "наём,найма,"
    # Verbs and participles.
    "берёт,берёте,берём,"
    "идёт,идём,идёте,пойдёт,пойдём,пойдёте,"
    "найдёт,найдём,найдёте,"
    "придёт,придём,придёте,"
    "подойдёт,подойдём,"
    "уйдёт,уйдём,"
    "пришёл,пришла,ушёл,ушла,нашёл,нашла,вышел,пошёл,пошла,"
    "подошёл,подошла,обошёл,перешёл,зашёл,зашла,дошёл,дошла,"
    "привёл,привела,увёл,увела,завёл,завела,довёл,довела,"
    "провёл,провела,отвёл,отвела,подвёл,подвела,перевёл,перевела,"
    "привёз,привезла,увёз,увезла,завёз,завезла,довёз,довезла,"
    "провёз,провезла,отвёз,отвезла,подвёз,подвезла,перевёз,перевезла,"
    "даёт,даём,даёте,задаёт,отдаёт,подаёт,раздаёт,передаёт,выдаёт,"
    "ждёт,ждём,ждёте,"
    "живёт,живём,живёте,"
    "зовёт,зовём,"
    "поёт,поём,поёте,"
    "жуёт,жуём,"
    "куёт,куём,"
    "клюёт,"
    "плюёт,"
    "суёт,"
    "несёт,несём,несёте,"
    "везёт,везём,везёте,"
    "ведёт,ведём,ведёте,"
    "метёт,метём,"
    "цветёт,цветём,"
    "растёт,растём,"
    "течёт,течём,"
    "печёт,печём,"
    "сечёт,"
    "стечёт,"
    "бережёт,"
    "стережёт,"
    "жжёт,жжём,"
    "лжёт,"
    "ревёт,ревём,"
    "орёт,орём,"
    "трёт,трём,"
    "прёт,прём,"
    "мрёт,"
    "врёт,врём,"
    "рвёт,рвём,"
    "шлёт,шлём,"
    "льёт,льём,льёте,"
    "пьёт,пьём,пьёте,"
    "бьёт,бьём,бьёте,"
    "вьёт,вьём,"
    "шьёт,шьём,"
    "взялёт,"
    "начнёт,начнём,"
    "вернёт,вернём,вернёте,"
    "повернёт,повернём,"
    "свернёт,свернём,"
    "завернёт,"
    "развернёт,"
    "толкнёт,толкнём,"
    "прыгнёт,прыгнём,"
    "крикнёт,крикнём,"
    "шепнёт,шепнём,"
    "махнёт,махнём,"
    "тронёт,тронём,"
    "коснётся,"
    "проснётся,"
    "улыбнётся,"
    "засмеётся,"
    "рассмеётся,"
    "обернётся,"
    "вернётся,"
    "придётся,"
    "удастся,"
    "понёс,понесла,принёс,принесла,унёс,унесла,донёс,донесла,"
    "перенёс,перенесла,вынес,"
    "произнёс,произнесла,"
    "потёр,потёрла,"
    "протёр,протёрла,"
    "растёр,растёрла,"
    "запёр,заперла,"
    "отпёр,отперла,"
    "умёр,умерла,"
    "стёр,стёрла,"
    "упёр,упёрла,"
    "подпёр,"
    # Adjectives and adverbs.
    "твёрдый,твёрдая,твёрдое,твёрдые,твёрдо,"
    "острённый,"
    "учёный,учёная,учёного,учёных,учёным,"
    "копчёный,копчёная,копчёное,"
    "печёный,печёная,печёное,"
    "мочёный,мочёная,мочёное,"
    "тушёный,тушёная,тушёное,"
    "варёный,варёная,варёное,"
    "солёный,солёная,солёное,"
    "вязаный,"
    "крёстный,крёстная,"
    "манёвр,манёвра,манёвры,"
    "далёкий,далёкая,далёкое,далёкие,далеко,"
    "тёсный,тёсная,тёсное,тёсные,тёсно,"
    # Pronouns and particles.
    "всё-таки,всё ещё,"
    # Past tense forms (common literature verbs).
    "замёрз,замёрзла,замёрзли,"
    "затёр,затёрла,"
    "расстёгнут,"
    "обожжёт,обожжён,"
    "поражён,поражёна,поражённый,"
    "восхищён,восхищёна,восхищённый,"
    "утомлён,утомлёна,утомлённый,"
    "удивлён,удивлёна,удивлённый,"
    "оскорблён,оскорблёна,оскорблённый,"
    "озадачён,"
    "разозлён,разозлёна,разозлённый,"
    "рождён,рождёна,рождённый,"
    "произведён,произведёна,"
    "введён,введёна,"
    "возведён,возведёна,"
    "проведён,проведёна,"
    "осуждён,осуждёна,осуждённый,"
    "обречён,обречёна,обречённый,"
    "вооружён,вооружёна,вооружённый,"
    "окружён,окружёна,окружённый,"
    "заключён,заключёна,заключённый,"
    "включён,включёна,включённый,"
    "облечён,"
    "обожжён,"
    "напряжён,напряжёна,напряжённый,напряжённо,"
    "увлечён,увлечёна,увлечённый,увлечённо,"
    "извлечён,"
    "отвлечён,отвлечёна,отвлечённый,отвлечённо,"
    "определён,определёна,определённый,определённо,"
    "совершён,совершёна,совершённый,совершённо,"
    "лишён,лишёна,лишённый,"
    "разрешён,разрешёна,разрешённый,"
    "обращён,обращёна,обращённый,"
    "освещён,освещёна,освещённый,"
    "размещён,размещёна,размещённый,"
    "посвящён,посвящёна,посвящённый,"
    "отражён,отражёна,отражённый,"
    "сражён,сражёна,сражённый,"
    "снабжён,снабжёна,снабжённый,"
    "погружён,погружёна,погружённый,"
    "заражён,заражёна,заражённый,"
    "покорён,покорёна,покорённый,"
    "ожёг,ожёгся,"
    # Nouns continued.
    "шёлковый,шёлковая,"
    "чёткий,чёткая,чёткое,чёткие,чётко,"
    "нёбо,"
    "вёрстка,"
    "жёрдочка,"
    "серьёзный,серьёзная,серьёзное,серьёзные,серьёзно,"
    "манёвренный,"
    "трёхэтажный,трёхлетний,трёхмерный,"
    "четырёхэтажный,четырёхлетний,четырёхмерный,"
    "трёх,четырёх,"
    "самолёт,самолёта,самолёты,самолётов,"
    "вертолёт,вертолёта,"
    "полёт,полёта,полёты,"
    "взлёт,взлёта,"
    "отлёт,"
    "налёт,налёта,"
    "залёт,"
    "перелёт,перелёта,"
    "влёт,"
    "излёт,"
    "разлёт,"
    "слёзы,слёз,слёзка,слёзки,"
    "гнёт,"
    "знамёна,"
    "имён,"
    "племён,"
    "семён,"
    "стёкла,стёклышко,"
    "зёрна,зёрен,зёрнышко,"
    "вёсел,"
    "сёстры,сёстрам,сестёр,"
    "свёкла,свёклы,"
    "плёнка,плёнки,плёнок,"
    "ёмкий,ёмкая,ёмкое,"
    "клёв,"
    "побоёв,"
    "боёв,"
    "героёв,"
    "злодёёв,"
    # Time/calendar.
    # Common words in literature.
    "вдвоём,втроём,вчетвером,"
    "ребром,"
    "верёвка,верёвки,верёвку,верёвкой,"
    "одёжка,"
    "подёрнутый,"
    "обёрнутый,"
    "завёрнутый,"
    "перевёрнутый,"
    "свёрнутый,"
    "свёрток,свёртка,"
    "манёвренность,"
    "гравёр,"
    "боёк,"
    "полотёр,"
    "метёлка,"
    "позёмка,"
    "жёнка,"
    "бурёнка,"
    "гнёздышко,"
    "телёночек,"
    "жеребёночек,"
    "козлёночек,"
    "ребёночек,"
    "цыплёнок,"
    "утёнок,"
    "гусёнок,"
    "слонёнок,"
    "мышонёк,"
    "волчёнок,"
    "медвежёнок,"
    "поросёнок,"
    "лисёнок,"
    "зайчёнок,"
    "совёнок,"
    "орлёнок,"
    "журавлёнок,"
    "ястребёнок,"
    "змеёныш,"
)

_WORD_BOUNDARY = re.compile(r"[а-яёА-ЯЁ]+", re.IGNORECASE)
_WORD_WITH_OFFSETS = re.compile(r"[а-яёА-ЯЁ]+", re.IGNORECASE)
_VSE_RE = re.compile(r"\b([Вв]се|ВСЕ)\b")

_PEYO_WARNED = False


@dataclass(frozen=True)
class YoSuggestion:
    """A non-applied ё suggestion that should be reviewed by a user."""

    before: str
    after: str
    index: int
    line: int = 1
    column: int = 1


def _build_dict() -> dict[str, str]:
    """Build the replacement dictionary from the word list."""
    result: dict[str, str] = {}
    for token in _YO_WORDS.split(","):
        word = token.strip()
        if not word:
            continue
        key = word.replace("ё", "е").replace("Ё", "Е")
        if key != word:
            result[key] = word
            cap_key = key[0].upper() + key[1:]
            cap_val = word[0].upper() + word[1:]
            result[cap_key] = cap_val
            result[key.upper()] = word.upper()
    return result


_YO_DICT = _build_dict()


def _warn_peyo_unavailable(exc: Exception) -> None:
    """Log peyo import/runtime failures once."""
    global _PEYO_WARNED
    if not _PEYO_WARNED:
        logger.info("peyo unavailable, falling back to built-in ё dictionary: %s", exc)
        _PEYO_WARNED = True


def _peyo_yoify(text: str, mode: str) -> str | None:
    """Run peyo yoification if available."""
    try:
        import peyo
    except ImportError as exc:
        _warn_peyo_unavailable(exc)
        return None

    try:
        return peyo.yoify(text, mode=mode)
    except Exception as exc:  # pragma: no cover - defensive against dependency changes
        _warn_peyo_unavailable(exc)
        return None


def _peyo_lint(text: str, mode: str) -> list[dict]:
    """Return peyo lint suggestions, or an empty list when unavailable."""
    try:
        import peyo
    except ImportError as exc:
        _warn_peyo_unavailable(exc)
        return []

    try:
        suggestions = peyo.lint(text, mode=mode, group_by_words=False)
    except Exception as exc:  # pragma: no cover - defensive against dependency changes
        _warn_peyo_unavailable(exc)
        return []
    return suggestions if isinstance(suggestions, list) else []


def _apply_builtin_dictionary(text: str) -> str:
    """Apply the local ё dictionary as a fallback/supplement."""

    def _replace(match: re.Match) -> str:
        word = match.group(0)
        # peyo safe mode intentionally avoids this high-frequency ambiguity.
        if word.lower() == "все":
            return word
        replacement = _YO_DICT.get(word)
        if replacement:
            return replacement
        return word

    return _WORD_BOUNDARY.sub(_replace, text)


def _word_around(text: str, index: int, *, before: bool) -> str:
    """Find the neighboring Cyrillic word around a character index."""
    if before:
        result = ""
        for match in _WORD_WITH_OFFSETS.finditer(text, 0, index):
            result = match.group(0)
        return result

    match = _WORD_WITH_OFFSETS.search(text, index)
    return match.group(0) if match else ""


def _preserve_vse_case(original: str) -> str:
    """Return всё with the same simple casing pattern as все."""
    if original.isupper():
        return "ВСЁ"
    if original[0].isupper():
        return "Всё"
    return "всё"


def _apply_contextual_vse_rules(text: str) -> str:
    """
    Conservatively resolve a few common все/всё contexts.

    pymorphy3 is used as a guard: when the next word is a likely plural head,
    the token is kept as ``все``.
    """
    phrase_after = {"равно", "еще", "ещё", "же", "таки"}
    phrase_before = {"это", "этим", "этого", "этом", "и"}
    neuter_or_impersonal_after = {
        "было", "будет", "стало", "становилось", "кончено", "закончилось",
        "хорошо", "тихо", "ясно", "понятно",
    }

    def _replace(match: re.Match[str]) -> str:
        original = match.group(1)
        next_word = _word_around(text, match.end(), before=False).lower()
        prev_word = _word_around(text, match.start(), before=True).lower()

        if next_word and is_likely_plural_head(next_word):
            return original

        if next_word in phrase_after or prev_word in phrase_before:
            return _preserve_vse_case(original)

        if next_word in neuter_or_impersonal_after:
            return _preserve_vse_case(original)

        after = text[match.end():match.end() + 2]
        if prev_word in {"это", "и"} and (not next_word or re.match(r"^[\s,.!?;:]", after)):
            return _preserve_vse_case(original)

        return original

    return _VSE_RE.sub(_replace, text)


def yoficate_text(text: str, mode: str = "safe") -> str:
    """Restore Russian ё with peyo safe mode and conservative local fallbacks.

    peyo is dictionary-based and runs in ``safe`` mode by default. If peyo is
    not installed, the previous built-in dictionary is used. Ambiguous peyo
    ``not_safe`` suggestions are not applied here; they are exposed via
    :func:`collect_yo_suggestions` for user review.
    """
    if not text:
        return text

    result = _peyo_yoify(text, mode=mode)
    if result is None:
        result = _apply_builtin_dictionary(text)
    elif mode == "safe":
        result = _apply_builtin_dictionary(result)

    if mode == "safe":
        result = _apply_contextual_vse_rules(result)

    return result


def collect_yo_suggestions(text: str) -> list[YoSuggestion]:
    """Collect peyo not_safe suggestions without modifying text."""
    suggestions: list[YoSuggestion] = []
    for item in _peyo_lint(text, mode="not_safe"):
        before = str(item.get("before") or "")
        after = str(item.get("after") or "")
        if not before or not after or before == after:
            continue

        positions = item.get("position")
        if not isinstance(positions, list) or not positions:
            index = text.find(before)
            if index < 0:
                continue
            suggestions.append(YoSuggestion(before=before, after=after, index=index))
            continue

        for pos in positions:
            if not isinstance(pos, dict):
                continue
            try:
                index = int(pos.get("index", -1))
                line = int(pos.get("line", 1))
                column = int(pos.get("column", 1))
            except (TypeError, ValueError):
                continue
            if index < 0:
                continue
            suggestions.append(
                YoSuggestion(
                    before=before,
                    after=after,
                    index=index,
                    line=line,
                    column=column,
                )
            )

    return suggestions
