# Daily Research Public Site Design Contract

## Product character

- This is a public evidence-led research publication, never a trading terminal or a promise of returns.
- The visible daily card must keep the thesis, source quality, risks, next review date, and disclaimer in the same reading flow.
- Private portfolio ownership, quantities, account data, internal scores, selection logic, and private Telegram content never cross the export boundary.
- A stale or review-hold result is a valid publishing state. The page must say so plainly instead of presenting an old card as today’s result.
- Public issue history starts on 2026-09-01. Records before that date are not part of the public archive or featured-card history.

## Visual language

- Use a Korean financial editorial voice: warm paper, near-black type, restrained cobalt for evidence, market red/blue only for directional signals, and a small orange action accent.
- Treat the featured research card as the primary visual asset. It shows the actual publication state rather than a generic stock-photo metaphor.
- Prefer ruled columns, clear labels, and compact factual blocks to decorative cards. Card corners stay square or nearly square.
- Headline type uses a serif Korean stack; utility labels use a compact sans-serif stack. Never use a purple gradient, glass panel, or decorative orb.
- The featured card may become a dark research dossier inside the warm-paper page: near-black evergreen ground, thin amber rules, large evidence grade, and no rounded sub-cards.
- Its reading order is fixed: company/market and issue context → thesis and reference price → evidence metrics → reasons and risks → review checkpoints → source-role ledger → disclaimer.
- “More information” means more public, reviewable context. It never means exposing source titles, URLs, private notes, portfolio scope, accounts, quantities, internal scores, or Telegram content.

## Interaction and responsive behavior

- Navigation uses anchors and remains useful without JavaScript.
- The app fetches a generated public JSON feed. Loading, unavailable, stale, and review-hold states all have distinct copy.
- At 720px and below, every multi-column block becomes one column, the header wraps without overlap, and horizontal scrolling is forbidden.
- Buttons and links keep a minimum 44px touch target and a visible keyboard focus ring.

## Verification

- Generate a fresh local feed before visual testing.
- Check a desktop viewport and 390x844 mobile viewport for Korean phrase wrapping, card hierarchy, no clipped content, readable contrast, and the stale/empty state.
