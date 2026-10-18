"""FAQVec-TR: sıfırdan eğitilen, izinli veriyle çalışabilen yerel n-gram encoder.

Önceden eğitilmiş üçüncü taraf ağırlık veya model indirmez.
Model: sabit Türkçe karakter n-gram hashing + denetimli kontrastif embedding tablosu.
Ağırlıklar yalnızca güvenli NPZ (pickle kapalı) biçiminde yüklenir.
"""
import hashlib
import json
from functools import lru_cache
from pathlib import Path

import numpy as np

from app.matching import normalize

FAMILY = "faqvec-tr"
FORMAT_VERSION = 1
DIM = 48
BUCKETS = 4096
DEFAULT_OWN_DIR = Path(__file__).resolve().parent.parent / "models" / "faqvec-tr-v0.1"


class OwnModelError(RuntimeError):
    pass


def features(sentence: str, buckets: int = BUCKETS) -> np.ndarray:
    """Platform bağımsız ve kararlı hash; Python'un salt'lı hash()'i kullanılmaz."""
    words = normalize(sentence).split()
    tokens = set()
    for word in words:
        wrapped = "^" + word + "$"
        tokens.add("w:" + word)
        for n in (2, 3, 4):
            for index in range(max(0, len(wrapped) - n + 1)):
                tokens.add("c:" + wrapped[index:index + n])
    if not tokens:
        return np.array([0], dtype=np.int64)
    ids = {
        int.from_bytes(
            hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest(),
            byteorder="little"
        ) % buckets for token in tokens
    }
    return np.fromiter(sorted(ids), dtype=np.int64)


def _unit(vectors):
    lengths = np.maximum(np.linalg.norm(vectors, axis=-1, keepdims=True), 1e-12)
    return vectors / lengths


class FaqVecEncoder:
    def __init__(self, weights):
        weights = np.asarray(weights, dtype=np.float32)
        if weights.ndim != 2 or weights.shape != (BUCKETS, DIM):
            raise OwnModelError("Model ağırlıkları beklenen boyutta değil.")
        if not np.isfinite(weights).all():
            raise OwnModelError("Modelde geçersiz sayılar var.")
        self.weights = weights

    def encode(self, sentences, **kwargs):
        if isinstance(sentences, str):
            sentences = [sentences]
        if not sentences:
            return np.zeros((0, DIM), dtype=np.float32)
        vectors = np.stack([
            self.weights[features(sentence)].mean(axis=0)
            for sentence in sentences
        ])
        return _unit(vectors).astype(np.float32)


def train_groups(groups, epochs=30, seed=42, batch_groups=16):
    """Her grubun ana ve alternatif soruları pozitif çifttir.

    Diğer gruplar negatif örnek olarak kullanılır. Tüm gruplar kullanıcıya
    ait/lisansı doğrulanmış veri olmalıdır. Bu fonksiyon ağ erişimi yapmaz.
    """
    valid = [[text.strip() for text in group if text and text.strip()] for group in groups]
    valid = [list(dict.fromkeys(group)) for group in valid if len(set(group)) >= 2]
    if len(valid) < 3:
        raise ValueError("Eğitim için en az üç farklı ihtiyaç ve ikişer soru gerekir.")
    if not 1 <= epochs <= 100:
        raise ValueError("Eğitim epoch sayısı 1–100 aralığında olmalı.")
    rng = np.random.default_rng(seed)
    weights = rng.normal(0, 0.13, size=(BUCKETS, DIM)).astype(np.float32)
    first = [[features(text) for text in group] for group in valid]
    momentum = np.zeros_like(weights)
    variance = np.zeros_like(weights)
    step = 0
    loss_last = 0.0
    for epoch in range(epochs):
        order = rng.permutation(len(valid))
        for start in range(0, len(order), batch_groups):
            batch = order[start:start + batch_groups]
            if len(batch) < 2:
                continue
            rows = []
            for group_index in batch:
                items = first[int(group_index)]
                picked = rng.choice(len(items), size=2, replace=False)
                rows.extend((items[int(picked[0])], items[int(picked[1])]))
            raw = np.stack([weights[ids].mean(axis=0) for ids in rows])
            norms = np.maximum(np.linalg.norm(raw, axis=1, keepdims=True), 1e-8)
            projected = raw / norms
            temp = 0.18
            logits = (projected @ projected.T) / temp
            np.fill_diagonal(logits, -1e9)
            logits = logits - logits.max(axis=1, keepdims=True)
            probs = np.exp(logits)
            probs /= probs.sum(axis=1, keepdims=True)
            positives = np.arange(len(rows)) ^ 1
            loss_last = float(-np.log(np.maximum(
                probs[np.arange(len(rows)), positives], 1e-12
            )).mean())
            ds = probs
            ds[np.arange(len(rows)), positives] -= 1
            ds /= len(rows) * temp
            de = (ds + ds.T) @ projected
            grad_raw = (de - projected * np.sum(de * projected, axis=1, keepdims=True)) / norms
            grad = np.zeros_like(weights)
            for ids, vec_grad in zip(rows, grad_raw):
                np.add.at(grad, ids, vec_grad / len(ids))
            step += 1
            # Adam: ağsız, ek derin öğrenme kütüphanesi gerektirmez.
            momentum = 0.9 * momentum + 0.1 * grad
            variance = 0.999 * variance + 0.001 * (grad * grad)
            corrected_m = momentum / (1 - 0.9 ** step)
            corrected_v = variance / (1 - 0.999 ** step)
            weights -= 0.002 * corrected_m / (np.sqrt(corrected_v) + 1e-7)
    return FaqVecEncoder(weights), {"last_train_loss": round(loss_last, 5),
                                    "train_intents": len(valid), "epochs": epochs}


