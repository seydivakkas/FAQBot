"""D06: yeni 72 özel test sorusu ve validation-only marj güvenlik sözleşmesi."""
import numpy as np
import pytest

from app.faqvec_d06_margin_gate import (
    MARGINS, gate_measure, calibrate_validation_margin
)
from app.faqvec_v2_data import DatasetError
from scripts.faqvec_d06_frozen_challenge import (
    frozen_challenge, challenge_queries, summary,
)
from scripts.faqvec_d06_hard_benchmark import evaluate_frozen_models
from scripts.faqvec_d04_real_benchmark import build_research_suite
from scripts.faqvec_d05_owned_data import load_auxiliary_training


def test_original_72_question_source_has_provenance_and_fixed_sha():
    records=frozen_challenge()
    assert len(records)==72
    assert summary()["positive"]==48
    assert summary()["near_miss_oos"]==24
    assert summary()["domains"]==12
    assert summary()["no_training_or_validation_use"] is True
    assert summary()["independent_customer_test"] is False


def test_contrast_grouping_has_four_positive_and_two_near_miss_per_domain():
    rows=challenge_queries()
    for domain in {x["domain"] for x in rows}:
        subset=[r for r in rows if r["domain"]==domain]
        assert len([x for x in subset if x["expected_id"] is not None])==4
        assert len([x for x in subset if x["expected_id"] is None])==2
    assert all(r["source"]=="d06_project_ai_authored_frozen_hard_test" for r in rows)


def test_no_old_or_new_train_validation_test_exact_duplicate():
    from app.matching import normalize
    old, *_=build_research_suite()
    _,old_gallery,old_split=build_research_suite()
    seen={normalize(q) for q in old_gallery}
    for split in old_split.values():
        seen.update(normalize(item["query"]) for item in split)
    for item in load_auxiliary_training():
        seen.update(normalize(x) for x in [item["question"],*item["alternatives"]])
    assert not seen.intersection(normalize(x["query"]) for x in challenge_queries())


def test_margin_gate_refuses_ambiguous_high_score():
    matrix=np.asarray([[.90,.895],[.91,.1],[.65,.64]])
    labels=["a","a",None]
    before=gate_measure(matrix,["a","b"],labels,threshold=.6,margin=0)
    after=gate_measure(matrix,["a","b"],labels,threshold=.6,margin=.02)
    assert before["correct_positive_count"]==2
    assert before["false_answer_count"]==1
    assert after["correct_positive_count"]==1
    assert after["false_answer_count"]==0
    assert after["positive_abstention_count"]==1


def test_d06_threshold_and_margin_selected_only_from_old_validation():
    ids=["a","b"]
    val=np.array([[.93,.20],[.10,.92],[.80,.79],[.68,.67]])
    val_labels=["a","b",None,None]
    chosen=calibrate_validation_margin(val,ids,val_labels)
    assert chosen["selection_source"]=="d04_validation_only"
    assert chosen["grid_thresholds"]==201
    assert chosen["grid_margins"]==51
    assert chosen["selected_margin"] in MARGINS
    assert chosen["validation_dual_gate"]["wrong_match_rate"]<=.1
    assert chosen["validation_dual_gate"]["false_answer_rate"]<=.1
    assert chosen["commercial_acceptance"]=="HOLD"


def test_d06_no_fake_model_results_if_weights_missing(tmp_path):
    from scripts.faqvec_d06_hard_benchmark import _check_model
    with pytest.raises(FileNotFoundError):
        _check_model("faqvec-d05",tmp_path/"no-model")


def test_frozen_hard_test_tfidf_produces_real_metrics_only():
    result=evaluate_frozen_models([("tfidf",None)],latency_samples=2)
    assert result["gallery_count"]==96
    assert result["fixed_calibration_count"]==31
    assert result["positive_new_questions"]==48
    assert result["near_miss_oos_new_questions"]==24
    assert result["new_test_used_in_training_or_calibration"] is False
    assert result["independent_customer_test"] is False
    assert result["commercial_acceptance"]=="HOLD"
    record=result["models"][0]
    assert record["name"]=="tfidf"
    assert record["dual_gate_test"]["positive"]==48
    assert record["dual_gate_test"]["oos"]==24
    assert len(record["dual_gate_per_domain"])==12
    assert record["validation_gate"]["selection_source"]=="d04_validation_only"


def test_duplicate_model_name_is_rejected():
    with pytest.raises(ValueError,match="yinelendi"):
        evaluate_frozen_models([("tfidf",None),("tfidf",None)],latency_samples=1)
