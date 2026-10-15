# Night 4 — 2026-10-15 into 2026-10-16

Executes the "new, and cheap" section of
[night 3's revised plan](overnight-2026-10-14.md): ship the consensus-ranking
result, then measure the one thing whose absence limits every comparison in
this repository — single-run training variance.

```
stage 0  consensus ranking shipped, dumps re-scored      18:26 -> 18:35
stage 1  decode sweep on small_1m (disjoint tuning set)  18:35 -> 19:23
stage 2  variance seed 1, 8,508 steps                    19:23 -> 22:25
stage 3  variance seed 2, 8,508 steps                    22:25 -> 01:21
stage 4  variance seed 3, 8,508 steps                    01:21 -> 04:22
stage 5  score all three on the common protocol          04:22 -> 04:51
stage 6  verify the swept decode setting                 04:51 -> 05:08
stage 7  re-run stage 6 with dumps, for a paired test    05:19 -> 05:36
stage 8  re-measure the T=1.0 default, matched code      05:36 -> 05:53
stage 9  is colder than 0.7 better? (tuning set)         05:53 -> 06:05
stage 10 verify T=0.6 on the common protocol             06:05 -> 06:38
```

Every stage completed, the driver finishing with 161 minutes of its window
unused; stages 7 to 9 and four free analyses of the dumps (5b to 5d) were added
in that time.

The headline is the **error bar**. Three runs identical but for `train.seed`
differ by up to 1.43 points of `rec@20` against a paired standard error of 0.8
points, so no gap below about 1.6 points between two training runs in this
repository has ever meant anything. That retires night 3's count-fingerprint
question as a genuine null (p = 0.32) and leaves every other claim the project
has made standing, the narrowest at four standard errors.

Two more results came out of the same three runs. The seeds **agree on 80% of
the evaluation set while proposing almost disjoint molecules** — Jaccard 0.098 —
so the remaining misses are a property of the molecules, which is night 3's
capability ceiling confirmed along an independent path. And **pooling votes across
several samplings of one model reaches `rec@20` 0.9279**, the best this project
has recorded, from no training at all.

The decode question that stage 1 left open also closed, in the direction stage 1
doubted: sampling at **T=0.6 instead of 1.0 is worth +1.99 points** on the common
protocol (p = 1.3e-05), and **all of it is on molecules of 35 heavy atoms or
more** (+7.52 points there, +0.75 below). The first thing in this project to
move the band where the ceiling lives turned out to be a decoder setting.

---

## Stage 0 — consensus ranking, shipped and generalised

Night 3 found that ordering a query's candidates by how many distinct SMILES
spellings the model gave each molecule lifts `small_1m`'s `rec@1` from 0.5302 to
0.7520. That was one model, measured by an analysis script. Two things were
needed before it could be believed or used: it had to hold for more than one
checkpoint, and it had to live in the library rather than in `scripts/`.

### It holds everywhere

`scripts/rerank_dumps.py` re-reads the candidate dumps from night 3 and
re-scores them under both orderings. Nothing is re-sampled; the candidate sets
are exactly those of the common protocol, and only the order changes.

| run | rec@20 | rec@1 generation | rec@1 consensus | Δ | struct@1 gen | struct@1 con | rec@20 consensus |
|---|---|---|---|---|---|---|---|
| `small_100k_3ep` | 0.0603 | 0.0046 | 0.0235 | +1.89 | 0.0041 | 0.0220 | 0.0608 |
| `medium_1m` | 0.2822 | 0.0527 | 0.1600 | +10.74 | 0.0506 | 0.1564 | 0.2832 |
| `count_fp_100k` | 0.5890 | 0.1687 | 0.3727 | +20.40 | 0.1651 | 0.3661 | 0.5920 |
| `small_100k` | 0.5982 | 0.1800 | 0.3793 | +19.94 | 0.1748 | 0.3681 | 0.5992 |
| `small_1m_matched` | 0.6324 | 0.2091 | 0.4407 | +23.16 | 0.2025 | 0.4310 | 0.6401 |
| `small_full` | 0.7403 | 0.3113 | 0.5700 | +25.87 | 0.3001 | 0.5573 | 0.7444 |
| `small_100k_long` | 0.8446 | 0.4519 | 0.6764 | +22.44 | 0.4284 | 0.6529 | 0.8476 |
| `small_1m` | 0.8947 | 0.5302 | 0.7526 | +22.24 | 0.5087 | 0.7249 | 0.8962 |

**Every competent model gains between +10.7 and +25.9 points of `rec@1`**, and
the one model that barely gains — `small_100k_3ep`, at +1.9 — is the
pre-competent one from night 3, which has no confidence to express. This is a
property of the task, not of a checkpoint: a model samples its best answer by
several routes, and generation order throws that signal away.

The gain does not grow monotonically with model quality, which is worth noting
because it would have been the tidier story. It rises from `medium_1m`'s +10.7
to a plateau around +20 to +26 and then flattens; `small_1m`, the strongest
model, gains slightly *less* than `small_full` and `small_1m_matched`. Consensus
ranking is most valuable in the middle of the quality range, where the model
knows the answer but does not put it first.

### `rec@20` moves too, and legitimately

Consensus ordering also lifts `rec@20` by +0.05 to +0.77 points. That needs
justifying, because `rec@20` was supposed to be insensitive to order.

It is sensitive because the top-up fix from night 3 draws **more than 20**
distinct candidates for most queries — 18.9 on average for `small_1m`, up to the
cap. Ranking therefore decides *which* 20 go to the oracle. That is legitimate
under this project's own definition of the budget: the k budget is oracle
queries, and spelling counts are free — they are already in the samples and need
no forward pass. A real system would spend its 20 oracle calls on its 20
most-confident candidates, which is exactly what consensus ordering does. It
recovers part of night 3's `beyond_budget` bucket (18 queries where a correct
candidate was drawn but ranked outside the window).

