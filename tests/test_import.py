"""CSV/XLSX toplu aktarım: önizleme, onay, atomiklik ve yerel güvenlik."""
import io
import csv
from openpyxl import Workbook
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db

HEADER = ["question", "answer", "category", "alternative_questions"]


def upload_csv(client, data, filename="faq.csv"):
    return client.post("/faqs/import/preview", files={
        "file": (filename, data, "text/csv")
    })


def build_csv(rows, delimiter=",", headers=HEADER):
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=delimiter)
    writer.writerow(headers)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8-sig")


def sample(number=1):
    return [
        f"Özel konu {number}: teslim bilgisi nasıl öğrenilir?",
        f"Bu örnek yalnızca özel {number} konusundaki demo cevaptır.",
        "siparis",
        f"Özel durum {number} hakkında bilgi alabilir miyim?|{number} numaralı demo bilgi talebi",
    ]


def test_preview_classifies_and_does_not_write(client):
    data = build_csv([
        sample(1),
        ["KARGOM NE ZAMAN GELİR???", "Mevcut kayıtla çakışır.", "kargo", ""],
        ["Boş cevaplı soru?", "", "destek", ""],
        sample(1),
        sample(2),
        ["Soru çakışmayan ama alternatifi çakışan?", "Yanıt metni.", "kargo", "Kargom kaç günde ulaşır?"],
    ])
    preview = upload_csv(client, data)
    assert preview.status_code == 200
    result = preview.json()
    assert (result["total"], result["ready"], result["duplicate"], result["invalid"]) == (6, 2, 3, 1)
    assert result["rows"][0]["row_number"] == 2
    assert result["rows"][0]["data"]["category"] == "siparis"
    assert "data" not in result["rows"][1]
    assert client.get("/faqs").json()["total"] == 110

    commit = client.post("/faqs/import/commit", json={
        "records": [r["data"] for r in result["rows"] if r["status"] == "ready"]
    })
    assert commit.status_code == 200
    assert commit.json()["inserted"] == 2
    assert client.get("/faqs").json()["total"] == 112
    assert client.post("/chat", json={"message": sample(1)[0]}).json()["match_type"] == "exact"
    assert init_db() == 112


def test_turkish_headers_and_semicolon_csv(client):
    data = build_csv([sample(3)], delimiter=";",
                     headers=["soru", "cevap", "kategori", "alternatif_sorular"])
    res = upload_csv(client, data)
    assert res.status_code == 200
    assert res.json()["ready"] == 1


def test_xlsx_first_sheet(client):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(HEADER)
    worksheet.append(sample(4))
    another = workbook.create_sheet("ignore")
    another.append(HEADER)
    another.append(sample(5))
    buffer = io.BytesIO()
    workbook.save(buffer)
    response = client.post("/faqs/import/preview", files={
        "file": ("ornek.xlsx", buffer.getvalue(),
                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    })
    assert response.status_code == 200
    assert response.json()["ready"] == 1
    assert response.json()["total"] == 1


def test_reject_invalid_files(client):
    assert upload_csv(client, b"fake", "unknown.txt").status_code == 422
    assert upload_csv(client, b"", "empty.csv").status_code == 422
    assert upload_csv(client, b"\xff\xfe", "bad.csv").status_code == 422
    assert upload_csv(client, b"not a workbook", "bad.xlsx").status_code == 422
    assert upload_csv(client, build_csv([sample(6)], headers=["foo"])).status_code == 422
    assert upload_csv(client, b"a" * (2*1024*1024 + 1)).status_code == 422


def test_row_limit(client):
    data = build_csv([sample(i+100) for i in range(501)])
    response = upload_csv(client, data)
    assert response.status_code == 422
    assert client.get("/faqs").json()["total"] == 110


def test_atomic_conflict_no_partial_insert(client):
    first = {"question": sample(7)[0], "answer": sample(7)[1],
             "category": "siparis",
             "alternative_questions": sample(7)[3].split("|")}
    other = {"question": "Kargom ne zaman gelir?",
             "answer": "Mevcut kayıt yerinde kalmalı.", "category": "kargo",
             "alternative_questions": []}
    res = client.post("/faqs/import/commit", json={"records": [first, other]})
    assert res.status_code == 409
    assert res.json()["detail"]["result"]["duplicate"] == 1
    assert client.get("/faqs").json()["total"] == 110
    assert first["question"] not in [x["question"] for x in client.get("/faqs").json()["faqs"]]


def test_file_preview_after_new_record_becomes_stale(client):
    data = build_csv([sample(8)])
    preview = upload_csv(client, data).json()
    first = preview["rows"][0]["data"]
    assert preview["ready"] == 1
    assert client.post("/faqs", json=first).status_code == 201
    response = client.post("/faqs/import/commit", json={"records": [first]})
    assert response.status_code == 409
    assert client.get("/faqs").json()["total"] == 111


def test_commit_validates_payload(client):
    invalid = {"question": "a", "answer": "b", "category": "destek",
               "alternative_questions": []}
    assert client.post("/faqs/import/commit", json={"records": [invalid]}).status_code == 422
    assert client.post("/faqs/import/commit", json={"records": []}).status_code == 422
    assert client.get("/faqs").json()["total"] == 110


def test_remote_and_cross_origin_import_denied(client, tmp_path, monkeypatch):
    valid = build_csv([sample(9)])
    assert client.post(
        "/faqs/import/preview", files={"file": ("a.csv", valid)},
        headers={"Origin": "https://example.org"}
    ).status_code == 403
    assert client.post(
        "/faqs/import/commit", json={"records": []},
        headers={"Origin": "https://example.org"}
    ).status_code == 403
    monkeypatch.setenv("FAQBOT_DB_PATH", str(tmp_path/"remote.db"))
    with TestClient(app, base_url="http://example.org") as remote:
        response = remote.post("/faqs/import/preview",
                               files={"file": ("a.csv", valid)})
        assert response.status_code == 403


def test_ui_edit_delete_and_import_exist(client):
    html = client.get("/app").text
    javascript = client.get("/static/app.js").text
    for entry in ("faqImportFile", "previewFaqImport", "commitFaqImport",
                  "faqImportPreview", "editQuestion", "deleteFaqButton",
                  "manageFaqList"):
        assert 'id="' + entry + '"' in html
    assert "editExistingFaq(faq)" in javascript
    assert "deleteFaqRecord(faq.id)" in javascript
    assert "fetch(\"/faqs/import/preview\"" in javascript
    assert "fetch(\"/faqs/import/commit\"" in javascript
    assert client.get("/static/faq_import_template.csv").status_code == 200
