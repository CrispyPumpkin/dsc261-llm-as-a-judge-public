# Can a language-model judge identify its own grading errors?
DSC 261 · Responsible Data Science · Final report

Haoxiang Qiu, Yuguo Du, Edith Gu, Lucia Si, Wenkai Kang

## Abstract
An automated grader makes two decisions possible: whether to accept a candidate answer and whether to trust the grader's verdict. We study the second on 400 benchmark questions using four configurations of a local large language model. At a target of 75% retention, its plain prompt routed 13 of 21 medical grading errors into 54 review slots, versus 8.1 expected at random. The apparent advantage on math mostly disappeared after accounting for identical confidence scores: 136 of 140 judgments shared the maximum. A separate prompt permitting abstention deferred none of 280 judgments. Enabling thinking improved grading accuracy but increased output length and occasionally produced no usable verdict. Using existing thinking-enabled verdicts to regrade the 54 medical referrals corrected 12 errors and introduced two, yielding 129 correct versus 125.2 expected with random referral. These results distinguish a better grader from a grader that can reliably prioritize its own mistakes.

## 1 Introduction
Consider an exam grader that rejects a correct numerical answer and reports complete confidence. A system that accepts confident judgments automatically can pass that mistake on to a student. Reviewing everything defeats much of the purpose of automated grading, but reviewing a fixed number of arbitrarily chosen answers may miss errors that a useful score could have located. We ask a practical question: given the same number of review slots, does prioritizing a judge's least confident verdicts find more errors than random selection?

Three questions organize the study. First, does the model decline when it is explicitly allowed to? Second, when the choice is made externally, do the model's scores distinguish correct from incorrect verdicts? Third, if a rubric or more computation improves the verdict itself, does its confidence become more useful for allocating review? A judge could excel at one task and fail at another. In particular, a solver that rarely makes errors leaves little evidence about whether it can rank those errors.

## 2 Related work
Selective classification [1] evaluates a predictor on the cases it retains and interprets error together with coverage. We borrow this comparison, with the grading decision as the prediction. Work on language models' self-reported probabilities [2] motivates asking for confidence, but a numerical answer alone does not establish calibration or discrimination. LLM-as-a-judge research [3] studies the reliability of automated evaluation. Here the outcome is narrower than preference agreement: an official key lets us score whether a judge correctly accepted or rejected a fixed candidate. It also lets us count errors referred for review without asserting what a human reviewer would do next.

## 3 Study design
**Cohort and labels.** We sampled 200 questions from each official test pool. Each question has one fixed candidate, shared across all prompts. In each domain, 60 questions calibrate the retention rule and 140 evaluate it. Each split contains equal numbers of correct and incorrect candidates. The judge receives the question, candidate and original options where applicable; only the evaluator has the official key. If the candidate is wrong and the judge rejects it, the judge earns a correct verdict.

| Domain | Correct candidate | Incorrect candidate |
| --- | --- | --- |
| GSM8K · math [4] | Official numeric answer | Deterministic change to the official number |
| US MedQA · exam questions [5] | Official answer option | An existing distractor from the same question |

The original pilot tested 100 questions per domain. The plain prompt disagreed with official labels 41 times on math and 13 times on medicine, enough to study selection in both. A harder medical challenger showed repeated truncations in its limited trial. We retained the two original domains; the formal sampling protocol excludes prior pilot and extension items by source ID and normalized question hash. This separates our own development work from evaluation, but cannot rule out prior exposure during model training. No judge generated the candidates.

**Unit of analysis.** Each test domain contains 70 correct and 70 incorrect candidates. The same item can elicit four verdicts, so the number of model calls is not the number of independent questions. Rejecting an incorrect candidate is a successful judgment, just as accepting a correct one is. A high-confidence rejection is not a claim that the candidate is probably correct: the reported probability refers to the verdict the judge just made.

**Controlled prompts.** We queried a local large language model for a binary verdict and confidence in that verdict. We crossed two prompt choices: providing a grading rubric and enabling the endpoint's thinking setting. Across four conditions and 400 candidates, 1,586 of 1,600 calls produced valid judgments. The 14 truncated responses occurred on medical questions with thinking enabled. We count these separately from a deliberate decision to defer.