### What shipped

- `QueryOutcome.spelling_counts()` and `QueryOutcome.scored_by_consensus()`.
- `recovery_at_k` and `structure_accuracy_at_k` take an `order` argument.
- Every report now carries `recovery_at_k_consensus` and
  `structure_accuracy_at_k_consensus` **beside** the generation-order fields,
  which keep their meaning, so numbers measured before this change stay
  comparable with numbers measured after. `primary_metric` is untouched.
- `Morg2Smiles.generate` sorts by `(fp_match, votes, tanimoto)`. `fp_match`
  stays on top — an exact hit is the answer, and the oracle is free to a caller
  who holds the query fingerprint — with consensus as the tiebreak inside each
  group where the oracle cannot discriminate.
- Nine tests, including that the two orderings agree once k covers the budget,
  that ties do not reshuffle generation order, and that the headline metric is
  unchanged.

---

## Stage 1 — decode sweep: no setting beats the default, and that is the finding

Every number in this project was measured at temperature 1.0, top_p 1.0, and
nothing had ever checked whether that was the right place to sample from.
`small_1m` fills only 64% of its 20-slot budget because it re-proposes the same
molecules, which is what a too-cold decoder looks like — so a hotter one might
buy recovery, or might spend validity for nothing.

15 settings, 400 molecules (386 fingerprint-unseen) drawn from the clean pool
**excluding the 2,000 of the common protocol**, so a winner could afterwards be
checked on a set it had not been fitted to. 18:35 → 19:23.

| T | top_p | rec@1 | con@1 | rec@20 | con@20 | validity | uniq/q | fill |
|---|---|---|---|---|---|---|---|---|
| 0.70 | 1.00 | 0.5674 | 0.7876 | **0.9145** | **0.9145** | 0.952 | 16.5 | 0.539 |
| 0.70 | 0.95 | 0.5984 | 0.7746 | 0.9041 | 0.9067 | 0.954 | 15.4 | 0.472 |
| 0.70 | 0.90 | 0.5829 | 0.7772 | 0.9067 | 0.9093 | 0.958 | 14.5 | 0.446 |
| 0.80 | 1.00 | 0.5337 | 0.7461 | 0.8912 | 0.8912 | 0.943 | 17.3 | 0.575 |
| 0.90 | 1.00 | 0.5466 | 0.7565 | 0.8990 | 0.9016 | 0.938 | 18.5 | 0.635 |
| **1.00** | **1.00** | 0.5026 | 0.7565 | 0.8938 | 0.8990 | 0.925 | 19.3 | 0.671 |
| 1.00 | 0.90 | 0.5674 | 0.7850 | 0.9093 | 0.9093 | 0.948 | 16.4 | 0.536 |
| 1.10 | 1.00 | 0.4508 | 0.7565 | 0.8808 | 0.8782 | 0.910 | 20.4 | 0.728 |

(Full grid in `results/overnight4/decode_sweep.json`.)

The nominal best is T=0.7, top_p=1.0, at +1.55 points of consensus `rec@20` over
the default. **That is not a result, and the arithmetic says so.** At n=386 and
p≈0.9 the standard error of a single cell is **1.53 points**. The winner's margin
is one standard error. Worse, it is the maximum of 15 correlated cells, and the
expected maximum of 15 draws sits well above the true mean even when every cell
is identical — the classic selection bias. A +1.55 point win selected this way
is exactly what no effect looks like.

Averaging the three top_p values at each temperature, which is the only read the
sample size supports:

| temperature | mean con@20 |
|---|---|
| 0.7 | 0.9102 |
| 0.8 | 0.8972 |
| 0.9 | 0.8998 |
| 1.0 | 0.9016 |
| 1.1 | 0.8912 |

A 1.9-point spread across the whole temperature range, non-monotone in the
middle. There is no decode setting worth adopting on this evidence. Stage 6
checks T=0.7 on the common protocol, where n=1,956 and the standard error falls
to 0.68 points, which is the only way to settle it.

### Two things the sweep does establish

**Consensus ranking absorbs the decoder's temperature sensitivity.** This is a
paired comparison on identical molecules, and the effect is large enough to
survive the sample size:

| ordering | rec@1 range across the grid | sd |
|---|---|---|
| generation | 0.4508 – 0.5984 (**14.8 points**) | 3.73 |
| consensus | 0.7461 – 0.7876 (**4.1 points**) | 1.30 |

