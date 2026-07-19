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
