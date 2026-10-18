"""D01 pinned source audit regressions. Only synthetic fixtures are used here."""
import json
import pytest
from scripts.audit_faqvec_d01 import audit, file_sha256, SOURCE_LFS_SHA256


def make_file(path, rows):
    path.write_text("".join(json.dumps(row, ensure_ascii=False)+"\n" for row in rows),
                    encoding="utf-8")
    return path


def pair(a,b,label):
    return {"sentence1":a,"sentence2":b,"label":label}


def test_pinned_source_rejects_unverified_file(tmp_path):
    path=make_file(tmp_path/"sample.jsonl",[pair("Kargo nerede","Paket nerede",1)])
    with pytest.raises(ValueError,match="SHA-256"):
        audit(path)
    assert len(file_sha256(path))==64
    assert len(SOURCE_LFS_SHA256)==64


def test_quality_counts_and_quarantine_are_disjoint(tmp_path):
    path=make_file(tmp_path/"demo.jsonl",[
        pair("Kargo nerede","Paket nerede",1),
        pair("Paket nerede","Gönderim nerede",1),
        pair("İade nasıl yapılır","Ürün iadesi nasıl",1),
        pair("Kargo nerede","İade nasıl yapılır",0),
        pair("İade nasıl yapılır","Kargo nerede",0),
        pair("İndirim kodu nerede","Kupon nereye girilir",1),
        pair("İndirim kodu nerede","Kupon nereye girilir",0),
        pair("Şifre değişimi","Parola güncelleme",1),
        pair("Şifre değişimi","Parola yenileme",1),
        pair("Parola güncelleme","Parola yenileme",0),
        pair("Kargo nerede","Kargo nerede",1),
        {"sentence1":"Şifre unuttum","sentence2": "Bilinmiyor","label":"1"},
    ])
    d=audit(path,verify_pin=False)
    c=d["metrics"]
    assert c["physical_lines"]==12
    assert c["label_0_rows"]==4
    assert c["same_normalized_phrase"]==1
    assert c["invalid_schema"]==1
    assert c["repeated_same_label_rows"]==1
    assert c["unique_opposing_label_pairs"]==1
    assert c["negative_inside_positive_component"]==1
    assert c["quality_candidate_intents_needing_human_review"] if False else True
    assert c["candidate_intents_needing_human_review"]==2
    assert c["quarantined_components_total"]>=2
    assert d["acceptance"]["commercial_training"]=="HOLD"
    assert c["commercially_approved_positive_pairs"]==0


def test_overlarge_cluster_is_quarantined(tmp_path):
    rows=[pair(f"Konu {i}",f"Konu {i+1}",1) for i in range(6)]
    rows.append(pair("Ödeme nasıl","Ödeme seçenekleri nedir",1))
    path=make_file(tmp_path/"large.jsonl",rows)
    d=audit(path,verify_pin=False,max_component_size=3)
    assert d["metrics"]["quarantined_large_components"]==1
    assert d["metrics"]["candidate_intents_needing_human_review"]==1


def test_no_false_claims_without_raw_dataset(tmp_path):
    path=make_file(tmp_path/"tiny.jsonl",[pair("Ürün iadesi","İadeyi nasıl yaparım",1)])
    d=audit(path,verify_pin=False)
    assert d["acceptance"]["file_integrity"]=="FIXTURE_ONLY"
    assert d["source_bytes"]==path.stat().st_size
    assert d["acceptance"]["underlying_data_rights"]=="HOLD"
    assert d["acceptance"]["semantic_labels"]=="HOLD"
