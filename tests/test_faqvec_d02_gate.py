"""D02 closure must not assert real rights or human review without evidence."""
import json

from scripts.faqvec_d02_acceptance import assess
from scripts.faqvec_d02_review import generate_bundle, write_new
from scripts.audit_faqvec_d01 import SOURCE_LFS_SHA256


def tiny_jsonl(path):
    phrases=[
        ("Nerede kargom", "Paketim nerede", 1),
        ("Nasıl iade yaparım", "Ürünü geri vermek istiyorum", 1),
        ("Siparişi iptal", "Siparişten vazgeçmek", 1),
        ("Nerede kargom", "Nasıl iade yaparım", 0),
    ]
    path.write_text("".join(json.dumps(
        {"sentence1":a,"sentence2":b,"label":label},ensure_ascii=False)+"\n"
        for a,b,label in phrases),encoding="utf-8")
    return path


def test_missing_human_and_legal_evidence_cannot_close_d02():
    status=assess()
    assert status["checks"]["commercial_E5_fine_tuning"]=="BLOCKED"
    assert not status["commercial_training_approved"]
    assert status["checks"]["rights_documents"]=="HOLD"
    assert status["checks"]["two_independent_review_files"]=="HOLD"
    assert status["blockers"]


def test_candidate_bundle_is_not_trusted_if_source_is_fixture(tmp_path):
    source=tiny_jsonl(tmp_path/"samples.jsonl")
    bundle,freeze,summary=generate_bundle(source,verify_pin=False)
    bundle_file=tmp_path/"bundle.json"
    freeze_file=tmp_path/"freeze.json"
    write_new(bundle_file,bundle)
    write_new(freeze_file,freeze)
    result=assess(bundle_path=bundle_file,freeze_path=freeze_file)
    assert result["checks"]["bundle"]=="HOLD"
    assert result["checks"]["frozen_test_candidates"]=="HOLD"
    assert not result["d02_closed"]
    assert SOURCE_LFS_SHA256!=bundle["source_sha256"]


def test_invalid_reviews_and_rights_entries_never_make_pass(tmp_path):
    left=tmp_path/"left.json"
    right=tmp_path/"right.json"
    legal=tmp_path/"rights.json"
    for path,data in ((left,{"schema":1,"bundle_id":"incorrect","reviewer_id":"A","decisions":[]}),
                      (right,{"schema":1,"bundle_id":"incorrect","reviewer_id":"B","decisions":[]}),
                      (legal,{"source_repo":"not-the-source"})):
        path.write_text(json.dumps(data),encoding="utf-8")
    result=assess(review_a_path=left,review_b_path=right,rights_path=legal)
    assert result["checks"]["rights_documents"]=="HOLD"
    assert result["checks"]["two_independent_review_files"]=="HOLD"
    assert result["commercial_training_approved"] is False


def test_windows_review_setup_and_ui_are_real_repo_files():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    batch=(root/"setup_faqvec_d02_windows.bat").read_text(encoding="utf-8")
    ui=(root/"frontend/d02_review_offline.html").read_text(encoding="utf-8")
    assert "--check-only" in batch
    assert "faqvec_d02_acceptance" in batch
    assert "faqvec_d02_review prepare" in batch
    assert "bundle_id" in ui and "reviewer_id" in ui
    assert "new Blob" in ui

def test_d02_source_cannot_be_approved_by_changing_manifest_checkbox(tmp_path):
    """An unverified rights claim is not an authorization to train commercially."""
    import hashlib
    import pytest
    from app.faqvec_v2_data import load_approved_sources, DatasetError
    record={
        "intent_id":"candidate-1","split":"train",
        "question":"Kargom nerede?",
        "alternatives":["Paketim nerede?"],
        "source_id":"turkish-paraphrase-candidate",
    }
    raw=(json.dumps(record,ensure_ascii=False)+"\n").encode("utf-8")
    dataset=tmp_path/"private.jsonl"
    dataset.write_bytes(raw)
    manifest={
        "schema_version":1,
        "sources":[{
            "id":"turkish-paraphrase-candidate",
            "origin_url":"https://huggingface.co/datasets/dogukanvzr/ml-paraphrase-tr",
            "license_spdx":"Apache-2.0",
            "reviewed_by":"unverified-local-checkbox",
            "evidence_sha256":"a"*64,
            "commercial_training_approved":True,
        }],
        "files":[{"path":"private.jsonl","sha256":hashlib.sha256(raw).hexdigest()}],
    }
    document=tmp_path/"manifest.json"
    document.write_text(json.dumps(manifest),encoding="utf-8")
    with pytest.raises(DatasetError,match="D02"):
        load_approved_sources(document,for_commercial=True)
    manifest["sources"][0]["id"]="renamed-source"
    manifest["sources"][0]["origin_url"]="https://huggingface.co/datasets/dogukanvzr/ml-paraphrase-tr/tree/main"
    document.write_text(json.dumps(manifest),encoding="utf-8")
    with pytest.raises(DatasetError,match="D02"):
        load_approved_sources(document,for_commercial=True)
