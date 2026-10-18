"""D02 local human review and rights evidence — no human approvals invented."""
import copy
import hashlib
import json

import pytest

from scripts.faqvec_d02_review import (
    aggregate, generate_bundle, validate_bundle, write_new
)
from scripts.faqvec_d02_rights import review_evidence
from scripts.audit_faqvec_d01 import SOURCE_LFS_SHA256, SOURCE_SHA, SOURCE_REPO


def fixture_file(tmp_path):
    rows=[
        ("Kargom nerede?", "Paketim ne zaman gelir?",1),
        ("Kargom nerede?", "Kargo takibi yapabilir miyim?",1),
        ("İadem ne zaman yapılır?", "Ürün iadesi kaç günde?",1),
        ("Şifremi nasıl değiştiririm?", "Parola güncelleme nerede?",1),
        ("Siparişimi iptal etmek istiyorum", "Siparişi geri alabilir miyim?",1),
        ("Kargom nerede?", "İadem ne zaman yapılır?",0),
        ("Kargom nerede?", "Parola güncelleme nerede?",0),
        ("İadem ne zaman yapılır?", "Ürün iadesi kaç günde?",0), # direct conflict
        ("Siparişimi iptal etmek istiyorum", "Parola güncelleme nerede?",0),
    ]
    path=tmp_path/"synthetic.jsonl"
    path.write_text("".join(json.dumps(
        {"sentence1":a,"sentence2":b,"label":v},ensure_ascii=False)+"\n"
        for a,b,v in rows),encoding="utf-8")
    return path


def test_d02_bundle_is_deterministic_and_freezes_candidates(tmp_path):
    path=fixture_file(tmp_path)
    one, freeze, summary=generate_bundle(path,verify_pin=False,positive_limit=5,neg_limit=4)
    two, freeze2, summary2=generate_bundle(path,verify_pin=False,positive_limit=5,neg_limit=4)
    assert one==two and freeze==freeze2 and summary==summary2
    validate_bundle(one)
    assert one["commercial_training_approved"] is False
    assert one["semantic_ground_truth_approved"] is False
    assert freeze["candidate_only"] is True
    assert freeze["independent_customer_test"] is False
    assert summary["unique_quarantine_components"]>=1
    assert summary["human_approved_pairs"]==0
    assert all(task["task_id"].startswith("D02-") for task in one["tasks"])
    assert "direct_conflict" in {task["reason"] for task in one["tasks"]}


def test_d02_tampered_tasks_are_rejected(tmp_path):
    bundle,_,_=generate_bundle(fixture_file(tmp_path),verify_pin=False)
    tampered=copy.deepcopy(bundle)
    tampered["tasks"][0]["question_a"]="Değiştirilmiş içerik"
    with pytest.raises(ValueError,match="bütünlük"):
        validate_bundle(tampered)


def example_decisions(bundle,person,decision="different"):
    return {
        "schema":1, "reviewer_id":person, "bundle_id":bundle["bundle_id"],
        "decisions":[{"task_id":t["task_id"],"decision":decision,"note":"İki cevap farklı"}
                     for t in bundle["tasks"]],
    }


def test_requires_two_distinct_reviewers_and_matching_bundle(tmp_path):
    bundle,_,_=generate_bundle(fixture_file(tmp_path),verify_pin=False)
    a=example_decisions(bundle,"reviewer_1")
    b=example_decisions(bundle,"reviewer_1")
    with pytest.raises(ValueError,match="FARKLI"):
        aggregate(bundle,a,b)
    b["reviewer_id"]="reviewer_2"
    b["bundle_id"]="tampered"
    with pytest.raises(ValueError,match="eşleşmiyor"):
        aggregate(bundle,a,b)


def test_double_human_reviews_do_not_grant_commercial_rights(tmp_path):
    bundle,_,_=generate_bundle(fixture_file(tmp_path),verify_pin=False)
    a=example_decisions(bundle,"A")
    b=example_decisions(bundle,"B")
    result=aggregate(bundle,a,b)
    assert result["outcomes"]["dual_agreement_different"]==len(bundle["tasks"])
    assert result["commercially_approved_negatives"]==0
    assert result["commercial_training"]=="HOLD"
    assert all(x["status"]=="reviewed_rights_hold"
               for x in result["research_only_negatives"])
    assert result["independent_customer_test"]=="HOLD"


def test_disagreement_or_uncertain_never_auto_pass(tmp_path):
    bundle,_,_=generate_bundle(fixture_file(tmp_path),verify_pin=False)
    a=example_decisions(bundle,"A","same")
    b=example_decisions(bundle,"B","different")
    result=aggregate(bundle,a,b)
    assert result["outcomes"]["disagreement"]==len(bundle["tasks"])
    assert not result["research_only_negatives"]
    b["decisions"][0]["decision"]="uncertain"
    result=aggregate(bundle,a,b)
    assert result["outcomes"]["uncertain"]==1
    assert result["pending_tasks"]


def test_review_rejects_duplicate_task_decisions(tmp_path):
    bundle,_,_=generate_bundle(fixture_file(tmp_path),verify_pin=False)
    a=example_decisions(bundle,"A")
    b=example_decisions(bundle,"B")
    a["decisions"].append(dict(a["decisions"][0]))
    with pytest.raises(ValueError,match="Yinelenen"):
        aggregate(bundle,a,b)


def test_immutable_existing_review_files(tmp_path):
    path=tmp_path/"answer.json"
    write_new(path,{"reviewer_id":"A"})
    with pytest.raises(FileExistsError):
        write_new(path,{"reviewer_id":"B"})


def test_rights_document_completeness_does_not_claim_legal_pass(tmp_path):
    register={
        "source_repo":SOURCE_REPO,"source_revision":SOURCE_SHA,
        "source_sha256":SOURCE_LFS_SHA256,
        "creator_or_rights_holder":"Published author",
        "contact_channel":"Dataset community",
        "underlying_sentence_origin":"Needs verification",
        "third_party_text_sources":"Unverified",
        "commercial_ml_training_permission":"granted_with_evidence",
        "fine_tuned_weight_distribution_permission":"granted_with_evidence",
        "license_obligations":"NOTICE",
        "independent_legal_reviewer":"Outside expert",
        "independent_legal_review_date":"2026-10-18",
    }
    r=review_evidence(register,tmp_path)
    assert r["commercial_training"]=="HOLD"
    assert r["technical_document_check"]=="HOLD"
    evidence=tmp_path/"source_reply.txt"
    evidence.write_text("Sample fixture; no genuine rights authorization.",encoding="utf-8")
    register["evidence_files"]=[{
        "path":evidence.name,
        "sha256":hashlib.sha256(evidence.read_bytes()).hexdigest()
    }]
    good=review_evidence(register,tmp_path)
    assert good["technical_document_check"]=="PASS"
    assert good["independent_rights_authenticity"]=="HOLD"
    assert good["commercial_distribution"]=="HOLD"
    register["evidence_files"][0]["sha256"]="0"*64
    with pytest.raises(ValueError,match="SHA-256"):
        review_evidence(register,tmp_path)


def test_rights_evidence_rejects_path_escape(tmp_path):
    register={
        "source_repo":SOURCE_REPO,"source_revision":SOURCE_SHA,
        "source_sha256":SOURCE_LFS_SHA256,
        "evidence_files":[{"path":"../outside.pdf","sha256":"0"*64}],
    }
    with pytest.raises(ValueError,match="dışına"):
        review_evidence(register,tmp_path)
