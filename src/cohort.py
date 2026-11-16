"""Original normalization, deduplication, candidate and split rules."""
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib, html, json, re, unicodedata
from judge import build_messages

DOMAINS = ("gsm8k", "medqa")
SPLIT_PRIORITY = {"test": 0, "dev": 1, "train": 2}
IMAGE_NOUN = r"(?:image|figure|photograph|picture|photomicrograph|ECG|EKG|electrocardiogram|radiograph|x-ray|MRI|scan)"
IMAGE_REFERENCE = re.compile(
    rf"<img|\b(?:shown|depicted|pictured)\b.{{0,40}}\b{IMAGE_NOUN}\b"
    rf"|\b(?:following|above|below|attached)\s+{IMAGE_NOUN}\b"
    rf"|\b{IMAGE_NOUN}\b.{{0,35}}\b(?:shown|below|above|attached|depicted)\b"
    rf"|\b(?:see|refer to)\s+(?:the\s+)?{IMAGE_NOUN}\b",
    re.IGNORECASE,
)


def normalize_text(text):
    text = unicodedata.normalize("NFKC", html.unescape(text))
    text = text.translate(str.maketrans({
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-", "\u200b": "",
    }))
    return " ".join(text.casefold().split())


def stable_hash(*parts):
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def parse_numeric(value):
    """Exact equivalence for signed integers, decimals, fractions, and grouped digits."""
    value = value.strip()
    if re.fullmatch(r"[+-]?\d+/[+-]?\d+", value):
        return Fraction(value)
    if not re.fullmatch(r"[+-]?(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?", value):
        raise ValueError("Unrecognized numeric final answer")
    return Fraction(value.replace(",", ""))


def render_integer(value):
    if value.denominator != 1:
        raise ValueError("This source preparation requires integer answers")
    return str(value.numerator)


def math_errors(gold):
    """Predefined arithmetic errors with the same sign and integer format as gold."""
    if gold == 0 or gold.denominator != 1:
        return []
    alternatives = [
        ("plus_one", gold + 1),
        ("minus_one", gold - 1),
        ("double", gold * 2),
        ("half", gold / 2),
    ]
    return [
        (rule, render_integer(value))
        for rule, value in alternatives
        if value != gold and value.denominator == 1 and value * gold > 0
    ]


def normalize_record(domain, split, line, raw):
    source_id = f"{domain}:{split}:{line:05d}"
    question = raw["question"].strip()
    if not question:
        raise ValueError("empty_question")
    if IMAGE_REFERENCE.search(question):
        raise ValueError("missing_image_reference")
    question_hash = stable_hash(normalize_text(question))
    record = {
        "id": f"{domain}-{question_hash[:20]}",
        "question_hash": question_hash,
        "source_id": source_id,
        "domain": domain,
        "source_split": split,
        "source_line": line,
        "question": question,
    }
    if domain == "gsm8k":
        solution = raw["answer"]
        if solution.count("####") != 1:
            raise ValueError("invalid_final_answer_separator")
        gold = parse_numeric(solution.rsplit("####", 1)[1])
        if not math_errors(gold):
            raise ValueError("no_sign_and_type_preserving_math_error")
        record.update(gold=render_integer(gold), solution=solution)
    else:
        options = raw["options"]
        if not isinstance(options, dict) or set(options) != set("ABCDE"):
            raise ValueError("non_native_five_option_mapping")
        if any(not isinstance(text, str) or not text.strip() for text in options.values()):
            raise ValueError("invalid_option_text")
        key = raw["answer_idx"]
        if key not in options or normalize_text(raw["answer"]) != normalize_text(options[key]):
            raise ValueError("official_answer_mapping_mismatch")
        if len({normalize_text(text) for text in options.values()}) != len(options):
            raise ValueError("equivalent_option_text")
        record.update(
            options=options, gold=options[key], gold_key=key,
            source_meta=raw.get("meta_info"),
        )
    return record