Temperature strongly determines which candidate the model emits *first* —
15 points of `rec@1` between the coldest and hottest settings — and consensus
ranking removes nearly three-quarters of that. Tuning the decoder was mostly a
way of getting the ordering right by accident; ordering it directly is better and
cheaper. This also means the choice of temperature matters much less than it
appears to, which is a convenient robustness property for the weekend runs.

**Budget under-fill costs nothing, confirming night 3 from a second direction.**
Temperature trades diversity against per-candidate correctness exactly as
expected — validity 0.952 → 0.910 and distinct candidates 16.5 → 20.4 from T=0.7
to T=1.1 — and `rec@20` does not improve at the diverse end. At T=0.7 the model
fills barely half its budget and recovers as well as or better than at T=1.1
where it fills three-quarters. Night 3 found under-fill concentrated on queries
the model had already solved; this says the same thing from the other side.
**Diversity is not the binding constraint. Per-candidate correctness is.**


---

## Stages 2–5 — the error bar this project never had

Every comparison in this repository, across four nights, has been a difference
between two numbers each measured once. Three retractions have already come out
of that, all of them cases where two things varied at once. But even a clean
comparison needs to clear the noise, and nobody here had ever measured the
noise. This was the night to do it.

Three runs, identical in every respect but `train.seed` (1, 2, 3): 8,508 steps
on the 100k shard, `patience: 0` so the schedule could not end early, scored on
the common protocol. Just under three hours each, 19:23 to 04:22.

8,508 steps was chosen because `small_100k`, `small_full` and `small_1m_matched`
all share it. The sd measured here therefore applies directly to the
fixed-compute data axis, which is where night 2's retracted scaling fit lived
and where the smallest surviving claim in the project sits.

| seed | rec@1 | rec@5 | rec@20 | con@1 | con@20 | validity |
|---|---|---|---|---|---|---|
| 1 | 0.1897 | 0.4243 | 0.6053 | 0.4059 | 0.6115 | 0.800 |
| 2 | 0.1922 | 0.4387 | 0.6084 | 0.4121 | 0.6130 | 0.800 |
| 3 | 0.1805 | 0.4228 | 0.5941 | 0.3978 | 0.6022 | 0.791 |
| **mean** | 0.1875 | 0.4286 | **0.6026** | 0.4052 | **0.6089** | 0.797 |
| **sd (points)** | 0.62 | 0.87 | **0.75** | 0.72 | **0.58** | 0.52 |
| range (points) | 1.18 | 1.58 | 1.43 | 1.43 | 1.07 | 0.92 |

**The headline number is an sd of 0.75 points of `rec@20`**, and a spread of
1.43 points between the luckiest and unluckiest of three seeds that differ in
nothing but their random initialisation and shuffling order.

Two independent checks agree with it. The training-time validation metric on
each run's own split — a different measurement on different molecules — has an
sd of 0.42 points (0.6121, 0.6126, 0.6051). And consensus ordering, which
night 3 showed absorbs decoder noise, also shrinks seed noise: 0.58 points
against 0.75.

### The right error bar is the paired one

A detail that matters more than the sd itself. Every run in the common protocol
is scored on the *same* 1,956 molecules, so comparing two runs is a paired
comparison, and the binomial error on 1,956 queries — 1.11 points at p=0.60, the
figure that looks like the obvious uncertainty — is the wrong one. It describes
the error of a *single* rate against the population of all molecules, not the
error of a *difference* measured twice on one fixed set, where everything the
two runs agree about cancels.

What does not cancel is disagreement, and the seeds disagree on 12.7% to 14.1%
of queries. McNemar's standard error, `sqrt(discordant)/n`:

| pair | difference | discordant | paired SE |
|---|---|---|---|
| s1 − s2 | −0.31 pts | 248 (12.7%) | 0.81 pts |
| s1 − s3 | +1.12 pts | 254 (13.0%) | 0.81 pts |
| s2 − s3 | +1.43 pts | 276 (14.1%) | 0.85 pts |

These three differences have a true value of exactly zero, and one of them is
+1.43 points — 1.7 paired standard errors. That is the whole lesson in one
number.

**The operating rule, for every future comparison in this project: a gap in
`rec@20` between two training runs below about 1.6 points (two paired standard
errors) is not evidence of anything.** Below 2.4 points it is weak. The sd from
three seeds and the McNemar error bar from 1,956 queries agree to within the
precision three seeds can offer — which is poor, since an sd on two degrees of
freedom is itself uncertain by roughly half its own size, so the McNemar figure,
computed from 1,956 paired observations, is the one to quote.

### Four fifths of the evaluation set has nothing to say about the model

The dumps answer something the summary table cannot: do the seeds fail on the
same molecules?

| seeds solving the query | observed | if seeds were independent | median heavy atoms |
|---|---|---|---|
| 0 of 3 | **585** | 123 | 34 |
| 1 of 3 | 188 | 558 | 29 |
| 2 of 3 | 201 | 847 | 28 |
| 3 of 3 | **982** | 428 | 24 |

