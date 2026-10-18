"""Tamamen yerel Sentence-Transformers embedding arayüzü.

Model kaydı yerel klasöre işaret eder. Buradaki hiçbir işlem model indirmez.
Kurulum eksikse açık hata döndürür; TF-IDF'e sessiz geçiş yapmaz.
"""
import importlib.util
from functools import lru_cache
from pathlib import Path

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from app.database import ROOT, _connect
from app.faqvec_tr import (DEFAULT_OWN_DIR, OwnModelError, artifact_status,
                           load_model, similarity_matrix as own_similarity)

DEFAULT_MODEL_PATH = ROOT / "models" / "paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_V2_MODEL_PATH = ROOT / "models" / "faqvec-tr-v0.2-e5" / "model"



class EmbeddingUnavailable(RuntimeError):
    pass


def get_settings():
    with _connect() as conn:
        items = conn.execute(
            "SELECT key, value FROM app_metadata WHERE key IN "
            "('duplicate_method', 'embedding_model_path')"
        ).fetchall()
    values = {row["key"]: row["value"] for row in items}
    return {
        "method": values.get("duplicate_method", "tfidf"),
        "model_path": values.get("embedding_model_path", str(DEFAULT_MODEL_PATH)),
    }


def model_status(path):
    resolved = Path(path).expanduser()
    exists = resolved.is_absolute() and resolved.is_dir() and (
        resolved / "modules.json"
    ).is_file()
    installed = importlib.util.find_spec("sentence_transformers") is not None
    return {
        "path_exists": bool(exists),
        "dependency_installed": bool(installed),
        "ready_to_load": bool(exists and installed),
    }


def set_settings(method, model_path):
    if method not in ("tfidf", "embedding", "faqvec_tr", "faqvec_v2"):
        raise ValueError("Yöntem tfidf, embedding, faqvec_tr veya faqvec_v2 olmalıdır.")
    if not model_path or len(model_path) > 1000:
        raise ValueError("Geçerli bir yerel model klasörü belirtin.")
    directory = Path(model_path).expanduser()
    if not directory.is_absolute():
        raise ValueError("Model klasörü mutlak yerel yol olmalıdır.")
    if str(directory).startswith("\\\\"):
        raise ValueError("Ağ klasörü desteklenmiyor; modeli yerel diske kaydedin.")
    if method == "embedding" and not model_status(str(directory))["ready_to_load"]:
        raise EmbeddingUnavailable(
            "Yerel model veya sentence-transformers kurulumu eksik. "
            "Önce isteğe bağlı embedding kurulumunu tamamlayın."
        )
    if method == "faqvec_v2":
        if not model_status(str(directory))["ready_to_load"] or not (
            directory / "faqvec_v2_manifest.json"
        ).is_file():
            raise EmbeddingUnavailable("FAQVec-TR v0.2 henüz eğitilmedi; yerel model klasörü ve manifest eksik.")
        try:
            manifest = __import__("json").loads(
                (directory / "faqvec_v2_manifest.json").read_text(encoding="utf-8")
            )
            if not manifest.get("backbone", {}).get("declared_license") == "MIT" or (
                manifest.get("model_input_prefix") != "query: "
            ):
                raise ValueError("Model kökeni veya E5 önek sözleşmesi geçersiz.")
            _get_model(str(directory))
        except (ValueError, OSError, KeyError) as exc:
            raise EmbeddingUnavailable("FAQVec-TR v0.2 metadata geçersiz.") from exc
    if method == "faqvec_tr":
        if not artifact_status(str(directory))["ready_to_load"]:
            raise EmbeddingUnavailable(
                "FAQVec-TR modeli henüz üretilmedi. Önce setup_faqvec_windows.bat çalıştırın."
            )
        try:
            load_model(directory)
        except OwnModelError as exc:
            raise EmbeddingUnavailable(str(exc)) from exc
    with _connect() as conn:
        for key, value in (
            ("duplicate_method", method),
            ("embedding_model_path", str(directory)),
        ):
            conn.execute(
                "INSERT INTO app_metadata (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
    return get_settings()


@lru_cache(maxsize=2)
def _get_model(model_path):
    path = Path(model_path)
    if not model_status(model_path)["ready_to_load"]:
        raise EmbeddingUnavailable("Model veya sentence-transformers yerelde bulunamadı.")
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(
            str(path), device="cpu", local_files_only=True, trust_remote_code=False
        )
    except Exception as exc:
        raise EmbeddingUnavailable(
            "Yerel embedding modeli yüklenemedi; kurulum ve model dosyalarını inceleyin."
        ) from exc


def display_status(method, path):
    if method == "faqvec_tr":
        return artifact_status(path)
    return model_status(path)


def similarity_matrix(phrases, model_path, method="embedding"):
    if method == "faqvec_tr":
        try:
            return own_similarity(phrases, model_path)
        except OwnModelError as exc:
            raise EmbeddingUnavailable(str(exc)) from exc
    if not phrases:
        return np.zeros((0, 0))
    model = _get_model(model_path)
    query_inputs = ["query: " + phrase for phrase in phrases] if method == "faqvec_v2" else phrases
    try:
        vectors = np.asarray(model.encode(
            query_inputs, convert_to_numpy=True, normalize_embeddings=True,
            show_progress_bar=False,
        ), dtype=np.float32)
    except Exception as exc:
        raise EmbeddingUnavailable("Yerel embedding üretilemedi.") from exc
    if vectors.ndim != 2 or vectors.shape[0] != len(phrases):
        raise EmbeddingUnavailable("Model beklenmeyen boyutta embedding üretti.")
    scores = cosine_similarity(vectors)
    return np.clip(scores, -1.0, 1.0)
