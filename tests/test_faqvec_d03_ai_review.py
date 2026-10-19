"""D03-02 kullanıcı tarafından AI'ya devredilen 96/48/24 kararının regresyon testleri."""
import json
from pathlib import Path
import pytest

from app.faqvec_v2_data import DatasetError, validate_intents
from scripts import faqvec_d03_ai_review as review


def test_all_intents_are_explicitly_reviewed_as_ai_not_human():
    rows, originals, negatives, oos, stats=review.evaluate()
    assert len(rows)==len(originals)==96
    assert len(negatives)==48 and len(oos)==24
    assert stats["intents_ai_reviewed"]==96
    assert stats["intent_corrections"]==11
    assert sum(len(r["alternatives"]) for r in rows)==192
    assert all(r["ai_review"]["reviewer"]==review.REVIEWER for r in originals)
    assert all(r["human_review"]=="not_performed" for r in originals)
    assert all(r["rights_verified"] is False for r in originals)


def test_detailed_ai_negative_decisions_not_all_called_hard():
    rows, _, negatives, _, stats=review.evaluate()
    assert stats["hard_negative_candidates"]==28
    assert stats["ordinary_negatives"]==20
    assert all(r["different_answers"] and not r["human_verified"] for r in negatives)
    assert all(r["status"]=="research_only" for r in negatives)
    all_ids={r["intent_id"] for r in rows}
    for r in negatives:
        assert r["anchor_intent"] in all_ids
        assert r["negative_intent"] in all_ids
        a=next(x for x in rows if x["intent_id"]==r["anchor_intent"])
        b=next(x for x in rows if x["intent_id"]==r["negative_intent"])
        assert a["split"]==b["split"]==r["split"]


def test_out_of_scope_ai_labels_exclude_unrealistic_cases():
    *_, oos, stats=review.evaluate()
    assert stats["oos_ai_reviewed"]==24
    assert stats["oos_candidates"]==22
    assert stats["oos_excluded"]==2
    excluded={x["candidate_id"] for x in oos
              if x["ai_decision"]=="excluded_unrealistic"}
    assert excluded==review.EXCLUDE_OOS
    assert all(x["human_verified"] is False for x in oos)


def test_corrections_do_not_change_splits_or_intent_ids():
    rows,orig,_,_,stats=review.evaluate()
    assert stats["splits"]=={"train":74,"validation":10,"test":12}
    assert validate_intents(rows)==stats["splits"]
    amended={x["intent_id"] for x in orig if x["ai_review"]["corrected"]}
    assert amended==set(review.CORRECTIONS)
    assert len(amended)==11


def test_package_remains_noncommercial_and_immutable(tmp_path):
    directory=tmp_path/"ai_review"
    result=review.export(directory)
    assert result["human_review_count"]==0
    manifest=json.loads(
        (directory/"manifest.AI_RESEARCH_ONLY.json").read_text(encoding="utf-8")
    )
    assert manifest["reviewer_type"]=="AI"
    assert manifest["independent_human_review"] is False
    assert manifest["commercial_training_approved"] is False
    assert manifest["rights_review_complete"] is False
    assert manifest["only_research"] is True
    assert len((directory/"faq.AI_RESEARCH.jsonl").read_text(encoding="utf-8").splitlines())==96
    assert len((directory/"negative_ai_review.jsonl").read_text(encoding="utf-8").splitlines())==48
    assert len((directory/"no_answer_ai_review.jsonl").read_text(encoding="utf-8").splitlines())==24
    with pytest.raises(FileExistsError):
        review.export(directory)


def test_modified_source_needs_new_review_not_silent_approval(tmp_path,monkeypatch):
    raw=review.CATALOG.read_text(encoding="utf-8")
    changed=tmp_path/"changed.json"
    changed.write_text(raw.replace("Siparişimin","Siparişlerimin",1),
                       encoding="utf-8")
    monkeypatch.setattr(review,"CATALOG",changed)
    with pytest.raises(DatasetError,match="okunmamış"):
        review.evaluate()