If each seed solved each query with independent probability 0.6026, 28% of
queries would be unanimous. **80.1% are.** 982 queries are recovered by every
seed and 585 by none; only 389 — 19.9% — are decided by which seed you trained.
Across those 389 contested queries the seeds succeed 50.6% of the time, which is
to say that on the contested fifth a run is a coin flip, and `rec@20` decomposes
into 50.2 points that are free and 10.1 points of luck.

The median-size column is the same finding night 3 reached from the failure
taxonomy, arrived at along a completely independent path: 24 heavy atoms for the
molecules every seed gets, rising monotonically to 34 for the molecules no seed
gets. Night 3 inferred a capability ceiling concentrated on large molecules from
one model's misses, where the obvious objection was that one model's bad luck
had been promoted to a law. Three seeds agreeing on which molecules are
impossible removes that objection. **The ceiling is in the molecules, and
training more seeds will not move it.**

## Stage 5b — every past claim, re-tested against that error bar

The error bar is only worth measuring if it is then applied. Every run in the
common protocol was dumped, so `scripts/paired_tests.py` computes McNemar's
exact test for all 28 pairs. The p-value asks whether a gap could be sampling
noise on these molecules; the last column asks the separate question of whether
it could be seed luck. A claim has to clear both.

| comparison | gap (rec@20) | paired SE | × SE | McNemar p | × seed sd |
|---|---|---|---|---|---|
| `count_fp_100k` → `small_100k` | +0.92 | 0.87 | +1.1 | **0.320** | +0.9 |
| `small_100k` → `small_1m_matched` | +3.43 | 0.83 | +4.1 | 4.6e-05 | +3.2 |
| `small_100k_long` → `small_1m` | +5.01 | 0.66 | +7.6 | 7.8e-15 | +4.7 |
| `small_1m_matched` → `small_full` | +10.79 | 0.92 | +11.7 | 7.4e-34 | +10.2 |
| `small_100k` → `small_100k_long` | +24.64 | 1.14 | +21.6 | 2.2e-133 | +23.2 |
| `small_100k` → `small_1m` | +29.65 | 1.24 | +24.0 | 2.7e-169 | +28.0 |

(All 28 pairs in `results/overnight4/paired_tests.json`, and under consensus
ordering in `paired_tests_consensus.json`.)

**Night 3's count-fingerprint result is now a real null.** Count fingerprints
scored 0.92 points below binary at 100k, which night 3 reported as "no large
gain" rather than "worse" on the grounds that the variance was unmeasured. The
variance is now measured, the gap is 1.1 paired standard errors, and McNemar
gives **p = 0.32** — under consensus ordering, +0.72 points and p = 0.45. The
caution was correct and is now quantified: on this protocol, at this scale,
count fingerprints and binary fingerprints are indistinguishable. Cancelling the
8-hour comparable-scale count run was the right call.

**Everything else the project has claimed survives, and nothing is close.** The
smallest surviving claim is the fixed-compute data axis, `small_100k` →
`small_1m_matched` at +3.43 points: four paired standard errors and 3.2 seed
sds, so it holds, but it is also the only claim that was ever at risk, and it is
the axis whose fit was retracted on night 2 for a different reason. Every other
gap in the table clears the bar by 7 to 40 standard errors. The step axis
(+24.6 points for 2.5× compute) and the corpus axis at matched steps
(+5.0 points per decade) are both far outside the noise, and their *ratio* — the
finding that compute buys five times what data buys here — rests on two gaps
that are 7.6 and 21.6 standard errors wide.

Two kinds of comparison in this project need none of this and should not be
confused with the ones that do. Night 3's oversample fix and night 4's consensus
ranking both hold the checkpoint, the candidate draws and the molecules fixed and
change only how many candidates are kept or what order they are scored in. The
oversample fix can only add candidates, so its +0.2 to +0.9 points cannot have a
sign error; consensus ranking reorders a fixed set, and its +22 points are
immune to training variance entirely. Neither needs a seed sd. Comparisons
between *training runs* need it, and from tonight they have it.

## Stage 5c — three seeds are also an ensemble, and that is free to test

The variance runs incidentally produced something this project has never had:
three independently initialised models of identical cost. Their dumps answer a
question about where compute should go, at no extra cost.

At least one seed solves 1,371 of the 1,956 queries, against a single-seed mean
of 1,179 — 9.8 points of headroom. But polling three models costs three times
the oracle calls, and oracle calls are this project's budget, so the comparison
has to be made at equal budget. `scripts/ensemble_seeds.py` draws the k
candidates round-robin by each seed's own consensus rank, deduplicated by
canonical SMILES, so the oracle is still called exactly k times.

| scheme | oracle calls | rec@1 | rec@5 | rec@20 |
|---|---|---|---|---|
| single seed (mean of 3) | k | 0.4052 | 0.5508 | 0.6089 |
| three seeds, round-robin | k | 0.4059 | 0.6069 | 0.6564 |
| **three seeds, votes pooled** | **k** | **0.4601** | **0.6288** | **0.6738** |
| three seeds, union of each top-k | 3k | 0.5353 | 0.6457 | 0.7035 |

**At the same oracle budget, three seeds with their votes pooled beat one seed
by 6.49 points of `rec@20` and 5.49 points of `rec@1`** — eight paired standard
errors, far outside the noise measured an hour earlier. That recovers about
two thirds of what 3× the oracle budget would buy.

