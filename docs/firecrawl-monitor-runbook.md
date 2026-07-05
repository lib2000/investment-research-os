# Firecrawl Monitor Runbook

Firecrawl Monitor is kept safe by default. The local env template starts with `FIRECRAWL_MONITOR_ENABLED=false` and `FIRECRAWL_MONITOR_DRY_RUN=true`; do not flip those until the preflight commands below are green.

## 1. Create A Local Env Template

```powershell
python tools\create_firecrawl_monitor_env_template.py --output tmp\firecrawl-monitor.local.env
```

The tool does not overwrite an existing file unless `--force` is passed. Fill `FIRECRAWL_API_KEY` and `FIRECRAWL_MONITOR_WEBHOOK_SECRET` manually after creation. Before final create readiness, also add a public `webhook.url` to each monitor registry entry that should feed the InvestmentJournalApp webhook endpoint.

The production webhook path is:

```text
https://<public-investment-app-host>/api/v1/public-ir-sec/firecrawl-monitor/webhook
```

Send the secret with either `X-Firecrawl-Webhook-Secret: <FIRECRAWL_MONITOR_WEBHOOK_SECRET>`, `X-Webhook-Secret: <FIRECRAWL_MONITOR_WEBHOOK_SECRET>`, or `Authorization: Bearer <FIRECRAWL_MONITOR_WEBHOOK_SECRET>`. The preflight command below verifies that mismatched secrets are rejected and valid secrets are accepted before any real monitor creation is allowed.

## 2. Validate Registry And Webhook

```powershell
python tools\check_firecrawl_monitor_operational_preflight.py --env-file tmp\firecrawl-monitor.local.env --env-override --require-env-registry --require-webhook-secret --require-monitor-webhook
```

This uses an isolated temporary vault by default. It verifies that a wrong webhook secret is rejected, a valid secret is accepted, and one sample event is saved.

## 3. Check Create Readiness

After setting a real API key and reviewing the registry, run:

```powershell
python tools\check_firecrawl_monitor_operational_preflight.py --env-file tmp\firecrawl-monitor.local.env --env-override --require-env-registry --require-webhook-secret --require-monitor-webhook --require-create-ready
```

Only this stage should require `FIRECRAWL_MONITOR_ENABLED=true`, `FIRECRAWL_MONITOR_DRY_RUN=false`, and a real `FIRECRAWL_API_KEY`.

To save the final non-secret creation report:

```powershell
python tools\check_firecrawl_monitor_operational_preflight.py --env-file tmp\firecrawl-monitor.local.env --env-override --require-env-registry --require-webhook-secret --require-monitor-webhook --require-create-ready --readiness-report output\firecrawl_monitor_create_readiness_report.json
```

The report stores conditions, readiness errors, monitor names, target counts, target types, schedule, webhook flag, and payload hash prefixes. It does not store API keys, webhook secrets, or full payload bodies.

## 4. Final Guardrails

- Keep the env file out of git.
- Never paste real API keys into docs, console output, or commits.
- Use `--use-live-vault` only when you intentionally want the webhook preflight event in `research_vault`.
- Review the monitor registry target URLs, schedule, goal, and webhook target before real creation.
