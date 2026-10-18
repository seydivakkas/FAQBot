"""Ortak galeri üzerinde Recall, yanlış eşleşme ve yanıtsız bırakma ölçümleri."""
import numpy as np


def score_topk(scores, gallery_ids, k=5):
    matrix = np.asarray(scores, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[1] != len(gallery_ids) or not gallery_ids:
        raise ValueError("Skor matrisi ve galeri boyutu uyuşmuyor.")
    if not np.isfinite(matrix).all():
        raise ValueError("Skor matrisinde NaN/sonsuz var.")
    order = np.argsort(-matrix, axis=1, kind="stable")[:, :k]
    return [[gallery_ids[j] for j in row] for row in order]


def thresholds_on_validation(scores, gallery_ids, labels, *, candidates=None,
                             wrong_cost=2.0, false_answer_cost=3.0,
                             abstain_cost=1.0):
    """Eşik yalnızca validation etiketlerinden seçilir, test verisine bakılmaz."""
    if not labels:
        raise ValueError("Eşik kalibrasyonu için validation etiketi gerekli.")
    if not any(label is None for label in labels):
        raise ValueError("Kalibrasyonda en az bir 'cevap yok' örneği bulunmalı.")
    if not any(label is not None for label in labels):
        raise ValueError("Kalibrasyonda pozitif örnek bulunmalı.")
    grid = candidates if candidates is not None else np.linspace(0.15, 0.99, 85)
    best = None
    for threshold in grid:
        report = evaluate_matrix(scores, gallery_ids, labels, float(threshold))
        penalty = (wrong_cost * report["wrong_answer_count"] +
                   false_answer_cost * report["false_answer_count"] +
                   abstain_cost * report["positive_abstention_count"]) / len(labels)
        value = (penalty, -float(threshold))
        if best is None or value < best[0]:
            best = (value, float(threshold))
    return round(best[1], 4)


def evaluate_matrix(scores, gallery_ids, labels, threshold, k=5):
    matrix = np.asarray(scores, dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape != (len(labels), len(gallery_ids)):
        raise ValueError("Etiket sayısı ve skor matrisi uyuşmuyor.")
    if not gallery_ids or len(set(gallery_ids)) != len(gallery_ids):
        raise ValueError("Galeri kimlikleri tekil olmalı.")
    if not np.isfinite(matrix).all():
        raise ValueError("Geçersiz skor.")
    if not 0 <= threshold <= 1:
        raise ValueError("Eşik 0..1 olmalı.")
    ranking = score_topk(matrix, gallery_ids, k=k)
    winner_idx = matrix.argmax(axis=1)
    best_score = matrix[np.arange(len(labels)), winner_idx]
    predictions = [
        gallery_ids[i] if score >= threshold else None
        for i, score in zip(winner_idx, best_score)
    ]
    positives = [i for i, label in enumerate(labels) if label is not None]
    negatives = [i for i, label in enumerate(labels) if label is None]
    npos, nneg = len(positives), len(negatives)
    def ratio(a, b):
        return round(a / b, 4) if b else None
    recall_1 = sum(ranking[i][0] == labels[i] for i in positives)
    recall_k = sum(labels[i] in ranking[i] for i in positives)
    wrong = sum(predictions[i] not in (None, labels[i]) for i in positives)
    abstain = sum(predictions[i] is None for i in positives)
    false_answer = sum(predictions[i] is not None for i in negatives)
    no_answer_correct = sum(predictions[i] is None for i in negatives)
    correct = sum(predictions[i] == label for i, label in enumerate(labels))
    return {
        "total": len(labels), "positives": npos, "out_of_scope": nneg,
        "threshold": round(threshold, 4),
        "recall_at_1": ratio(recall_1, npos), "recall_at_5": ratio(recall_k, npos),
        "wrong_match_rate": ratio(wrong, npos), "wrong_answer_count": wrong,
        "positive_abstention_rate": ratio(abstain, npos), "positive_abstention_count": abstain,
        "no_answer_accuracy": ratio(no_answer_correct, nneg),
        "false_answer_rate": ratio(false_answer, nneg),
        "false_answer_count": false_answer,
        "overall_accuracy": ratio(correct, len(labels)),
    }
