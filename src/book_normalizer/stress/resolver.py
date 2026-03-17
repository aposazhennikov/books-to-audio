"""Interactive stress resolver for unknown/ambiguous words."""

from __future__ import annotations

import logging

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from book_normalizer.models.book import Book, Paragraph
from book_normalizer.stress.annotator import AnnotationResult
from book_normalizer.stress.dictionary import (
    COMBINING_ACUTE,
    VOWELS,
    StressDictionary,
    apply_stress,
    count_vowels,
    is_russian_word,
)

logger = logging.getLogger(__name__)


def _find_context_for_word(book: Book, word: str, max_contexts: int = 2) -> list[str]:
    """Find example sentence-level contexts where a word appears in the book."""
    contexts: list[str] = []
    target = word.lower()
    sentence_separators = ".!?"

    for chapter in book.chapters:
        for para in chapter.paragraphs:
            text = para.normalized_text or para.raw_text
            lower_text = text.lower()
            idx = lower_text.find(target)
            if idx < 0:
                continue

            # Expand to sentence boundaries.
            start = idx
            while start > 0 and text[start] not in sentence_separators and text[start] != "\n":
                start -= 1
            if start < len(text) and text[start] in sentence_separators:
                start += 1

            end = idx + len(word)
            while end < len(text) and text[end] not in sentence_separators and text[end] != "\n":
                end += 1
            if end < len(text):
                end += 1

            sentence = text[start:end].strip()
            # Include small prefix/suffix from paragraph for additional context.
            prefix_start = max(0, start - 40)
            suffix_end = min(len(text), end + 40)
            prefix = text[prefix_start:start].strip()
            suffix = text[end:suffix_end].strip()

            full_context_parts: list[str] = []
            if prefix:
                full_context_parts.append("..." + prefix)
            full_context_parts.append(sentence)
            if suffix:
                full_context_parts.append(suffix + "...")

            contexts.append(" ".join(full_context_parts))
            if len(contexts) >= max_contexts:
                return contexts

    return contexts


class StressResolver:
    """
    Interactive TUI for resolving stress on unknown words.

    Presents each unknown word with context, shows numbered
    vowel options, and lets the user pick stress placement
    or enter a custom stressed form.
    """

    def __init__(
        self,
        dictionary: StressDictionary,
        console: Console | None = None,
    ) -> None:
        self._dict = dictionary
        self._console = console or Console()

    def resolve(
        self,
        book: Book,
        annotation_result: AnnotationResult,
    ) -> int:
        """
        Interactively resolve stress for all unknown words.

        Returns the number of words resolved.
        """
        unknown = sorted(annotation_result.unknown_word_set)
        if not unknown:
            self._console.print("[green]No unknown words to resolve.[/green]")
            return 0

        self._console.print()
        self._console.rule("[bold]Stress Resolution[/bold]")
        self._console.print(f"  Unknown words: {len(unknown)}")
        self._console.print()

        resolved_count = 0

        for idx, word in enumerate(unknown, 1):
            self._console.print(f"[dim]Word {idx}/{len(unknown)}[/dim]")

            contexts = _find_context_for_word(book, word)
            stressed = self._prompt_for_word(word, contexts)

            if stressed is None:
                self._console.print("[yellow]Quit stress review. Progress saved.[/yellow]")
                break

            if stressed:
                # Store decision together with compact context for future disambiguation.
                context_hint = " | ".join(contexts[:2]) if contexts else ""
                self._dict.add_user_entry(word, stressed, confirmed=True, context_hint=context_hint)
                resolved_count += 1
                self._console.print(f"[green]Saved: {word} -> {stressed}[/green]")
            else:
                self._console.print("[dim]Skipped.[/dim]")

        self._update_book_segments(book)
        book.add_audit("stress", "resolve", f"resolved={resolved_count}")
        return resolved_count

    def _prompt_for_word(self, word: str, contexts: list[str]) -> str | None:
        """
        Show a word and prompt for stress placement.

        Returns:
        - stressed form string if user resolved it.
        - empty string if user skipped.
        - None if user wants to quit.
        """
        header = Text()
        header.append(word, style="bold cyan")
        header.append(f"  ({count_vowels(word)} vowels)", style="dim")

        self._console.print(Panel(header, title="Word", border_style="cyan"))

        if contexts:
            for ctx in contexts:
                self._console.print(f"  [dim]{ctx}[/dim]")

        vowel_positions = self._show_vowel_options(word)

        self._console.print(
            "  Enter [bold]number[/bold] for vowel position, "
            "[bold]c[/bold] for custom, "
            "[bold]s[/bold] to skip, "
            "[bold]q[/bold] to quit"
        )

        while True:
            choice = self._console.input("[bold]> [/bold]").strip().lower()

            if choice == "q":
                return None
            if choice == "s":
                return ""
            if choice == "c":
                return self._custom_input(word)

            try:
                num = int(choice)
                if 1 <= num <= len(vowel_positions):
                    return apply_stress(word, num - 1)
                self._console.print(f"[red]Pick 1-{len(vowel_positions)}.[/red]")
            except ValueError:
                self._console.print("[red]Invalid input.[/red]")

    def _show_vowel_options(self, word: str) -> list[int]:
        """Display numbered vowel options for stress placement."""
        vowel_positions: list[int] = []
        display = Text()

        vi = 0
        for i, ch in enumerate(word):
            if ch in VOWELS:
                vi += 1
                vowel_positions.append(i)
                display.append(f"[{vi}]{ch}", style="bold yellow")
            else:
                display.append(ch)

        self._console.print(f"  Vowels: ", end="")
        self._console.print(display)
        return vowel_positions

    def _custom_input(self, word: str) -> str:
        """Let user type a custom stressed form."""
        self._console.print(
            f"  Type stressed form (use ' after stressed vowel, "
            f"e.g. моло'ко for молоко{COMBINING_ACUTE}):"
        )
        raw = self._console.input("  [bold]> [/bold]").strip()

        if not raw:
            return ""

        if "'" in raw:
            return self._convert_apostrophe_to_acute(raw)

        if COMBINING_ACUTE in raw:
            return raw

        return raw

    @staticmethod
    def _convert_apostrophe_to_acute(text: str) -> str:
        """Convert apostrophe-based stress notation to combining acute."""
        result: list[str] = []
        i = 0
        while i < len(text):
            if text[i] == "'" and result and result[-1] in VOWELS:
                result.append(COMBINING_ACUTE)
            else:
                result.append(text[i])
            i += 1
        return "".join(result)

    def _update_book_segments(self, book: Book) -> None:
        """
        Re-resolve stress for segments that were previously unknown.

        Called after interactive session so newly learned words
        get their stress_form populated.
        """
        updated = 0
        for chapter in book.chapters:
            for para in chapter.paragraphs:
                for seg in para.segments:
                    if seg.text and not seg.stress_form and is_russian_word(seg.text):
                        if count_vowels(seg.text) > 1:
                            stressed = self._dict.lookup(seg.text)
                            if stressed:
                                seg.stress_form = stressed
                                updated += 1

        if updated:
            logger.info("Updated %d segments with newly resolved stress.", updated)
