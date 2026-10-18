"""110 demo SSS ile yalnızca taslak negatif adayları üret. Manuel onay gerekli."""
import argparse
from app.faqvec_v2_data import load_bundled_demo, write_candidate_negatives, validate_intents

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="reports/faqvec_v2_negative_candidates.jsonl")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()
    rows = load_bundled_demo()
    print("Intent splits:", validate_intents(rows))
    print("Candidates requiring review:",
          write_candidate_negatives(rows, args.output, top_k=args.top_k))
    print("Status: needs_human_review; not accepted for training")


if __name__ == "__main__":
    main()
