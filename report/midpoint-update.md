# Can a Language-Model Judge Identify Its Own Grading Errors?
DSC 261 · Responsible Data Science · Midterm Update

Haoxiang Qiu, Yuguo Du, Edith Gu, Lucia Si, Wenkai Kang

University of California San Diego

## 1 The grading decision we want to check

Suppose a student gives the right numerical answer and an automated grader marks it wrong. The student's answer is correct, but the grading decision is an error. If a reviewer has time to check only a few decisions, can the grader's own confidence help them find mistakes like this one? We study that question on math word problems and medical examination questions. Both have answer keys, so we can count exactly how many mistakes a review queue contains before anyone attempts a correction.

We tested two ways of asking the grader where it needed help. In one run, it could explicitly decline to grade a candidate. In the other runs, it had to give a verdict and report its confidence. We then kept some of those verdicts and set the rest aside. A useful confidence score should put more mistakes into a queue of a given size than drawing the same number of cases at random. This comparison follows selective classification [1]. Prior work on models' stated probabilities [2] and on automated judging [3] motivates a narrower question here. Even a judge that grades most answers correctly may give its few wrong verdicts the highest possible score.

## 2 Questions, candidates and scoring

We first needed to know whether these benchmarks would yield enough grading errors to study. During development, the plain prompt disagreed with the key on 41 of 100 math candidates and 13 of 100 medical candidates. We kept both datasets. We sampled the formal questions from the official test pools and excluded development items by source identifier and normalized question text. The sampling seed was 2612026. This gives us fresh questions relative to our pilot. We have no way to check whether the judge encountered a benchmark during training.

Each formal question received one candidate answer, which stayed the same across prompts. For GSM8K [4], a correct candidate used the reference number and a wrong candidate used a deterministic numerical change. For US MedQA [5], a correct candidate used the keyed option and a wrong one used a distractor already present in the question. A local large language model saw the question, the candidate and, for MedQA, the options. We kept the key for scoring. A rejection of a wrong candidate and an acceptance of a correct candidate each earned one correct judgment.

Table 1. The two splits serve different purposes. Within every cell, half the candidates were correct and half were wrong.

| Dataset | Set the rule | Test the rule | Total |
| --- | --- | --- | --- |
| GSM8K | 60 | 140 | 200 |
| US MedQA | 60 | 140 | 200 |

## 3 Four ways to grade the same answer

We started with a short prompt asking for a verdict and a number from 0 to 1. The number referred to the judge's confidence in its own verdict. A judge could reject a candidate with confidence 1.0. We varied two choices independently. The rubric asked it to solve the problem, check units and constraints, and compare the result with the candidate. The thinking setting controlled whether the model could use a reasoning phase before returning its verdict. This gave us four conditions: plain, rubric only, thinking only, and thinking with the rubric.

The 400 questions yielded 1,600 scheduled judgments across those conditions. We obtained 1,586 usable responses. The other 14 reached the output limit on MedQA with thinking enabled. We recorded them as incomplete. Counting an interrupted response as a voluntary decision to abstain would mix a limit on generation with the behavior we wanted to measure.

---

## 4 Could the judge choose cases for review?

Our initial experiment required a verdict. Drawing on the team's judging framework [6], we added a separate prompt that also accepted “Abstain.” We used the plain prompt with thinking disabled and gave it the same 280 held-out candidates. It graded every one. Against the official keys, it made 41 math errors and 22 medical errors. Of the 63 mistakes, 48 accepted a wrong candidate and 15 rejected a correct one. All 63 would have passed through a system that waited for the judge to ask for help.

This left us with zero referrals from the voluntary prompt. Matching every other method to that workload would simply keep all 140 cases in each domain. We therefore evaluated the confidence scores from the four required-verdict runs at three prespecified retention targets. The voluntary prompt has its own result in the text. The figure compares the two methods that actually selected subsets.

## 5 What confidence buys at a fixed workload

For each domain and grading condition, we used the 60 calibration cases to set a rule targeting 50%, 75% or 90% retention. We froze both the score cutoff and the rule for cases tied at that cutoff. On the 140 test questions, the number kept could differ from the target. Coverage is the number kept divided by 140. Retained error rate is the number of grading mistakes among the kept cases divided by the number kept. For each comparison, random selection keeps exactly the same number from the same pool of valid verdicts. Its average retained error rate equals the error rate in that pool.

Table 2. Plain-prompt test results. Each entry gives the number of mistakes divided by the number of verdicts kept. Each domain started with 140 verdicts.

| Target | GSM8K | US MedQA |
| --- | --- | --- |
| 50% | 19/69 (27.54%) | 6/64 (9.38%) |
| 75% | 24/102 (23.53%) | 8/86 (9.30%) |
| 90% | 31/123 (25.20%) | 16/122 (13.11%) |

![Retained error against actual coverage for math and medicine](risk-coverage.png)

Figure 1. Plain prompt, thinking off. The horizontal axis shows the share of test cases actually kept. The labels identify the targets used on calibration data. The dashed line is the expected error rate if we keep the same number at random.

### Following 54 medical referrals

The plain medical judge made 21 mistakes in 140 verdicts. At the 75% target, the rule kept 86 verdicts and marked the other 54 for review. The 86 kept cases contained eight mistakes. The queue therefore contained 13 mistakes and 41 sound verdicts. Choosing 54 cases at random would find 54 × 21/140 = 8.1 mistakes on average. With the same number of places, the confidence rule found about five more. We can count those mistakes from the key. How many a reviewer would actually correct is a separate question.