def deduplicate(records):
    groups = defaultdict(list)
    for record in records:
        groups[record["question_hash"]].append(record)
    kept, exclusions, overlaps = [], [], Counter()
    for question_hash, group in sorted(groups.items()):
        splits = sorted({item["source_split"] for item in group})
        if len(group) > 1:
            overlaps["/".join(splits)] += 1
        signatures = {
            (
                item["domain"], normalize_text(item["gold"]),
                tuple(sorted(normalize_text(text) for text in item.get("options", {}).values())),
            )
            for item in group
        }
        if len(signatures) != 1:
            exclusions.extend({
                "source_id": item["source_id"], "question_hash": question_hash,
                "reason": "conflicting_duplicate_content",
            } for item in group)
            continue
        ordered = sorted(
            group,
            key=lambda item: (SPLIT_PRIORITY[item["source_split"]], item["source_line"]),
        )
        kept.append(ordered[0])
        exclusions.extend({
            "source_id": item["source_id"], "question_hash": question_hash,
            "reason": "normalized_duplicate", "kept_source_id": ordered[0]["source_id"],
        } for item in ordered[1:])
    return kept, exclusions, dict(sorted(overlaps.items()))

def judge_payload(record):
    payload = {
        "id": record["id"], "question": record["question"],
        "candidate": record["candidate"],
    }
    if "options" in record:
        payload["options"] = record["options"]
    return payload

def judge_messages(payload, rubric=False):
    return build_messages(payload["question"], payload["candidate"], payload.get("options"), rubric=rubric)

def validate_pilot(pilot, formal):
    ids = [record["id"] for record in pilot + formal]
    hashes = [record["question_hash"] for record in pilot + formal]
    if len(ids) != len(set(ids)) or len(hashes) != len(set(hashes)):
        raise ValueError("Pilot/formal question overlap or ID collision")
    for record in pilot:
        if record["domain"] == "gsm8k":
            gold, candidate = parse_numeric(record["gold"]), parse_numeric(record["candidate"])
            if (candidate == gold) != record["candidate_correct"]:
                raise ValueError("Math candidate label/equivalence mismatch")
            if (
                candidate * gold <= 0 or candidate.denominator != 1
                or render_integer(candidate) != record["candidate"]
            ):
                raise ValueError("Math candidate sign/type/rendering clue")
        else:
            if (record["candidate_key"] == record["gold_key"]) != record["candidate_correct"]:
                raise ValueError("MedQA candidate label/mapping mismatch")
            expected = f"{record['candidate_key']}. {record['options'][record['candidate_key']]}"
            if (
                record["candidate"] != expected
                or normalize_text(record["gold"]) != normalize_text(record["options"][record["gold_key"]])
            ):
                raise ValueError("MedQA native source mapping mismatch")
        payload = judge_payload(record)
        if set(payload) - {"id", "question", "candidate", "options"}:
            raise ValueError("Evaluator fields entered judge artifact")
        for rubric in (False, True):
            user_fields = json.loads(judge_messages(payload, rubric)[1]["content"])
            if set(user_fields) - {"question", "candidate", "options"}:
                raise ValueError("Evaluator fields entered actual judge messages")

