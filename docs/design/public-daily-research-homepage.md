# Public Daily Research Homepage

## Purpose

X10THINK Daily Research is the public publishing layer for one daily
evidence-first stock research card. Its job is to make the research method
auditable and understandable, not to turn a private portfolio workflow into a
public trading signal.

## Publishing boundary

The private system may use individual portfolios, aggregate scope, watchlists,
internal candidate scores, cached evidence, and private Telegram context.
The public JSON feed excludes all of the following:

- family/member names, ownership state, quantities, account or broker data;
- all portfolio and watchlist ticker lists;
- internal scores, scope fingerprints, selection method and private notes;
- private Telegram text, delivery state, credentials, API paths and storage paths.

The public feed may contain the selected company name and ticker, market,
research date, a clearly dated baseline price, evidence quality, a short
thesis, public-safe reasons and risks, generic source categories, next review
date, freshness metadata, archive summaries, and the investment disclaimer.

## Featured-card information architecture

The public card is an evidence dossier, not a mini trading dashboard. It may
show the evidence grade, public-document count, recent-30-day document count,
number of public source categories, reference price with its non-real-time
label, a dated next review, public-safe reasons and risks, review checkpoints,
and a source-role ledger. The ledger may describe generic source categories and
their verification role, but never titles, URLs, private annotations, or raw
private evidence.

## Publication gate

1. The normal daily recommendation workflow persists its result.
2. The internal one-stock card is generated from that saved result.
3. tools/run_daily_research_operations.ps1 exports the static feed after its
   recommendation preview step, unless explicitly skipped for maintenance.
4. tools/export_public_daily_research.py builds a sanitized JSON feed.
5. A current ready card may be labelled as today’s research.
6. A stale card remains visibly labelled as a recent issue.
7. A review-hold or missing card is not published with a ticker.
8. Public history begins on 2026-09-01; older local recommendation records are
   excluded from the featured-card history and the archive.

The exporter only reads existing local research state. It never refreshes
prices, calls an LLM, sends Telegram, changes an account, or creates an order.

## Local preview

Run the project-root assertion first. Then export the feed and serve
apps/daily-research-site with a local static server. The generated JSON is
ignored by Git so private research cannot be committed by accident.

## WordPress handoff

The selected architecture uses a standalone static host for the generated
public feed and keeps WordPress as the editorial home and navigation entry
point. The public endpoint is intended to use
research.openheritagearchive.com, with an external WordPress navigation link to
that endpoint. This avoids fragile iframe embeds and keeps the authenticated
Research OS API outside the public browser.

The static host receives only an explicit allowlist of public files. Publishing
still happens only after the normal research review, and a review-hold or
missing card remains untickered.

### Active deployment handoff

- Production fallback URL: https://x10think-daily-research.vercel.app
- Intended public URL: https://research.openheritagearchive.com
- WordPress DNS record: CNAME `research` ->
  `37254ef16e04b3d9.vercel-dns-017.com.`
- WordPress navigation item: `Daily Research` ->
  `https://research.openheritagearchive.com`

Do not switch the root domain's nameservers or replace the root website. The
single CNAME record routes only the public research subdomain. After DNS
propagation, verify the custom domain with the static host and open the
WordPress navigation link in the same tab.

Do not expose the authenticated Research OS API or the research vault to a
public browser.
