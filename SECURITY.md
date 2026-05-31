# Security Policy

Investment Research OS is a local-first research and portfolio analysis project. It may integrate with broker APIs, market data providers, research report sources, and local RAG storage, so security reviews focus on preventing accidental exposure of private financial data and credentials.

## Supported Scope

Security fixes are accepted for the current `main` branch. The active local application is the FastAPI backend plus Classic Research Console described in `README.md`.

## Sensitive Data Rules

Do not commit or paste the following values into issues, pull requests, screenshots, or chat transcripts:

- API keys, app keys, app secrets, access tokens, refresh tokens, or broker credentials
- Raw account numbers, unmasked brokerage account labels, or personal identity data
- Local `.env` files, token cache JSON files, SQLite databases, or `research_vault` contents
- Private report PDFs, copyrighted full-text report bodies, or paid/login-only source material

The repository intentionally tracks only `.env.example` files. Real secrets belong in ignored local files such as `backend/.env` or ignored token cache paths under `research_vault/_system`.

## Reporting a Vulnerability

If you find a vulnerability, open a private security advisory on GitHub if available, or contact the maintainer by email from the GitHub profile. Include:

- A concise description of the issue
- Affected file, endpoint, or workflow
- Reproduction steps using dummy data only
- Whether credentials, account data, local files, or RAG content could be exposed

Please do not include live credentials, account screenshots, raw token values, or private portfolio data in the report.

## Maintainer Checklist

Before publishing changes, run:

```powershell
python tools\check_public_repo_safety.py
python tools\check_offline_readiness.py
python tools\check_backend_runtime_env.py --strict
```

If a check reports tracked secrets or private data paths, remove the files from Git tracking before pushing.