The retained error rate was 9.30%, compared with 15.00% under random selection. The estimated difference was −5.70 percentage points, with a 95% paired bootstrap interval from −11.10 to −1.02 points for the frozen policy. Raising the target to 90% reduced the queue to 18 cases and left 16 mistakes among the 122 kept. The choice of target changes both how many decisions someone must examine and how many wrong decisions get through.

---

## 6 Why the math result needs a closer look

At the 75% target, the plain math run appears to tell a similar story. It kept 102 of 140 verdicts, with 24 mistakes among them (23.53%), below the 28.57% random baseline. But when we inspected the scores, 136 of the 140 verdicts had exactly the same confidence, 1.0. Those 136 included 38 mistakes. The rule had to choose 102 cases from that tied group. Their confidence scores provided no ordering within the group.

We kept the same workload and averaged over equally likely ways to choose 102 of the 136 ties. That gives 102 × 38/136 = 28.5 retained mistakes on average, or 27.94%. Most of the apparent five-point gain came from which equally confident cases the frozen rule happened to keep. Applying the same check to the plain medical run gave 10.96% retained error, still below 15.00% at random. The medical scores carried some information about where mistakes were concentrated, even though they often gave several cases the same priority.

The rubric-only results offer a second check. On math, the observed retained error was 20.79%. Averaging across choices within the cutoff tie raised it to 26.81%, alongside a random expectation of 26.43%. On medicine the corresponding figures were 11.43%, 11.04% and 13.57%. The same caution about tied math scores applies under either prompt.

## 7 What changed with the grading prompt?

Table 3. Grading errors at the 75% target. “All” counts every valid test verdict. “Kept” counts only the verdicts retained by the confidence rule. The two columns for each domain refer to the same 140 scheduled questions.

| Prompt | Math all | Math kept | Med. all | Med. kept |
| --- | --- | --- | --- | --- |
| Plain | 40/140 | 24/102 | 21/140 | 8/86 |
| Rubric | 37/140 | 21/101 | 19/140 | 12/105 |
| Thinking | 1/140 | 1/92 | 5/138 | 0/107 |
| Both | 0/140 | 0/90 | 4/136 | 0/113 |

Adding the rubric to the plain prompt reduced total mistakes slightly in both domains. Enabling thinking changed the verdicts much more. In math, the thinking-only run made just one mistake, and the retention rule kept it. The run with both settings made none. With so few mistakes, high grading accuracy gives us little evidence about whether the judge can identify its own failures.

In medicine, the thinking-only run returned 138 valid verdicts. All five errors scored below the retention cutoff. The run with both settings returned 136 valid verdicts and placed all four errors below its cutoff. We observed zero errors among the 107 and 113 retained judgments, respectively. The corresponding 95% Wilson upper limits are 3.47% and 3.29%. The denominators in Table 3 show a second cost. Six of the 280 scheduled medical test responses across these two settings were incomplete. A system using either prompt would still need a policy for a case that reaches the output limit before a verdict arrives.

## 8 What remains for the final study

By midpoint we had completed the pilot, the four grading conditions, the voluntary-abstention run and all 24 comparisons of confidence with random selection. The two benchmarks differ in answer format, the kinds of wrong answers we constructed, and difficulty. We cannot attribute the contrast to subject matter alone. We also deliberately balanced correct and wrong candidates. A classroom or clinical review queue could have a different mix. Our medical results concern agreement with examination keys.

The next question follows directly from the 54 medical referrals. If we use the thinking-enabled verdict for just those cases, how many first-pass errors does it correct, and how many sound decisions does it overturn? We can answer by matching the saved verdicts question by question and comparing with random referral of the same size. We can also count the output tokens spent on both passes. This would show what the proposed second look buys beyond putting more mistakes in the queue.

The project archive includes the case counts, selection rules and recorded verdicts used in these calculations. Codex assisted with implementation, analysis and drafting.

## References

[1] Yonatan Geifman and Ran El-Yaniv. 2017. Selective Classification for Deep Neural Networks. NeurIPS 30. https://arxiv.org/abs/1705.08500

[2] Saurav Kadavath et al. 2022. Language Models (Mostly) Know What They Know. arXiv:2207.05221. https://arxiv.org/abs/2207.05221

[3] Lianmin Zheng et al. 2023. Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena. NeurIPS Datasets and Benchmarks. https://arxiv.org/abs/2306.05685

[4] Karl Cobbe et al. 2021. Training Verifiers to Solve Math Word Problems. arXiv:2110.14168. https://arxiv.org/abs/2110.14168

[5] Di Jin, Eileen Pan, Nassim Oufattole, Wei-Hung Weng, Hanyi Fang and Peter Szolovits. 2021. What Disease Does This Patient Have? A Large-Scale Open Domain Question Answering Dataset from Medical Exams. Applied Sciences 11(14), 6421. doi:10.3390/app11146421. https://doi.org/10.3390/app11146421

[6] EdithGu. DSC261 judging pipeline skeleton, project collaboration, commit c9f40de. https://github.com/EdithGu/dsc261-llm-judge/tree/c9f40de92fa61309b0cd733dabcfafd9fa5363f2