Two things in this table are worth more than the headline.

**Agreement between models is a better signal than agreement within one.**
Round-robin and pooled votes select from exactly the same union of candidates
and differ only in ranking, and pooling gains 5.4 points of `rec@1` over
round-robin where round-robin gains nothing at all at k=1. Night 3's consensus
result said a model reaches its best answer by several routes; this says that
when three independently trained models reach the same molecule, that is
stronger evidence still. Some of what single-model consensus measures is the
idiosyncrasy of one training run, and a second model filters it out.

**The gain is new molecules, not more draws.** A single seed, allowed unlimited
oracle calls over every candidate it drew, tops out at 0.632 — only 2.3 points
above its score at 20 calls, which is night 3's under-fill finding again: one
model's sampling is nearly exhausted. The three-seed union reaches 0.726 on the
same measure. And the seeds' candidate sets barely overlap: 25.2 distinct valid
candidates each, 66.8 in the union, mean pairwise Jaccard **0.098**.

That last pair of numbers is the sharpest thing the night produced. **The seeds
propose almost disjoint molecules while agreeing on four fifths of which queries
are solvable at all.** Diversity in what they propose, unanimity in what they
can do. A fifth consecutive confirmation that the ceiling is a property of the
molecules.

### It still loses to training for longer

The honest comparison is against spending the same compute sequentially. Three
8,508-step runs cost what one 25,524-step run would, and the step axis is the
best-measured effect in the project: `small_100k` → `small_100k_long`, 8,508 to
21,117 steps, is **+24.64 points** for 2.5× compute. Ensembling three seeds buys
+6.49 points for 3× compute.

**Depth beats breadth by roughly four to one, so the weekend plan does not
change: train longer, do not train three.** The ensemble result is worth having
for a different reason — it is the cheapest way to raise `rec@1` on a model that
already exists, and pooled cross-model voting is a ranking idea that may well
transfer to a single model's samples.

### Pooling the models you already have

Three equally strong seeds is not a situation anyone is in. Three checkpoints of
differing quality on a disk is. The night-3 dumps hold `small_1m` (0.8962),
`small_100k_long` (0.8476) and `small_full` (0.7444) on the identical protocol,
so the same test costs nothing.

| | oracle calls | rec@1 | rec@5 | rec@20 |
|---|---|---|---|---|
| best single model (`small_1m`) | k | 0.7526 | 0.8676 | 0.8962 |
| the three pooled by votes | k | 0.7607 | 0.8814 | 0.9039 |
| gap, McNemar p | | +0.82, p=0.18 | +1.38, p=4e-05 | +0.77, p=0.001 |

**Pooling the three models already on disk beats the best of them by 0.77 points
of `rec@20` at the same oracle budget** — 18 queries gained against 3 lost —
and by 1.38 points at `rec@5`. `rec@1` does not move.

The contrast with the seeds is the useful part. Equal-strength members gained
6.08 points over their best; members 5 and 15 points apart gain 0.77. **Pooling
pays when the members are comparably strong, not when you combine whatever is
lying around**: a much weaker model's votes mostly dilute. This is still the
best `rec@20` the project has recorded — 0.9039 — and it needed no training.

### The 1.6-point rule is for training runs, not for everything

This nearly went in as a null. Comparing +0.77 against the 0.8-point paired
standard error measured from the seed pairs makes it one standard error and
therefore nothing. That comparison is wrong, and the way it is wrong matters for
every future experiment here.

The 0.8-point figure comes from pairs of runs that disagree on **13%** of
queries. `small_1m` and a pooled ensemble containing `small_1m` disagree on
**21 queries — 1.1%** — because they are largely scoring the same candidates.
The paired standard error is `sqrt(21)/1956` = **0.23 points**, so +0.77 is 3.3
standard errors, and McNemar gives p = 0.001.

**The error bar has to be computed per comparison, from that comparison's own
discordance.** The 1.6-point threshold is specifically for two *independently
trained* runs, where both seed luck and 13% discordance apply. Two ranking or
decoding schemes evaluated over fixed checkpoints share almost everything,
almost everything cancels, and gaps far below a point are detectable. Which is
exactly why stage 6 was worth re-running with dumps.

## Stage 5d — where the ceiling is, and what the weekend run can do about it

Two checks that cost no GPU time and change what the weekend run should be
expected to achieve.

First, recovery against molecule size across the three seeds, with the column
that the variance analysis showed actually matters — the fraction of queries the
seeds *disagree* on, since unanimous queries carry no information about which
run is better:

| heavy atoms | n | recovery | contested | share of all discriminating power |
|---|---|---|---|---|
| 0–19 | 247 | 0.877 | 11.7% | 7.7% |
| 20–24 | 465 | 0.766 | 15.3% | 18.9% |
| 25–29 | 512 | 0.702 | 21.3% | 29.1% |
| 30–34 | 373 | 0.513 | 27.9% | 27.7% |
| 35–39 | 195 | 0.268 | 23.6% | 12.3% |
| 40–49 | 123 | 0.114 | 13.0% | 4.3% |
| 50+ | 41 | 0.024 | **0.0%** | 0.0% |

