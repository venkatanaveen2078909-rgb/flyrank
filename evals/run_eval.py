import json
import sys
from pathlib import Path

# Support UTF-8 output on all operating systems
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.llm.client import triage_message


def run_evaluation():
    cases_file = ROOT_DIR / "evals" / "cases.json"
    if not cases_file.exists():
        print(f"Error: {cases_file} not found")
        sys.exit(1)

    with open(cases_file, "r", encoding="utf-8") as f:
        cases = json.load(f)

    print("\n=======================================================")
    print("[EVAL] RUNNING EVALUATION SUITE: 8 Hand-Labelled Test Cases")
    print("=======================================================\n")

    category_matches = 0
    urgency_matches = 0
    failures = []

    for case in cases:
        case_id = case["id"]
        text_input = case["input"]
        expected_cat = case["expected_category"]
        expected_urg = case["expected_urgency"]

        try:
            result = triage_message(text_input)
            cat_ok = result.category.value == expected_cat
            urg_ok = result.urgency.value == expected_urg

            if cat_ok:
                category_matches += 1
            if urg_ok:
                urgency_matches += 1

            status_icon = "PASS" if cat_ok else "FAIL"
            print(f"[{status_icon}] Case #{case_id}: {case['description']}")
            print(f"       Expected: category={expected_cat}, urgency={expected_urg}")
            print(f"       Got:      category={result.category.value}, urgency={result.urgency.value} (confidence={result.confidence:.2f})")
            print(f"       Reason:   {result.reason}\n")

            if not cat_ok:
                failures.append({
                    "id": case_id,
                    "input": text_input,
                    "expected": expected_cat,
                    "got": result.category.value,
                })

        except Exception as e:
            print(f"[ERROR] Case #{case_id} failed with exception: {e}\n")
            failures.append({"id": case_id, "input": text_input, "error": str(e)})

    total = len(cases)
    cat_pct = (category_matches / total) * 100.0
    urg_pct = (urgency_matches / total) * 100.0

    print("=======================================================")
    print("[REPORT] EVALUATION RESULTS SUMMARY")
    print(f"Category Match Rate: {category_matches}/{total} ({cat_pct:.1f}%)")
    print(f"Urgency Match Rate:  {urgency_matches}/{total} ({urg_pct:.1f}%)")
    print(f"Failed Cases:        {len(failures)}")
    print("=======================================================\n")

    return category_matches, total, cat_pct


if __name__ == "__main__":
    run_evaluation()
