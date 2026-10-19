"""FAQVec-TR v0.2 hak, veri sızıntısı ve benchmark regresyon kontrolleri."""
import hashlib
import json

import numpy as np
import pytest

from app import faqvec_v2_data as d
from app import faqvec_v2_metrics as m
from scripts.benchmark_faqvec_v2 import build_suite, benchmark


def row(ident, split, question=None):
    return {"intent_id": ident, "split": split,
            "question": question or f"Örnek soru {ident}",
            "alternatives": [f"Alternatif {ident}"], "source_id": "test"}


def test_bundled_groups_split_and_no_cross_leakage():
    groups = d.load_bundled_demo()
    assert len(groups) == 110
    counts = d.validate_intents(groups)
    assert sum(counts.values()) == 110 and min(counts.values()) > 0
    assert all(not item["rights_verified"] for item in groups)
    with pytest.raises(d.DatasetError):
        d.validate_intents([row("a", "train"), row("a", "test")])
    with pytest.raises(d.DatasetError):
        d.validate_intents([
            row("a", "train", question="Benim aynı sorum"),
            row("b", "test", question="BENİM aynı sorum?"),
        ])


def test_negatives_need_explicit_human_approval(tmp_path):
    rows = [row("a", "train"), row("b", "train"), row("c", "test")]
    assert len(d.positive_pairs(rows)) == 2
    out = tmp_path / "neg.jsonl"
    d.write_candidate_negatives(rows, out, top_k=1)
    pending = d._read_jsonl(out)
    assert len(pending) == 2
    assert all(item["status"] == "needs_human_review" for item in pending)
    assert d.approved_triplets(out, rows) == []
    pending[0].update(status="approved", reviewed_by="human")
    out.write_text(json.dumps(pending[0]), encoding="utf-8")
    assert len(d.approved_triplets(out, rows)) == 1
    pending[0]["negative_intent"] = "c"
    out.write_text(json.dumps(pending[0]), encoding="utf-8")
    with pytest.raises(d.DatasetError):
        d.approved_triplets(out, rows)


def test_licensed_manifest_enforces_explicit_commercial_rights(tmp_path):
    samples = [row("a", "train")]
    content = (json.dumps(samples[0])+"\n").encode()
    (tmp_path/"sample.jsonl").write_bytes(content)
    evidence = b"Bu veri senaryo yazari tarafindan sifirdan uretilmistir; kaynak yok."
    (tmp_path/"rights.txt").write_bytes(evidence)
    manifest = {"schema_version":1, "sources":[{
        "id":"test","origin_url":"local://original-faq-test",
        "license_spdx":"OWNED","reviewed_by":"human reviewer",
        "origin_kind":"self_authored","rights_review_complete":True,
        "rights_evidence_path":"rights.txt",
        "evidence_sha256":hashlib.sha256(evidence).hexdigest(),
        "commercial_training_approved":False,
    }],"files":[{"path":"sample.jsonl",
                 "sha256":hashlib.sha256(content).hexdigest()}]}
    file = tmp_path/"manifest.json"
    file.write_text(json.dumps(manifest),encoding="utf-8")
    assert d.load_approved_sources(file)[0] == samples
    with pytest.raises(d.DatasetError):
        d.load_approved_sources(file,for_commercial=True)
    manifest["sources"][0]["license_spdx"] = "CC-BY-NC-4.0"
    manifest["sources"][0]["commercial_training_approved"] = True
    file.write_text(json.dumps(manifest),encoding="utf-8")
    with pytest.raises(d.DatasetError):
        d.load_approved_sources(file,for_commercial=True)
    manifest["sources"][0]["license_spdx"] = "OWNED"
    manifest["files"][0]["path"] = "../outside.jsonl"
    file.write_text(json.dumps(manifest),encoding="utf-8")
    with pytest.raises(d.DatasetError):
        d.load_approved_sources(file)


def test_recall_wrong_matches_and_abstention():
    scores = np.array([[.9,.1],[.8,.2],[.3,.2],[.8,.15],[.4,.35]])
    report = m.evaluate_matrix(scores,["A","B"],["A","B","A",None,None],.6)
    assert report["recall_at_1"] == pytest.approx(2/3,abs=1e-4)
    assert report["wrong_match_rate"] == pytest.approx(1/3,abs=1e-4)
    assert report["positive_abstention_rate"] == pytest.approx(1/3,abs=1e-4)
    assert report["false_answer_rate"] == .5
    assert report["no_answer_accuracy"] == .5
    with pytest.raises(ValueError):
        m.thresholds_on_validation(scores[:2],["A","B"],["A","B"])
    cutoff = m.thresholds_on_validation(
        np.array([[.9,.1],[.1,.9],[.35,.3]]),
        ["A","B"],["A","B",None])
    assert .35 < cutoff <= .9


def test_demo_benchmark_reports_diagnostic_not_commercial():
    report = benchmark(d.load_bundled_demo(), [("tfidf",None,False)])
    assert report["gallery_size"] == 110
    assert report["validation_queries"] > 0
    assert report["test_queries"] > 0
    assert report["models"][0]["diagnostic_only"]
    assert report["models"][0]["test"]["no_answer_accuracy"] is None


def test_no_answer_human_review_changes_calibration(tmp_path):
    dataset=[row("a","train"),row("b","validation"),row("c","test")]
    f=tmp_path/"neg.jsonl"
    f.write_text("\n".join(json.dumps(x) for x in [
        {"split":"validation","query":"Kahve yapıyor musunuz",
         "expected_id":None,"review_status":"approved","reviewed_by":"human"},
        {"split":"test","query":"Okul saat kaçta açılıyor",
         "expected_id":None,"review_status":"approved","reviewed_by":"human"},
    ]),encoding="utf-8")
    _,_,q=build_suite(dataset,f)
    assert sum(x["expected_id"] is None for x in q["test"]) == 1
    report=benchmark(dataset,[("tfidf",None,False)],f)
    assert report["models"][0]["validation_calibrated"] is True
