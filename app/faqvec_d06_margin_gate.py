"""FAQVec D06 — çift koşullu güvenlik kapısı.

Bir sorgu yalnız (benzerlik >= eşik) ve
(ilk iki niyet arasındaki skor farkı >= marj) olduğunda yanıt alır.
Hem eşik hem marj yalnız D04'te kilitli VALIDATION verisiyle seçilir.
D06 zor testi burada hiçbir parametre seçimine katılmaz.
"""
import numpy as np

from app.faqvec_d05_policy import (
    THRESHOLDS, MAX_FALSE_ANSWER_RATE, MAX_WRONG_MATCH_RATE,
    choose_guardrail_threshold
)

MARGINS = tuple(round(i / 200, 4) for i in range(51))  # 0..0.25, 0.005
VERSION = "d06-validation-threshold-margin-201x51-v1"


def _checked(scores, gallery_ids, labels):
    arr = np.asarray(scores, dtype=float)
    if arr.ndim != 2 or arr.shape != (len(labels), len(gallery_ids)):
        raise ValueError("Skor, galeri ve etiket sayısı uyuşmuyor.")
    if len(gallery_ids) < 2 or len(set(gallery_ids)) != len(gallery_ids):
        raise ValueError("Marj için en az iki benzersiz niyet gerekir.")
    if not np.isfinite(arr).all():
        raise ValueError("NaN veya Inf skor kullanılamaz.")
    return arr


def top_information(scores, gallery_ids, labels):
    arr = _checked(scores, gallery_ids, labels)
    winners = np.argmax(arr, axis=1)
    top = arr[np.arange(arr.shape[0]), winners]
    second = np.partition(arr, -2, axis=1)[:, -2]
    gap = np.maximum(top - second, 0.0)
    expected = np.array(labels, dtype=object)
    chosen = np.array([gallery_ids[x] for x in winners], dtype=object)
    positive = np.array([x is not None for x in labels], dtype=bool)
    return top, gap, chosen, expected, positive


def gate_measure(scores, gallery_ids, labels, *, threshold, margin):
    if not 0 <= threshold <= 1 or not 0 <= margin <= 1:
        raise ValueError("Eşik ve marj 0..1 aralığında olmalı.")
    top, gap, chosen, expected, positive = top_information(scores, gallery_ids, labels)
    accepted = (top >= threshold) & (gap >= margin)
    good = accepted & positive & (chosen == expected)
    wrong = accepted & positive & (chosen != expected)
    false = accepted & ~positive
    refused = ~accepted & positive
    rejected = ~accepted & ~positive
    npos = int(positive.sum())
    noos = int((~positive).sum())
    nans = int(accepted.sum())
    correct = int(good.sum())
    errors = int(wrong.sum() + false.sum())
    def rate(n, size):
        return round(int(n) / int(size), 4) if size else None
    return {
        "threshold": round(float(threshold), 4),
        "margin": round(float(margin), 4),
        "positive": npos, "oos": noos,
        "correct_positive_count": correct,
        "wrong_match_count": int(wrong.sum()),
        "positive_abstention_count": int(refused.sum()),
        "false_answer_count": int(false.sum()),
        "no_answer_correct_count": int(rejected.sum()),
        "overall_correct_count": int(correct + rejected.sum()),
        "correct_positive_rate": rate(correct, npos),
        "wrong_match_rate": rate(wrong.sum(), npos),
        "positive_abstention_rate": rate(refused.sum(), npos),
        "false_answer_rate": rate(false.sum(), noos),
        "no_answer_accuracy": rate(rejected.sum(), noos),
        "overall_accuracy": rate(correct + rejected.sum(), len(labels)),
        "answered_total": nans,
        "risk_on_answered": rate(errors, nans),
        "correct_predictions": correct,
    }


def _fast_counts(top, gap, chosen, expected, positive, threshold, margin):
    accepted = (top >= threshold) & (gap >= margin)
    correct = int(np.count_nonzero(accepted & positive & (chosen == expected)))
    wrong = int(np.count_nonzero(accepted & positive & (chosen != expected)))
    false = int(np.count_nonzero(accepted & ~positive))
    return correct, wrong, false


def calibrate_validation_margin(validation_scores, gallery_ids, validation_labels):
    """Parametre seçimi yalnız eski D04 VALIDATION veri kümesini okur."""
    top, gap, chosen, expected, positive = top_information(
        validation_scores, gallery_ids, validation_labels
    )
    npos = int(positive.sum())
    noos = len(positive) - npos
    if npos == 0 or noos == 0:
        raise ValueError("Kilitli validation pozitif ve OOS içermeli.")
    best = None
    eligible_count = 0
    for threshold in THRESHOLDS:
        for margin in MARGINS:
            correct, wrong, false = _fast_counts(
                top, gap, chosen, expected, positive, threshold, margin
            )
            if wrong / npos > MAX_WRONG_MATCH_RATE or false / noos > MAX_FALSE_ANSWER_RATE:
                continue
            eligible_count += 1
            # En çok DOĞRU cevabı veren güvenlik-adayını bul.
            # Aynı doğru cevapta daha az hata; eşitlikte yüksek eşik ve marj.
            key = (correct, -(wrong+false), -false, -wrong, threshold, margin)
            if best is None or key > best[0]:
                best = (key, threshold, margin)
    if best is None:
        raise ValueError("Kısıtlara uygun validation eşik ve marj çifti bulunamadı.")
    _, threshold, margin = best
    before = choose_guardrail_threshold(
        validation_scores, gallery_ids, validation_labels
    )
    single = gate_measure(
        validation_scores, gallery_ids, validation_labels,
        threshold=before["threshold"], margin=0
    )
    selected = gate_measure(
        validation_scores, gallery_ids, validation_labels,
        threshold=threshold, margin=margin
    )
    return {
        "policy_version": VERSION,
        "selection_source": "d04_validation_only",
        "grid_thresholds": len(THRESHOLDS),
        "grid_margins": len(MARGINS),
        "eligible_count": eligible_count,
        "selected_threshold": threshold,
        "selected_margin": margin,
        "validation_single_gate": single,
        "validation_dual_gate": selected,
        "validation_usable": selected["correct_positive_count"] > 0,
        "test_guardrail_is_not_guaranteed": True,
        "human_review": False,
        "commercial_acceptance": "HOLD",
    }