**It is a cliff, not a slope.** Above 40 heavy atoms the model is almost never
right; above 50 it recovers about one query in forty-one and **no seed ever
differs from another** — not one contested query in that band. Those 41 queries
are a constant and cannot contribute to any comparison between runs.

**And the protocol cannot be sharpened much by reweighting it.** The contested
fraction peaks at 27.9% in the 30–34 band but sits at 12–24% nearly everywhere
else, so an evaluation set stratified to the middle of the size range would buy
about 25% more discriminating power per oracle call — 0.240 contested queries
per query against 0.192 — which is not worth redesigning the protocol for. The
80% unanimity is not an artefact of including trivial or impossible molecules.
It is spread through the distribution.

Second, the shards are random subsets of ChEMBL, so they have identical size
*distributions*:

| shard | train molecules | ≥35 heavy atoms | ≥50 heavy atoms |
|---|---|---|---|
| 100k | 90,682 | 19.0% (17,205) | 2.42% (2,192) |
| 1M | 900,917 | 19.0% (171,422) | 2.42% (21,757) |
| full | 1,881,996 | 18.9% (356,074) | 2.31% (43,474) |

(40,000-molecule samples per shard.)

The full-ChEMBL run therefore doubles the absolute number of large molecules the
model will see while leaving their share of every batch at about 2.3%. **If the
cliff is a matter of exposure, uniform data scaling closes it only in proportion
to total data; if it is capacity or architecture, it will not close it at all.**
The run is still the right deliverable — it is the best model this project can
build — but night 3 motivated it partly by the hope that more data would reach
the large molecules, and that hope was never checked against the mix. It should
not be expected to fix the ceiling.

The experiment that follows from both checks is a **size-weighted training mix**
— over-sample molecules above 30 heavy atoms, 8,508 steps, three hours — and the
metric has to be chosen before it runs, because the error bar now demands it:
watch the **30–39 band** (568 queries, recovery 0.26 to 0.51), not the ≥50 band,
where 41 queries give a standard error of 7 points and nothing is measurable.

## Stages 6–9 — the decode setting, settled

Stage 1 refused to adopt T=0.7 because a +1.55-point win, selected as the
maximum of 15 correlated cells at n=386, is what no effect looks like. Stage 6
ran it on the common protocol, where n=1,956 and the comparison is paired —
same checkpoint, same molecules, only the temperature differs. **The refusal was
right as procedure and wrong about the answer.**

| | rec@1 | rec@5 | rec@20 |
|---|---|---|---|
| T=1.0, generation order | 0.5302 | 0.7996 | 0.8947 |
| T=0.7, generation order | 0.5726 | 0.8292 | 0.9064 |
| T=1.0, consensus | 0.7526 | 0.8676 | 0.8962 |
| **T=0.7, consensus** | **0.7694** | **0.8834** | **0.9080** |
| gap, McNemar p | +1.69, p=0.013 | +1.58, p=0.001 | +1.18, p=0.010 |

**Sampling at T=0.7 is worth +1.18 points of `rec@20`, and it is a real
effect**: 48 queries gained against 25 lost, a paired standard error of 0.44
points, p = 0.0095.

That error bar is the one from stage 5c, not the one stage 1 guessed. 0.44
points, against the 0.68 predicted from the binomial and the 1.6-point rule for
training runs — because the two arms share a checkpoint and most of their
candidates, so almost everything cancels.

### Three controls

**The baseline is matched, bit for bit.** The T=1.0 arm came from night 3's
dump, written by code that predates stage 0's changes. Stage 8 re-measured the
default with tonight's code: 0.5302 / 0.7996 / 0.8947 by generation order,
0.7526 / 0.8676 / 0.8962 by consensus, 123.4 samples per query, fill 0.6391 —
**identical to night 3 in every digit**, so the sampling path is unchanged and
the comparison needs no correction. Three retractions in this project came from
comparisons where a second thing had also moved; this is the check that costs 35
minutes and removes the whole class of objection.

**The gain is not bought with extra sampling.** A colder decoder repeats itself,
so the adaptive top-up keeps drawing and gives up: 140.3 samples per query
against 123.4, which is 14% more forward passes for the same 20 oracle calls.
Truncating both arms to the first M candidates drawn, in draw order:

| candidates seen | T=1.0 | T=0.7 | gap | p |
|---|---|---|---|---|
| 20 | 0.8727 | 0.8891 | **+1.64** | 6e-04 |
| 40 | 0.8942 | 0.9049 | +1.07 | 0.019 |
| 80 | 0.8962 | 0.9075 | +1.12 | 0.014 |
| all | 0.8962 | 0.9080 | +1.18 | 0.010 |

T=0.7 wins at every matched budget, and by most at the tightest one. T=1.0 has
saturated by 80 candidates while T=0.7 is still climbing at 120. The gain is the
decoder, not the compute — and under a *sampling* budget rather than an oracle
budget the colder setting looks better still.

