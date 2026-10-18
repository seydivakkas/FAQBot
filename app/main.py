"""Yerel çalışan FAQBot: sohbet, SSS listesi ve SSS yönetimi."""

import ipaddress
import sqlite3
import logging
from contextlib import asynccontextmanager
from datetime import date
from urllib.parse import urlparse
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator

from app.reviews import (
    initialize as init_reviews, get_logging_enabled, set_logging_enabled,
    record_chat, list_reviews, label_review, clear_reviews, evaluate,
    ReviewConflict,
)
from app.importer import ImportConflict, ImportFormatError, MAX_FILE_BYTES, analyze, commit_records, parse_file, summarize
from app.database import (add_faq, delete_faq, get_faq, init_db, load_faqs, update_faq,
                          list_deleted_faqs, restore_faq, RestoreConflict)
from app.matching import find_best_match, normalize
from app.semantic import (EmbeddingUnavailable, get_settings as get_semantic_settings,
                          set_settings as set_semantic_settings, display_status)
from app.faqvec_tr import DEFAULT_OWN_DIR
from app.duplicates import (
    DEFAULT_DUPLICATE_THRESHOLD, MIN_DUPLICATE_THRESHOLD,
    MAX_DUPLICATE_THRESHOLD, MergeConflict, detect,
    get_threshold, set_threshold, merge_records,
)

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT / "frontend"
FALLBACK = (
    "Bu konuda doğrulanmış bir cevabım bulunmuyor. "
    "Kargo, iade, ödeme veya siparişlerle ilgili başka bir soru sorabilirsiniz."
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    init_reviews()
    yield


app = FastAPI(
    title="FAQBot API",
    description="Yerel SSS ve opsiyonel çevrimdışı embedding yönetimi",
    version="1.6.1",
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
    source_title: str = ""
    source_url: str = ""
    valid_until: str | None = None
    verification_status: str = "unverified"
    validity_status: str = "unspecified"


class FAQInput(BaseModel):
    question: str = Field(min_length=3, max_length=250)
    answer: str = Field(min_length=2, max_length=3000)
    category: Literal["kargo", "iade", "odeme", "hesap", "siparis", "urun", "kampanya", "destek"]
    alternative_questions: list[str] = Field(default_factory=list, max_length=15)
    source_title: str = Field(default="", max_length=250)
    source_url: str = Field(default="", max_length=500)
    valid_until: date | None = None
    verification_status: Literal["unverified", "review_needed", "verified"] = "unverified"

    @field_validator("source_title", "source_url")
    @classmethod
    def trim_source(cls, value: str) -> str:
        return value.strip()

    @field_validator("source_url")
    @classmethod
    def safe_source_url(cls, value: str) -> str:
        if value and (urlparse(value).scheme not in ("http", "https")
                      or not urlparse(value).netloc
                      or any(ch in value for ch in "\r\n\t")):
            raise ValueError("Kaynak adresi geçerli bir http/https URL olmalıdır.")
        return value

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
        if self.verification_status == "verified" and not (
            self.source_title and self.source_url
        ):
            raise ValueError("Elle doğrulandı seçimi için kaynak başlığı ve URL gereklidir.")
        return self


def _payload_fields(payload: FAQInput) -> dict:
    data = payload.model_dump()
    data["alternatives"] = data.pop("alternative_questions")
    if data.get("valid_until") is not None:
        data["valid_until"] = data["valid_until"].isoformat()
    return data


def _info(faq: dict | None) -> dict:
    if faq is None:
        return {"source_title": "", "source_url": "", "valid_until": None,
                "verification_status": "unverified", "validity_status": "unspecified"}
    return {key: faq.get(key) for key in (
        "source_title", "source_url", "valid_until", "verification_status", "validity_status"
    )}


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
        {key: item[key] for key in ("question", "answer", "category", "alternative_questions",
                             "source_title", "source_url", "valid_until", "verification_status")}
        for item in faqs
    ]
    return JSONResponse(
        content={"total": len(cleaned), "faqs": cleaned},
        headers={"Content-Disposition": 'attachment; filename="faqbot-sss-yedek.json"'},
    )


class FAQImportCommit(BaseModel):
    records: list[FAQInput] = Field(min_length=1, max_length=500)


@app.post("/faqs/import/preview")
async def preview_faq_import(_: LocalEditor, file: UploadFile = File(...)):
    """Önizleme veritabanına hiçbir kayıt yazmaz."""
    try:
        content = await file.read(MAX_FILE_BYTES + 1)
        source_rows = parse_file(file.filename, content)
    except ImportFormatError as error:
        raise HTTPException(status_code=422, detail=str(error))
    finally:
        await file.close()
    return summarize(analyze(source_rows, load_faqs() + list_deleted_faqs(), FAQInput))


@app.post("/faqs/import/commit")
def commit_faq_import(request: FAQImportCommit, _: LocalEditor):
    """Tamamı uygunsa ekle; önizlemeden beri oluşan çakışmada 409 ve sıfır INSERT."""
    try:
        count = commit_records([record.model_dump() for record in request.records], FAQInput)
    except ImportConflict as error:
        raise HTTPException(
            status_code=409, detail={
                "message": "Kayıtlar değişmiş veya çakışıyor. Yeniden önizleyin.",
                "result": error.details,
            }
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))
    return {"inserted": count}


