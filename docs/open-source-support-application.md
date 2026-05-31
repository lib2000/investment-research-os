# Codex Open Source Support Application Notes

This document keeps the public, non-sensitive text prepared for the Codex open-source support application. Do not add OpenAI organization IDs, private emails beyond the submitted account email, API keys, broker credentials, or personal portfolio data.

## Repository

- GitHub user: `lib2000`
- Repository: `https://github.com/lib2000/investment-research-os`
- Maintainer: HYUNGJU LEE
- Role: primary maintainer and lead developer

## Role Description

I am the primary maintainer and lead developer of this repository. I design the architecture, implement backend and frontend features, maintain data ingestion workflows, review and organize issues, manage releases, and operate the project’s quality checks, documentation, and automation scripts.

## Why This Repository Fits

Investment Research OS is an actively maintained open-source research and portfolio analysis system that combines market data ingestion, filings monitoring, research report indexing, RAG-based retrieval, portfolio quality checks, daily recommendation tracking, and operational validation tools. The project focuses on improving investor research workflows with transparent data quality checks, Korean-language UX, and reproducible local automation.

## API Credit Plan

I plan to use API credits to improve maintainability and automation for the project: summarizing and classifying research documents, generating structured metadata, validating RAG indexing quality, assisting issue triage, producing Korean-language operational reports, and testing recommendation explanations. Credits will be used for development, QA automation, and maintainer workflows rather than private user data resale or unrelated commercial use.

## Codex Security Need

The project integrates portfolio data, broker APIs, research ingestion, RAG indexing, and local automation, so security review is important. Codex Security would help identify risks in secret handling, authentication boundaries, dependency usage, data storage, prompt/RAG injection, and accidental exposure of financial information before the project is reused by others.

## Extra Notes

This project is maintained as a local-first, transparent research assistant with strong emphasis on data provenance, manual review, and operational safeguards. Codex support would help accelerate code review, refactoring, security checks, documentation, and test coverage as the project grows from a single-maintainer tool into a more reusable open-source research platform.

## Preflight Checklist

- GitHub profile is visible in a logged-out or incognito browser.
- Repository is visible in a logged-out or incognito browser.
- `git status` is clean and local commits are pushed.
- `python tools\check_public_repo_safety.py` passes.
- `.env`, token cache files, `research_vault`, local DBs, and private report content are not tracked by Git.
