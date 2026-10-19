"""User policy: external corpora are not FAQVec-TR training data."""
import hashlib
import json

import pytest

from app.faqvec_v2_data import DatasetError, load_approved_sources


def manifest_fixture(folder, *, license="OWNED", origin="self_authored",
                     rights_complete=True, evidence=True,
                     source_url="local://self-authored-example"):
    folder.mkdir(parents=True, exist_ok=True)
    data={
        "intent_id":"original-self-001",
        "split":"train",
        "question":"Kendi hazırladığım özgün soru nedir?",
        "alternatives":["Özgün sorunun başka ifadesi nedir?"],
        "source_id":"original-source",
    }
    contents=(json.dumps(data,ensure_ascii=False)+"\n").encode("utf-8")
    (folder/"original.jsonl").write_bytes(contents)
    proof=b"Test: original self authored. No copied third-party sentences."
    if evidence:
        (folder/"rights.txt").write_bytes(proof)
    doc={
        "schema_version":1,
        "sources":[{
            "id":"original-source",
            "origin_url":source_url,
            "license_spdx":license,
            "reviewed_by":"original_author",
            "origin_kind":origin,
            "rights_review_complete":rights_complete,
            "rights_evidence_path":"rights.txt",
            "evidence_sha256":hashlib.sha256(proof).hexdigest(),
            "commercial_training_approved":True,
        }],
        "files":[{"path":"original.jsonl","sha256":hashlib.sha256(contents).hexdigest()}],
    }
    dest=folder/"manifest.json"
    dest.write_text(json.dumps(doc,ensure_ascii=False),encoding="utf-8")
    return dest,doc


def test_local_self_authored_data_can_be_loaded_if_evidence_matches(tmp_path):
    manifest,_=manifest_fixture(tmp_path)
    rows,_=load_approved_sources(manifest,for_commercial=True)
    assert len(rows)==1


def test_cc0_requires_verified_provenance(tmp_path):
    manifest,_=manifest_fixture(tmp_path,license="CC0-1.0",origin="verified_cc0")
    rows,_=load_approved_sources(manifest,for_commercial=True)
    assert len(rows)==1


@pytest.mark.parametrize("license",["Apache-2.0","MIT","BSD-3-Clause","CC-BY-4.0"])
def test_open_license_does_not_mean_copyright_free(tmp_path,license):
    manifest,_=manifest_fixture(tmp_path,license=license)
    with pytest.raises(DatasetError,match="OWNED"):
        load_approved_sources(manifest)


def test_missing_evidence_or_source_rights_review_fails_closed(tmp_path):
    manifest,_=manifest_fixture(tmp_path/"missing",evidence=False)
    with pytest.raises(DatasetError,match="Kanıt"):
        load_approved_sources(manifest)
    other,_=manifest_fixture(tmp_path/"review",rights_complete=False)
    with pytest.raises(DatasetError,match="belgelenmemiş"):
        load_approved_sources(other)


def test_source_origin_kind_must_match_license(tmp_path):
    manifest,_=manifest_fixture(tmp_path,license="OWNED",origin="verified_cc0")
    with pytest.raises(DatasetError,match="köken türü"):
        load_approved_sources(manifest)


def test_original_unverified_third_party_corpus_is_not_allowed_even_with_owned_label(tmp_path):
    manifest,data=manifest_fixture(tmp_path)
    data["sources"][0]["origin_url"]="https://huggingface.co/datasets/dogukanvzr/ml-paraphrase-tr"
    manifest.write_text(json.dumps(data),encoding="utf-8")
    with pytest.raises(DatasetError,match="D02"):
        load_approved_sources(manifest)


def test_network_data_downloads_are_deactivated():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    workflow_paths=[
        root/".github/workflows/faqvec-d01.yml",
        root/".github/workflows/faqvec-d02.yml",
    ]
    for path in workflow_paths:
        source=path.read_text(encoding="utf-8")
        assert "scripts.fetch_faqvec_d01_original" not in source
        assert "huggingface-hub" not in source
    for script in ("scripts/fetch_faqvec_d01_original.py",
                   "scripts/fetch_faqvec_v2_pairs.py"):
        source=(root/script).read_text(encoding="utf-8")
        assert "snapshot_download" not in source
        assert "hf_hub_download" not in source
    assert (root/"docs/VERI_KAYNAGI_KESIN_POLITIKA.md").exists()