class DuplicateSettings(BaseModel):
    # 0.70 ekranda %70 olarak gösterilir; sohbet eşik değerinden bağımsızdır.
    threshold: float = Field(
        ge=MIN_DUPLICATE_THRESHOLD, le=MAX_DUPLICATE_THRESHOLD
    )

    @field_validator("threshold")
    @classmethod
    def one_percent_steps(cls, value: float) -> float:
        if abs(value * 100 - round(value * 100)) > 1e-7:
            raise ValueError("Eşik değeri yüzde 1 adımlarla değiştirilmelidir.")
        return round(value, 2)


class DuplicateMergeRequest(BaseModel):
    keep_id: int = Field(gt=0)
    remove_id: int = Field(gt=0)
    expected_keep: str = Field(min_length=64, max_length=64)
    expected_remove: str = Field(min_length=64, max_length=64)
    confirm: Literal[True]


@app.get("/settings/duplicates")
def read_duplicate_settings(_: LocalEditor):
    return {"threshold": get_threshold(), "default": DEFAULT_DUPLICATE_THRESHOLD,
            "minimum": MIN_DUPLICATE_THRESHOLD, "maximum": MAX_DUPLICATE_THRESHOLD}


@app.put("/settings/duplicates")
def save_duplicate_settings(payload: DuplicateSettings, _: LocalEditor):
    return {"threshold": set_threshold(payload.threshold)}


class SemanticSettingsRequest(BaseModel):
    method: Literal["tfidf", "embedding", "faqvec_tr"]
    model_path: str = Field(min_length=1, max_length=1000)


@app.get("/settings/semantic")
def read_semantic_settings(_: LocalEditor):
    info = get_semantic_settings()
    return {**info, **display_status(info["method"], info["model_path"]),
            "default_own_model_path": str(DEFAULT_OWN_DIR)}


@app.put("/settings/semantic")
def update_semantic_settings(payload: SemanticSettingsRequest, _: LocalEditor):
    try:
        result = set_semantic_settings(payload.method, payload.model_path)
    except (ValueError, EmbeddingUnavailable) as error:
        raise HTTPException(status_code=422, detail=str(error))
    return {**result, **display_status(result["method"], result["model_path"]),
            "default_own_model_path": str(DEFAULT_OWN_DIR)}


@app.get("/faqs/duplicates")
def find_duplicate_faqs(_: LocalEditor):
    """Yalnızca aday önerir; hiç kayıt değiştirmez."""
    cutoff = get_threshold()
    all_faqs = load_faqs()
    config = get_semantic_settings()
    try:
        suggestions = detect(
            all_faqs, cutoff, max_results=150,
            method=config["method"], model_path=config["model_path"]
        )
    except EmbeddingUnavailable as error:
        raise HTTPException(status_code=409, detail=str(error))
    return {"threshold": cutoff, "total": len(suggestions), "candidates": suggestions,
            "method": config["method"], "truncated": len(suggestions) == 150}


