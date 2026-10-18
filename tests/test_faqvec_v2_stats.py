"""Niyet bazlı anlamlılık, performans yardımcıları ve örnekten kanıt üretmeme."""
import numpy as np
import pytest

from app.faqvec_v2_metrics import paired_intent_bootstrap_recall_delta
from scripts.profile_faqvec_v2 import percentile, model_directory_size


def test_paired_bootstrap_uses_intents_and_is_reproducible():
    labels = [f"i{i}" for i in range(10)]
    ideal = np.eye(10)
    bad = np.roll(ideal, 1, axis=1)
    first = paired_intent_bootstrap_recall_delta(bad, ideal, labels, labels, seed=42)
    second = paired_intent_bootstrap_recall_delta(bad, ideal, labels, labels, seed=42)
    assert first == second
    assert first["intents"] == 10
    assert first["delta_recall_at_1"] == 1.0
    assert first["ci95"] == [1.0, 1.0]
    assert first["significant_positive"] is True


def test_bootstrap_small_or_no_intents_does_not_invent_significance():
    labels = ["a","b","c"]
    result = paired_intent_bootstrap_recall_delta(
        np.roll(np.eye(3), 1, axis=1), np.eye(3), labels, labels
    )
    assert result["intents"] == 3
    assert result["ci95"] is None
    assert result["significant_positive"] is None
    oos = paired_intent_bootstrap_recall_delta(
        np.eye(2),np.eye(2),["a","b"],[None,None]
    )
    assert oos["intents"] == 0
    assert oos["ci95"] is None


def test_bootstrap_rejects_inconsistent_data():
    with pytest.raises(ValueError):
        paired_intent_bootstrap_recall_delta(
            np.eye(3),np.eye(2),["a","b","c"],["a","b","c"]
        )
    with pytest.raises(ValueError):
        paired_intent_bootstrap_recall_delta(
            np.array([[float("nan")]]),np.eye(1),["a"],["a"]
        )


def test_profile_helpers_have_exact_interpretable_outputs(tmp_path):
    (tmp_path/"a.bin").write_bytes(b"a"*23)
    nested = tmp_path/"models"
    nested.mkdir()
    (nested/"b.bin").write_bytes(b"b"*7)
    assert model_directory_size(tmp_path) == 30
    assert percentile([10,20,30,40,50], 50) == 30
    assert percentile([10,20,30,40,50], 95) == pytest.approx(48)
    assert percentile([], 95) is None
