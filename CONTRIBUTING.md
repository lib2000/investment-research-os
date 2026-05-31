# Contributing

Thank you for considering a contribution to Investment Research OS. The project is currently maintained as a local-first research assistant with strong safeguards around private portfolio data, broker credentials, and copyrighted source material.

## Development Rules

- Work from `C:\Users\lib20\InvestmentJournalApp` on the maintainer machine. Do not use OneDrive as the project root.
- Do not commit `.env`, `research_vault`, local databases, token files, downloaded private reports, or screenshots containing account data.
- Keep user-facing status and error messages in Korean where they are part of the app UI.
- Prefer small, validated changes over broad rewrites.
- Preserve the Classic Research Console while React migration work remains in progress.

## Useful Checks

```powershell
python tools\check_public_repo_safety.py
python tools\check_offline_readiness.py
python tools\check_backend_module_health.py --strict
python tools\check_console_static_contract.py --strict
python tools\check_daily_recommendations_store.py --require-milestones --require-quality
```

For actual browser verification, run browser smoke checks from Windows PowerShell because WSL/Codex sandboxing can block localhost DevTools ports:

```powershell
python tools\smoke_research_console_clicks.py --only-system-check
```

## Pull Request Notes

A useful pull request should include:

- What changed and why
- Which scripts or tests were run
- Whether the change touches data ingestion, RAG indexing, portfolio storage, broker integration, or security-sensitive paths
- Any manual browser checks performed

Use dummy data in tests and examples. Never attach real portfolio exports, account pages, API credentials, or paid report content.
