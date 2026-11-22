# Can a Language-Model Judge Identify Its Own Grading Errors?
DSC 261 · Responsible Data Science · Midterm Update

Haoxiang Qiu, Yuguo Du, Edith Gu, Lucia Si, Wenkai Kang

University of California San Diego

## 1 Can a grader find its own mistakes?

An automated grader can reject a correct answer or accept a wrong one. We ask whether it can identify judgments that need a second look. We first let it choose to abstain, then test whether its stated confidence locates more errors than random selection at the same review workload. The target is the correctness of the grading decision, not whether the candidate answer is correct.

We apply selective classification [1], stated confidence [2] and LLM judging [3] to controlled math and medical cases, checking whether benefits survive alternative choices among identical confidence scores.

![Midpoint study workflow](workflow-midterm.png)
Figure 1. Midpoint scope: construct fixed cases, collect judgments, and test error selection. Selecting a case does not yet correct its judgment.

## 2 Questions, candidates and scoring

Pilot runs found 41 math and 13 medical grading errors per 100 candidates, so we kept both datasets. Formal sampling used seed 2612026 and the official test pools, excluding development items by source ID and normalized question text. This prevents reuse of our pilot questions, not possible exposure during model training.

Each formal question received one candidate answer, which stayed the same across prompts. For GSM8K [4], a correct candidate used the reference integer; wrong candidates used a fixed, seeded choice among adding one, subtracting one, doubling or halving, restricted to a different integer with the same sign. US MedQA [5] used the native five-option English questions: a correct candidate was the keyed option and a wrong one an existing distractor. We excluded unusable answer formats, missing-image references and conflicting duplicates before sampling. No model generated candidates. The judge saw the question, candidate and original medical options. We kept the key for scoring. A rejection of a wrong candidate and an acceptance of a correct candidate each earned one correct judgment.

Table 1. The two splits serve different purposes. Within each split, half the candidates were correct and half were wrong; every question had one fixed candidate.

| Dataset | Set the rule | Test the rule | Total |
| --- | --- | --- | --- |
| GSM8K | 60 | 140 | 200 |
| US MedQA | 60 | 140 | 200 |

## 3 Model and four controlled conditions

All reported judgments used one locally hosted model served as qwen3.8-27b. The archived formal configuration and interface audit agree on that identifier. We have not independently verified its upstream weight revision. Formal calls used temperature 0, an 8,192-token output limit, concurrency one and no retries. A new run need not produce identical outputs.

Table 2. One model, four configurations. The rubric asked the judge to solve independently, check units and constraints, then compare its answer with the candidate.

| Condition | Thinking | Rubric |
| --- | --- | --- |
| C1: plain | Off | No |
| C2: rubric | Off | Yes |
| C3: thinking | On | No |
| C4: both | On | Yes |

The interface setting enable_thinking controlled the reasoning mode. Each response returned a binary verdict and confidence from 0 to 1 in that verdict. Rejecting a candidate with confidence 1.0 therefore means certainty in the rejection. Of 1,600 scheduled calls on 400 candidates, 1,586 were usable. The remaining 14 reached the output limit on MedQA with thinking enabled; they are incomplete calls, not voluntary abstentions. Exact prompts and model provenance accompany the release.

---

## 4 Could the judge choose cases for review?

Our initial experiment required a verdict. For the same 280 held-out candidates, we added “Abstain” as a third possible response to the plain prompt and kept thinking disabled. It graded every one. Against the official keys, it made 41 math errors and 22 medical errors. Of the 63 mistakes, 48 accepted a wrong candidate and 15 rejected a correct one. All 63 would have passed through a system that waited for the judge to ask for help.

This left us with zero referrals from the voluntary prompt. Matching every other method to that workload would simply keep all 140 cases in each domain. We therefore evaluated the confidence scores from the four required-verdict runs at three prespecified retention targets. The voluntary prompt has its own result in the text. The figure compares the two methods that actually selected subsets.

## 5 What confidence buys at a fixed workload

For each domain and grading condition, we used the 60 calibration cases to set a rule targeting 50%, 75% or 90% retention. We froze both the score cutoff and a tie rule based on a seeded hash of the case ID, without using correctness labels. Here calibration sets a selection rule; it does not recalibrate the probabilities. On the 140 test questions, the number kept could differ from the target. Coverage is the number kept divided by 140. Retained error rate is the number of grading mistakes among the kept cases divided by the number kept. For each comparison, random selection keeps exactly the same number from the same pool of valid verdicts. Its average retained error rate equals the error rate in that pool.

Table 3. Plain-prompt test results. Each entry gives the number of mistakes divided by the number of verdicts kept. Each domain started with 140 verdicts.

| Target | GSM8K | US MedQA |
| --- | --- | --- |
| 50% | 19/69 (27.54%) | 6/64 (9.38%) |
| 75% | 24/102 (23.53%) | 8/86 (9.30%) |
| 90% | 31/123 (25.20%) | 16/122 (13.11%) |

![Retained error against actual coverage for math and medicine](risk-coverage.png)

Figure 2. Plain prompt, thinking off. The horizontal axis shows the share of test cases actually kept. The labels identify the targets used on calibration data. The dashed line is the expected error rate if we keep the same number at random.

### Following 54 medical referrals

