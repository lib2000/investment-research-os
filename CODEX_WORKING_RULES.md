# Codex Working Rules

- Do not modify, run servers from, or write generated files under any OneDrive path.
- The active project root is `C:\Users\lib20\InvestmentJournalApp`.
- Before changing files or starting backend/frontend servers, verify the working directory is under the active project root.
- OneDrive paths may be read only when the user explicitly asks for safe migration, and must never be edited.
- Use `tools\assert_project_root.ps1` before project scripts or manual server startup.
- Use `tools\list_cleanup_candidates.ps1` to inspect cleanup candidates before deleting temporary folders.
