"""Offline confidence calibration and paired evaluation for a later approved cohort.

Inputs are evaluator records with case_id/domain/condition/model/split/classification.
Valid records also contain verdict/confidence. Test records contain the official
candidate_correct boolean. This module performs no I/O or model requests.
"""

from dataclasses import dataclass
from itertools import combinations
import json
import math
import random

from replay_helpers import percentile, random_matched, wilson
from judge import validate_verdict
from replay_helpers import order_hash


TARGETS = (.50, .75, .90)
PRIMARY_TARGET = .75


@dataclass(frozen=True)
class CalibrationPolicy:
    group: tuple[str, str, str]
    seed: int
    fraction: float
    calibration_ids: tuple[str, ...]
    calibration_valid: int
    retained_calibration: int
    cutoff_confidence: float | None
    cutoff_hash: str | None
    status: str

    def __post_init__(self):
        object.__setattr__(self, "group", tuple(self.group))
        object.__setattr__(self, "calibration_ids", tuple(self.calibration_ids))
        if self.retained_calibration != math.floor(self.fraction * self.calibration_valid):
            raise ValueError("Policy count differs from its frozen calibration fraction")
        if (self.status == "available") != (self.retained_calibration > 0):
            raise ValueError("Policy availability differs from its retained calibration count")
        if self.status != "available" and (self.cutoff_confidence is not None or self.cutoff_hash is not None):
            raise ValueError("Unavailable policy must accept no cases")


def shared_hash(seed, case_id):
    return order_hash(seed, case_id)


def validate_records(records, group, split, labels_required=False):
    ids = []
    for record in records:
        if tuple(record[key] for key in ("domain", "condition", "model")) != group or record["split"] != split:
            raise ValueError("Records must match the policy group and separate source split")
        case_id = record["case_id"]
        if not isinstance(case_id, str) or not case_id:
            raise ValueError("Stable nonempty case IDs are required")
        ids.append(case_id)
        if record["classification"] == "valid":
            validate_verdict(json.dumps({key: record[key] for key in ("verdict", "confidence")}))
        if labels_required and not isinstance(record.get("candidate_correct"), bool):
            raise ValueError("Test candidate labels must be official booleans")
    if len(set(ids)) != len(ids):
        raise ValueError("A group must have one record per source question")


def calibrate(records, *, domain, condition, model, fraction, seed=2612026):
    if isinstance(fraction, bool) or not 0 <= fraction <= 1:
        raise ValueError("Retention fraction must lie in [0, 1]")
    group = (domain, condition, model)
    validate_records(records, group, "calibration")
    valid = [record for record in records if record["classification"] == "valid"]
    ordered = sorted(valid, key=lambda record: (-record["confidence"], shared_hash(seed, record["case_id"])))
    count = math.floor(fraction * len(valid))
    boundary = ordered[count - 1] if count else None
    status = "available" if count else "no_valid_calibration" if not valid else "zero_retained_calibration"
    return CalibrationPolicy(
        group, seed, fraction, tuple(sorted(record["case_id"] for record in records)), len(valid), count,
        boundary["confidence"] if boundary else None,
        shared_hash(seed, boundary["case_id"]) if boundary else None, status,
    )


def accepts(record, policy):
    if record["classification"] != "valid" or policy.status != "available":
        return False
    return record["confidence"] > policy.cutoff_confidence or (
        record["confidence"] == policy.cutoff_confidence
        and shared_hash(policy.seed, record["case_id"]) <= policy.cutoff_hash
    )


def rate(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator,
            "value": numerator / denominator if denominator else None,
            "wilson_95": wilson(numerator, denominator)}


def summarize(records, policy, planned):
    valid = [record for record in records if record["classification"] == "valid"]
    accepted = [record for record in valid if accepts(record, policy)]
    def mismatch(record):
        return (record["verdict"] == "Correct") != record["candidate_correct"]

    valid_errors = sum(mismatch(record) for record in valid)
    accepted_errors = sum(mismatch(record) for record in accepted)
    attempted = sum(record["classification"] != "unattempted" for record in records)
    risk = accepted_errors / len(accepted) if accepted else None
    pool_error = valid_errors / len(valid) if valid else None
    return {
        "planned": planned, "attempted": attempted, "valid": len(valid),
        "operational_failures": attempted - len(valid), "pending": planned - attempted,
        "accepted": len(accepted), "accepted_ids": [record["case_id"] for record in accepted],
        "official_mismatches_valid": valid_errors, "official_mismatches_accepted": accepted_errors,
        "valid_all_planned": rate(len(valid), planned),
        "accepted_valid": rate(len(accepted), len(valid)),
        "accepted_all_planned": rate(len(accepted), planned),
        "mismatches_accepted": rate(accepted_errors, len(accepted)),
        "mismatches_valid": rate(valid_errors, len(valid)),
        "full_valid_pool_error": pool_error,
        "expected_random_error": pool_error if accepted else None,
        "risk_minus_expected_random": risk - pool_error if accepted else None,
        "policy_status": policy.status,
    }