## 4 Direct abstention
In a separate run, we kept thinking off and used the plain prompt, but gave the judge a third option: it could abstain. The local model graded all 280 evaluation cases. It made 41 math errors and 22 medical errors. Of those 63 mistakes, 48 accepted a wrong candidate and 15 rejected a correct one. Giving the judge discretion referred none of them for review. This establishes its behavior on this prompt and sample. With all cases retained, there is no selected subset on which to evaluate its ability to pick cases. The following comparison uses the confidence scores from the binary-verdict runs.


## 5 Confidence under a fixed review budget
For each domain and prompt, we used the calibration scores to set a cutoff for each target (50%, 75%, 90%) and fixed the rule for ties. Applying that rule to new cases produces a realized count, k. Coverage is k divided by 140 planned cases. Retained error rate is the number of incorrect retained verdicts divided by k. The random comparison draws exactly k from the same valid pool. Its expected error rate equals the pool's error rate because each verdict has the same chance of being drawn.

The three percentages are calibration targets, not probability thresholds or enforced test quotas. For example, the medical 75% policy does not mean keeping scores of 0.75 or higher, nor does it mean taking the top 105 test cases. That latter procedure would use the test cohort to set the rule anew. We instead preserve the policy a user could have fixed before seeing those cases. Consequently, matching random selection to actual k, rather than target k, is essential.

![Retained error versus actual coverage in both domains](../risk-coverage.png)

Figure 1. Plain prompt, thinking off. Points show frozen confidence rules and labels show their calibration targets. Dashed lines give the exact matched random expectation. A lower point at the same horizontal position means fewer errors for the same number of reviews.

Table 1. Counts behind Figure 1. Each group began with 140 test cases. Before selection, the plain judge made 40 math errors (28.57%) and 21 medical errors (15.00%).

| Target | GSM8K retained | Errors / retained | MedQA retained | Errors / retained |
| --- | --- | --- | --- | --- |
| 50% | 69/140 | 19/69 · 27.54% | 64/140 | 6/64 · 9.38% |
| 75% | 102/140 | 24/102 · 23.53% | 86/140 | 8/86 · 9.30% |
| 90% | 123/140 | 31/123 · 25.20% | 122/140 | 16/122 · 13.11% |

### What did 54 medical review slots buy?
At the 75% target, the rule actually retained 86/140 judgments (61.4%). Of the 21 original errors, 8 remained and 13 fell in the 54 flagged cases. Randomly flagging 54 would capture 8.1 errors on average. Confidence therefore located about five additional errors at the same workload. Moving from the 50% to the 75% target retained 22 more decisions with almost the same error rate. At the 90% target only 18 were flagged, and retained error rose to 13.11%. The fixed-rule medical error gap at the 75% target was -5.70 percentage points (paired bootstrap 95% interval, -11.10 to -1.02 points). This interval holds the calibrated policy fixed; the tie analysis below varies which equal-score cases are retained. These counts evaluate routing against the official key; we did not measure a human reviewer's subsequent decisions.


### How much of the gain survives tied scores?
On GSM8K, 136/140 plain-prompt judgments received maximum confidence. At the 75% target, 102 of those 136 tied cases were retained. The fixed rule happened to keep 24 errors, but the tied group contained 38. Uniformly choosing 102 within the tie would keep 102 × 38/136 = 28.5 errors on average. The resulting 27.94% risk is close to the 28.57% random baseline. The apparent five-point gain in Figure 1 thus depends largely on which equal-score cases were kept. On MedQA, averaging over cutoff ties yields 10.96%, still below its 15.00% random baseline.

These diagnostics answer different questions. The frozen result describes the decisions this particular rule would have made. The tie average keeps all strictly higher scores and the same number of boundary cases but averages uniformly over equally scored choices. It asks how much information the scores themselves provided. For rubric-only math, the fixed error rate of 20.79% rises to 26.81% under this check, versus 26.43% at random. The direction of the small residual difference reverses. For rubric-only medicine, the tie average is 11.04% versus 13.57% at random. Adding a rubric does not eliminate the domain difference.

