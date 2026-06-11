# Pilot Error Log

One row per incident. Sources: runner output, `audit_events` where action in (`pilot.run_failed`, `ingest.*`), analyst feedback kind=`wrong`. Every guardrail bypass also becomes a new eval case in `backend/app/evals/fixtures.py` — bypasses turn into permanent regression tests.

| Date | Watchlist | Stage (ingest/parse/retrieve/generate/validate/export/UI) | Symptom | Root cause | Severity (blocker/degraded/cosmetic) | Fix / follow-up | Eval case added? |
|---|---|---|---|---|---|---|---|
| _yyyy-mm-dd_ | | | | | | | |

## Known failure modes to watch (from build phases)

- EDGAR primary documents that are XBRL viewer stubs rather than filing HTML → parser yields thin chunks (mitigation: edgartools-native parsing, backlog)
- Amended filings (10-K/A) pairing with originals in the diff grouping
- FRED series with `.` placeholders at the latest date (handled — verify in macro panel)
- Very long Item 1A sections chunking mid-sentence at window boundaries (cosmetic span drift)
- Deterministic-mode claims reading verbatim/clipped when no LLM key is set (expected; note for demo)