def evaluate(records, policy, *, planned=None, random_seed=2612026, repeats=1000):
    if isinstance(repeats, bool) or not isinstance(repeats, int) or repeats <= 0:
        raise ValueError("Positive integer simulation repeats are required")
    validate_records(records, policy.group, "test", labels_required=True)
    if set(record["case_id"] for record in records) & set(policy.calibration_ids):
        raise ValueError("Calibration/test source-question overlap")
    planned = len(records) if planned is None else planned
    if isinstance(planned, bool) or not isinstance(planned, int) or planned < len(records):
        raise ValueError("Planned denominator must cover all provided records")
    report = summarize(records, policy, planned)
    valid = [{"judge_correct": (record["verdict"] == "Correct") == record["candidate_correct"]}
             for record in records if record["classification"] == "valid"]
    report["random_control"] = random_matched(valid, report["accepted"], random_seed, repeats)
    return report


def paired_question_bootstrap(records_by_group, policies, *, seed=2612026, repeats=1000):
    """Pair source questions across groups, stratifying on official candidate label.

    Call separately per domain with complete planned question records, including
    invalid/unattempted placeholders. Calibration policies remain fixed in every
    replicate. Undefined conditional-risk replicates are counted explicitly.
    """
    if isinstance(repeats, bool) or not isinstance(repeats, int) or repeats <= 0 or records_by_group.keys() != policies.keys() or not policies:
        raise ValueError("Matching nonempty policy groups and positive repeats are required")
    if len({policy.group[0] for policy in policies.values()}) != 1:
        raise ValueError("Bootstrap must operate within one domain")
    points = {key: evaluate(records, policies[key], repeats=repeats) for key, records in records_by_group.items()}
    indexed = {key: {record["case_id"]: record for record in records} for key, records in records_by_group.items()}
    first = indexed[next(iter(indexed))]
    if any(records.keys() != first.keys() for records in indexed.values()):
        raise ValueError("Paired groups require identical planned source IDs and missing-output placeholders")
    if any(record["candidate_correct"] != first[case_id]["candidate_correct"] for records in indexed.values() for case_id, record in records.items()):
        raise ValueError("Official candidate labels differ across paired conditions/models")
    strata = {label: sorted(case_id for case_id, record in first.items() if record["candidate_correct"] == label) for label in (False, True)}
    names = sorted(indexed)
    pairs = list(combinations(names, 2))
    metrics = ("valid_all_planned", "accepted_valid", "accepted_all_planned", "mismatches_accepted", "risk_minus_expected_random")
    samples = {key: {metric: [] for metric in metrics} for key in names}
    differences = {(left, right): {metric: [] for metric in metrics} for left, right in pairs}

    def value(report, metric):
        item = report[metric]
        return item["value"] if isinstance(item, dict) else item

    generator = random.Random(seed)
    for _ in range(repeats):
        ids = [case_id for stratum in strata.values() for case_id in generator.choices(stratum, k=len(stratum))]
        reports = {key: summarize([indexed[key][case_id] for case_id in ids], policies[key], len(ids)) for key in names}
        for key in names:
            for metric in metrics:
                samples[key][metric].append(value(reports[key], metric))
        for left, right in pairs:
            for metric in metrics:
                lvalue, rvalue = value(reports[left], metric), value(reports[right], metric)
                differences[(left, right)][metric].append(rvalue - lvalue if lvalue is not None and rvalue is not None else None)

    def interval(values):
        defined = [value for value in values if value is not None]
        return {
            "defined_replicates": len(defined), "undefined_replicates": len(values) - len(defined),
            "interval_95": [percentile(defined, .025), percentile(defined, .975)] if defined else None,
        }

    return {
        "seed": seed, "repeats": repeats, "stratum_counts": {str(key): len(value) for key, value in strata.items()},
        "method": "Question resampling paired across groups within domain and official candidate-label strata; fixed calibration policies",
        "points": points,
        "group_intervals": {key: {metric: interval(values) for metric, values in row.items()} for key, row in samples.items()},
        "paired_differences": [{"left": left, "right": right, "direction": "right-minus-left",
                                "metrics": {metric: interval(values) for metric, values in differences[(left, right)].items()}}
                               for left, right in pairs],
        "interval_interpretation": "Descriptive question-bootstrap ranges; conditional-risk intervals use defined replicates only",
    }
