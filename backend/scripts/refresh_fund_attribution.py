"""Recompute the saved fund's daily attribution from TWSE after-close data.

Run on an evening cron (after the Taiwan close and TWSE data settle), e.g.:

    30 11 * * 1-5  cd /opt/cited-market-brief-agent && \
      docker compose --env-file .env.staging -f docker-compose.staging.yml \
      exec -T backend python scripts/refresh_fund_attribution.py

11:30 UTC ≈ 19:30 Taipei. No-op until a fund is configured on the page.
"""

from app.fund_attribution.service import refresh_latest_attribution


def main() -> None:
    result = refresh_latest_attribution()
    if result is None:
        print("No fund configured yet; nothing to refresh.")
        return
    print(
        f"Refreshed {result.fund_name} for {result.as_of}: "
        f"active {result.active_return_pct:+.2f}% vs {result.benchmark_name} "
        f"(explained {result.explained_return_pct:+.2f}%, residual {result.residual_pct:+.2f}%)."
    )


if __name__ == "__main__":
    main()