## 6 Rubric and thinking ablations
Table 2. Results at the 75% calibration target. Fractions give errors / judgments. The random expectation in each row equals the error rate of all valid judgments. Parenthesized rates show the observed error among retained judgments.

| Prompt | GSM8K all valid | GSM8K retained | MedQA all valid | MedQA retained |
| --- | --- | --- | --- | --- |
| Plain | 40/140 | 24/102 (23.53%) | 21/140 | 8/86 (9.30%) |
| Rubric | 37/140 | 21/101 (20.79%) | 19/140 | 12/105 (11.43%) |
| Thinking | 1/140 | 1/92 (1.09%) | 5/138 | 0/107 (0.00%) |
| Thinking + rubric | 0/140 | 0/90 (0.00%) | 4/136 | 0/113 (0.00%) |

Enabling thinking coincided with the largest drop in overall error. On math, one or zero errors remained to be found. On medicine, both thinking settings placed all observed valid errors below the cutoff. Zero retained errors still permits positive underlying risk: the 95% Wilson upper limits are 3.47% for 0/107 and 3.29% for 0/113. With the rubric alone, both domains had slightly fewer total mistakes than under the plain prompt; the confidence rule also retained different numbers. Comparisons to random are matched within each row.

The denominator matters when interpreting a stronger configuration. Counting every attempted test item, thinking alone on MedQA produced 133 correct verdicts, five wrong ones and two truncations. Adding a rubric produced 132 correct verdicts, four wrong ones and four truncations. The latter has slightly better accuracy among valid answers but did not deliver more correct decisions in the same 140 slots. Conversely, zero math errors with both options leaves no errors for any review policy to identify; that ceiling says little about error ranking.

### Confidence quality and the cost of thinking

For each valid binary verdict we squared the distance between its reported confidence and the outcome (1 if the judge agreed with the key, 0 otherwise), then averaged within condition. Lower Brier scores indicate better probability predictions. This measure reflects accuracy as well as confidence; a low value alone cannot establish useful ordering. The cutoff-tie comparison in Section 5 tests that separate question.

| Domain / prompt | Correct / valid | Brier | Output tokens | Time (s) |
| --- | --- | --- | --- | --- |
| GSM8K / plain | 100/140 | 0.284 | 16.7 | 0.25 |
| GSM8K / rubric | 103/140 | 0.264 | 17.7 | 0.25 |
| GSM8K / thinking | 139/140 | 0.008 | 294.1 | 0.91 |
| GSM8K / both | 140/140 | 0.002 | 365.6 | 0.96 |
| MEDQA / plain | 119/140 | 0.141 | 16.7 | 0.25 |
| MEDQA / rubric | 121/140 | 0.129 | 16.5 | 0.25 |
| MEDQA / thinking | 133/138 | 0.030 | 1255.1 | 2.78 |
| MEDQA / both | 132/136 | 0.023 | 1191.0 | 2.83 |

Token counts are mean completion tokens per attempted test call; time is median observed seconds per attempt. Each row covers the same 140 scheduled cases; Brier and accuracy use valid verdicts only. MedQA thinking increased average output from about 17 to 1,255 tokens and median time from 0.25 to 2.78 seconds. Better verdicts therefore came with longer responses and occasional truncation on this endpoint.

For intuition, a verdict reported at 0.95 contributes 0.0025 to the Brier loss if correct and 0.9025 if wrong. Confident mistakes therefore matter. But the score averages over all verdicts; it can improve merely because many more verdicts are correct. On the medical thinking-only run, the resource summary includes two truncated attempts even though the probability score excludes them. Keeping these denominators separate avoids crediting the model with a usable judgment it did not deliver or ignoring computation it actually consumed.