@app.post("/faqs/duplicates/merge")
def apply_duplicate_merge(payload: DuplicateMergeRequest, _: LocalEditor):
    try:
        return merge_records(
            payload.keep_id, payload.remove_id,
            payload.expected_keep, payload.expected_remove, payload.confirm,
        )
    except (MergeConflict, EmbeddingUnavailable) as error:
        raise HTTPException(status_code=409, detail=str(error))
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


class ReviewLoggingSettings(BaseModel):
    enabled: bool


class ReviewLabelRequest(BaseModel):
    status: Literal["pending", "correct", "incorrect", "unsure"]
    expected_faq_id: int | None = Field(default=None, gt=0)
    note: str = Field(default="", max_length=500)


class ReviewClearRequest(BaseModel):
    confirm: Literal[True]


class ReviewEvaluateRequest(BaseModel):
    include_embedding: bool = False


@app.get("/reviews/settings")
def read_review_settings(_: LocalEditor):
    return {"enabled": get_logging_enabled(), "retention_limit": 1000,
            "sensitive_filter": True}


@app.put("/reviews/settings")
def update_review_settings(payload: ReviewLoggingSettings, _: LocalEditor):
    return {"enabled": set_logging_enabled(payload.enabled)}


@app.get("/reviews")
def read_review_list(_: LocalEditor, status: Literal[
    "all", "pending", "correct", "incorrect", "unsure"
] = "all", limit: int = 100):
    if not 1 <= limit <= 200:
        raise HTTPException(status_code=422, detail="Liste sınırı 1–200 olmalıdır.")
    return list_reviews(status=status, limit=limit)


@app.patch("/reviews/{review_id}")
def update_review_label(review_id: int, payload: ReviewLabelRequest, _: LocalEditor):
    try:
        return label_review(
            review_id, payload.status, payload.expected_faq_id, payload.note
        )
    except ReviewConflict as exc:
        raise HTTPException(status_code=404 if "bulunamadı" in str(exc) else 409,
                            detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.delete("/reviews")
def delete_review_history(payload: ReviewClearRequest, _: LocalEditor):
    return {"deleted": clear_reviews()}


@app.post("/reviews/evaluate")
def evaluate_reviewed_data(payload: ReviewEvaluateRequest, _: LocalEditor):
    return evaluate(include_embedding=payload.include_embedding)


@app.get("/faqs/trash")
def get_faq_trash(_: LocalEditor):
    """Silinmiş kayıtlar tam içerikleri ve silinme zamanlarıyla görüntülenir."""
    entries = list_deleted_faqs()
    return {"total": len(entries), "faqs": entries}


class FAQRestoreRequest(BaseModel):
    confirm: Literal[True]


@app.post("/faqs/trash/{faq_id}/restore")
def restore_deleted_faq(faq_id: int, payload: FAQRestoreRequest, _: LocalEditor):
    """Tek SSS kaydını yalnızca açık onayla ve etkin kayıtlarla çakışmıyorsa geri getir."""
    try:
        return restore_faq(faq_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error))
    except (RestoreConflict, sqlite3.IntegrityError) as error:
        raise HTTPException(status_code=409, detail=str(error))


@app.post("/faqs", status_code=status.HTTP_201_CREATED)
def create_faq(payload: FAQInput, _: LocalEditor):
    try:
        return add_faq(**_payload_fields(payload))
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Bu ana soru aktif kayıtlarda veya çöp kutusunda mevcut.")


@app.put("/faqs/{faq_id}")
def edit_faq(faq_id: int, payload: FAQInput, _: LocalEditor):
    try:
        item = update_faq(faq_id, **_payload_fields(payload))
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
def chat(request: ChatRequest, http_request: Request):
    match = find_best_match(request.message, load_faqs())
    reply = match["faq"]["answer"] if match else FALLBACK
    # Kayda yalnızca açık yönetici tercihi ve yerel istekle izin ver.
    if _is_loopback(http_request.client.host if http_request.client else None):
        try:
            record_chat(request.message, match, reply)
        except sqlite3.Error:
            logging.getLogger(__name__).exception("Yerel eşleşme günlüğüne kayıt yapılamadı.")
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
        **_info(faq),
    )


@app.get("/app", include_in_schema=False)
def chatbot_page():
    return FileResponse(FRONTEND_DIR / "index.html")
