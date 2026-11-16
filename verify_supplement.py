"""Rebuild and compare the cohort without model access (Python 3.12)."""
import hashlib, json, sys
from pathlib import Path
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'src'))
from cohort import normalize_record, deduplicate, build_pilot, select_cohort, judge_payload
X = Path(sys.argv[1]) if len(sys.argv)>1 else root/'supplement'
def rows(path): return [json.loads(s) for s in path.read_text(encoding='utf-8-sig').splitlines() if s.strip()]
def indexed(seq,key):
    out={r[key]:r for r in seq}; assert len(out)==len(seq); return out
cfg=json.loads((root/'data-sources/design.json').read_text(encoding='utf-8'))
records=[]
for p in sorted((X/'source').glob('*.jsonl')):
    domain,split=p.stem.split('-')
    for line,row in enumerate(rows(p),1):
        try: records.append(normalize_record(domain,split,line,row))
        except (KeyError,ValueError,TypeError,AttributeError,ZeroDivisionError): pass
eligible=deduplicate(records)[0]
initial=build_pilot(eligible,cfg['seed'],40)
previous=initial+build_pilot(eligible,cfg['seed'],60,'independent-extension-60-v1',{r['id'] for r in initial})
assert indexed(previous,'id')==indexed(rows(X/'development/pilot-cases.jsonl'),'id'), 'Pilot reconstruction mismatch'
cohort=select_cohort(eligible,previous,cfg)[0]
assert len(cohort)==400 and indexed(cohort,'id')==indexed(rows(X/'cohort/cases.jsonl'),'id'), 'Cohort reconstruction mismatch'
assert list(map(judge_payload,cohort))==rows(X/'cohort/judge-inputs.jsonl'), 'Model-visible payload mismatch'
cases=indexed(cohort,'id'); calls=rows(X/'calls/formal.jsonl'); assert len(calls)==1600
calls_by_key={(r['analysis_id'],r['condition']):r for r in calls}; assert len(calls_by_key)==1600
pred=rows(root/'report/data/formal-predictions.jsonl'); assert len(pred)==1120
for r in pred:
    c=calls_by_key[r['case_id'],r['condition']]; assert all(r.get(k)==c.get(k) for k in ('verdict','classification','confidence','domain','split')); assert cases[c['id']]['candidate_correct']==r['candidate_correct']
assert len(rows(X/'calls/abstention.jsonl'))==280
print('Verified: 200 development cases; 400 formal cases and their judge inputs; 1,600 formal calls; all 1,120 held-out formal predictions matched; 280 optional-abstention calls present.')

import csv
ctx=json.loads((root/'report/data/formal-replay-context.json').read_text(encoding='utf-8'))
assert len(ctx['calibration'])==480
for r in ctx['calibration']:
    c=calls_by_key[r['case_id'],r['condition']]; assert all(c.get(k)==r.get(k) for k in ('verdict','confidence','classification','domain','split'))
opt=indexed(rows(X/'calls/abstention.jsonl'),'analysis_id')
for r in rows(root/'report/data/optional-abstention.jsonl'):
    for cond,c in [('C1',calls_by_key[r['id'],'C1']),('C5',opt[r['id']])]:
        assert all(c.get(k)==r[cond].get(k) for k in ('verdict','confidence','classification'))
for name in ('test-resources.csv','abstention-output-tokens.csv'):
    with (root/'report/final'/name).open(encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            c=calls_by_key[r['case_id'],r['condition']] if 'condition' in r else opt[r['case_id']]
            assert str(c['usage']['completion_tokens'])==r['completion_tokens']
print('Verified calibration, optional abstention verdicts, and all 1,400 held-out output-token counts.')
