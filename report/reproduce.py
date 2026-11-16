"""Replay sanitized stored outcomes with the frozen statistical code, without private data."""

import argparse
import csv
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import statistics
import sys
from collections import Counter

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
sys.path.insert(0, str(PROJECT / "report"))
from formal_analysis import calibrate, accepts, evaluate, paired_question_bootstrap
from replay_helpers import order_hash
from confidence_ties import verify_and_write

DATA = Path(__file__).resolve().parent / "data"
EXCLUSIONS = (
    "gsm8k:test:00560", "medqa:test:00735", "medqa:test:00603",
    "medqa:test:00277", "medqa:test:01038", "medqa:test:00060",
)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_sanitized(data=DATA):
    context = read(data / "formal-replay-context.json")
    for name, digest in context["input_sha256"].items():
        if sha(data / name) != digest:
            raise ValueError(f"Sanitized input hash differs: {name}")
    with (data / "formal_cohort_manifest.csv").open(encoding="utf-8-sig", newline="") as handle:
        cohort = list(csv.DictReader(handle))
    if len(cohort) != 400 or len({row["source_id"] for row in cohort}) != 400:
        raise ValueError("Sanitized cohort must contain 400 distinct source questions")
    original_by_exported = {order_hash(context["seed"], "formal-report-id", row["id"]): row for row in cohort}
    if len(original_by_exported) != 400:
        raise ValueError("Sanitized ID collision")
    predictions = [json.loads(line) for line in (data / "formal-predictions.jsonl").read_text(encoding="utf-8").splitlines()]
    records = []
    for row in context["calibration"] + predictions:
        source = original_by_exported[row["case_id"]]
        if source["domain"] != row["domain"] or source["split"] != row["split"]:
            raise ValueError("Sanitized record/cohort mapping differs")
        restored = dict(row, case_id=source["id"])
        if row["split"] == "test":
            if row["candidate_correct"] != (source["candidate_correct"] == "True"):
                raise ValueError("Sanitized official candidate label differs")
        records.append(restored)
    pairs = [(row["case_id"], row["condition"]) for row in records]
    if len(records) != 1600 or len(set(pairs)) != 1600:
        raise ValueError("Expected 1600 distinct case-condition outcomes")
    policies = []
    for domain in context["domains"]:
        for condition in context["conditions"]:
            rows = [row for row in records if row["domain"] == domain and row["condition"] == condition and row["split"] == "calibration"]
            for fraction in context["targets"]:
                policy = calibrate(rows, domain=domain, condition=condition, model=context["model"], fraction=fraction, seed=context["seed"])
                fields = {key: value for key, value in asdict(policy).items() if key != "calibration_ids"}
                expected = next(item for item in context["policies"] if item["group"] == list(policy.group) and item["fraction"] == fraction)
                if json.loads(json.dumps(fields)) != expected:
                    raise ValueError("Reconstructed calibration cutoff differs from the frozen published policy")
                policies.append(policy)
    for row in records:
        if row["split"] == "test":
            for policy in policies:
                if policy.group == (row["domain"], row["condition"], row["model"]):
                    if row["accepted"][str(policy.fraction)] != accepts(row, policy):
                        raise ValueError("Stored acceptance differs from frozen confidence/hash cutoff")
    return context, cohort, records, policies


def analyze_records(records, policies, context, excluded_original_ids=(), repeats=None):
    repeats = context["repeats"] if repeats is None else repeats
    test = [row for row in records if row["split"] == "test" and row["case_id"] not in set(excluded_original_ids)]
    output = {}
    for domain in context["domains"]:
        output[domain] = {}
        for fraction in context["targets"]:
            selected = {policy.group[1]: policy for policy in policies if policy.group[0] == domain and policy.fraction == fraction}
            groups = {condition: [row for row in test if row["domain"] == domain and row["condition"] == condition] for condition in context["conditions"]}
            report = paired_question_bootstrap(groups, selected, seed=context["seed"], repeats=repeats)
            allowed_pairs = {tuple(sorted(pair)) for pair in context["comparisons"]}
            report["paired_differences"] = [pair for pair in report["paired_differences"] if (pair["left"], pair["right"]) in allowed_pairs]
            for condition, rows in groups.items():
                valid = [row for row in rows if row["classification"] == "valid"]
                point = report["points"][condition]
                point["brier_own_verdict_correctness"] = statistics.mean((row["confidence"] - ((row["verdict"] == "Correct") == row["candidate_correct"])) ** 2 for row in valid) if valid else None
                point["confidence_counts"] = dict(sorted(Counter(str(row["confidence"]) for row in valid).items()))
                point["operational_classifications"] = dict(Counter(row["classification"] for row in rows))
            common = set.intersection(*[{row["case_id"] for row in rows if row["classification"] == "valid"} for rows in groups.values()])
            planned = len(groups[context["conditions"][0]])
            report["common_valid_sensitivity"] = {
                "scope": "Secondary conditional analysis on questions valid in every condition; fixed policies",
                "common_questions": len(common), "main_planned_per_condition": planned,
                "conditional_planned_denominator": len(common),
                "groups": {condition: evaluate([row for row in rows if row["case_id"] in common], selected[condition], repeats=repeats) for condition, rows in groups.items()},
            }
            output[domain][str(fraction)] = report
    return output


