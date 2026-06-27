# Git Workflow

- On Windows, do not use Windows `git`; use WSL `git` if git commands are needed.
- After completing any requested file change, commit the coherent completed change by default unless the user explicitly says not to commit.
- Commit intermediate results after each coherent, working chunk of changes.
- Keep intermediate commits focused: include only files related to the completed chunk.
- Do not include unrelated user changes in intermediate commits.
- Before each commit, review `git status --short` and the staged diff.
- Use clear commit messages that describe the completed step.
