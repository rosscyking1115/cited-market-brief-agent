# ADR 0001: Separate radar and company research routes

**Date:** 2026-07-19
**Status:** accepted

## Context

The newer region-aware radar and the original evidence-backed company brief shared one oversized page. This duplicated region/language controls, made the professional review workflow appear secondary, and let radar state change the brief’s audited reading mode.

## Decision

Serve the Morning Market Radar at `/` and the evidence-backed company research workspace at `/brief`. Regional URL/local-storage state applies only to the radar. The brief opens in English and exposes Traditional Chinese and Korean only as labelled reading aids. Shared navigation, theme and text-size controls remain in one header component.

## Alternatives rejected

- Keep the brief below the radar — preserves the mixed-audience hierarchy and duplicated controls.
- Remove the brief — discards the project’s strongest claim-level citation and review proof.
- Create separate repositories — unnecessary operational split for two related research surfaces sharing the same backend and evidence model.

## Consequences

Each route has one job and can be linked, tested and documented independently. Demo fixtures live outside route files. Public copy must describe one workbench with two routes, not two modules on one page.

## Note on later wording (does not amend the decision)

The Decision above is left as it was recorded, because an ADR is a record of what
was decided and when. One phrase in it has since been superseded and would
mislead a reader who met it on its own.

“Labelled reading aids” implied a verified relationship to the English source
that nothing measured. Automatic structure and citation checks on the translated
brief were added later, so the accurate statement is now: **structure and
citation problems are recorded automatically but not blocked**, the wording
itself is not evaluated, and review and approval stay tied to the English
original. The checks set a flag that nothing reads, so they are instrumentation
rather than a gate. Radar news translations carry no checks at all. See claims 9,
9a and 9b in [`docs/claims/claim-ledger.md`](../claims/claim-ledger.md).

The routing decision this ADR records is unaffected.
