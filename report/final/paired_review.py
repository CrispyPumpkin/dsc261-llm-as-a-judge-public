"""Replay two-stage grading using frozen verdicts, selection flags and call costs."""
import json
from collections import Counter
from itertools import product
from math import comb

from study import HERE, REPORT, correct, load_csv, save_csv


def random_scores(changes, size, starting_score):
    """Count all same-size subsets by their final number of correct decisions."""
    gains = changes.count(1)
    losses = changes.count(-1)
    neutral = len(changes) - gains - losses
    counts = Counter()
    for gain in range(min(gains, size) + 1):
        for loss in range(min(losses, size - gain) + 1):
            other = size - gain - loss
            if other <= neutral:
                counts[starting_score + gain - loss] += (
                    comb(gains, gain) * comb(losses, loss) * comb(neutral, other)
                )
    total = comb(len(changes), size)
    assert sum(counts.values()) == total
    assert len(changes) * sum((score-starting_score)*w for score,w in counts.items()) == total * size * sum(changes)
    return counts


def percentile(counts, thousandths):
    total = sum(counts.values())
    cumulative = 0
    for score, weight in sorted(counts.items()):
        cumulative += weight
        if 1000 * cumulative >= thousandths * total:
            return score
    raise ValueError('Empty distribution')


def replay():
    grouped = {}
    for line in (REPORT/'data/formal-predictions.jsonl').read_text().splitlines():
        row = json.loads(line)
        key = row['domain'], row['condition']
        entries = grouped.setdefault(key, {})
        assert row['split'] == 'test' and row['case_id'] not in entries
        entries[row['case_id']] = row
    costs = {(r['case_id'], r['condition']): int(r['completion_tokens'])
             for r in load_csv(HERE/'test-resources.csv')}
    policies = {(r['domain'],r['condition'],r['target']):r for r in load_csv(REPORT/'coverage-results.csv')}
    assert len(costs) == sum(map(len, grouped.values())) == 1120
    results = []
    for domain, (base, thinking) in product(('gsm8k','medqa'), (('C1','C3'),('C2','C4'))):
        first, second = grouped[domain,base], grouped[domain,thinking]
        assert first.keys() == second.keys() and len(first) == 140
        ids = sorted(first)
        changes = {}
        first_correct = 0
        thinking_correct = 0
        missing = set()
        for q in ids:
            a,b = first[q],second[q]
            assert a['candidate_correct'] == b['candidate_correct'] and a['classification'] == 'valid'
            initial = int(correct(a))
            first_correct += initial
            if b['classification'] == 'valid':
                end = int(correct(b))
                thinking_correct += end
                changes[q] = end - initial
            else:
                missing.add(q)
                changes[q] = 0  # Keep first verdict on an incomplete second call.
        first_tokens = sum(costs[q,base] for q in ids)
        thinking_tokens = sum(costs[q,thinking] for q in ids)
        for target in ('0.5','0.75','0.9'):
            rule = policies[domain,base,target]
            selected = {q for q in ids if not first[q]['accepted'][target]}
            size = len(selected)
            assert 140-size == int(rule['retained'])
            gains = sum(changes[q] == 1 for q in selected)
            losses = sum(changes[q] == -1 for q in selected)
            actual = first_correct + gains - losses
            counts = random_scores(list(changes.values()),size,first_correct)
            expected = sum(s*w for s,w in counts.items())/sum(counts.values())
            cutoff = float(rule['cutoff'])
            below = {q for q in ids if first[q]['confidence'] < cutoff}
            tied = {q for q in ids if first[q]['confidence'] == cutoff}
            assert below <= selected <= below | tied
            tie_average = first_correct + sum(changes[q] for q in below)
            if tied:
                tie_average += (size-len(below))*sum(changes[q] for q in tied)/len(tied)
            results.append(dict(domain=domain,base=base,thinking=thinking,target=target,
                switched=size,first_correct=first_correct,corrected=gains,introduced=losses,
                fallback=len(selected & missing),final_correct=actual,random_mean=round(expected,4),
                random_p025=percentile(counts,25),random_p975=percentile(counts,975),
                tie_mean=round(tie_average,4),thinking_only_correct=thinking_correct,
                thinking_only_missing=len(missing),all_switched_with_fallback=first_correct+sum(changes.values()),
                first_tokens=first_tokens,thinking_only_tokens=thinking_tokens,
                policy_tokens=first_tokens+sum(costs[q,thinking] for q in selected),
                random_expected_tokens=round(first_tokens+size*thinking_tokens/len(ids),2)))
    return results


if __name__ == '__main__':
    save_csv('paired-results.csv', replay())
