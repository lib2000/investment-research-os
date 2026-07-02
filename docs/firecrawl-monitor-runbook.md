# Firecrawl Monitor Runbook

Firecrawl Monitor is kept safe by default. The local env template starts with `FIRECRAWL_MONITOR_ENABLED=false` and `FIRECRAWL_MONITOR_DRY_RUN=true`; do not flip those until the preflight commands below are green.

## 1. Create A Local Env Template

```powershell
python tools\create_firecrawl_monitor_env_template.py --output tmp\firecrawl-monitor.local.env
```

The tool does not overwrite an existing file unless `--force` is passed. Fill `FIRECRAWL_API_KEY` and `FIRECRAWL_MONITOR_WEBHOOK_SECRET` manually after creation.

## 2. Validate Registry And Webhook

```powershell
python tools\check_firecrawl_monitor_operational_preflight.py --env-file tmp\firecrawl-monitor.local.env --env-override --require-env-registry --require-webhook-secret
```

This uses an isolated temporary vault by default. It verifies that a wrong webhook secret is rejected, a valid secret is accepted, and one sample event is saved.

## 3. Check Create Readiness

After setting a real API key and reviewing the registry, run:

```powershell
python tools\check_firecrawl_monitor_operational_preflight.py --env-file tmp\firecrawl-monitor.local.env --env-override --require-env-registry --require-webhook-secret --require-create-ready
```

Only this stage should require `FIRECRAWL_MONITOR_ENABLED=true`, `FIRECRAWL_MONITOR_DRY_RUN=false`, and a real `FIRECRAWL_API_KEY`.

## 4. Final Guardrails

- Keep the env file out of git.
- Never paste real API keys into docs, console output, or commits.
- Use `--use-live-vault` only when you intentionally want the webhook preflight event in `research_vault`.
- Review the monitor registry target URLs, schedule, goal, and webhook target before real creation.
