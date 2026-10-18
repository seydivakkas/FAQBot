"""Haricî Türkçe eşanlamlı çiftlerin güvenli hazırlanması ve karantina testleri.

Bu testler gerçek haricî veri indirip ticari hakları kendiliğinden onaylamaz.
"""
import hashlib
import json
import pytest

from scripts.prepare_faqvec_v2_pairs import (
    PairDataError, prepare_pairs, read_pairs, save_candidate_package,
)
from app.faqvec_v2_data import load_approved_sources, validate_intents


def make(a,b,label):
    return {"sentence1":a,"sentence2":b,"label":label}


def examples():
    return [
        make("Kargom nerede", "Paketim hangi aşamada",1),
        make("Paketim hangi aşamada","Gönderi takip nasıl yapılır",1),
        make("Şifremi unuttum","Hesabıma nasıl giriş yaparım",1),
        make("Kupon nasıl kullanılır","İndirim kodu nereye yazılır",1),
        make("Kargom nerede","Şifremi unuttum",0),
        make("Kupon nasıl kullanılır","Kargom nerede",0),
    ]


def test_union_find_keeps_paraphrase_chain_in_one_intent():
    rows, negatives, report=prepare_pairs(examples())
    assert len(rows)==3
    assert sum(report["split_intents"].values())==3
    assert any(len(row["alternatives"])==2 for row in rows)
    assert all(r["rights_verified"] is False for r in rows)
    assert all(c["status"]=="needs_human_review" for c in negatives)
    assert validate_intents(rows)


def test_counter_labels_and_positive_cluster_conflicts_fail_closed():
    with pytest.raises(PairDataError, match="etiket"):
        prepare_pairs([
            make("Paket nerede","Kargo nerede",1),
            make("Kargo nerede","Paket nerede",0)
        ])
    with pytest.raises(PairDataError, match="negatif çift"):
        prepare_pairs([
            make("Paket nerede","Kargo nerede",1),
            make("Kargo nerede","Gönderi nerede",1),
            make("Paket nerede","Gönderi nerede",0)
        ])


def test_cluster_limit_prevents_ambiguous_transitive_chain():
    rows=[make(f"Aktarım {i}",f"Aktarım {i+1}",1) for i in range(7)]
    rows += [
        make("Yeni İade A","Yeni İade B",1),
        make("Ödeme A","Ödeme B",1),
    ]
    result,_,summary=prepare_pairs(rows,max_component_size=5)
    assert len(result)==2
    assert summary["statistics"]["quarantined_large_clusters"]==1


def test_pair_import_deterministic_and_no_cross_split_leakage():
    first, _, _=prepare_pairs(examples())
    second, _, _=prepare_pairs(list(reversed(examples())))
    assert first==second
    phrases={}
    for row in first:
        for text in [row["question"],*row["alternatives"]]:
            assert text not in phrases
            phrases[text]=row["split"]


def test_json_jsonl_read_and_input_limit(tmp_path):
    content=examples()
    p=tmp_path/"examples.json"
    p.write_text(json.dumps(content,ensure_ascii=False),encoding="utf-8")
    assert list(read_pairs(p))==content
    with pytest.raises(PairDataError,match="limit"):
        list(read_pairs(p,limit=2))
    other=tmp_path/"examples.jsonl"
    other.write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in content),
                     encoding="utf-8")
    assert list(read_pairs(other))==content


def test_candidate_manifest_remains_unapproved_for_commercial(tmp_path):
    rows,negatives,report=prepare_pairs(examples())
    raw=tmp_path/"raw.jsonl"
    raw.write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in examples()),
                   encoding="utf-8")
    card=tmp_path/"README.md"
    card.write_text("license: apache-2.0; origin: independent review needed",encoding="utf-8")
    manifest_path=save_candidate_package(
        rows,negatives,report,source_file=raw,output_dir=tmp_path/"prepared",
        source_repo="dogukanvzr/ml-paraphrase-tr",revision="f"*40,
        card_path=card,
    )
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["commercial_acceptance"]=="HOLD"
    assert manifest["sources"][0]["reviewed_by"] is None
    assert manifest["sources"][0]["commercial_training_approved"] is False
    assert manifest["sources"][0]["evidence_sha256"]==hashlib.sha256(card.read_bytes()).hexdigest()
    assert len(negatives)==len((tmp_path/"prepared"/"negative_candidates_unreviewed.jsonl").read_text(encoding="utf-8").splitlines())
    with pytest.raises(Exception):
        load_approved_sources(manifest_path,for_commercial=True)


def test_malformed_pair_rows_do_not_make_training_labels():
    rows,negative,stats=prepare_pairs([
        make("","Eksik çift",1),
        make("Aynı soru","Aynı Soru?",1),
        make("A sorusu","B sorusu",1),
        make("C sorusu","D sorusu",1),
    ])
    assert len(rows)==2
    assert stats["statistics"]["invalid_or_identical"]==2
