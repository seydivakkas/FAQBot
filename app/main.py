"""Yerel çalışan FAQBot: sohbet, SSS listesi ve SSS yönetimi."""

import ipaddress
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator

from app.database import add_faq, delete_faq, get_faq, init_db, load_faqs, update_faq
from app.matching import find_best_match, normalize

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"
FALLBACK = (
    "Bu konuda doğrulanmış bir cevabım bulunmuyor. "
    "Kargo, iade, ödeme veya siparişlerle ilgili başka bir soru sorabilirsiniz."
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="FAQBot API",
    description="TF-IDF tabanlı SSS ve yerel kayıt yönetimi",
    version="1.2.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)

    @field_validator("message")
    @classmethod
    def trim_and_validate(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Mesaj boş olamaz.")
        return cleaned


class ChatResponse(BaseModel):
    answer: str
    matched_question: str | None
    category: str | None
    match_type: str
    match_score: float


class FAQInput(BaseModel):
    question: str = Field(min_length=3, max_length=250)
    answer: str = Field(min_length=2, max_length=3000)
    category: Literal["kargo", "iade", "odeme", "hesap"]
    alternative_questions: list[str] = Field(default_factory=list, max_length=15)

    @field_validator("question", "answer")
    @classmethod
    def clean_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Alan boş olamaz.")
        return value

    @field_validator("alternative_questions")
    @classmethod
    def validate_alternatives(cls, values: list[str]) -> list[str]:
        cleaned = [item.strip() for item in values]
        if any(not item or len(item) > 250 for item in cleaned):
            raise ValueError("Alternatif sorular boş olamaz ve 250 karakteri geçemez.")
        return cleaned

    @model_validator(mode="after")
    def no_duplicate_phrases(self):
        phrases = [self.question, *self.alternative_questions]
        normalized = [normalize(item) for item in phrases]
        if len(set(normalized)) != len(phrases):
            raise ValueError("Ana soru ve alternatif sorular birbirinden farklı olmalı.")
        return self


def _is_loopback(host: str | None) -> bool:
    if not host:
        return False
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def require_local_editor(request: Request) -> None:
    """Yazma işlemleri yalnızca yerel makinede, aynı origin'den yapılabilir.

    Kimlik doğrulamanın yerini tutmaz. İnternete yayınlanacaksa auth eklenmeli.
    """
    client_host = request.client.host if request.client else None
    if not _is_loopback(client_host) or not _is_loopback(request.url.hostname):
        raise HTTPException(status_code=403, detail="SSS düzenleme yalnızca yerel erişime açıktır.")
    origin = request.headers.get("origin")
    if origin:
        expected = str(request.base_url).rstrip("/")
        if origin != expected:
            raise HTTPException(status_code=403, detail="Farklı bir kaynaktan düzenleme yapılamaz.")


LocalEditor = Annotated[None, Depends(require_local_editor)]


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse(url="/app")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/faqs")
def get_faqs():
    faqs = load_faqs()
    return {"total": len(faqs), "faqs": faqs}


@app.get("/faqs/export")
def export_faqs(_: LocalEditor):
    """Güncel kayıtların indirilebilir JSON yedeği."""
    faqs = load_faqs()
    cleaned = [
        {key: item[key] for key in ("question", "answer", "category", "alternative_questions")}
        for item in faqs
    ]
    return JSONResponse(
        content={"total": len(cleaned), "faqs": cleaned},
        headers={"Content-Disposition": 'attachment; filename="faqbot-sss-yedek.json"'},
    )


@app.post("/faqs", status_code=status.HTTP_201_CREATED)
def create_faq(payload: FAQInput, _: LocalEditor):
    try:
        return add_faq(
            payload.question, payload.answer, payload.category, payload.alternative_questions
        )
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Bu ana soru zaten kayıtlı.")


@app.put("/faqs/{faq_id}")
def edit_faq(faq_id: int, payload: FAQInput, _: LocalEditor):
    try:
        item = update_faq(
            faq_id, payload.question, payload.answer, payload.category,
            payload.alternative_questions,
        )
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Bu ana soru başka bir kayıtta mevcut.")
    if item is None:
        raise HTTPException(status_code=404, detail="SSS kaydı bulunamadı.")
    return item


@app.delete("/faqs/{faq_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_faq(faq_id: int, _: LocalEditor):
    if not delete_faq(faq_id):
        raise HTTPException(status_code=404, detail="SSS kaydı bulunamadı.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    match = find_best_match(request.message, load_faqs())
    if match is None:
        return ChatResponse(
            answer=FALLBACK,
            matched_question=None,
            category=None,
            match_type="none",
            match_score=0.0,
        )

    faq = match["faq"]
    return ChatResponse(
        answer=faq["answer"],
        matched_question=faq["question"],
        category=faq["category"],
        match_type=match["match_type"],
        match_score=match["match_score"],
    )


@app.get("/app", include_in_schema=False)
def chatbot_page():
    return FileResponse(FRONTEND_DIR / "index.html")
