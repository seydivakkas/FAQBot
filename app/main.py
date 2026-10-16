"""FAQBot FastAPI uygulaması; HTML arayüzü aynı origin üzerinden sunulur."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from app.database import init_db, load_faqs
from app.matching import find_best_match

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
    description="TF-IDF ile e-ticaret SSS eşleştirme (örnek veriler)",
    version="1.0.0",
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
