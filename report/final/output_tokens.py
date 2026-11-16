"""Tabulate test-set output lengths and grading outcomes for standalone and replay policies."""
import json
from collections import Counter

from study import HERE, REPORT, correct, load_csv, save_csv


def summarize():
    outputs = []
    def add(domain, method, prompt, target, reviews, correct_count, tokens, basis):
        outputs.append(dict(domain=domain, method=method, prompt=prompt, retention_target=target,
                            cases=140, second_calls=reviews, correct_verdicts=correct_count,
                            output_tokens=tokens, basis=basis))

    resource = {(r['case_id'], r['condition']): int(r['completion_tokens'])
                for r in load_csv(HERE / 'test-resources.csv')}
    counts = Counter()
    tokens = Counter()
    for line in (REPORT / 'data/formal-predictions.jsonl').read_bytes().splitlines():
        r = json.loads(line)
        group = r['domain'], r['condition']
        counts[group] += 1
        tokens[group] += resource.pop((r['case_id'], r['condition']))
    assert not resource and len(counts) == 8 and set(counts.values()) == {140}
    for r in load_csv(HERE / 'judging-summary.csv'):
        group = r['domain'], r['condition']
        add(group[0], 'standalone', group[1], '', 0, int(r['correct']), tokens[group], 'observed')

    active = {r['case_id']: int(r['completion_tokens'])
              for r in load_csv(HERE / 'abstention-output-tokens.csv')}
    active_counts, active_correct, active_tokens = Counter(), Counter(), Counter()
    for line in (REPORT / 'data/optional-abstention.jsonl').read_bytes().splitlines():
        r = json.loads(line)
        domain = r['domain']
        active_counts[domain] += 1
        active_tokens[domain] += active.pop(r['id'])
        if r['C5']['classification'] == 'valid' and r['C5']['verdict'] in ('Correct', 'Incorrect'):
            active_correct[domain] += correct(dict(r['C5'], candidate_correct=r['candidate_correct']))
    assert not active and active_counts == {'gsm8k': 140, 'medqa': 140}
    for domain in sorted(active_counts):
        add(domain, 'abstention permitted', 'C5', '', 0, active_correct[domain], active_tokens[domain], 'observed')

    for r in load_csv(HERE / 'paired-results.csv'):
        domain, base, second = r['domain'], r['base'], r['thinking']
        size = int(r['switched'])
        pair = base + '/' + second
        assert tokens[domain, base] == int(r['first_tokens'])
        assert tokens[domain, second] == int(r['thinking_only_tokens'])
        expected = round(tokens[domain, base] + size * tokens[domain, second] / 140, 2)
        assert expected == float(r['random_expected_tokens'])
        add(domain, 'confidence review', pair, r['target'], size, int(r['final_correct']), int(r['policy_tokens']), 'observed replay')
        add(domain, 'random review', pair, r['target'], size, r['random_mean'], expected, 'same-count expectation')
    assert len(outputs) == 34
    save_csv('output-token-summary.csv', outputs)


if __name__ == '__main__':
    summarize()
