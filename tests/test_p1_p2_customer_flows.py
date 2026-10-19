"""P1–P2 kabul: SSS önerileri, feedback, destek talebi ve gerçek API'li demo akışı."""
from fastapi.testclient import TestClient

from app.main import app


def test_chat_keeps_legacy_exact_and_shows_feedback_id(client):
    res = client.post("/chat", json={"message":"Kargom ne zaman gelir?"})
    assert res.status_code == 200
    chat=res.json()
    assert chat["match_type"] == "exact"
    assert chat["faq_id"] > 0
    assert chat["suggestions"] == []


def test_unknown_chat_can_suggest_but_does_not_hallucinate_answer(client):
    res = client.post("/chat", json={"message":"Galaktik kuasar astronomi gözlemi"})
    assert res.status_code == 200
    row=res.json()
    assert row["match_type"] == "none"
    assert row["faq_id"] is None
    assert row["matched_question"] is None
    assert len(row["suggestions"]) <= 3
    assert all(set(x)>= {"faq_id","question","category","score","is_answer"}
               and x["is_answer"] is False for x in row["suggestions"])


def test_suggestions_are_unique_and_only_questions(client):
    r=client.post("/chat",json={"message":"Kargom geldi ama hasarlı bir paket teslim aldım"})
    assert r.status_code == 200
    options=r.json()["suggestions"]
    assert len(options) <= 3
    assert len({x["faq_id"] for x in options}) == len(options)
    assert all("answer" not in x for x in options)


def test_feedback_is_explicit_and_has_no_chat_text(client):
    initial=client.get("/feedback/summary").json()
    assert initial["total"] == 0
    faq=client.post("/chat",json={"message":"Kargom ne zaman gelir?"}).json()
    yes=client.post("/feedback",json={"faq_id":faq["faq_id"],"helpful":True})
    no=client.post("/feedback",json={"faq_id":None,"helpful":False})
    assert yes.status_code == 201
    assert no.status_code == 201
    data=client.get("/feedback/summary").json()
    assert data["total"] == 2
    assert data["helpful"] == 1
    assert data["not_helpful"] == 1
    assert "question" not in data
    assert client.post("/feedback",json={"faq_id":999999,"helpful":True}).status_code == 404
    assert client.post("/feedback",json={"faq_id":1,"helpful":"yes"}).status_code == 422


