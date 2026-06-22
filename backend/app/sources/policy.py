"""Human-readable source policy metadata.

This registry is deliberately small and conservative. It is not a substitute for
legal review, but it keeps product labels aligned with each source's approved
use in the family pilot.
"""

from dataclasses import dataclass
from typing import Literal

SourceKey = Literal["bbc_rss", "gdelt_doc", "nyt_most_popular"]


@dataclass(frozen=True)
class SourcePolicy:
    key: SourceKey
    display_name: str
    source_status: Literal["official_api", "rss", "licensed", "planned", "manual_reference"]
    allowed_label: str
    forbidden_label: str
    rights_note: str


SOURCE_POLICIES: dict[SourceKey, SourcePolicy] = {
    "bbc_rss": SourcePolicy(
        key="bbc_rss",
        display_name="BBC",
        source_status="rss",
        allowed_label="Latest from BBC",
        forbidden_label="BBC Most Read",
        rights_note=(
            "BBC RSS/latest only after terms review; do not scrape or label as Most Read."
        ),
    ),
    "gdelt_doc": SourcePolicy(
        key="gdelt_doc",
        display_name="GDELT",
        source_status="official_api",
        allowed_label="Trending / Most covered",
        forbidden_label="Most read",
        rights_note="GDELT discovery row: link to publisher; do not republish article text.",
    ),
    "nyt_most_popular": SourcePolicy(
        key="nyt_most_popular",
        display_name="NYT",
        source_status="official_api",
        allowed_label="Most viewed (NYT)",
        forbidden_label="Reproduce article text",
        rights_note=(
            "NYT Most Popular API: genuine most-viewed; display headline + link and link "
            "back to nytimes.com. Do not reproduce article body text."
        ),
    ),
}


def source_policy(key: SourceKey) -> SourcePolicy:
    return SOURCE_POLICIES[key]
