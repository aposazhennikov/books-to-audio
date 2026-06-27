---
name: code-review-reception
description: Use when receiving review feedback, external suggestions, or audit findings. Helps Codex verify suggestions against this repository before implementing them.
---

# Code Review Reception

Adapted for Codex from Obra Superpowers `receiving-code-review`.

## Process

1. Read the complete feedback before changing files.
2. Restate the technical requirement internally or ask if scope is unclear.
3. Verify the suggestion against this codebase, current diff, tests, platform needs, and project rules.
4. Implement one coherent item at a time.
5. Run the narrowest relevant verification for each coherent chunk.
6. Report what changed and what remains.

## Push Back When Needed

Do not blindly apply external feedback if it:

- Breaks existing behavior.
- Conflicts with project rules or user decisions.
- Adds unused features.
- Assumes a different stack, platform, or deployment model.
- Cannot be verified from available context.

When unsure, ask a focused question or state the uncertainty with evidence.

## Tone

Avoid performative agreement. Prefer technical action:

- "Verified the issue in `X`; fixed it in `Y`."
- "I checked this suggestion and it would break Windows install flow because `Z`."
- "I need clarification on item 4 before editing because it changes the data model."
