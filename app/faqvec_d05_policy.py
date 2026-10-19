"""D05: yanlış yanıt güvenlik kapısı ve coverage-risk analiz sözleşmesi.

Yalnız validation verisi ile eşik seçilir. Test etiketleri politika seçimine
hiçbir şekilde giremez. Seçilen eşik testte güvenli olmayı GARANTİ etmez.
"""
import numpy as np

from app.faqvec_v2_metrics import evaluate_matrix, thresholds_on_validation


POLICY_VERSION = "d05-guardrail-grid-201-v1"
# Kabul: validation OOS <=%10 yanlış yanıt, pozitif <=%10 yanlış niyet.
MAX_FALSE_ANSWER_RATE = 0.10
MAX_WRONG_MATCH_RATE = 0.10
# Eşik önceden 201 sabit adaydan seçilir; test skoruna bakılarak eklenmez.
THRESHOLDS = tuple(round(i / 200, 4) for i in range(201))


def _check(scores, gallery_ids, labels):
    matrix = np.asarray(scores, dtype=float)
    if matrix.shape != (len(labels), len(gallery_ids)):
        raise ValueError("Doğrulama skor/etiket/galeri boyutları uyuşmuyor.")
    if not np.isfinite(matrix).all():
        raise ValueError("Doğrulamada NaN/Inf skor.")
    if not any(x is None for x in labels) or not any(x is not None for x in labels):
        raise ValueError("Doğrulama pozitif ve cevap-yok kayıt içermeli.")


def coverage_risk_point(scores, gallery_ids, labels, threshold):
    _check(scores, gallery_ids, labels)
    r = evaluate_matrix(scores, gallery_ids, labels, threshold)
    positive_correct = (
        r["positives"] - r["wrong_answer_count"] - r["positive_abstention_count"]
    )
    answered = r["positives"] - r["positive_abstention_count"] + r["false_answer_count"]
    errors = r["wrong_answer_count"] + r["false_answer_count"]
    return {
        "threshold": round(float(threshold), 4),
        "correct_positive_answer_count": positive_correct,
        "wrong_positive_count": r["wrong_answer_count"],
        "oos_false_answer_count": r["false_answer_count"],
        "positive_coverage": round(1 - r["positive_abstention_rate"], 4),
        "total_answered_count": answered,
        "answered_risk": round(errors / answered, 4) if answered else None,
        "false_answer_rate": r["false_answer_rate"],
        "wrong_match_rate": r["wrong_match_rate"],
        "positive_abstention_rate": r["positive_abstention_rate"],
        "overall_accuracy": r["overall_accuracy"],
    }


def choose_guardrail_threshold(validation_scores, gallery_ids, validation_labels):
    """Kısıtları sağlayan eşikler arasında en çok DOĞRU pozitif cevap seç.

    Hiçbir güvenli eşik doğru cevap üretemiyorsa tüm yanıtları reddeden
    güvenli/işe yaramayan eşik bulunur ve kullanılabilir sayılmaz.
    """
    _check(validation_scores, gallery_ids, validation_labels)
    candidates = [
        coverage_risk_point(validation_scores, gallery_ids, validation_labels, t)
        for t in THRESHOLDS
    ]
    eligible = [
        x for x in candidates
        if (x["false_answer_rate"] <= MAX_FALSE_ANSWER_RATE
            and x["wrong_match_rate"] <= MAX_WRONG_MATCH_RATE)
    ]
    if not eligible:
        raise ValueError("Önceden sabitlenen güvenlik kısıtlarına uygun eşik yok.")
    best = max(
        eligible,
        key=lambda x: (
            x["correct_positive_answer_count"],
            -x["wrong_positive_count"],
            -x["oos_false_answer_count"],
            x["threshold"],  # Tam eşitlikte daha güvenli olan yüksek eşik
        ),
    )
    return {
        "policy_version": POLICY_VERSION,
        "threshold": best["threshold"],
        "validation": best,
        "validation_eligible_count": len(eligible),
        "usable_on_validation": best["correct_positive_answer_count"] > 0,
        "constraints": {
            "max_validation_false_answer_rate": MAX_FALSE_ANSWER_RATE,
            "max_validation_wrong_match_rate": MAX_WRONG_MATCH_RATE,
        },
        "selection_source": "validation_only",
        "commercial_acceptance": "HOLD",
    }


def policy_diagnostics(validation_scores, gallery_ids, validation_labels):
    """D04 ceza maliyeti ile yeni güvenlik politikası aynı VALIDATION üzerinde."""
    _check(validation_scores, gallery_ids, validation_labels)
    old = thresholds_on_validation(
        validation_scores, gallery_ids, validation_labels
    )
    guard = choose_guardrail_threshold(
        validation_scores, gallery_ids, validation_labels
    )
    # Bağımsız bir skor seçimi yapılmaması için test hiç okunmaz.
    return {
        "d04_penalty_threshold": old,
        "d04_validation": coverage_risk_point(
            validation_scores, gallery_ids, validation_labels, old
        ),
        "d05_guardrail": guard,
        # Gösterim için 41 noktalı eşik/coverage-risk eğrisi,
        # seçimde ise yukarıdaki 201 noktanın tümü kullanılır.
        "validation_coverage_risk_curve": [
            coverage_risk_point(
                validation_scores, gallery_ids, validation_labels, t
            ) for t in THRESHOLDS[::5]
        ],
        "evaluated_candidate_count": len(THRESHOLDS),
    }
