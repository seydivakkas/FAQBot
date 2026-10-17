"""HTTP sözleşmesi ve frontend dosyalarının basit testleri."""


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_root_redirect(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/app"


def test_faq_list(client):
    response = client.get("/faqs")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 20
    assert len(data["faqs"]) == 20
    assert isinstance(data["faqs"][0]["alternative_questions"], list)


def test_faq_list_categories(client):
    """Arayüzde gösterilecek 20 soru, 4 kategoriye eşit dağılmalı."""
    data = client.get("/faqs").json()
    categories = {}
    for faq in data["faqs"]:
        categories[faq["category"]] = categories.get(faq["category"], 0) + 1
        assert faq["question"].strip()
        assert faq["answer"].strip()
    assert categories == {"kargo": 5, "iade": 5, "odeme": 5, "hesap": 5}


def test_exact_question(client):
    response = client.post("/chat", json={"message": "Kargom ne zaman gelir?"})
    assert response.status_code == 200
    data = response.json()
    assert data["matched_question"] == "Kargom ne zaman gelir?"
    assert data["category"] == "kargo"
    assert data["match_type"] == "exact"
    assert data["match_score"] == 1.0
    assert "1-3 iş günü" in data["answer"]


def test_alternative_question(client):
    data = client.post(
        "/chat", json={"message": "Ürünü geri göndermek istiyorum."}
    ).json()
    assert data["category"] == "iade"
    assert data["match_type"] == "exact"


def test_unknown_question_fallback(client):
    data = client.post(
        "/chat", json={"message": "Nebula kuasar teleskop astronomi"}
    ).json()
    assert data["match_type"] == "none"
    assert data["matched_question"] is None
    assert data["category"] is None
    assert "doğrulanmış bir cevabım" in data["answer"]


def test_blank_message_rejected(client):
    assert client.post("/chat", json={"message": "   "}).status_code == 422


def test_missing_message_rejected(client):
    assert client.post("/chat", json={}).status_code == 422


def test_too_long_message_rejected(client):
    assert client.post("/chat", json={"message": "x" * 501}).status_code == 422


def test_frontend_is_served(client):
    response = client.get("/app")
    assert response.status_code == 200
    assert "FAQBot" in response.text
    assert client.get("/static/style.css").status_code == 200
    assert client.get("/static/app.js").status_code == 200


def test_faq_panel_wired_to_api(client):
    """Soru panelinin DOM elemanları ve gerçek /faqs çağrısı mevcut."""
    html = client.get("/app").text
    js = client.get("/static/app.js").text
    for element_id in ("faqToggle", "faqPanel", "faqList", "faqSearch", "faqClose"):
        assert 'id="' + element_id + '"' in html
    for category in ("kargo", "iade", "odeme", "hesap"):
        assert 'data-category="' + category + '"' in html
    assert 'fetch("/faqs")' in js
    assert "faq.question" in js
    assert "sendMessage(faq.question)" in js
    assert 'id="settingsToggle"' in html
    assert 'id="faqEditForm"' in html