def select_cohort(records, previous, config):
    seed, namespaces = config["seed"], config["namespaces"]
    previous_ids = {row["source_id"] for row in previous}
    previous_hashes = {stable_hash(normalize_text(row["question"])) for row in previous}
    overlap_exclusions = []
    available = []
    for row in records:
        if row["source_split"] != "test":
            continue
        if row["source_id"] in previous_ids or row["question_hash"] in previous_hashes:
            overlap_exclusions.append({"source_id": row["source_id"], "question_hash": row["question_hash"], "reason": "pilot_or_extension_source_id_or_question_hash"})
        else:
            available.append(row)
    cohort = []
    for domain in DOMAINS:
        selected = sorted(
            [row for row in available if row["domain"] == domain],
            key=lambda row: stable_hash(seed, namespaces["selection"], domain, row["question_hash"]),
        )[:200]
        if len(selected) != 200:
            raise ValueError("Insufficient eligible test questions")
        split_order = sorted(selected, key=lambda row: stable_hash(seed, namespaces["split"], domain, row["question_hash"]))
        for split, pool in (("calibration", split_order[:60]), ("test", split_order[60:])):
            label_order = sorted(pool, key=lambda row: stable_hash(seed, namespaces["label"], domain, split, row["question_hash"]))
            correct_ids = {row["id"] for row in label_order[:len(pool) // 2]}
            for source in pool:
                row = dict(source, split=split, candidate_correct=source["id"] in correct_ids)
                if domain == "gsm8k":
                    rule, wrong = min(math_errors(parse_numeric(row["gold"])),
                                      key=lambda pair: stable_hash(seed, namespaces["wrong"], row["question_hash"], pair[0]))
                    row.update(candidate=row["gold"] if row["candidate_correct"] else wrong,
                               error_rule="official_answer" if row["candidate_correct"] else rule)
                else:
                    wrong = min([key for key in row["options"] if key != row["gold_key"]],
                                key=lambda key: stable_hash(seed, namespaces["wrong"], row["question_hash"], key))
                    key = row["gold_key"] if row["candidate_correct"] else wrong
                    row.update(candidate_key=key, candidate=f"{key}. {row['options'][key]}",
                               error_rule="official_option" if row["candidate_correct"] else "native_distractor")
                cohort.append(row)
    cohort.sort(key=lambda row: (row["domain"], row["split"], row["id"]))
    validate_cohort(cohort, previous)
    return cohort, overlap_exclusions

def validate_cohort(cohort, previous):
    validate_pilot(cohort, [])
    if len(cohort) != 400 or len({row["source_id"] for row in cohort}) != 400:
        raise ValueError("Formal cohort must have 400 unique source questions")
    if {row["source_id"] for row in cohort} & {row["source_id"] for row in previous}:
        raise ValueError("Formal source ID overlaps previous evidence")
    previous_hashes = {stable_hash(normalize_text(row["question"])) for row in previous}
    if {row["question_hash"] for row in cohort} & previous_hashes:
        raise ValueError("Formal normalized question overlaps previous evidence")
    for domain in DOMAINS:
        for split, count in (("calibration", 60), ("test", 140)):
            rows = [row for row in cohort if row["domain"] == domain and row["split"] == split]
            if len(rows) != count or Counter(row["candidate_correct"] for row in rows) != {True: count // 2, False: count // 2}:
                raise ValueError("Formal split/label counts differ from the reviewed contract")
    if any(row["source_split"] != "test" for row in cohort):
        raise ValueError("Formal questions must come from official test pools")

def build_pilot(records, seed, count=40, namespace="", excluded_ids=(), domains=DOMAINS, source_split="train"):
    if count % 2:
        raise ValueError("Pilot count must be even for exact balance")
    pilot = []
    prefix = namespace + "/" if namespace else ""
    for domain in domains:
        eligible = [
            record for record in records
            if record["domain"] == domain and record["source_split"] == source_split
            and record["id"] not in excluded_ids
        ]
        selected = sorted(
            eligible,
            key=lambda record: stable_hash(seed, prefix + "question_sample", domain, record["question_hash"]),
        )[:count]
        if len(selected) != count:
            raise ValueError(f"Insufficient eligible training questions for {domain}")
        label_order = sorted(
            selected,
            key=lambda record: stable_hash(seed, prefix + "candidate_label", domain, record["question_hash"]),
        )
        correct_ids = {record["id"] for record in label_order[:count // 2]}
        for source in selected:
            record = dict(source)
            correct = record["id"] in correct_ids
            if domain == "gsm8k":
                errors = math_errors(parse_numeric(record["gold"]))
                rule, wrong = min(
                    errors,
                    key=lambda pair: stable_hash(seed, prefix + "math_error", record["question_hash"], pair[0]),
                )
                record.update(
                    candidate=record["gold"] if correct else wrong,
                    error_rule="official_answer" if correct else rule,
                )
            else:
                distractors = [key for key in record["options"] if key != record["gold_key"]]
                wrong_key = min(
                    distractors,
                    key=lambda key: stable_hash(seed, prefix + "native_distractor", record["question_hash"], key),
                )
                candidate_key = record["gold_key"] if correct else wrong_key
                record.update(
                    candidate=f"{candidate_key}. {record['options'][candidate_key]}",
                    candidate_key=candidate_key,
                    error_rule="official_option" if correct else "native_distractor",
                )
            record["candidate_correct"] = correct
            pilot.append(record)
    return pilot

