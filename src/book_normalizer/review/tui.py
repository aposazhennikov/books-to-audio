"""Interactive terminal UI for reviewing detected issues."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from book_normalizer.memory.correction_store import CorrectionStore
from book_normalizer.memory.punctuation_store import PunctuationStore
from book_normalizer.models.memory import CorrectionMemoryEntry, PunctuationMemoryEntry
from book_normalizer.models.review import (
    IssueType,
    ReviewAction,
    ReviewDecision,
    ReviewIssue,
)
from book_normalizer.review.session import ReviewSession

logger = logging.getLogger(__name__)

_SEVERITY_COLORS = {
    "low": "yellow",
    "medium": "dark_orange",
    "high": "red",
    "critical": "bold red",
}


class InteractiveReviewer:
    """
    Rich-based TUI for reviewing issues one by one.

    Presents each issue with context, offers action choices,
    records decisions, and persists them to memory stores.
    """

    def __init__(
        self,
        correction_store: CorrectionStore | None = None,
        punctuation_store: PunctuationStore | None = None,
        console: Console | None = None,
    ) -> None:
        self._correction_store = correction_store
        self._punctuation_store = punctuation_store
        self._console = console or Console()

    def run(self, session: ReviewSession) -> ReviewSession:
        """
        Run the interactive review loop.

        Returns the session with all decisions recorded.
        The caller is responsible for saving the session.
        """
        self._console.print()
        self._console.rule("[bold]Interactive Review Session[/bold]")
        self._console.print(
            f"  Total issues: {session.total_issues}  |  "
            f"Resolved: {session.resolved_count}  |  "
            f"Pending: {session.pending_count}"
        )
        self._console.print()

        while True:
            issue = session.get_current_issue()
            if issue is None:
                self._console.print("[green]All issues have been reviewed.[/green]")
                session.completed = True
                break

            self._display_issue(issue, session)
            action = self._prompt_action()

            if action == "q":
                self._console.print("[yellow]Session saved. You can resume later.[/yellow]")
                break
            elif action == "a":
                self._accept(session, issue)
            elif action == "k":
                self._keep_original(session, issue)
            elif action == "e":
                self._edit_manually(session, issue)
            elif action == "s":
                session.skip_current()
                self._console.print("[dim]Skipped.[/dim]")

        return session

    def _display_issue(self, issue: ReviewIssue, session: ReviewSession) -> None:
        """Display a single issue with context and suggestion."""
        idx = session.pending_issues.index(issue) + 1 if issue in session.pending_issues else 0
        total_pending = session.pending_count
        severity_color = _SEVERITY_COLORS.get(issue.severity.value, "white")

        header = Text()
        header.append(f"Issue {idx}/{total_pending}", style="bold")
        header.append("  |  ", style="dim")
        header.append(f"Type: {issue.issue_type.value}", style="cyan")
        header.append("  |  ", style="dim")
        header.append(f"Severity: {issue.severity.value}", style=severity_color)
        header.append("  |  ", style="dim")
        header.append(f"Confidence: {issue.confidence:.0%}", style="blue")

        self._console.print()
        self._console.print(header)

        context = Text()
        if issue.context_before:
            context.append(issue.context_before, style="dim")
        context.append(issue.original_fragment, style="bold red underline")
        if issue.context_after:
            context.append(issue.context_after, style="dim")

        self._console.print(Panel(context, title="Context", border_style="blue"))

        if issue.suggested_fragment:
            suggestion = Text()
            if issue.context_before:
                suggestion.append(issue.context_before, style="dim")
            suggestion.append(issue.suggested_fragment, style="bold green")
            if issue.context_after:
                suggestion.append(issue.context_after, style="dim")
            self._console.print(Panel(suggestion, title="Suggestion", border_style="green"))

    def _prompt_action(self) -> str:
        """Prompt user for an action choice."""
        self._console.print(
            "  [bold][a][/bold] accept  "
            "[bold][k][/bold] keep original  "
            "[bold][e][/bold] edit  "
            "[bold][s][/bold] skip  "
            "[bold][q][/bold] quit & save"
        )
        while True:
            choice = self._console.input("[bold]> [/bold]").strip().lower()
            if choice in ("a", "k", "e", "s", "q"):
                return choice
            self._console.print("[red]Invalid choice. Use a/k/e/s/q.[/red]")

    def _accept(self, session: ReviewSession, issue: ReviewIssue) -> None:
        """Accept the suggested fix."""
        final = issue.suggested_fragment or issue.original_fragment
        decision = ReviewDecision(
            issue_id=issue.id,
            action=ReviewAction.ACCEPT,
            original_fragment=issue.original_fragment,
            final_fragment=final,
        )
        session.record_decision(decision)
        self._persist_to_memory(issue, decision)
        self._console.print(f"[green]Accepted: {issue.original_fragment!r} -> {final!r}[/green]")

    def _keep_original(self, session: ReviewSession, issue: ReviewIssue) -> None:
        """Keep the original text as-is."""
        decision = ReviewDecision(
            issue_id=issue.id,
            action=ReviewAction.KEEP_ORIGINAL,
            original_fragment=issue.original_fragment,
            final_fragment=issue.original_fragment,
        )
        session.record_decision(decision)
        self._persist_to_memory(issue, decision)
        self._console.print("[yellow]Kept original.[/yellow]")

    def _edit_manually(self, session: ReviewSession, issue: ReviewIssue) -> None:
        """Let the user enter a custom replacement."""
        self._console.print(f"  Original: [red]{issue.original_fragment!r}[/red]")
        custom = self._console.input("  Enter replacement: ").strip()

        if not custom:
            self._console.print("[yellow]Empty input, skipping.[/yellow]")
            session.skip_current()
            return

        decision = ReviewDecision(
            issue_id=issue.id,
            action=ReviewAction.CUSTOM,
            original_fragment=issue.original_fragment,
            final_fragment=custom,
        )
        session.record_decision(decision)
        self._persist_to_memory(issue, decision)
        self._console.print(f"[green]Custom: {issue.original_fragment!r} -> {custom!r}[/green]")

    def _persist_to_memory(self, issue: ReviewIssue, decision: ReviewDecision) -> None:
        """Save the decision to the appropriate memory store."""
        now = datetime.now(timezone.utc)

        if issue.issue_type == IssueType.PUNCTUATION and self._punctuation_store:
            self._punctuation_store.add(
                PunctuationMemoryEntry(
                    original=decision.original_fragment,
                    replacement=decision.final_fragment,
                    confirmed=True,
                    updated_at=now,
                )
            )

        if issue.issue_type in (
            IssueType.OCR_ARTIFACT,
            IssueType.SPELLING,
            IssueType.YOFICATION,
        ) and self._correction_store:
            token = decision.original_fragment.strip()
            normalized_token = token.lower()
            auto_apply_safe = _should_mark_auto_apply_safe(issue, token)

            self._correction_store.add(
                CorrectionMemoryEntry(
                    original=decision.original_fragment,
                    replacement=decision.final_fragment,
                    context_hint=_build_context_hint(issue),
                    confirmed=True,
                    issue_type=issue.issue_type.value,
                    token=token,
                    normalized_token=normalized_token,
                    auto_apply_safe=auto_apply_safe,
                    updated_at=now,
                )
            )


_CYRILLIC_RE = re.compile(r"[а-яёА-ЯЁ]")


def _build_context_hint(issue: ReviewIssue, window: int = 20) -> str:
    """Build a compact context hint around the original fragment."""
    before = issue.context_before[-window:] if issue.context_before else ""
    after = issue.context_after[:window] if issue.context_after else ""
    return f"{before}|{after}" if before or after else ""


def _looks_numeric_like(token: str) -> bool:
    """Return True if token looks like a number, date component, or list index."""
    s = token.strip()
    if not s:
        return False
    if re.fullmatch(r"[0-9]+([.:][0-9]+)*", s):
        return True
    return False


def _looks_cyrillic_with_digit(token: str) -> bool:
    """Return True if token is a Cyrillic word containing embedded digits."""
    if not token:
        return False
    has_digit = any(ch.isdigit() for ch in token)
    has_cyrillic = bool(_CYRILLIC_RE.search(token))
    if not (has_digit and has_cyrillic):
        return False
    stripped = token.replace("-", "")
    if not stripped:
        return False
    for ch in stripped:
        if not (ch.isdigit() or _CYRILLIC_RE.match(ch)):
            return False
    return len(stripped) >= 3


def _should_mark_auto_apply_safe(issue: ReviewIssue, token: str) -> bool:
    """
    Decide whether a correction should be marked safe for auto-apply.

    Detection (issue creation) and auto-apply safety are separate:
    here we are intentionally stricter than in the detector.
    """
    token = token.strip()
    if not token:
        return False
    # Very short fragments are never auto-safe.
    if len(token) <= 1:
        return False
    # Numeric-like tokens (years, dates, list indices) are never auto-safe.
    if _looks_numeric_like(token):
        return False
    if issue.issue_type != IssueType.OCR_ARTIFACT:
        return False

    # Stricter OCR auto-safe rules:
    # - must be a Cyrillic+digit word (already enforced by looks_cyrillic_with_digit).
    # - first and last characters must be Cyrillic letters.
    # - limited number of digits, no long digit runs.
    if not _looks_cyrillic_with_digit(token):
        return False

    first, last = token[0], token[-1]
    if not (_CYRILLIC_RE.match(first) and _CYRILLIC_RE.match(last)):
        # E.g. "0тдельный" or "молок0" should not be auto-safe.
        return False

    digits = sum(1 for ch in token if ch.isdigit())
    if digits == 0:
        return False
    # Do not auto-apply when there are many digits.
    if digits > 2:
        return False
    # No long digit runs.
    max_run = 0
    current = 0
    for ch in token:
        if ch.isdigit():
            current += 1
            max_run = max(max_run, current)
        else:
            current = 0
    if max_run > 1:
        return False

    # Uppercase-only tokens are likely codes/abbreviations.
    core_letters = [ch for ch in token if _CYRILLIC_RE.match(ch)]
    if core_letters and all(ch.isupper() for ch in core_letters):
        return False

    return True
