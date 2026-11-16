"""Post-hoc finite-test-set expectation over fixed-count boundary-tie subsets."""

import csv
import json

from formal_analysis import accepts, validate_records


def diagnostic(records, policy):
    validate_records(records, policy.group, "test", labels_required=True)
    valid = [r for r in records if r["classification"] == "valid"]
    threshold = policy.cutoff_confidence
    above = [r for r in valid if threshold is not None and r["confidence"] > threshold]
    tie = [r for r in valid if threshold is not None and r["confidence"] == threshold]
    below = [r for r in valid if threshold is not None and r["confidence"] < threshold]
    accepted = [r for r in valid if accepts(r, policy)]
    retained_ties = sum(accepts(r, policy) for r in tie)
    errors = lambda rows: sum((r["verdict"] == "Correct") != r["candidate_correct"] for r in rows)
    expected_errors = errors(above) + (retained_ties * errors(tie) / len(tie) if tie else 0)
    count = len(accepted)
    return {
        "domain": policy.group[0], "condition": policy.group[1], "calibration_target": policy.fraction,
        "policy_status": policy.status, "cutoff": threshold, "valid_n": len(valid),
        "above_n": len(above), "above_errors": errors(above), "tie_n": len(tie), "tie_errors": errors(tie),
        "below_n": len(below), "below_errors": errors(below),
        "unpartitioned_n": len(valid) - len(above) - len(tie) - len(below),
        "tie_accepted_n": retained_ties, "accepted_n": count, "accepted_errors": errors(accepted),
        "actual_selected_risk": errors(accepted) / count if count else None,
        "expected_accepted_errors_over_uniform_tie_subsets": expected_errors,
        "expected_risk_over_uniform_tie_subsets": expected_errors / count if count else None,
        "baseline_risk": errors(valid) / len(valid) if valid else None,
    }


def analyze(records, policies):
    return {"analysis": "post-hoc fixed-count boundary-tie diagnostic",
            "scope": "Exact finite-test-set conditional expectation; not a new primary policy or population confidence interval",
            "formula": "(above_errors + tie_accepted_n * tie_errors / tie_n) / accepted_n",
            "empty_boundary_rule": "Zero tie contribution when tie_n is zero; null risk for zero acceptance; null cutoff leaves valid records unpartitioned",
            "primary_results_changed": False, "calibration_policies_refitted": False,
            "rows": [diagnostic([r for r in records if r["split"] == "test" and
                                  (r["domain"], r["condition"], r["model"]) == p.group], p) for p in policies]}


def verify_and_write(records, policies, data, output):
    result = analyze(records, policies)
    published = json.loads((data / "confidence-tie-diagnostic.json").read_text(encoding="utf-8"))
    if result != published:
        raise ValueError("Confidence-tie diagnostic differs from sanitized replay")
    output.mkdir(parents=True, exist_ok=True)
    (output / "confidence-tie-diagnostic.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    with (output / "confidence-tie-diagnostic.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(result["rows"][0]))
        writer.writeheader()
        writer.writerows(result["rows"])
    return result