def export_ids(value, seed, field=None):
    if field == "accepted_ids":
        return [order_hash(seed, "formal-report-id", case_id) for case_id in value]
    if isinstance(value, dict):
        return {key: export_ids(item, seed, key) for key, item in value.items()}
    if isinstance(value, list):
        return [export_ids(item, seed) for item in value]
    return value


def verify_primary(replayed, stored, seed):
    if export_ids(replayed, seed) != stored["domains"]:
        raise ValueError("Sanitized replay differs from frozen points, random draws or bootstrap intervals")
    return {"point_estimates": 24, "policies_reconstructed": 24, "acceptance_flags": 3360,
            "exact_seeded_random_and_bootstrap_replay": True, "private_data_required": False,
            "interpretation": "Replay of stored outcomes using original deterministic ID ordering; fresh inference is a separate experiment"}


def write_tables(domains, output, analysis):
    output.mkdir(parents=True, exist_ok=True)
    rows, comparisons = [], []
    for domain, targets in domains.items():
        for target, report in targets.items():
            for condition, point in report["points"].items():
                interval = report["group_intervals"][condition]["risk_minus_expected_random"]
                rows.append({"analysis": analysis, "domain": domain, "condition": condition, "calibration_target": target,
                             "planned": point["planned"], "attempted": point["attempted"], "valid": point["valid"],
                             "operational_failures": point["operational_failures"], "official_mismatches_valid": point["official_mismatches_valid"],
                             "accepted": point["accepted"], "official_mismatches_accepted": point["official_mismatches_accepted"],
                             "valid_planned": point["valid_all_planned"]["value"], "accepted_valid": point["accepted_valid"]["value"],
                             "accepted_planned": point["accepted_all_planned"]["value"], "valid_error": point["mismatches_valid"]["value"],
                             "accepted_error": point["mismatches_accepted"]["value"],
                             "accepted_error_wilson_low": point["mismatches_accepted"]["wilson_95"][0] if point["accepted"] else None,
                             "accepted_error_wilson_high": point["mismatches_accepted"]["wilson_95"][1] if point["accepted"] else None,
                             "expected_random_error": point["expected_random_error"], "gap": point["risk_minus_expected_random"],
                             "gap_bootstrap_low": interval["interval_95"][0] if interval["interval_95"] else None,
                             "gap_bootstrap_high": interval["interval_95"][1] if interval["interval_95"] else None,
                             "undefined_bootstrap_draws": interval["undefined_replicates"], "brier": point["brier_own_verdict_correctness"]})
            for pair in report["paired_differences"]:
                for metric, interval in pair["metrics"].items():
                    left, right = report["points"][pair["left"]][metric], report["points"][pair["right"]][metric]
                    left = left["value"] if isinstance(left, dict) else left
                    right = right["value"] if isinstance(right, dict) else right
                    comparisons.append({"analysis": analysis, "domain": domain, "calibration_target": target,
                                        "contrast": pair["right"] + "-" + pair["left"], "metric": metric,
                                        "difference": right-left if left is not None and right is not None else None,
                                        "bootstrap_low": interval["interval_95"][0] if interval["interval_95"] else None,
                                        "bootstrap_high": interval["interval_95"][1] if interval["interval_95"] else None,
                                        "undefined_draws": interval["undefined_replicates"]})
    for name, values in ((f"{analysis}-summary.csv", rows), (f"{analysis}-paired-comparisons.csv", comparisons)):
        with (output / name).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(values[0]))
            writer.writeheader()
            writer.writerows(values)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "tables")
    args = parser.parse_args()
    context, cohort, records, policies = load_sanitized(args.data)
    domains = analyze_records(records, policies, context)
    verification = verify_primary(domains, read(args.data / "formal-metrics.json"), context["seed"])
    write_tables(domains, args.output, "primary")
    sensitivity_path = args.data / "source-ambiguity-sensitivity.json"
    if sensitivity_path.exists():
        stored = read(sensitivity_path)
        excluded = {row["id"] for row in cohort if row["source_id"] in EXCLUSIONS}
        sensitivity = analyze_records(records, policies, context, excluded)
        if export_ids(sensitivity, context["seed"]) != stored["domains"]:
            raise ValueError("Prospective six-case sensitivity replay differs")
        write_tables(sensitivity, args.output, "source-sensitivity")
        verification["six_case_sensitivity_replayed"] = True
    verify_and_write(records, policies, args.data, args.output)
    (args.output / "reproduction-verification.json").write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(verification, indent=2))


if __name__ == "__main__":
    main()
