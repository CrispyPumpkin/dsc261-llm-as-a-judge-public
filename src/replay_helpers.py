"""Deterministic sampling and intervals used in the original analysis."""
import hashlib, json, math, random, statistics

def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()

def order_hash(*parts):
    return digest_bytes(json.dumps(parts, separators=(",", ":")).encode("utf-8"))

def wilson(successes, count):
    if not count:
        return None
    z = 1.959963984540054
    proportion = successes / count
    denominator = 1 + z * z / count
    center = (proportion + z * z / (2 * count)) / denominator
    half = z * math.sqrt(proportion * (1 - proportion) / count + z * z / (4 * count * count)) / denominator
    return [max(0, center - half), min(1, center + half)]

def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)

def random_matched(rows, retained, seed, repeats=1000):
    if retained < 0 or retained > len(rows):
        raise ValueError("Random count must match an eligible retained count")
    generator = random.Random(seed)
    errors = [sum(not row["judge_correct"] for row in generator.sample(rows, retained)) for _ in range(repeats)]
    risks = [count / retained for count in errors] if retained else []
    return {
        "seed": seed, "repeats": repeats, "retained_each_draw": retained,
        "eligible_count": len(rows), "draw_error_counts": errors,
        "mean_risk": statistics.mean(risks) if risks else None,
        "risk_draw_interval_95": [percentile(risks, 0.025), percentile(risks, 0.975)] if risks else None,
        "risk_standard_deviation": statistics.pstdev(risks) if risks else None,
        "analytic_expected_risk": sum(not row["judge_correct"] for row in rows) / len(rows) if rows and retained else None,
        "interval_interpretation": "Random-subset variation conditional on this eligible pool",
    }
