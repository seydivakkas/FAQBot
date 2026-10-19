"""P1–P2: yerel destek talepleri, geri bildirim ve KURGUSAL sipariş/iade takibi.

Harici servis, kullanıcı hesabı, gerçek sipariş ya da ödeme verisi yoktur.
Veriler mevcut SQLite dosyasında saklanır ve yalnız localhost'tan yönetilir.
"""
import sqlite3
from datetime import datetime, timezone

from app.database import _connect

DEMO_ORDERS = {
    "DEMO-1001": {
        "code": "DEMO-1001", "item": "Örnek masa lambası",
        "status": "preparing", "shipment": "not_shipped",
        "events": [
            {"stage": "created", "label": "Sipariş oluşturuldu"},
            {"stage": "preparing", "label": "Hazırlanıyor"},
        ],
    },
    "DEMO-1002": {
        "code": "DEMO-1002", "item": "Örnek kulaklık",
        "status": "shipped", "shipment": "in_transit",
        "events": [
            {"stage": "created", "label": "Sipariş oluşturuldu"},
            {"stage": "preparing", "label": "Hazırlandı"},
            {"stage": "shipped", "label": "Kurgusal kargoya verildi"},
            {"stage": "in_transit", "label": "Kurgusal taşıma sürecinde"},
        ],
    },
    "DEMO-1003": {
        "code": "DEMO-1003", "item": "Örnek kitap",
        "status": "delivered", "shipment": "delivered",
        "events": [
            {"stage": "created", "label": "Sipariş oluşturuldu"},
            {"stage": "shipped", "label": "Kurgusal kargoya verildi"},
            {"stage": "delivered", "label": "Kurgusal teslimat tamamlandı"},
        ],
    },
}
TICKET_STATES = ("open", "in_progress", "resolved")
RETURN_STATES = ("requested", "reviewing", "approved", "rejected")


def initialize():
    with _connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            detail TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS faq_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            faq_id INTEGER,
            helpful INTEGER NOT NULL CHECK(helpful IN (0, 1)),
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS demo_returns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_code TEXT NOT NULL UNIQUE,
            reason TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'requested',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_tickets_status ON support_tickets(status, id);
        """)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _row(row):
    return dict(row) if row is not None else None


def create_ticket(subject, detail):
    now = _utc_now()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO support_tickets(subject,detail,status,created_at,updated_at) "
            "VALUES(?,?,'open',?,?)",
            (subject, detail, now, now),
        )
        ticket = conn.execute(
            "SELECT * FROM support_tickets WHERE id=?", (cur.lastrowid,)
        ).fetchone()
    return _row(ticket)


def list_tickets(limit=100):
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM support_tickets ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row(row) for row in rows]


def get_ticket(ticket_id):
    with _connect() as conn:
        row = conn.execute("SELECT * FROM support_tickets WHERE id=?", (ticket_id,)).fetchone()
    return _row(row)


def set_ticket_status(ticket_id, state):
    if state not in TICKET_STATES:
        raise ValueError("Geçersiz talep durumu.")
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE support_tickets SET status=?,updated_at=? WHERE id=?",
            (state, _utc_now(), ticket_id),
        )
        if cur.rowcount == 0:
            return None
        return _row(conn.execute(
            "SELECT * FROM support_tickets WHERE id=?", (ticket_id,)
        ).fetchone())


def record_feedback(faq_id, helpful):
    if faq_id is not None:
        # Silinen/olmayan bir SSS'ye kalite sinyali yazmayalım.
        with _connect() as conn:
            exists = conn.execute(
                "SELECT 1 FROM faqs WHERE id=? AND deleted_at IS NULL", (faq_id,)
            ).fetchone()
            if not exists:
                raise LookupError("SSS kaydı bulunamadı.")
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO faq_feedback(faq_id,helpful,created_at) VALUES(?,?,?)",
            (faq_id, int(helpful), _utc_now()),
        )
    return {"id": cur.lastrowid, "saved": True}


def feedback_summary():
    with _connect() as conn:
        rows = conn.execute(
            "SELECT helpful,COUNT(*) n FROM faq_feedback GROUP BY helpful"
        ).fetchall()
    by_state = {int(row["helpful"]): row["n"] for row in rows}
    return {
        "total": sum(by_state.values()),
        "helpful": by_state.get(1, 0),
        "not_helpful": by_state.get(0, 0),
        "notice": "Geri bildirim öznel değerlendirmedir; doğru etiket sayılmaz.",
    }


def demo_order(order_code):
    order = DEMO_ORDERS.get(order_code)
    if not order:
        return None
    return {**order, "demo": True, "real_tracking": False}


def create_demo_return(order_code, reason):
    order = demo_order(order_code)
    if order is None:
        raise LookupError("Kurgusal sipariş bulunamadı.")
    if order["status"] != "delivered":
        raise ValueError("Demo iade talebi yalnız teslim edilmiş sipariş için açılabilir.")
    now = _utc_now()
    try:
        with _connect() as conn:
            cur = conn.execute(
                "INSERT INTO demo_returns(order_code,reason,status,created_at,updated_at) "
                "VALUES(?,?,'requested',?,?)", (order_code, reason, now, now),
            )
            result = conn.execute(
                "SELECT * FROM demo_returns WHERE id=?", (cur.lastrowid,)
            ).fetchone()
        return _row(result)
    except sqlite3.IntegrityError as error:
        raise ValueError("Bu demo sipariş için zaten bir iade talebi var.") from error


def get_demo_return(return_id):
    with _connect() as conn:
        row = conn.execute("SELECT * FROM demo_returns WHERE id=?", (return_id,)).fetchone()
    return _row(row)


def list_demo_returns():
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM demo_returns ORDER BY id DESC LIMIT 100").fetchall()
    return [_row(row) for row in rows]


def set_demo_return_status(return_id, state):
    if state not in RETURN_STATES:
        raise ValueError("Geçersiz iade durumu.")
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE demo_returns SET status=?,updated_at=? WHERE id=?",
            (state, _utc_now(), return_id),
        )
        if not cur.rowcount:
            return None
        return _row(conn.execute(
            "SELECT * FROM demo_returns WHERE id=?", (return_id,)
        ).fetchone())
