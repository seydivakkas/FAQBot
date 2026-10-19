"""P1/P2: Gerçek Chromium tarayıcı tıklama + yerel FastAPI + geçici SQLite E2E.

GitHub CI için ayrı browser kabulüdür. Windows Edge fiziksel kabulü DEĞİLDİR.
Üçüncü taraf soru korpusu, bulut inference ve gerçek müşteri verisi kullanılmaz.
"""
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


def _get_free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _serve(port, database):
    env = {**os.environ, "FAQBOT_DB_PATH": str(database),
           "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT, env=env, stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    for _ in range(100):
        if proc.poll() is not None:
            raise RuntimeError(f"Yerel sunucu beklenmedik biçimde durdu: {proc.returncode}")
        try:
            with urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as res:
                if res.status == 200:
                    return proc
        except OSError:
            time.sleep(0.15)
    proc.terminate()
    raise RuntimeError("FAQBot localhost sunucusu açılamadı.")


def main():
    with tempfile.TemporaryDirectory(prefix="faqbot-browser-") as tmp:
        port = _get_free_port()
        base = f"http://127.0.0.1:{port}"
        server = _serve(port, Path(tmp) / "browser-test.sqlite3")
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(viewport={"width": 1280, "height": 850})
                # Her ağ isteği yalnız bu localhost API'sine izinlidir.
                context.route("**/*", lambda route:
                    route.continue_() if route.request.url.startswith(base)
                    else route.abort())
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(base + "/app", wait_until="domcontentloaded")
                expect(page.locator("#chatForm")).to_be_visible()

                # P1: gerçek sohbet -> API -> Like/Dislike -> SQLite sayım.
                page.locator("#messageInput").fill("Kargom ne zaman gelir?")
                page.locator("#chatForm button[type=submit]").click()
                like = page.get_by_role("button", name="Beğendim").last
                expect(like).to_be_visible()
                like.click()
                expect(page.get_by_text("Geri bildiriminiz yerel olarak kaydedildi.")).to_be_visible()
                page.locator("#messageInput").fill("Kapıda ödeme var mı?")
                page.locator("#chatForm button[type=submit]").click()
                dislike = page.get_by_role("button", name="Beğenmedim").last
                expect(dislike).to_be_visible()
                dislike.click()
                assert page.request.get(base + "/feedback/summary").json()["total"] == 2
                assert page.request.get(base + "/feedback/summary").json()["not_helpful"] == 1

                # P1: öneriler gerçekten /chat yanıtından gelir; kesin cevap diye sunulmaz.
                page.locator("#messageInput").fill(
                    "Kargom geldi ama hasarlı bir paket teslim aldım"
                )
                page.locator("#chatForm button[type=submit]").click()
                expect(page.get_by_text("BUNU MU DEMEK İSTEDİNİZ?")).to_be_visible()
                assert page.locator(".answer-suggestion").count() >= 1

                # P1: cevapsız soru -> kullanıcı onaylı destek bilet formu -> API.
                page.locator("#messageInput").fill("Galaktik kuasar teleskop astronomi")
                page.locator("#chatForm button[type=submit]").click()
                ticket_btn = page.get_by_role(
                    "button", name="Sorunum çözülmedi — destek talebi oluştur"
                ).last
                expect(ticket_btn).to_be_visible()
                ticket_btn.click()
                expect(page.locator("#supportSubject")).to_be_visible()
                page.locator("#supportSubject").fill("Kargo Gecikmesi")
                page.locator("#supportDetail").fill("Yalnız kurgusal destek test kaydı.")
                page.locator("#supportForm button[type=submit]").click()
                expect(page.locator("#supportMessage")).to_contain_text(
                    "BİLET_KARGO_GECIKMESI_000001"
                )
                expect(page.locator("#supportTickets")).to_contain_text(
                    "BİLET_KARGO_GECIKMESI_000001"
                )
                page.locator("#supportTickets select").first.select_option("in_progress")
                expect(page.locator("#supportTickets")).to_contain_text("İnceleniyor")
                ticket = page.request.get(base + "/support/tickets/1").json()
                assert ticket["ticket_code"] == "BİLET_KARGO_GECIKMESI_000001"
                assert [row["status"] for row in ticket["history"]] == [
                    "open", "in_progress"
                ]

                # P2: demo kargo olayları doğrudan API metadatasına dayanır.
                page.locator("#demoOrderSection summary").click()
                page.locator("#demoOrderCode").select_option("DEMO-1002")
                page.locator("#demoOrderForm button[type=submit]").click()
                expect(page.locator("#demoOrderResult")).to_contain_text(
                    "KURGU-DEMO-1002"
                )
                expect(page.locator("#demoOrderResult")).to_contain_text(
                    "Kurgusal taşıma sürecinde"
                )
                expect(page.locator("#demoOrderResult .shipment-timeline li")).to_have_count(4)
                expect(page.locator("#demoReturnForm")).to_be_hidden()

                # P2: yalnız teslim edilen demo sipariş -> iade -> doğru sipariş bağı.
                page.locator("#demoOrderCode").select_option("DEMO-1003")
                page.locator("#demoOrderForm button[type=submit]").click()
                expect(page.locator("#demoReturnForm")).to_be_visible()
                page.locator("#demoReturnReason").select_option("damaged")
                page.locator("#demoReturnForm button[type=submit]").click()
                expect(page.locator("#demoOrderMessage")).to_contain_text(
                    "İADE_DEMO-1003_000001"
                )
                expect(page.locator("#demoReturns")).to_contain_text(
                    "İADE_DEMO-1003_000001"
                )
                expect(page.locator("#demoOrderResult")).to_contain_text(
                    "Bu siparişe bağlı iade talebi #1"
                )
                page.locator("#demoReturns select").first.select_option("reviewing")
                expect(page.locator("#demoReturns")).to_contain_text("İnceleniyor")
                linked = page.request.get(base + "/demo/returns/1").json()
                assert linked["order_code"] == "DEMO-1003"
                assert linked["order_ref"]["tracking_id"] == "KURGU-DEMO-1003"
                assert [i["status"] for i in linked["history"]] == [
                    "requested", "reviewing"
                ]
                page.get_by_role("button", name="Bağlı siparişi göster").click()
                expect(page.locator("#demoOrderResult")).to_contain_text("DEMO-1003")
                assert page.request.get(base + "/demo/orders/DEMO-1003").json()[
                    "return_request"]["id"] == 1
                assert not errors, "JS tarayıcı hatası: " + "; ".join(errors)
                browser.close()
                print("P1_P2_BROWSER_E2E_PASS: suggestions like dislike tickets events returns")
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()


if __name__ == "__main__":
    main()
