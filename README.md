# Can a Language-Model Judge Identify Its Own Grading Errors?

DSC 261 · Responsible Data Science. A locally hosted language model served as qwen3.8-27b graded supplied answers to math and medical questions. We test when its reported confidence helps to select cases for abstention or a second pass, and how many output tokens those policies use.

| Read | Report | Supporting results |
|---|---|---|
| Final report | [PDF](report/final/final-report.pdf) · [editable text](report/final/final-report.md) | [Paired review](report/final/paired-results.csv) · [output tokens](report/final/output-token-summary.csv) |
| Midterm update | [PDF](report/midpoint-update.pdf) · [editable text](report/midpoint-update.md) | [Selective grading at three coverage targets](report/coverage-results.csv) |

**Reproduce the numbers.** From the root, run `python replay.py` with Python 3.12. No model, GPU, credentials, or additional packages are required for the numerical analysis. The program checks the frozen policies and regenerates the tables for both reports. For the PDFs and figures, install the [pinned rendering dependencies](report/requirements-report.txt) with `python -m pip install -r report/requirements-report.txt`, then run `python replay.py --pdf`.

**Rebuild the cases.** The instructor ZIP contains this same snapshot plus a `supplement/` folder. Extract the entire ZIP, then run `python verify_supplement.py`. This reconstructs the selection from the source questions, compares candidates and judge-visible inputs, and joins the held-out verdicts back to individual questions. The saved responses allow analysis without fresh inference. They do not establish that new model calls would produce identical responses.

**Where to look:** [frozen analysis inputs](report/data/README.md), [sources, licenses, prompt templates and design](data-sources/), [cohort and statistical routines](src/), and the [instructor inventory](INVENTORY.md). The two reports share the same analytical inputs. Earlier midterm and final milestones remain in Git history; use this snapshot for instruction and reproduction.
