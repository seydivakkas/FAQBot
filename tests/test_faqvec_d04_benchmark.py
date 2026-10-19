"""D04 kalite, eşik ve gerçek model koşusu olmadan metrik uydurmama kontrolleri."""
import pytest

from scripts.faqvec_d04_real_benchmark import (
    build_research_suite, compare, compute_scores,
)


def test_ai_research_uses_fixed_validation_and_test_no_answer_groups():
    ids, gallery, questions=build_research_suite()
    assert len(ids)==len(gallery)==96
    assert len(questions["validation"])==31
    assert len(questions["test"])==35
    assert sum(q["expected_id"] is None for q in questions["validation"])==11
    assert sum(q["expected_id"] is None for q in questions["test"])==11
    for split in questions:
        assert sum(q["expected_id"] is not None for q in questions[split]) in (20,24)
        assert all(q["source"].startswith("project_ai_reviewed")
                   for q in questions[split])


def test_validation_and_test_queries_never_overlap():
    _, _, questions=build_research_suite()
    val={x["query"] for x in questions["validation"]}
    test={x["query"] for x in questions["test"]}
    assert not val.intersection(test)
    assert all(x["expected_id"] for x in questions["test"]
               if x["source"]=="project_ai_reviewed_paraphrase")


def test_tfidf_runs_real_metrics_but_reports_synthetic_limit():
    result=compare([("tfidf",None)],latency_samples=2)
    assert result["gallery_size"]==96
    assert result["validation_oos"]==result["test_oos"]==11
    assert len(result["models"])==1
    item=result["models"][0]
    assert item["quality"]["out_of_scope"]==11
    assert item["quality"]["positives"]==24
    assert 0<=item["threshold_from_validation_only"]<=1
    assert isinstance(item["quality"]["recall_at_1"],float)
    assert isinstance(item["quality"]["wrong_match_rate"],float)
    assert isinstance(item["quality"]["no_answer_accuracy"],float)
    assert item["measured_real_model"] is False
    assert result["independent_customer_test"] is False
    assert result["commercial_acceptance"]=="HOLD"
    assert result["human_labeling_performed"] is False


def test_no_fake_embedding_scores_if_local_weights_missing(tmp_path):
    _,gallery,queries=build_research_suite()
    with pytest.raises(FileNotFoundError):
        compute_scores("e5-base",tmp_path/"missing",gallery,queries)


def test_disjoint_oos_are_not_trainable():
    _,_,questions=build_research_suite()
    assert all(x["source"] != "human_approved_out_of_scope"
               for split in questions for x in questions[split])


def test_unsupported_model_is_not_treated_as_real(tmp_path):
    _,gallery,questions=build_research_suite()
    (tmp_path/"bogus").mkdir()
    with pytest.raises(ValueError,match="Desteklenmeyen"):
        compute_scores("bogus",tmp_path/"bogus",gallery,questions)