**0.7 is not the edge of a better region.** Stage 1's grid stopped at its
coldest cell, so stage 9 extended it on the same disjoint tuning molecules:
consensus `rec@20` of 0.8990 at T=0.4, 0.9093 at 0.5 and 0.9145 at 0.6, against
0.9145 at 0.7, 0.8990 at 1.0 and 0.8782 at 1.1. Eight temperatures now trace a
single peak across 0.6–0.7 with falloff on both sides, so the plateau is found
rather than guessed at from an endpoint.

### The gain is entirely on large molecules

| heavy atoms | n | T=1.0 | T=0.7 | gap |
|---|---|---|---|---|
| 0–24 | 712 | 0.9537 | 0.9579 | +0.42 |
| 25–29 | 512 | 0.9570 | 0.9590 | +0.20 |
| 30–34 | 373 | 0.8901 | 0.8981 | +0.80 |
| **35–44** | **287** | **0.7666** | **0.8153** | **+4.88** |
| 45+ | 72 | 0.4444 | 0.4722 | +2.78 |

Collapsed and tested: **≥35 heavy atoms, +4.46 points on 359 queries, p = 0.014;
below 35, +0.44 points on 1,597 queries, p = 0.31.** The queries T=0.7 gains have
a median of 35 heavy atoms, against 26 for the ones both settings already solve.

**This is the first intervention in the project to move the band where the
ceiling lives.** The mechanism is plausible without being proven here: sampling
error compounds along a sequence, so the molecules needing the longest strings
are the ones a hot decoder is most likely to derail, and the failures above 35
heavy atoms were never collisions or missing information. One caveat on the
size of it — five bins were inspected before collapsing to two, so +4.9 locates
the effect better than it measures it.

It is also complementary to consensus ranking rather than redundant: at T=0.7,
consensus ordering still lifts `rec@1` from 0.5726 to 0.7694. And stage 1's
claim that consensus absorbs about three-quarters of the decoder's temperature
sensitivity holds in direction but was overstated: between these two
temperatures at n=1,956, `rec@1` moves 4.24 points by generation order and 1.69
by consensus, so **consensus absorbs 60%, not 75%.**

## Stage 10 — T=0.6 is better still, and three temperatures beat all of them

Stage 9's tuning-set curve tied 0.6 with 0.7, so 0.6 was chosen on that evidence
and then measured on the common protocol it had not been fitted to.

| T | rec@1 | rec@5 | rec@20 | validity | uniq/q | samples/q |
|---|---|---|---|---|---|---|
| 1.0 (old default) | 0.7526 | 0.8676 | 0.8962 | 0.921 | 18.9 | 123.4 |
| 0.7 | 0.7694 | 0.8834 | 0.9080 | 0.946 | 15.8 | 140.3 |
| **0.6** | **0.7730** | **0.8870** | **0.9162** | 0.948 | 14.7 | 145.9 |

(Consensus ordering throughout.)

**T=0.6 reaches 0.9162, +1.99 points over the default at p = 1.3e-05**, and it
wins at every matched candidate budget too — +2.40 points when only 20
candidates are seen (p = 7.7e-06). Against T=0.7 it is +0.82 points at p = 0.056,
which is to say **0.6 and 0.7 are not distinguishable from each other** while
both clearly beat 1.0. Two independent evaluation sets put 0.6 at or above 0.7,
so 0.6 is the adopted setting, and the honest summary is a plateau across
0.6–0.7 rather than a sharp optimum.

The large-molecule effect deepens monotonically as the decoder cools:

| | ≥35 heavy atoms (n=359) | <35 (n=1,597) |
|---|---|---|
| T=0.7 − T=1.0 | +4.46, p=0.014 | +0.44, p=0.31 |
| **T=0.6 − T=1.0** | **+7.52, p=1.4e-05** | +0.75, p=0.08 |

In the 35–44 band alone, T=0.6 moves recovery from 0.7666 to 0.8502. **Eight
points of the hardest band, from a decoder setting and no retraining.** It
suggests the optimum temperature is size-dependent — colder for longer strings —
which is a cheap and well-motivated next experiment, since the fingerprint's
bit count predicts molecule size before anything is generated.

### Three temperatures of one model, pooled

The seeds showed that cross-model agreement ranks better than within-model
agreement. Three temperatures of the *same* model are the cheapest possible
version of that, and all three dumps already existed.

| scheme | oracle calls | rec@1 | rec@5 | rec@20 |
|---|---|---|---|---|
| best single (T=0.6) | 20 | 0.7730 | 0.8870 | 0.9162 |
| **T=0.6/0.7/1.0 pooled** | **20** | **0.7812** | **0.9049** | **0.9279** |
| gap, McNemar p | | +0.82, p=0.09 | +1.79, p=2e-06 | **+1.18, p=7e-05** |

**0.9279 is the best `rec@20` this project has recorded**, from one trained
model, one fingerprint, and twenty oracle calls.

It costs 3× the forward passes, so the control matters. Capping each arm so the
three together see about as many candidates as T=0.6 sees alone:

| per-arm cap | total candidates | pooled | vs T=0.6 alone | p |
|---|---|---|---|---|
| 20 | 60 | 0.9131 | −0.31 | 0.39 |
| **34** | **~102** | **0.9238** | **+0.77** | **0.006** |
| 50 | 150 | 0.9259 | +0.97 | 0.001 |
| all | ~440 | 0.9279 | +1.18 | 7e-05 |

