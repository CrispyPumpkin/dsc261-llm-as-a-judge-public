# What the instructor needs

**To reproduce the reported numbers:** the repository snapshot and Python 3.12. Run `python replay.py`. To regenerate the PDFs, also install the pinned report requirements and pass `--pdf`. To inspect the original questions or reconstruct sampling, use the full instructor ZIP instead; the ZIP already includes the repository snapshot. No model access is needed for either path.

| Item | Location | What it establishes |
|---|---|---|
| Sources and licenses | `data-sources/`; ZIP: `supplement/source/` | Exact GSM8K train/test and US MedQA train/dev/test source files; original provenance and terms. |
| Study design | `data-sources/design.json`, `prompt-templates.json`, `src/cohort.py` | Sampling seed, split rules, correct/incorrect candidate generation and judge instructions. |
| Formal cases and inputs | ZIP: `supplement/cohort/` | 400 questions with source IDs, gold answers, candidates, labels and splits; a separate file shows what the judge actually saw. |
| Recorded calls | ZIP: `supplement/calls/` | Final response text and available verdict, confidence, timing, and resource fields. Includes 1,600 four-condition calls and 280 optional-abstention calls. A normalized export, not a transport log. |
| Development evidence | ZIP: `supplement/development/` | Initial and extension cases and calls; separate small medical challenger pilot. These are not additional held-out cases. |
| Frozen analysis inputs | `report/data/`; `report/final/test-resources.csv` | 1,120 held-out four-condition records, calibration context, frozen selections, tie diagnostics, per-call resource measurements and optional abstention. |
| Analysis and figures | `replay.py`, `src/`, `report/`, `report/final/` | Regenerate comparisons at three coverage targets, matched random ranges, paired review, case analysis, output-token tables, and both reports. |
| Package checks | ZIP: `SHA256SUMS.txt`; `verify_supplement.py` | File integrity; independently reconstruct the cohort and check the join between case-level calls and reported predictions. |

The local large language model itself is not included. These materials reproduce the analysis of its recorded decisions; substituting a different judge would be a new experiment. No GPU, model credentials or network endpoint is needed for offline replay.
