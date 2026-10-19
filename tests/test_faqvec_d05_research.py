"""D05 veri hakları, train-only sızıntı, güvenli eşik ve adil benchmark."""
import json
import numpy as np
import pytest

from app.faqvec_v2_data import DatasetError
from app.faqvec_d05_policy import (
    THRESHOLDS, choose_guardrail_threshold, coverage_risk_point,
    policy_diagnostics
)
from scripts.faqvec_d05_owned_data import (
    load_auxiliary_training, augmented_positive_pairs, summary
)
from scripts.faqvec_d05_real_benchmark import (
    _check_model, run_experiment
)
from scripts.faqvec_d04_real_benchmark import build_research_suite


def test_new_24_intents_are_all_train_only_and_unapproved():
    items = load_auxiliary_training()
    assert len(items) == 24
    assert len(set(r["domain"] for r in items)) == 6
    assert all(x["train_only_auxiliary"] is True for x in items)
    assert all(x["split"] == "train" for x in items)
    assert all(x["commercial_training_approved"] is False for x in items)
    assert all(x["human_review"] == "not_performed" for x in items)
    assert summary()["own_train_only_alternatives"] == 48


def test_training_pairs_196_and_legacy_gallery_unchanged():
    pairs = augmented_positive_pairs()
    assert len(pairs) == 196
    assert len({x["intent_id"] for x in pairs}) == 98
    ids, gallery, queries = build_research_suite()
    assert len(ids) == len(gallery) == 96
    assert len(queries["validation"]) == 31
    assert len(queries["test"]) == 35
    assert not set(ids).intersection(
        r["intent_id"] for r in load_auxiliary_training()
    )


def test_guardrail_policy_uses_validation_only():
    ids = ["a", "b"]
    val_scores = np.array([
        [.92,.10], [.10,.91], [.39,.31], [.43,.13],
    ])
    val_labels = ["a","b",None,None]
    chosen = choose_guardrail_threshold(val_scores, ids, val_labels)
    assert chosen["selection_source"] == "validation_only"
    assert chosen["usable_on_validation"] is True
    assert chosen["threshold"] > .43
    assert chosen["threshold"] <= .91
    assert chosen["validation"]["correct_positive_answer_count"] == 2
    assert chosen["validation"]["oos_false_answer_count"] == 0
    assert len(THRESHOLDS) == 201
    assert policy_diagnostics(val_scores,ids,val_labels)["evaluated_candidate_count"] == 201


def test_guardrail_can_be_safe_but_unusable():
    ids = ["a","b"]
    mat = np.array([[.25,.26],[.40,.35]])
    chosen = choose_guardrail_threshold(mat,ids,["a",None])
    assert chosen["usable_on_validation"] is False
    assert chosen["validation"]["correct_positive_answer_count"] == 0


def test_risk_coverage_handles_zero_answers():
    info = coverage_risk_point(
        np.array([[.3,.2],[.2,.1]]), ["a","b"],["a",None],1.0
    )
    assert info["total_answered_count"] == 0
    assert info["answered_risk"] is None
    assert info["positive_abstention_rate"] == 1.0


def test_no_missing_embedding_can_pass_as_finetune(tmp_path):
    with pytest.raises(FileNotFoundError):
        _check_model("faqvec-d05",tmp_path/"unknown")
    empty = tmp_path/"model"
    empty.mkdir()
    with pytest.raises(ValueError,match="manifesti"):
        _check_model("faqvec-d05",empty)
    f=empty/"faqvec_v2_manifest.json"
    f.write_text(json.dumps({
        "source_mode":"ai_reviewed_project_owned_research_only",
        "research_only":True,
        "commercial_training_approved":False,
        "d05_owned_expansion":False,
    }),encoding="utf-8")
    with pytest.raises(ValueError,match="196"):
        _check_model("faqvec-d05",empty)
    with pytest.raises(ValueError):
        _check_model("faqvec-d04",empty) if False else _check_model("unknown",empty)


def test_true_tfidf_d05_evaluation_does_not_fake_other_models():
    result = run_experiment([("tfidf",None)],latency_samples=2)
    assert result["gallery"] == 96
    assert result["test_positive"] == 24
    assert result["test_oos"] == 11
    assert result["validation_queries"] == 31
    assert result["test_queries"] == 35
    assert result["third_party_question_dataset_used"] is False
    assert result["commercial_release"] == "HOLD"
    assert len(result["models"]) == 1
    item = result["models"][0]
    assert item["name"] == "tfidf"
    assert item["d05_policy_test"]["total"] == 35
    assert item["validation_diagnostics"]["d05_guardrail"]["selection_source"] == "validation_only"
    assert len(item["validation_diagnostics"]["validation_coverage_risk_curve"]) == 41


def test_duplicated_model_is_rejected_without_running_model():
    with pytest.raises(ValueError,match="iki kere"):
        run_experiment([("tfidf",None),("tfidf",None)],latency_samples=1)
