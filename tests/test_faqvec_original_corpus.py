"""Özgün FAQVec taslağı: kaynak, niyet, insan onayı ve sızıntı güvenliği."""
import json
import pytest
from app.faqvec_v2_data import DatasetError, load_approved_sources, validate_intents
from scripts.build_faqvec_original import (
    CATALOG, OOS_CATALOG, load_original_draft, load_no_answer_draft,
    build_draft, build_package, file_hash
)


def test_96_self_written_intents_across_12_domains():
    items=load_original_draft()
    assert len(items)==96
    assert len(set(x["domain"] for x in items))==12
    assert all(len(x["alternatives"])==2 for x in items)
    assert all(x["source_id"]=="faqvec-original-project-draft" for x in items)
    assert all(x["rights_verified"] is False for x in items)
    assert len(file_hash(CATALOG))==64


def test_splits_group_confusable_intents_in_same_group():
    original=load_original_draft()
    rows,negatives,reviews,train=build_draft(original)
    counts=validate_intents(rows)
    assert sum(counts.values())==96
    assert min(counts.values())>0
    assert len(negatives)==48
    assert len(reviews)==96
    assert len(train)>0
    assert all(x["status"]=="needs_human_review" for x in negatives)
    assert all(x["reviewed_by"] is None for x in negatives)
    family_splits={}
    for row in rows:
        s=family_splits.setdefault(row["family_id"],row["split"])
        assert row["split"]==s
    assert len(family_splits)==48
    assert all(x["split"]=="train" for x in train)
    assert all(x["human_review"]=="pending" for x in rows)


def test_no_answer_examples_are_24_unreviewed_original_candidates():
    rows,_,_,_=build_draft(load_original_draft())
    candidates=load_no_answer_draft(intent_records=rows)
    assert len(candidates)==24
    assert len(file_hash(OOS_CATALOG))==64
    assert set(item["review_status"] for item in candidates)=={"needs_human_review"}
    assert all(item["expected_id"] is None for item in candidates)
    assert not any(item["reviewed_by"] for item in candidates)


def test_package_is_not_commercial_training_authorization(tmp_path):
    result=build_package(output_dir=tmp_path/"original")
    assert result["intents"]==96
    assert result["positive_paraphrase_pairs"]==192
    assert result["candidate_hard_negative_pairs"]==48
    assert result["no_answer_review_candidates"]==24
    assert result["human_approved_intents"]==0
    assert result["commercial_acceptance"]=="HOLD"
    directory=tmp_path/"original"
    manifest=directory/"manifest.DRAFT.json"
    source=json.loads(manifest.read_text(encoding="utf-8"))
    assert source["sources"][0]["origin_kind"]=="self_authored"
    assert source["sources"][0]["rights_review_complete"] is False
    assert source["sources"][0]["commercial_training_approved"] is False
    with pytest.raises(DatasetError):
        load_approved_sources(manifest,for_commercial=True)
    assert len((directory/"hard_negative_review.DRAFT.jsonl").read_text(encoding="utf-8").splitlines())==48
    assert len((directory/"no_answer_review.DRAFT.jsonl").read_text(encoding="utf-8").splitlines())==24
    with pytest.raises(FileExistsError):
        build_package(output_dir=directory)


def test_tampered_draft_cannot_be_hidden_as_human_approved(tmp_path):
    source=json.loads(CATALOG.read_text(encoding="utf-8"))
    source["records"][0]["rights_verified"]=True
    path=tmp_path/"catalog.json"
    path.write_text(json.dumps(source,ensure_ascii=False),encoding="utf-8")
    with pytest.raises(DatasetError,match="TASLAK"):
        load_original_draft(path)


def test_duplicated_query_across_intents_is_rejected(tmp_path):
    source=json.loads(CATALOG.read_text(encoding="utf-8"))
    source["records"][1]["alternatives"][0]=source["records"][0]["question"]
    path=tmp_path/"catalog.json"
    path.write_text(json.dumps(source,ensure_ascii=False),encoding="utf-8")
    with pytest.raises(DatasetError,match="Tekrarlanan"):
        load_original_draft(path)


def test_external_data_is_not_used_in_generated_draft():
    rows=load_original_draft()
    for row in rows:
        assert "dogukanvzr" not in json.dumps(row,ensure_ascii=False).lower()
        assert row["authorship"]=="newly_written_project_draft"
    catalog=json.loads(CATALOG.read_text(encoding="utf-8"))
    assert catalog["commercial_training_approved"] is False


def test_historical_demo_commands_are_blocked():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    workflow=(root/".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "scripts.train_faqvec_tr --epochs" not in workflow
    assert "benchmark_faqvec_v2 --demo" not in workflow
    assert "scripts.build_faqvec_original --check-only" in workflow
    trainer=(root/"scripts/train_faqvec_v2.py").read_text(encoding="utf-8")
    assert 'if args.demo:' in trainer