## 7 Which judgments benefit from a second pass?
We replayed a two-stage workflow on the same 140 test cases per domain. The first pass issues a verdict with thinking disabled. A case excluded by its frozen retention rule receives the independent thinking-enabled verdict on that same candidate. Both calls use the same rubric setting (C1 to C3 without a rubric, C2 to C4 with one). When the second output is incomplete, the workflow keeps the usable first verdict and charges the second call's tokens. Each case therefore has one final decision. No model saw its earlier judgment.

**Random assignment.** For a policy that switches k cases, every k-subset of the 140 is equally likely in the comparison. Each item contributes +1 if switching corrects a mistake, -1 if it introduces one, or 0 otherwise. We count subsets with each possible number of gains and losses to obtain the exact distribution of final correct counts. The mean and the 2.5th and 97.5th percentiles describe assignment variability on these fixed items. The twelve comparisons reuse cases and are descriptive. They do not quantify variation across new cohorts or model runs.

Table 3. Correct verdicts out of 140 after switching. The first column identifies the prompt pair and its target retention percentage. Random uses exactly the number switched in the second column. Brackets give its central 95% range.

| Pair / target | Switched | Correct | Random mean | 95% range |
| --- | --- | --- | --- | --- |
| Math 1/3 · 50% | 71 | 121 | 119.8 | 114–125 |
| Math 1/3 · 75% | 38 | 116 | 110.6 | 106–115 |
| Math 1/3 · 90% | 17 | 109 | 104.7 | 101–108 |
| Math 2/4 · 50% | 71 | 123 | 121.8 | 117–127 |
| Math 2/4 · 75% | 39 | 119 | 113.3 | 109–118 |
| Math 2/4 · 90% | 14 | 110 | 106.7 | 104–110 |
| Med. 1/3 · 50% | 76 | 130 | 127.7 | 123–132 |
| Med. 1/3 · 75% | 54 | 129 | 125.2 | 121–129 |
| Med. 1/3 · 90% | 18 | 122 | 121.1 | 118–124 |
| Med. 2/4 · 50% | 58 | 128 | 126.4 | 123–130 |
| Med. 2/4 · 75% | 35 | 125 | 124.2 | 121–128 |
| Med. 2/4 · 90% | 13 | 123 | 122.2 | 120–125 |

On the medical plain prompt at the 75% target, switching 54 cases corrected 12 decisions and introduced two errors. One incomplete second call kept its original verdict. The total rose from 119 to 129. Randomly switching 54 averaged 125.2 correct, with 129 at the upper endpoint. With the rubric at the same target, switching 35 cases corrected five and introduced one, raising 121 to 125 against a random mean of 124.2. Across all six medical comparisons, confidence exceeded the random mean but stayed within its central range.

On math, three observed totals exceeded the upper random endpoint by one verdict. Scores were heavily tied. At the 75% target, averaging over alternative selections at the identical boundary score changes the plain result from 116 to 111.25 (random 110.59), and the rubric result from 119 to 112.92 (random 113.31). On medicine the corresponding tie averages were 127.49 and 125.71 versus random means of 125.17 and 124.25. These finite-sample comparisons support a modest medical ranking signal and show how fixed tie choices can magnify a math result.

![Paired replay output cost and correct verdicts](paired-cost.png)

Figure 2. Each curve starts with thinking disabled and adds second calls at three workloads. Circles denote plain prompts and squares denote rubrics. Open markers give correct verdicts from standalone thinking across all 140 attempts, including missing outputs in the denominator. Token counts include both stages of the replay.

### Output tokens per grading method
Table 4. Plain prompt at 75% target retention. Each cell gives correct verdicts out of 140 and total output tokens. The random row gives same-count expectations rounded to one verdict decimal and the nearest token.

| Method | Math: correct / tokens | Medicine: correct / tokens |
| --- | --- | --- |
| First pass only | 100 / 2,342 | 119 / 2,334 |
| Confidence review | 116 / 14,799 | 129 / 95,815 |
| Random review | 110.6 / 13,519 | 125.2 / 70,111 |
| Thinking throughout | 139 / 41,177 | 133 / 175,719 |