def test_support_tickets_persist_and_have_trackable_status(client):
    res=client.post("/support/tickets",json={
        "subject":"Gönderim hakkında bilgi istiyorum",
        "detail":"Bu yalnız kurgusal denemedir."
    })
    assert res.status_code == 201
    ticket=res.json()
    assert ticket["status"] == "open"
    assert ticket["demo_local_only"] is True
    assert ticket["id"] > 0
    assert [event["status"] for event in ticket["history"]] == ["open"]
    detail=client.get("/support/tickets/"+str(ticket["id"]))
    assert detail.status_code == 200
    assert detail.json()["subject"] == ticket["subject"]
    listing=client.get("/support/tickets").json()["tickets"]
    assert len(listing) == 1
    updated=client.patch("/support/tickets/"+str(ticket["id"]),
                         json={"status":"in_progress"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"
    updated=client.patch("/support/tickets/"+str(ticket["id"]),
                         json={"status":"resolved"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "resolved"
    assert [event["status"] for event in updated.json()["history"]] == [
        "open", "in_progress", "resolved"
    ]
    # Aynı durum yeniden kaydedilirse sahte geçmiş adımı üretilmez.
    repeated=client.patch("/support/tickets/"+str(ticket["id"]),json={"status":"resolved"})
    assert len(repeated.json()["history"]) == 3
    assert client.get("/support/tickets/999999").status_code == 404
    assert client.patch("/support/tickets/999999",json={"status":"resolved"}).status_code == 404


def test_support_ticket_invalid_data_and_status_blocked(client):
    assert client.post("/support/tickets",
                       json={"subject":"kısa","detail":""}).status_code == 422
    assert client.post("/support/tickets",
                       json={"subject":"a"*181}).status_code == 422
    assert client.patch("/support/tickets/1",
                        json={"status":"closed"}).status_code == 422
    assert client.get("/support/tickets").json()["tickets"] == []


def test_kurgusal_order_and_shipping_statuses(client):
    all_orders=client.get("/demo/orders")
    assert all_orders.status_code == 200
    orders=all_orders.json()["orders"]
    assert len(orders) == 3
    assert all(o["code"].startswith("DEMO-") and o["demo"] is True
               and o["real_tracking"] is False for o in orders)
    by_code={o["code"]:o for o in orders}
    assert by_code["DEMO-1001"]["shipment"] == "not_shipped"
    assert by_code["DEMO-1002"]["shipment"] == "in_transit"
    assert by_code["DEMO-1003"]["shipment"] == "delivered"
    assert len(by_code["DEMO-1002"]["events"]) > 2
    assert client.get("/demo/orders/DEMO-1002").json()["code"] == "DEMO-1002"
    assert client.get("/demo/orders/REAL-1002").status_code == 404


def test_demo_return_is_only_for_delivered_order_and_trackable(client):
    for code in ["DEMO-1001","DEMO-1002"]:
        denied=client.post("/demo/returns",json={
            "order_code":code,"reason":"changed_mind"
        })
        assert denied.status_code == 409
    res=client.post("/demo/returns",json={
        "order_code":"DEMO-1003","reason":"wrong_item"
    })
    assert res.status_code == 201
    request=res.json()
    assert request["demo"] is True
    assert request["status"] == "requested"
    assert [x["status"] for x in request["history"]] == ["requested"]
    assert client.post("/demo/returns",json={
        "order_code":"DEMO-1003","reason":"damaged"
    }).status_code == 409
    assert len(client.get("/demo/returns").json()["returns"]) == 1
    assert client.get("/demo/returns/"+str(request["id"])).json()["order_code"] == "DEMO-1003"
    changed=client.patch("/demo/returns/"+str(request["id"]),json={"status":"reviewing"})
    assert changed.status_code == 200
    assert changed.json()["status"] == "reviewing"
    changed=client.patch("/demo/returns/"+str(request["id"]),json={"status":"approved"})
    assert changed.json()["status"] == "approved"
    assert [e["status"] for e in changed.json()["history"]] == [
        "requested", "reviewing", "approved"
    ]
    duplicate=client.patch("/demo/returns/"+str(request["id"]),json={"status":"approved"})
    assert len(duplicate.json()["history"]) == 3
    assert client.get("/demo/returns/999999").status_code == 404
    assert client.patch("/demo/returns/999999",json={"status":"approved"}).status_code == 404


def test_untrusted_web_origin_cannot_mutate_local_tickets_returns_feedback(client):
    cross_origin={"Origin":"https://malicious.example"}
    assert client.post("/support/tickets",headers=cross_origin,
                       json={"subject":"Açık yardım başvurum"}).status_code == 403
    assert client.post("/feedback",headers=cross_origin,
                       json={"faq_id":None,"helpful":True}).status_code == 403
    assert client.post("/demo/returns",headers=cross_origin,
                       json={"order_code":"DEMO-1003","reason":"other"}).status_code == 403
    assert client.get("/support/tickets",headers=cross_origin).status_code == 403
    with TestClient(app, base_url="http://127.0.0.1", client=("198.51.100.30",43000)) as external:
        assert external.get("/demo/orders").status_code == 403


def test_frontend_connects_all_p1_p2_controls(client):
    html=client.get("/app").text
    js=client.get("/static/app.js").text
    css=client.get("/static/style.css").text
    for ident in ("supportForm","supportTickets","supportSubject",
                  "demoOrderForm","demoReturnForm","demoOrderResult",
                  "demoReturns","loadDemoReturns","loadSupportTickets"):
        assert 'id="'+ident+'"' in html
    for uri in ("/feedback","/support/tickets","/demo/orders/",
                "/demo/returns"):
        assert uri in js
    assert "showAnswerTools(" in js
    assert "customer-tools" in css
