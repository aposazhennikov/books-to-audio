"""Interactive terminal UI for reviewing detected issues."""

from __future__ import annotations

import logging
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

        if issue.issue_type in (IssueType.OCR_ARTIFACT, IssueType.SPELLING) and self._correction_store:
            self._correction_store.add(
                CorrectionMemoryEntry(
                    original=decision.original_fragment,
                    replacement=decision.final_fragment,
                    confirmed=True,
                    updated_at=now,
                )
            )