The two-stage totals include the first verdict on all 140 cases and every selected second call, including truncated outputs. On medicine, selecting 54 cases by confidence yielded 3.8 more correct verdicts than random review on average and used 25,704 more output tokens (37%). Thinking throughout yielded another four correct verdicts and two incomplete outputs. On math, selecting 38 cases used 1,280 more tokens than random review on average. Much of the observed accuracy advantage depended on which equally confident cases were selected.

Across all six medical policies, confidence-selected review used 32% to 56% more tokens than expected for the same number of random reviews. On math the difference ranged from 2% fewer to 80% more. The separate abstention prompt used 2,757 tokens on math and 2,546 on medicine. The companion table reports all four standalone settings, abstention, and all twelve confidence/random comparisons. These totals measure generated output length on held-out cases.

## 8 Case analysis

We selected the smallest blinded ID per domain in each of three plain-prompt groups: maximum-confidence errors, flagged errors and flagged correct verdicts at the 75% target. In a 100-vote math problem, the correct remainder was 50 votes. The local model rejected 50 at full confidence; the tie rule sent it for review. The same rule flagged a correct verdict on a jury-pay problem (net hourly pay of 2). In MedQA a fully confident acceptance of a distractor was retained. A rejection of the keyed answer on an immune-signaling item was flagged at 0.95. All 54 flagged medical cases had that boundary score, including 41 correct verdicts. These are automated record checks against the official key; human review quality was not measured.

At the medical boundary the score was informative at the group level, not decisive for any particular case. All 54 referrals had the same reported confidence, 0.95. Only 13 of them were errors; the remaining 41 judgments agreed with the key. Among the 86 retained decisions, eight still disagreed. A budget owner therefore trades a higher concentration of errors in the review queue for two costs: time spent on sound decisions and wrong decisions that remain automated. The six examples illustrate those outcomes; their selection rule does not make them a representative survey of failure mechanisms.

## 9 Interpretation and limitations

A fixed review budget helped on this medical sample. On math, a queue of equally confident judgments offered little information about review priority. Validate the local score distribution before using a cutoff. The benchmarks differ in format, difficulty and distractor construction, labels are balanced by design, and training exposure is unknown. Results cover one served model and official exam keys. Performance on new questions, another judge or real clinical decisions remains untested. A numerical cutoff should be evaluated against a same-workload alternative in its intended setting. If most cases share the highest score, report both the fixed result and the result under alternate choices among ties. If valid accuracy improves, also report missing verdicts and time or token use. A favorable grading result does not establish downstream benefit: the benchmark scores against official exam keys, not patient outcomes, student appeals or human corrections. Direct abstention was evaluated with one prompt only, so its zero rate is not evidence that the model could never be induced to decline.

**Reproducibility.** The release includes de-identified verdict records, the locked inclusion flags, the 24 coverage comparisons, 12 paired replays with exact random ranges, and resource fields from 1,120 scheduled test calls. Offline replay reconstructs the estimates, case selection and report without querying the model. The instructor supplement contains source questions, constructed candidates and recorded final response text. Replay verifies the analysis of observed outputs; it does not establish that a fresh inference run would return identical verdicts. Codex assisted with implementation, analysis, record checks and drafting.

## References

[1] Yonatan Geifman and Ran El-Yaniv. 2017. Selective Classification for Deep Neural Networks. NeurIPS 30. https://arxiv.org/abs/1705.08500

[2] Saurav Kadavath et al. 2022. Language Models (Mostly) Know What They Know. arXiv:2207.05221. https://arxiv.org/abs/2207.05221

[3] Lianmin Zheng et al. 2023. Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. NeurIPS Datasets and Benchmarks. https://arxiv.org/abs/2306.05685

[4] Karl Cobbe et al. 2021. Training Verifiers to Solve Math Word Problems. arXiv:2110.14168. https://arxiv.org/abs/2110.14168

[5] Di Jin, Eileen Pan, Nassim Oufattole, Wei-Hung Weng, Hanyi Fang and Peter Szolovits. 2021. What Disease Does This Patient Have? A Large-Scale Open Domain Question Answering Dataset from Medical Exams. Applied Sciences 11(14), 6421. doi:10.3390/app11146421. https://doi.org/10.3390/app11146421
