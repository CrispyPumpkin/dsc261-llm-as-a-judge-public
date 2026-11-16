"""Summarize test-only confidence, resource use and prespecified example strata."""
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

HERE = Path(__file__).resolve().parent
REPORT = HERE.parent
sys.path.insert(0, str(REPORT))
from analysis import compute


def load_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def save_csv(name, rows):
    with (HERE / name).open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0], lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def correct(row):
    return (row['verdict'].lower() == 'correct') == row['candidate_correct']


def analyze():
    comparisons = compute()
    cutoffs = {r['domain']: r['cutoff'] for r in comparisons if r['condition'] == 'C1' and r['target'] == .75}
    primary = {(r['domain'], r['condition']): float(r['brier']) for r in load_csv(REPORT / 'tables/primary-summary.csv')}
    resources = {(r['case_id'], r['condition']): r for r in load_csv(HERE / 'test-resources.csv')}
    groups = defaultdict(list)
    for line in (REPORT / 'data/formal-predictions.jsonl').read_text().splitlines():
        row = json.loads(line)
        cost = resources.pop((row['case_id'], row['condition']))
        assert row['classification'] == cost['classification'] and row['split'] == 'test'
        groups[row['domain'], row['condition']].append((row, cost))
    assert not resources and len(groups) == 8
    summary, examples = [], []
    for (domain, condition), pairs in sorted(groups.items()):
        assert len(pairs) == 140
        valid = [r for r, _ in pairs if r['classification'] == 'valid']
        brier = mean((r['confidence'] - correct(r)) ** 2 for r in valid)
        assert math.isclose(brier, primary[domain, condition], abs_tol=1e-10)
        summary.append(dict(domain=domain, condition=condition, attempted=len(pairs), valid=len(valid),
                            truncated=sum(r['classification'] != 'valid' for r,_ in pairs),
                            correct=sum(correct(r) for r in valid), accuracy=mean(correct(r) for r in valid),
                            brier=brier, mean_prompt_tokens=mean(int(c['prompt_tokens']) for _,c in pairs),
                            mean_completion_tokens=mean(int(c['completion_tokens']) for _,c in pairs),
                            median_latency_seconds=median(float(c['latency_seconds']) for _,c in pairs)))
        if condition != 'C1':
            continue
        strata = {'maximum-confidence error': [r for r in valid if r['confidence'] == 1 and not correct(r)],
                  'flagged error': [r for r in valid if not r['accepted']['0.75'] and not correct(r)],
                  'flagged correct': [r for r in valid if not r['accepted']['0.75'] and correct(r)]}
        for name, candidates in strata.items():
            if not candidates:
                raise ValueError(f'Empty example stratum: {domain} {name}')
            case = min(candidates, key=lambda r: r['case_id'])
            examples.append(dict(domain=domain, stratum=name, eligible=len(candidates), case_id=case['case_id'],
                                 cutoff=cutoffs[domain], confidence=case['confidence'], verdict=case['verdict'],
                                 candidate_correct=case['candidate_correct'], retained=case['accepted']['0.75']))
    return summary, examples


if __name__ == '__main__':
    summary, examples = analyze()
    save_csv('judging-summary.csv', summary)
    save_csv('case-review.csv', examples)
