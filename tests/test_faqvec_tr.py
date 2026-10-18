"""FAQVec-TR: kendi ağırlık eğitimi, güvenli seri hale getirme ve entegrasyon.

Ağ erişimi veya üçüncü taraf temel model ağırlığı kullanılmaz.
"""
import hashlib
import json
import numpy as np
from app import faqvec_tr
from app import semantic
from scripts import train_faqvec_tr


def tiny_groups():
    return [
        ["Kargom nerede?", "Paketim nerede?", "Kargo takibi nasıl yapılır?"],
        ["Ürünümü nasıl geri verebilirim?", "İade işlemi ne şekilde yapılır?"],
        ["Kredi kartı kabul ediyor musunuz?", "Kartla ödeme yapabilir miyim?"],
        ["Hesabımın şifresini unuttum", "Parolamı nasıl yenilerim?"],
        ["Sipariş iptali nasıl olur?", "Siparişi iptal edeceğim"],
        ["Kampanya kodunu nereden uygularım?", "Kuponu nereye yazmalıyım?"],
    ]


def build(tmp_path, epochs=2):
    model, stats = faqvec_tr.train_groups(tiny_groups(), epochs=epochs, seed=17)
    folder = tmp_path / "faqvec"
    faqvec_tr.save_model(model, folder, {"validation":{"independent_real_customer_test":False}})
    return folder, stats


def test_feature_hash_is_deterministic_and_handles_turkish():
    a = faqvec_tr.features("Ürünümü nasıl iade ederim?")
    b = faqvec_tr.features("Ürünümü nasıl iade ederim?")
    assert np.array_equal(a, b)
    assert len(a) > 10
    assert a.min() >= 0 and a.max() < faqvec_tr.BUCKETS
    assert not np.array_equal(a, faqvec_tr.features("Kargo teslimatı"))


def test_train_encoder_local_and_safe_weights(tmp_path):
    folder, stats = build(tmp_path)
    assert stats["train_intents"] == 6
    assert stats["epochs"] == 2
    encoder = faqvec_tr.load_model(folder)
    vectors = encoder.encode(["Kargom nerede?", "Siparişim nerede?"])
    assert vectors.shape == (2, faqvec_tr.DIM)
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-4)
    assert np.isfinite(vectors).all()
    assert np.allclose(faqvec_tr.load_model(folder).encode(["Kargom nerede?"]),
                       encoder.encode(["Kargom nerede?"]))
    details = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    assert details["pretrained_external_weights"] is False
    assert details["commercial_acceptance"] == "HOLD"
    assert details["weights_sha256"] == hashlib.sha256(
        (folder / "weights.npz").read_bytes()
    ).hexdigest()


def test_bad_or_missing_weights_are_rejected(tmp_path):
    folder, _ = build(tmp_path)
    with open(folder / "weights.npz", "ab") as file:
        file.write(b"tamper")
    try:
        faqvec_tr.load_model(folder)
        assert False, "Hash uyuşmazlığı reddedilmeli"
    except faqvec_tr.OwnModelError as error:
        assert "SHA-256" in str(error)
    try:
        faqvec_tr.load_model(tmp_path / "missing")
        assert False, "Eğitim öncesi model olmamalı"
    except faqvec_tr.OwnModelError:
        pass


def test_training_is_deterministic():
    first, _ = faqvec_tr.train_groups(tiny_groups(), epochs=2, seed=11)
    second, _ = faqvec_tr.train_groups(tiny_groups(), epochs=2, seed=11)
    assert np.array_equal(first.weights, second.weights)


def test_semantic_selection_and_duplicate_scan(client, tmp_path):
    assert client.get("/settings/semantic").json()["method"] == "tfidf"
    own = client.get("/settings/semantic").json()
    assert "faqvec-tr-v0.1" in own["default_own_model_path"]
    missing = client.put("/settings/semantic", json={
        "method": "faqvec_tr", "model_path": str(tmp_path / "not_trained")
    })
    assert missing.status_code == 422
    assert client.get("/settings/semantic").json()["method"] == "tfidf"

    folder, _ = build(tmp_path)
    response = client.put("/settings/semantic", json={
        "method": "faqvec_tr", "model_path": str(folder),
    })
    assert response.status_code == 200
    assert response.json()["method"] == "faqvec_tr"
    assert response.json()["ready_to_load"] is True
    scan = client.get("/faqs/duplicates")
    assert scan.status_code == 200
    assert scan.json()["method"] == "faqvec_tr"
    assert client.get("/faqs").json()["total"] == 110
    # Algoritma ayarı sohbet motoruna müdahale etmez.
    assert client.post("/chat", json={
        "message":"Kargom ne zaman gelir?"
    }).json()["match_type"] == "exact"


def test_model_can_be_evaluated_with_local_review_data(client, tmp_path):
    folder, _ = build(tmp_path)
    assert client.put("/settings/semantic", json={
        "method": "faqvec_tr", "model_path": str(folder)
    }).status_code == 200
    assert client.put("/reviews/settings", json={"enabled":True}).status_code == 200
    client.post("/chat", json={"message":"Kargom ne zaman gelir?"})
    record = client.get("/reviews").json()["rows"][0]
    assert client.patch("/reviews/" + str(record["id"]), json={
        "status":"correct"
    }).status_code == 200
    metrics = client.post("/reviews/evaluate", json={
        "include_embedding":True
    })
    assert metrics.status_code == 200
    assert metrics.json()["embedding"]["method"] == "faqvec_tr"
    assert metrics.json()["embedding"]["status"] == "ok"


def test_offline_train_script_uses_repository_faqs():
    corpus = train_faqvec_tr._source()
    assert len(corpus) == 110
    assert all(len(c) >= 2 for c in corpus)
    assert not any("https://" in q for group in corpus for q in group)


def test_ui_allows_original_embedding(client):
    page = client.get("/app").text
    js = client.get("/static/app.js").text
    assert '<option value="faqvec_tr">' in page
    assert "setup_faqvec_windows.bat" in page
    assert 'dupMethod.value === "faqvec_tr"' in js
