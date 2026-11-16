"""Replay saved judgments and validate every summary against the frozen v0.0 tables."""
import csv
import json
from collections import Counter
from math import isclose
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORT = HERE

def jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]

def prior_table(name):
    with (REPORT / 'tables' / name).open(encoding='utf-8-sig', newline='') as handle:
        return {(r['domain'], r['condition'], r['calibration_target']): r for r in csv.DictReader(handle)}

def wrong(row):
    assert row['verdict'] in ('Correct', 'Incorrect')
    return (row['verdict'] == 'Correct') != row['candidate_correct']

def compute():
    predictions = jsonl(REPORT / 'data/formal-predictions.jsonl')
    summary = prior_table('primary-summary.csv')
    ties = prior_table('confidence-tie-diagnostic.csv')
    results = []
    for (domain, condition, target), old in sorted(summary.items()):
        cases = [r for r in predictions if (r['domain'],r['condition'],r['split']) == (domain,condition,'test')]
        assert len(cases) == len({r['case_id'] for r in cases}) == 140
        valid = [r for r in cases if r['classification']=='valid']
        kept = [r for r in valid if r['accepted'][target]]
        n,k = len(valid),len(kept)
        errors,kept_errors = sum(map(wrong,valid)),sum(map(wrong,kept))
        diag = ties[domain,condition,target]
        cutoff = float(diag['cutoff'])
        above = [r for r in valid if r['confidence']>cutoff]
        boundary = [r for r in valid if r['confidence']==cutoff]
        t = k-len(above)
        assert all(r['accepted'][target] for r in above) and all(r['confidence']>=cutoff for r in kept)
        assert 0 <= t <= len(boundary)
        tie_risk = (sum(map(wrong,above)) + (t*sum(map(wrong,boundary))/len(boundary) if boundary else 0))/k
        assert (n,k,errors,kept_errors)==tuple(int(old[key]) for key in ('valid','accepted','official_mismatches_valid','official_mismatches_accepted'))
        assert isclose(tie_risk,float(diag['expected_risk_over_uniform_tie_subsets'])) and isclose(errors/n,float(old['expected_random_error']))
        results.append(dict(domain=domain,condition=condition,target=float(target),planned=len(cases),valid=n,retained=k,errors_valid=errors,errors_retained=kept_errors,actual_coverage=k/len(cases),coverage_among_valid=k/n,confidence_risk=kept_errors/k,random_risk=errors/n,random_expected_errors=k*errors/n,cutoff=cutoff,tied=len(boundary),tied_retained=t,tie_averaged_risk=tie_risk))
    assert len(results)==24
    c5 = jsonl(REPORT/'data/optional-abstention.jsonl')
    assert len(c5)==len({r['id'] for r in c5})==280
    counts=Counter()
    for r in c5:
        v=r['C5']; assert v['classification']=='valid'
        counts[r['domain'],'total']+=1
        if v['verdict']=='Abstain': counts[r['domain'],'abstain']+=1
        else: counts[r['domain'],'wrong']+=wrong(dict(v,candidate_correct=r['candidate_correct']))
    for d,e in [('gsm8k',41),('medqa',22)]: assert (counts[d,'total'],counts[d,'abstain'],counts[d,'wrong'])==(140,0,e)
    return results

if __name__=='__main__':
    rows=compute()
    with (HERE/'coverage-results.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0].keys(),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    print('Verified 24 comparisons and 280 optional-deferral verdicts.')
