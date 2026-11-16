"""Offline replay of frozen results. Pass --pdf to also regenerate the figures and PDFs."""
from pathlib import Path
import os,sys,subprocess,argparse
args=argparse.ArgumentParser(description=__doc__);args.add_argument('--pdf',action='store_true'); opts=args.parse_args(); root=Path(__file__).resolve().parent
scripts=['report/reproduce.py','report/analysis.py','report/final/study.py','report/final/paired_review.py','report/final/output_tokens.py']
if opts.pdf: scripts+=['report/build.py','report/final/render.py']
for script in scripts:
    print('Running',script,flush=True); subprocess.run([sys.executable,'-B','-X','utf8',str(root/script)],cwd=root,check=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
