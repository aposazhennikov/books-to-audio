# Git Workflow

- On Windows, prefer WSL `git` when git commands are needed.
- If ordinary WSL `git` cannot operate on a Codex-created worktree because `.git` points to Windows paths, first use WSL `git` with explicit `--git-dir` and `--work-tree` paths.
- Use the Codex bundled git or another available git only if the explicit WSL `--git-dir` / `--work-tree` fallback still fails, and report the fallback reason.
- After completing any requested file change, commit the coherent completed change by default unless the user explicitly says not to commit.
- Commit intermediate results after each coherent, working chunk of changes.
- If working in a Codex-created git worktree, merge the completed work back into the main repository branch before finishing, then push the unified branch unless the user explicitly says not to merge or push.
- Do not merge or push worktree changes until verification passes, conflicts are resolved, and the final branch contains only intended changes.
- Keep intermediate commits focused: include only files related to the completed chunk.
- Do not include unrelated user changes in intermediate commits.
- Before each commit, review `git status --short` and the staged diff with the same git executable that will create the commit.
- Use clear commit messages that describe the completed step.
