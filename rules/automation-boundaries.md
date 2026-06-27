# Automation Boundaries

- Automation should not drive the UI from inside the application.
- Business workflows belong in services or workflow layers that GUI, CLI, resume, and tests can call consistently.
- GUI pages should start workflows, provide inputs, and display structured state; they should not own core business decisions.
- Avoid auto pipelines that call private page methods to perform production logic.
- If UI-only behavior must be reused, extract the reusable logic before automating it.
