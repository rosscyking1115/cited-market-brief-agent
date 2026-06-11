# Cited Market Brief Agent Pilot Runbook

Two-week daily-brief pilot with a domain user (plan §12 Phase 6). Goal: a recurring brief the analyst calls genuinely useful, with failure modes documented. Public data only.

## Setup (day 0)

1. `docker compose up -d db valkey minio` · `python scripts/bootstrap_db.py` · `python scripts/apply_rls.py --apply`
2. `.env`: `SEC_USER_AGENT` (required), `FRED_API_KEY`, one LLM key (`ANTHROPIC_API_KEY` recommended; without it the pilot runs in extractive mode — still citation-perfect, less synthesis).
3. `python scripts/seed_watchlists.py` — seeds Semis / Megabanks / Energy templates, weekdays 10:30 UTC. Trim to the pilot user's actual coverage; 1–2 lists beat 3 neglected ones.
4. Schedule `python scripts/run_scheduled.py` every 15 min (cron / Task Scheduler). First run: `--force`.
5. Verify the loop once end to end: dashboard shows **LIVE**, claims open to evidence, exports download.

## Daily ritual (analyst, ~10 min)

1. Open the brief before the morning meeting. Read "Since last brief" first — diffs and vintage revisions are the highest-signal content.
2. Click through 2–3 claims to the evidence ledger. Spot-check one against the actual filing (trust calibration is the pilot's product).
3. Act on every section: accept / edit / reject / needs-source. Hit the feedback buttons on wrong or weak claims — feedback rows are the eval-dataset seed.
4. Approve if everything is resolved; export the format the analyst would actually circulate internally (PPTX for morning meetings, PDF for notes).

## Daily ritual (operator, ~5 min)

- Runner exit code ≠ 0 or `pilot.run_failed` in audit_events → triage into `pilot/ERROR_LOG.md` same day.
- Watch for: EDGAR 403s (UA/rate), FRED key limits, parser misses on odd filings, validator flagging correct claims (false positives matter as much as misses).

## Weekly review (30 min, together)

Pull metrics (plan §11) and record in `pilot/CASE_STUDY.md`:

| Metric | Source |
|---|---|
| Time saved per brief (analyst estimate vs prior manual process) | interview |
| % claims with validated citations | brief meta / manifest |
| Unsupported-claim rate | needs-review counts |
| Wrong-source feedback rate | feedback rows, kind=wrong |
| Sections accepted unchanged vs edited vs rejected | user_edits |
| Export rate (briefs the analyst actually used) | exports table |
| Failure modes + frequency | ERROR_LOG.md |

## Exit interview prompts

Which section did you stop reading? Which claim made you check the source — and did the evidence hold? What would you remove? Would you notice if the brief stopped arriving? (The last one is the real usefulness test.)

## Success criteria

- ≥1 watchlist where the analyst says the brief is part of the morning routine
- ≥95% of material claims citation-validated across the pilot window
- Top 5 failure modes documented with reproduction notes
- Demo flow rehearsed from real pilot output (see `docs/Cited_Market_Brief_Agent_Demo.pptx`)