**At matched sampling cost the ensemble still wins**, by +0.77 points, and more
if you spend more. T=0.6 alone is saturated — its curve runs 0.9151, 0.9156,
0.9162 from 80 candidates to all of them — so the extra samples are not what
buys the gain. Mixing temperatures is.

That refines stage 1's conclusion rather than contradicting it. Diversity
*within* one temperature is exhausted and buys nothing, which is what stage 1
and night 3 both found. Diversity *across* temperatures is not exhausted, and a
cold arm and a hot arm make different mistakes.

---

## What tonight changes about the plan

### Unchanged, and now better justified

**Weekend 1 — full ChEMBL, 3 epochs, 44,112 steps, ~18 h — is still the
deliverable.** Depth beats breadth by about four to one (the step axis buys
+24.6 points for 2.5× compute; three seeds pooled buy +6.5 for 3×), so nothing
tonight argues for spending training compute on multiple runs. But its
*motivation* is corrected: it will not close the size cliff, because every shard
has the same size distribution. It is the best model this project can build, and
that is reason enough.

**Weekend 2 — step saturation, 52,500 steps on the 100k shard, ~21 h — is still
the science**, and it is now the axis whose effect most comfortably clears the
error bar: +24.6 points per 2.5× against a 1.6-point threshold.

**15M capacity stays deferred** as a debugging job, for night 3's reasons.

### New: every experiment now has to be sized before it is run

The error bar splits future work into two classes that need different treatment,
and this is the most useful thing the night produced.

*Paired comparisons over fixed checkpoints* — ranking, decoding, budget policy,
ensembling. Error bars of **0.2 to 0.5 points**, because the arms share a
checkpoint and most of their candidates, so sub-point effects are measurable and
most of these cost no GPU time at all. **All three of the night's best results
came from this class**: consensus ranking (+22 points of `rec@1`), T=0.7 (+1.2),
pooled ensembling (+0.77).

*Independent training runs* — data, capacity, architecture, schedule,
tokenisation. Error bar **1.6 points** before anything is believable, at three
hours minimum per arm. An experiment in this class whose expected effect is
under about 2 points should not be run as a single pair: it needs three seeds, at
3× the cost, or it should not be run.

Applied now: **counts are closed** (p = 0.32, and a comparable-scale rerun would
need seeds to say anything). Any "small architectural tweak" belongs in the same
bin unless someone can argue for a 2-point effect in advance.

### New: the ceiling needs a size-weighted mix, not more data

Recovery falls off a cliff above 35 heavy atoms and above 50 no seed ever
differs from another. Every shard holds the same ~2.3% of molecules at 50+ heavy
atoms, so uniform data scaling cannot concentrate learning there. The experiment
is a **size-weighted training mix** at 8,508 steps (~3 h), and the metric is
fixed in advance by the error bar: **the 30–39 band, 568 queries** — not the 41
queries above 50, where the standard error is 7 points.

Tonight's decode result is the first evidence that the cliff is partly
*decoding*, not only capability: +4.5 points above 35 heavy atoms from
temperature alone, with no retraining. That makes the band worth attacking from
both directions.

### New: adopt the colder decoder, and keep the protocol where it is

The user-facing default moves to the measured optimum; `generate_outcomes` and
`sample` stay at 1.0, so every number measured before tonight keeps its meaning
and re-scoring an old checkpoint reproduces it exactly. Every report already
records the temperature it used, so a future protocol change is one flag away.
**This is a choice worth reversing if you would rather the product and the
protocol agree** — the cost of agreeing is re-measuring the whole table.

### New: pooled-vote ensembling is the cheapest `rec@20` available

0.9039 at the same oracle budget, from three checkpoints already on disk and no
training. Worth adding to the library as a multi-checkpoint `generate`, which is
an API decision rather than a research one, so it is proposed and not built:
~2 h.

### Carried forward

Report `rec@1` under consensus ordering. Generation order is kept beside it in
every report, but it is not a neutral baseline — it discards information already
present in the samples.

### A known unknown

The 0.75-point sd is measured at **one** point: 8,508 steps on the 100k shard,
with a model whose `rec@20` is 0.60. Whether it shrinks at 21,117 steps, where
the model is far more competent and may be more tightly determined, is unknown
and was not worth three more hours tonight. Do not assume it transfers to the
weekend runs; lean on effects far larger than 1.6 points there, which both
weekend axes are.

### Revised schedule

| slot | job | cost | note |
|---|---|---|---|
| **Done tonight** | Consensus ranking, error bar, decode setting, ensembling | — | stages 0–10 |
| **Working day** | Size-weighted training mix, 8,508 steps | ~3 h | the ceiling; metric is the 30–39 band |
| | Multi-checkpoint ensemble in the library | ~2 h | best `rec@20`, needs an API decision |
| **Weekend 1** | Full ChEMBL, 3 epochs, 44,112 steps | ~18 h (~20 h window) | the deliverable |
| **Weekend 2** | Step saturation, 52,500 steps | ~21 h | the science |
| *Deferred* | 15M capacity | — | debug, not scale |
| *Closed* | Count fingerprints | — | null at p = 0.32 |