def _weights_paths(folder):
    directory = Path(folder)
    return directory / "weights.npz", directory / "manifest.json"


def artifact_status(folder):
    weights_path, info_path = _weights_paths(folder)
    exists = weights_path.is_file() and info_path.is_file()
    return {
        "path_exists": bool(exists),
        "dependency_installed": True,
        "ready_to_load": bool(exists),
    }


def save_model(model, folder, metadata):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    weights_path, info_path = _weights_paths(folder)
    np.savez_compressed(weights_path, weights=model.weights)
    checksum = hashlib.sha256(weights_path.read_bytes()).hexdigest()
    info = {
        "family": FAMILY, "format_version": FORMAT_VERSION,
        "architecture": "hashed_char_word_ngram_contrastive_mean_pool",
        "dimensions": DIM, "buckets": BUCKETS, "weights_sha256": checksum,
        "pretrained_external_weights": False,
        "commercial_acceptance": "HOLD",
        **metadata,
    }
    info_path.write_text(json.dumps(info, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    _load_model.cache_clear()
    return info


@lru_cache(maxsize=2)
def _load_model(folder, modified):
    weights_path, info_path = _weights_paths(folder)
    try:
        info = json.loads(info_path.read_text(encoding="utf-8"))
        if info["family"] != FAMILY or info["format_version"] != FORMAT_VERSION:
            raise OwnModelError("Model dosyası FAQVec-TR v0.1 değil.")
        if info["dimensions"] != DIM or info["buckets"] != BUCKETS:
            raise OwnModelError("Model mimarisi bu sürümle uyumlu değil.")
        digest = hashlib.sha256(weights_path.read_bytes()).hexdigest()
        if digest != info["weights_sha256"]:
            raise OwnModelError("Model ağırlıkları SHA-256 doğrulamasından geçmedi.")
        with np.load(weights_path, allow_pickle=False) as tensors:
            if list(tensors.files) != ["weights"]:
                raise OwnModelError("Model dosyasında beklenmeyen alan bulunuyor.")
            return FaqVecEncoder(tensors["weights"])
    except (OSError, KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise OwnModelError("FAQVec-TR dosyaları eksik, bozuk veya uyumsuz.") from exc


def load_model(folder):
    weights_path, info_path = _weights_paths(folder)
    if not weights_path.is_file() or not info_path.is_file():
        raise OwnModelError("FAQVec-TR eğitim dosyaları bulunamadı. Önce yerel eğitimi çalıştırın.")
    return _load_model(str(Path(folder).resolve()),
                       (weights_path.stat().st_mtime_ns, info_path.stat().st_mtime_ns))


def similarity_matrix(sentences, folder):
    matrix = load_model(folder).encode(sentences)
    return np.clip(matrix @ matrix.T, -1.0, 1.0)
