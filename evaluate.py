#!/usr/bin/env python3
"""
ScamShield — Performance Evaluation Script (UC13)

Evaluates the rule-based detection engine on a labelled dataset of scam and genuine messages
WITHOUT invoking external LLM APIs. Computes precision, recall, accuracy, confusion matrix,
and lists misclassified communications.
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import List, Dict, Any

from app.pipeline.preprocess import preprocess_message
from app.pipeline.rules import RuleEngine


def evaluate_dataset(dataset_path: Path, split: str = "all") -> Dict[str, Any]:
    if not dataset_path.exists():
        print(f"Error: Dataset file not found at: {dataset_path}", file=sys.stderr)
        sys.exit(1)

    engine = RuleEngine()

    total = 0
    tp = 0  # Actual Scam, Predicted Scam
    fp = 0  # Actual Genuine, Predicted Scam
    tn = 0  # Actual Genuine, Predicted Genuine
    fn = 0  # Actual Scam, Predicted Genuine

    correct_categories = 0
    total_scams = 0
    misclassified = []

    with open(dataset_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_split = row.get("split", "").strip().lower()
            if split != "all" and row_split != split.lower():
                continue

            total += 1
            msg_id = row.get("id", str(total))
            message = row.get("message", "").strip()
            actual_label = row.get("label", "").strip().lower()
            actual_cat = row.get("category", "").strip().lower()

            # Run detection pipeline WITHOUT LLM
            cleaned, masked = preprocess_message(message)
            eval_res = engine.evaluate(cleaned)

            pred_risk = eval_res["risk_level"]
            pred_score = eval_res["score"]
            pred_cat = eval_res["category_id"]

            # Scam definition: Medium or High risk (score >= 3)
            # Genuine definition: Low risk (score <= 2)
            predicted_label = "scam" if pred_risk in ("Medium", "High") else "genuine"

            # Confusion Matrix bookkeeping
            if actual_label == "scam":
                total_scams += 1
                if predicted_label == "scam":
                    tp += 1
                    # Category accuracy check
                    if actual_cat == pred_cat:
                        correct_categories += 1
                    else:
                        misclassified.append({
                            "id": msg_id,
                            "type": "Category Mismatch",
                            "message": message,
                            "actual": f"{actual_label} ({actual_cat})",
                            "predicted": f"{predicted_label} ({pred_cat})",
                            "score": pred_score,
                            "flags": [f.id for f in eval_res["matched_flags"]],
                        })
                else:
                    fn += 1
                    misclassified.append({
                        "id": msg_id,
                        "type": "False Negative (Missed Scam)",
                        "message": message,
                        "actual": f"{actual_label} ({actual_cat})",
                        "predicted": f"{predicted_label} ({pred_cat})",
                        "score": pred_score,
                        "flags": [f.id for f in eval_res["matched_flags"]],
                    })
            else:
                if predicted_label == "scam":
                    fp += 1
                    misclassified.append({
                        "id": msg_id,
                        "type": "False Positive (False Alarm)",
                        "message": message,
                        "actual": f"{actual_label}",
                        "predicted": f"{predicted_label} ({pred_cat})",
                        "score": pred_score,
                        "flags": [f.id for f in eval_res["matched_flags"]],
                    })
                else:
                    tn += 1

    # Metrics calculation
    accuracy = (tp + tn) / total if total > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    category_acc = (correct_categories / total_scams) if total_scams > 0 else 0.0

    return {
        "split": split,
        "total": total,
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "total_scams": total_scams,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "category_accuracy": category_acc,
        "correct_categories": correct_categories,
        "misclassified": misclassified,
    }


def print_report(res: Dict[str, Any]):
    print("=" * 68)
    print(f" ScamShield Performance Evaluation Report  (Split: {res['split'].upper()})")
    print("=" * 68)
    print(f" Total Samples Evaluated : {res['total']}")
    print(f" Total Scams in Set      : {res['total_scams']}")
    print(f" Total Genuine in Set    : {res['total'] - res['total_scams']}")
    print("-" * 68)
    print(f" Accuracy                : {res['accuracy'] * 100:.2f}%")
    print(f" Precision               : {res['precision'] * 100:.2f}%")
    print(f" Recall                  : {res['recall'] * 100:.2f}%")
    print(f" F1-Score                : {res['f1'] * 100:.2f}%")
    print(f" Category Accuracy       : {res['category_accuracy'] * 100:.2f}% ({res['correct_categories']}/{res['total_scams']})")
    print("-" * 68)
    print(" Confusion Matrix:")
    print("                      Predicted Scam    Predicted Genuine")
    print(f"   Actual Scam       :     {res['tp']:<15} {res['fn']:<15} (Total: {res['tp'] + res['fn']})")
    print(f"   Actual Genuine    :     {res['fp']:<15} {res['tn']:<15} (Total: {res['fp'] + res['tn']})")
    print("=" * 68)

    misclassified = res["misclassified"]
    if misclassified:
        print(f"\n Misclassified Communications ({len(misclassified)} items):")
        print("-" * 68)
        for idx, item in enumerate(misclassified, 1):
            msg_snippet = (item["message"][:75] + "...") if len(item["message"]) > 75 else item["message"]
            print(f" [{idx}] ID: {item['id']} | Type: {item['type']}")
            print(f"     Text     : \"{msg_snippet}\"")
            print(f"     Expected : {item['actual']}")
            print(f"     Got      : {item['predicted']} (Score: {item['score']})")
            print(f"     Flags    : {', '.join(item['flags']) if item['flags'] else 'None'}")
            print("-" * 68)
    else:
        print("\n [OK] Excellent: 0 misclassified communications in this split!")
    print("=" * 68)


def main():
    parser = argparse.ArgumentParser(
        description="ScamShield Rule Engine Performance Evaluation (Precision, Recall, Accuracy)"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=str(Path(__file__).resolve().parent / "data" / "sample_dataset.csv"),
        help="Path to labelled CSV dataset (default: data/sample_dataset.csv)"
    )
    parser.add_argument(
        "--split",
        type=str,
        choices=["all", "dev", "test"],
        default="all",
        help="Dataset split to evaluate: 'dev', 'test', or 'all' (default: all)"
    )

    args = parser.parse_args()
    results = evaluate_dataset(Path(args.dataset), split=args.split)
    print_report(results)


if __name__ == "__main__":
    main()
