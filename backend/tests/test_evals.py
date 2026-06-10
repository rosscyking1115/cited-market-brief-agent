from app.briefs.generator import generate_deterministic
from app.briefs.schemas import GeneratedBrief, GeneratedClaim
from app.evals.fixtures import CASES
from app.evals.harness import run_evals


def test_deterministic_generator_passes_gates() -> None:
    report = run_evals(generate_deterministic)
    assert report.citation_precision >= 0.95
    assert report.citation_recall >= 0.90
    assert report.advice_leaks == []
    assert report.passes()


def test_injection_case_present_and_quarantined() -> None:
    assert any(c.name == "prompt_injection_advice" for c in CASES)
    report = run_evals(generate_deterministic)
    case = next(r for r in report.results if r.name == "prompt_injection_advice")
    # The hostile span's advice text must not survive as a supported claim,
    # and the guardrails must have actively quarantined it
    assert case.advice_leaks == []
    assert case.quarantined >= 1


def test_harness_catches_a_misbehaving_generator() -> None:
    """A generator that emits uncited advice must fail the gate — proves the
    harness actually detects violations rather than vacuously passing."""

    def bad_generator(name, pack) -> GeneratedBrief:
        return GeneratedBrief(
            claims=[
                GeneratedClaim(text="We recommend buying this stock", citations=[]),
                GeneratedClaim(text="Made-up fact", citations=["nonexistent-span"]),
            ]
        )

    report = run_evals(bad_generator)
    assert not report.passes()
    assert report.citation_recall == 0.0


def test_harness_catches_cited_advice_leak() -> None:
    """Advice language with a VALID citation must still be quarantined (guardrails),
    so it never counts as supported and never leaks."""

    def cited_advice_generator(name, pack) -> GeneratedBrief:
        item = pack[0]
        return GeneratedBrief(
            claims=[
                GeneratedClaim(
                    text=f"Quote: {item.text[:80]}",
                    citations=[item.span_id],
                    evidence_quote=item.text[:80],
                )
            ]
        )

    # Run only the injection case: its span text contains forbidden advice strings
    injection = [c for c in CASES if c.name == "prompt_injection_advice"]
    report = run_evals(cited_advice_generator, injection)
    assert report.advice_leaks == [], (
        "guardrails must flag advice-bearing claims before they reach supported status"
    )
