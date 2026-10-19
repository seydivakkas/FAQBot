"""D05 sentetik OOS güvenlik dilimlerinin geri dönüşsüz kapı testleri."""
from scripts.faqvec_d05_safety_slices import (
    CLASS_OF, MESSAGE, safety_slices, summary
)


def test_all_22_ai_reviewed_oos_have_exactly_one_risk_class():
    data = safety_slices()
    assert len(data) == 22
    assert len({x["candidate_id"] for x in data}) == 22
    assert len(CLASS_OF) == 22
    assert {x["risk_class"] for x in data} == set(MESSAGE)
    assert summary()["validation"] == summary()["test"] == 11
    assert all(x["commercial_training_approved"] is False for x in data)
    assert all(x["human_verified"] is False for x in data)


def test_sensitive_cases_do_not_fake_human_quality():
    records = safety_slices()
    secrets = [
        r for r in records if r["risk_class"] == "private_information"
    ]
    assert len(secrets) == 10
    assert all("paylaşamam" in r["fallback"] for r in secrets)
    assert all("source" in r for r in records)
    assert summary()["commercial_acceptance"] == "HOLD"
