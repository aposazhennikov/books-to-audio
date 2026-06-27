"""PDF text layout repair helpers."""

from __future__ import annotations

import re

from book_normalizer.chaptering.patterns import match_chapter_heading, match_work_heading


def _repair_isolated_layout_word_blocks(blocks: list[str]) -> list[str]:
    """Remove or reflow words that PDF extraction split out of one visual line."""

    result: list[str] = []
    index = 0
    while index < len(blocks):
        block = blocks[index]
        stripped = block.strip()
        if not _is_isolated_layout_word_block(stripped):
            result.append(block)
            index += 1
            continue

        words: list[str] = []
        run_start = index
        while index < len(blocks) and _is_isolated_layout_word_block(blocks[index].strip()):
            words.append(blocks[index].strip())
            index += 1

        if result and _try_reflow_isolated_words_into_previous(result, words):
            continue

        next_block = blocks[index].strip() if index < len(blocks) else ""
        if result and next_block and _try_reflow_isolated_words_between_blocks(result, words, blocks, index):
            continue

        previous = result[-1].strip() if result else ""
        if _should_drop_isolated_layout_word_run(words, previous=previous, next_block=next_block):
            continue

        result.extend(blocks[run_start:index])
    return result


def _is_isolated_layout_word_block(text: str) -> bool:
    if not text or "\n" in text:
        return False
    return bool(re.fullmatch(r"\(?[А-ЯЁа-яё]{1,14}", text.strip()))


def _try_reflow_isolated_words_into_previous(previous_blocks: list[str], words: list[str]) -> bool:
    previous = previous_blocks[-1]
    joined = " ".join(words)
    final_parenthetical_matches = list(
        re.finditer(
            r"\((?P<head>[А-ЯЁа-яё]{1,20})\s+"
            r"(?P<tail>[А-ЯЁа-яё]{1,20})(?P<close>\)[.!?…]?)",
            previous,
        )
    )
    final_parenthetical = final_parenthetical_matches[-1] if final_parenthetical_matches else None
    if final_parenthetical and all(not word.startswith("(") for word in words):
        replacement = (
            f"({final_parenthetical.group('head')} {joined} "
            f"{final_parenthetical.group('tail')}{final_parenthetical.group('close')}"
        )
        previous_blocks[-1] = (
            previous[: final_parenthetical.start()]
            + replacement
            + previous[final_parenthetical.end():]
        )
        return True

    if any(word.startswith("(") for word in words):
        phrase = " ".join(word.strip() for word in words)
        gap = re.search(
            r"\b(?P<anchor>[А-ЯЁа-яё]{2,20})\s+(?P<trailer>[А-ЯЁа-яё]{2,20}\)\))",
            previous,
        )
        if gap:
            replacement = f"{gap.group('anchor')} {phrase} {gap.group('trailer')}"
            previous_blocks[-1] = previous[: gap.start()] + replacement + previous[gap.end():]
            return True
    return False


def _try_reflow_isolated_words_between_blocks(
    previous_blocks: list[str],
    words: list[str],
    blocks: list[str],
    next_index: int,
) -> bool:
    previous = previous_blocks[-1]
    next_block = blocks[next_index]
    if any(word.startswith("(") for word in words):
        return False

    previous_match = re.search(r"\((?P<head>[А-ЯЁа-яё]{1,20})\s*$", previous)
    next_match = re.match(
        r"\s*(?P<tail>[А-ЯЁа-яё]{1,20})(?P<close>\)[.!?…]?)(?P<rest>.*)$",
        next_block,
        re.DOTALL,
    )
    if not previous_match or not next_match:
        return False

    joined = " ".join(words)
    rest = next_match.group("rest").lstrip()
    previous_blocks[-1] = (
        previous[: previous_match.start()]
        + f"({previous_match.group('head')} {joined} "
        + f"{next_match.group('tail')}{next_match.group('close')}"
        + (f" {rest}" if rest else "")
    )
    blocks[next_index] = ""
    return True


def _should_drop_isolated_layout_word_run(
    words: list[str],
    *,
    previous: str,
    next_block: str,
) -> bool:
    joined = " ".join(word.strip(" ,.;:!?") for word in words).strip()
    if match_chapter_heading(joined) or match_work_heading(joined):
        return False
    if len(words) < 2:
        return False
    if not previous or not next_block:
        return False
    if len(words) >= 3:
        return True
    return bool(re.search(r"[.!?…]\s*$", previous) and next_block[:1].isupper())