The plain medical judge made 21 mistakes in 140 verdicts. At the 75% target, the rule kept 86 verdicts and marked the other 54 for review. The 86 kept cases contained eight mistakes. The queue therefore contained 13 mistakes and 41 sound verdicts. Choosing 54 cases at random would find 54 × 21/140 = 8.1 mistakes on average. With the same number of places, the confidence rule found about five more. We can count those mistakes from the key. How many a reviewer would actually correct is a separate question.

The retained error rate was 9.30%, compared with 15.00% under random selection. The estimated difference was −5.70 percentage points, with a 95% paired bootstrap interval from −11.10 to −1.02 points. We resampled questions 1,000 times within candidate-label groups while keeping the calibrated rule fixed; this does not include uncertainty from fitting a new rule. Raising the target to 90% reduced the queue to 18 cases and left 16 mistakes among the 122 kept. The choice of target changes both how many decisions someone must examine and how many wrong decisions get through.

---

## 6 Why the math result needs a closer look

At the 75% target, the plain math run appears to tell a similar story. It kept 102 of 140 verdicts, with 24 mistakes among them (23.53%), below the 28.57% random baseline. But when we inspected the scores, 136 of the 140 verdicts had exactly the same confidence, 1.0. Those 136 included 38 mistakes. The rule had to choose 102 cases from that tied group. Their confidence scores provided no ordering within the group.

We kept the same workload and averaged over equally likely ways to choose 102 of the 136 ties. That gives 102 × 38/136 = 28.5 retained mistakes on average, or 27.94%. Most of the apparent five-point gain came from which equally confident cases the frozen rule happened to keep. Applying the same check to the plain medical run gave 10.96% retained error, still below 15.00% at random. The medical scores carried some information about where mistakes were concentrated, even though they often gave several cases the same priority.

The rubric-only results offer a second check. On math, the observed retained error was 20.79%. Averaging across choices within the cutoff tie raised it to 26.81%, alongside a random expectation of 26.43%. On medicine the corresponding figures were 11.43%, 11.04% and 13.57%. The same caution about tied math scores applies under either prompt.

## 7 What changed with the grading prompt?

Table 4. Grading errors at the 75% target. “All” counts every valid test verdict. “Kept” counts only the verdicts retained by the confidence rule. The two columns for each domain refer to the same 140 scheduled questions.

| Prompt | Math all | Math kept | Med. all | Med. kept |
| --- | --- | --- | --- | --- |
| Plain | 40/140 | 24/102 | 21/140 | 8/86 |
| Rubric | 37/140 | 21/101 | 19/140 | 12/105 |
| Thinking | 1/140 | 1/92 | 5/138 | 0/107 |
| Both | 0/140 | 0/90 | 4/136 | 0/113 |

Adding the rubric to the plain prompt reduced total mistakes slightly in both domains. Enabling thinking changed the verdicts much more. In math, the thinking-only run made just one mistake, and the retention rule kept it. The run with both settings made none. With so few mistakes, high grading accuracy gives us little evidence about whether the judge can identify its own failures.

In medicine, the thinking-only run returned 138 valid verdicts. All five errors scored below the retention cutoff. The run with both settings returned 136 valid verdicts and placed all four errors below its cutoff. We observed zero errors among the 107 and 113 retained judgments, respectively. The corresponding 95% Wilson upper limits are 3.47% and 3.29%. The denominators in Table 4 show a second cost. Six of the 280 scheduled medical test responses across these two settings were incomplete. A system using either prompt would still need a policy for a case that reaches the output limit before a verdict arrives.

## 8 Midpoint findings and next steps

Completed work comprises the pilot, four grading conditions, voluntary abstention and all 24 confidence/random comparisons. The medical scores concentrated some errors into a smaller queue. Math scores were almost all identical, so favorable fixed selections did not establish useful ranking. Thinking improved grading substantially but left few errors with which to evaluate failure detection.

The benchmarks differ in format, constructed error types and difficulty; the contrast cannot be attributed to subject matter alone. The balanced, controlled candidates are not a representative sample of student or model-generated mistakes. Training exposure is unknown, and medical correctness means agreement with examination keys, not clinical validation.

The final study will ask what happens after referral: using each flagged case's saved thinking-enabled verdict, how many errors are corrected and how many new errors introduced? We will compare equal-size random referrals and count both stages' output tokens. This is an offline reconstruction using independent judgments, not a model reading and revising its own earlier answer.

The archive supplies source/candidate construction, frozen rules and saved judgments. It supports offline analysis without the model; a fresh model run is a separate reproduction step. Codex assisted with implementation, analysis and drafting.

## References

[1] Yonatan Geifman and Ran El-Yaniv. 2017. Selective Classification for Deep Neural Networks. NeurIPS 30. https://arxiv.org/abs/1705.08500

[2] Saurav Kadavath et al. 2022. Language Models (Mostly) Know What They Know. arXiv:2207.05221. https://arxiv.org/abs/2207.05221

[3] Lianmin Zheng et al. 2023. Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. NeurIPS Datasets and Benchmarks. https://arxiv.org/abs/2306.05685

[4] Karl Cobbe et al. 2021. Training Verifiers to Solve Math Word Problems. arXiv:2110.14168. https://arxiv.org/abs/2110.14168

[5] Di Jin, Eileen Pan, Nassim Oufattole, Wei-Hung Weng, Hanyi Fang and Peter Szolovits. 2021. What Disease Does This Patient Have? A Large-Scale Open Domain Question Answering Dataset from Medical Exams. Applied Sciences 11(14), 6421. doi:10.3390/app11146421. https://doi.org/10.3390/app11146421
