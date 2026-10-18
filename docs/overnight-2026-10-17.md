# Weekend — 2026-10-17 into 2026-10-19

Thirty-five hours, Saturday 20:42 to Monday 08:00. The plan is in
[night 5's document](overnight-2026-10-16.md) under "what to do next", with one
change of priority: night 5 published a claim about what moves the budget
curve's exponent, and the claim was mislabelled. Block 1 exists to find out
what the label should have been, and it runs first, before the 16-hour training
job, because everything else written this weekend depends on the answer.

```
GPU queue
  block 1  the exponent 2x2, four scoring runs, no training    20:55 -> 23:42
  block 2  medium_1m_full, 15.1M parameters, 21,117 steps      23:42 -> ~11:45
  block 3  the capacity arm on both protocols                        (chained)
  block 4  size_mix_t35 cooled, on the common protocol               (chained)
  block 5  size_mix_rev, the reverse-direction mix                   (chained)
  tail     small_full at k=60, the third corpus point                (chained)
```

## Block 1 — it was training length, and the exponent is not a separate dial

### What was wrong

Night 5 fitted `1 − rec(k) = A·k^−b` to every arm it had and found the
exponent at 35+ heavy atoms sitting at 0.078 for the baseline, unmoved by the
training mix, nudged to 0.094 by cooling, and at **0.303** for `small_1m`. It
published that last step as capacity bending the curve, under the heading "the
exponent is a property of capacity", with the corpus difference recorded as the
first of three caveats.

The caveat was the whole story, and it was worse than the caveat admitted.
`variance_s1` is **7,951,945** parameters and `small_1m` is **7,962,225** — the
same architecture, the same `d_model`, the same layer counts. There is no
capacity difference between those two cells at all. What differs is the corpus
(90,682 against 900,917 molecules) and the training length (8,508 against
21,117 steps), and night 5 moved both at once and named the result after a
third thing that never changed.

### The 2×2

Two checkpoints already trained filled in the missing cells, so the test cost
four scoring runs and no GPU training. All four cells are the same
7.95M-parameter architecture, scored on the same large protocol (2,400
molecules, 2,321 fingerprint-unseen, `--min-heavy-atoms 30`) at T=0.6 to k=60.

Exponent at 35+ heavy atoms, fitted on the k = 5…60 rungs, with rec@60 in
`miss_anatomy.py`'s first-k-slots units beside it:

| | 8,508 steps | 21,117 steps | length effect |
|---|---|---|---|
| **100k corpus** | 0.104 / 0.310 | 0.229 / 0.673 | +0.125 / +0.363 |
| **1M corpus** | 0.122 / 0.361 | 0.281 / 0.769 | +0.159 / +0.407 |
| **corpus effect** | +0.019 / +0.051 | +0.053 / +0.095 | |

**Pre-registered, and falsified in both arms.** The driver's committed header
argued from night 5's concentration result: recovery is governed by which
fingerprints the learned conditional can reach at all, so seeing ten times as
many distinct molecules should widen that set while re-reading the same 90,682
more often should not. That predicted `small_1m_matched` ≥ 0.25 and
`small_100k_long` ≤ 0.15. Measured: **0.122** and **0.229**. Both wrong, both
in the same direction, and the direction is unambiguous — re-reading the same
100k corpus 2.5 times more is worth four to five times what seeing ten times as
many molecules is worth. Averaging the two main effects, in every band:

| band | on the exponent | on rec@60 | ratio |
|---|---|---|---|
| 30–34 | length +0.121, corpus +0.036 | length +0.236, corpus +0.045 | 3.4× / 5.3× |
| 35–39 | length +0.175, corpus +0.054 | length +0.366, corpus +0.070 | 3.3× / 5.3× |
| 40–49 | length +0.167, corpus +0.029 | length +0.434, corpus +0.076 | 5.8× / 5.7× |
| 50+ | length +0.104, corpus +0.030 | length +0.335, corpus +0.083 | 3.4× / 4.0× |
| 35+ | length +0.142, corpus +0.036 | length +0.385, corpus +0.073 | 4.0× / 5.3× |

The same ordering holds in protocol (molecule-budget) units on the whole large
protocol: rec@20 of 0.4106, 0.7415, 0.4649, 0.8121 for the four cells, a length
effect of +0.339 against a corpus effect of +0.062, 5.5×.

So these models were never corpus-limited at 8,508 steps. They were
under-trained, and 100k molecules read twelve times was still further from
exhausted than 900k molecules read once. That is not a surprising fact about
data; it is a statement that night 5's whole arm set was measured before
convergence, and every level it reported is a level on the way up.

### The exponent is not an axis of its own

Having four cells spanning 3.3× in `b` makes it possible to ask something night
5 could not: is the exponent carrying information the recovery level does not?

| run | b at 35+ | rec@60 at 35+ | b / rec@60 |
|---|---|---|---|
| `variance_s1` (100k, 8.5k steps) | 0.104 | 0.310 | 0.334 |
| `small_1m_matched` (1M, 8.5k) | 0.122 | 0.361 | 0.339 |
| `small_100k_long` (100k, 21k) | 0.229 | 0.673 | 0.340 |
| `small_1m` (1M, 21k) | 0.281 | 0.769 | 0.366 |
| `variance_s1` at T=1.0 | 0.085 | 0.249 | 0.341 |

Across a threefold range in the exponent, through two corpora, two training
lengths and two temperatures, the ratio moves by 10%. **"What moves the
exponent" has no answer separate from "what moves recovery."** Night 5's
framing — level and slope as separate dials, the mix moving one and capacity
bending the other — does not survive this table. The mix looked like it moved
the level without the slope because it moves both by very little; a 2.8-point
recovery gain comes with a 0.01 exponent gain, which is exactly what this ratio
predicts and what night 5 read as a null.

This is not an arithmetic identity. If `A` were pinned at 1 the ratio would
itself run from 0.29 to 0.41 over the observed range of `b`, and `A` is not
pinned: at 35+ it falls from 1.06 to 0.73 as training lengthens. Both fitted
parameters move together, in the directions that both raise recovery, and they
very nearly cancel in the ratio. Decomposing the gain by moving one parameter
at a time:

| contrast | band | total | b alone | A alone | b's share |
|---|---|---|---|---|---|
| 2.5× steps, 100k | 35+ | +0.373 | +0.279 | +0.156 | 75% |
| 2.5× steps, 1M | 35+ | +0.408 | +0.306 | +0.196 | 75% |
| 2.5× steps, 100k | 30–34 | +0.235 | +0.134 | +0.160 | 57% |
| 2.5× steps, 100k | 50+ | +0.286 | +0.275 | +0.015 | 96% |
| 2.5× steps, 1M | 50+ | +0.365 | +0.379 | −0.022 | 104% |

There is one place where night 5's instinct was right, under a different label.
`A` is the deficit the law extrapolates back to k=1 — `A` = 1 means nothing at
all is found in a single try. Above 50 heavy atoms `A` sits at **1.01, 1.00,
1.00, 1.02** across all four cells: no model in this project, at any corpus or
training length, ever finds a 50-atom molecule on its first proposal. There the
exponent really is the only quantity anything can move, because the other one
is against its ceiling. At 30–34 atoms `A` runs 0.98 → 0.44 and carries half
the gain. So the sharp version of the claim is: **for large molecules the
exponent is the only thing that moves, and what moves it is training length.**

### The reachable set widens and stays concentrated

Night 5's mechanism was concentration: above 50 atoms the preimages the decoder
draws land on a minority of queries, 52% of queries drew none at all, and the
measured recovery sat far below the Poisson benchmark that the same preimage
count would give if it fell independently. Does training longer widen the
reachable set, or just hit the same set harder? Band 50+, within k=60:

| run | preimages/query | share drawing none | per hit | measured | if Poisson | ratio |
|---|---|---|---|---|---|---|
| `variance_s1` (100k, 8.5k) | 0.087 | 96.9% | 2.75 | 0.0315 | 0.0830 | 0.38 |
| `small_1m_matched` (1M, 8.5k) | 0.134 | 93.7% | 2.12 | 0.0630 | 0.1253 | 0.50 |
| `small_100k_long` (100k, 21k) | 1.031 | 66.1% | 3.05 | 0.3386 | 0.6435 | 0.53 |
| `small_1m` (1M, 21k) | 1.307 | 52.0% | 2.72 | 0.4803 | 0.7294 | 0.66 |

Both. Preimages per query rise twelvefold with training length and the share of
queries drawing none falls from 96.9% to 52.0%, so the reachable set genuinely
widens rather than deepening. But the preimages per *hit* barely move (2.75 →
3.05 at matched corpus), and the last column — measured recovery over its own
Poisson benchmark, which is how evenly the draw spreads — climbs only 0.38 to
0.66. Even in the best cell a third of the recovery that the draw count would
support is still being lost to concentration. The cliff is being pushed back,
not dissolved.

### The size defect was the same mislabel, and the same correction

Stage 12 found the project's most promising-looking lever dead: the decoder
systematically proposes molecules too small for the fingerprint, but the defect
"does not survive on the 1M model", which at a matched 20-slot budget put 2.54
right-sized proposals above 50 atoms into the list against 0.54 and converted
14.6% of them against none. That was written up as capacity, in the same
sentence structure and with the same error. The four cells, at k=20, band 50+:

| | right-sized per query | queries with any | match rate among them | truncation on misses |
|---|---|---|---|---|
| 100k, 8,508 steps | 0.58 | 42.5% | 1.4% | −9.71 atoms |
| 100k, 21,117 steps | 2.17 | 71.7% | 14.6% | −4.13 |
| 1M, 8,508 steps | 0.73 | 40.2% | 7.5% | −10.28 |
| 1M, 21,117 steps | 2.54 | 76.4% | 14.6% | −4.23 |

Training 2.5× longer on the same 100k molecules closes 81% of the proposal-count
gap and 100% of the match-rate gap. Ten times the corpus at a fixed step count
closes 8% of the first, half of the second, and makes the truncation *worse*.
The length conditional is something these models learn late, not something they
learn from more molecules, and at 8,508 steps none of them had learned it yet.

That is the second night-5 conclusion to change label without changing sign.
The practical reading is unchanged and arguably strengthened: a length prior
still has nothing to correct, because the thing it would correct is a
transient of under-training rather than a property of the architecture or the
fingerprint.

### Plan item 1b, confirmed

Night 5 left one open pre-registration: the 100k arm had never been generated
past k=20, and three methods disagreed about where its k=60 recovery at 35+
would land. The power law fitted to its own k ≤ 20 rungs said 0.232,
independence said 0.47, and a recovery multiplier said 0.28. Registered band:
**0.21–0.26**, in first-k-slots units.

**Measured 0.2491.** Inside the band, 1.7 points above the power law's point
prediction, 3 points below the multiplier, and 22 points below independence,
which is now wrong by a wide margin for the fourth time in two nights. The
power law remains the only one of the three worth quoting, and the fact that it
was fitted on k ≤ 20 and held to k=60 on an arm it had never seen is the
strongest evidence so far that the extrapolated prices are lower bounds rather
than fiction.

### The third route, priced in the same currency as the other two

Block 1 was a correction, but it leaves a question the project has never asked.
If training length is the dial, how does its price compare with the one
`budget_curve.py` measured? Both are answerable from files already on disk, so
this cost no GPU time at all: `scripts/step_curve.py`.

The deficit turns out to follow a power law in training steps too, and the
exponent can be measured on exactly the same queries as the budget exponent, by
taking the two checkpoints that differ only in step count and reading the
deficit at one fixed k:

    c = log(D at 8,508 steps / D at 21,117 steps) / log(21,117 / 8,508)

Same architecture, same shard, same protocol, same k — so `b` and `c` are
commensurable. Reading both at k=20 on the 1M-corpus pair:

| band | b (budget) | c (steps) | c / b |
|---|---|---|---|
| 30–34 | 0.396 | 1.294 | 3.27 |
| 35–39 | 0.387 | 1.240 | 3.20 |
| 40–49 | 0.263 | 0.893 | 3.39 |
| 50+ | 0.144 | 0.366 | 2.54 |
| 35+ | 0.281 | 0.937 | 3.33 |
| all | 0.317 | 1.062 | 3.35 |

The 100k pair gives 2.86, 3.10, 2.92, 3.08, 3.13, 3.03 for the same bands. So
across two corpora and every size band, **a doubling of training steps cuts the
recovery deficit about 3.1 times as far as a doubling of inference budget**, and
the ratio is flat in molecule size even though both exponents fall by a factor
of three across the bands. Above 50 atoms, where the budget exponent is nearly
dead at 0.09–0.14, the step exponent is still 0.28–0.37.

That is not yet a recommendation, because the two are not the same kind of
spend: budget is charged on every query forever, training once. Cutting the
deficit by a factor f needs `f^(−1/b)` times the budget or `f^(−1/c)` times the
steps, so there is a query count above which the longer run is cheaper. With
training at 1.337 s/step (`small_1m`: 7.84 h for 21,117 steps) and generation at
0.016 s/slot/query (`small_1m_matched`: 2,298 s for 2,400 queries × 60 slots),
starting from 21,117 steps and k=20:

| band | queries, for a ×0.75 cut | for a ×0.5 cut |
|---|---|---|
| 35–39 | 20,900 | 13,300 |
| 40–49 | 16,900 | 8,000 |
| 50+ | 16,600 | 4,100 |
| 35+ | 17,900 | 9,000 |

**Below roughly ten thousand queries, buy budget; above it, train longer.** The
deeper the cut, the more the longer run wins, which is `c > b` restated. This
project's own protocols are 2,000 and 2,400 queries, an order of magnitude below
the crossover — so every "the brute-force route is affordable" statement in the
README is correct *for a benchmark*, and would be the wrong advice for anyone
actually inverting fingerprints at scale.

**And the step law is the weaker of the two, which the script reports rather
than hides.** The budget deficit is straight in log-log to |r| ≥ 0.991 over a
twelvefold range of k, and fitting it to k ≤ 20 predicts k=60 within a few
points. The step deficit is not straight. Fitting a 15-point trace to its first
half and predicting its last point *underestimates* recovery by 4.33 points on
`small_1m` and 2.64 on `small_100k_long`, with the fitted exponent climbing from
0.568 to 0.805 as more of the range is included. A curve accelerating in log-log
space cannot continue — recovery is bounded by 1 — so `c` is a local slope at
the top of the measured range and nothing more. Every number above is computed
inside the measured interval for that reason; the temptation to ask what 80,000
steps would buy is exactly the extrapolation that cost this project its
brute-force prices two days ago, and it is declined.

The honest summary is narrower than the table looks: within the range both laws
have been measured over, training steps are about three times more efficient per
doubling than inference budget, the crossover for this hardware sits near ten
thousand queries, and nobody has measured what either law does past it.

Two independent routes to the same quantity agree, which is worth recording
because almost nothing else in this project has a second measurement. The
matched-pair exponent above comes from two checkpoints scored on 2,321 holdout
molecules; restricting each run's own 500-molecule training trace to the same
8,508–21,117 window gives 0.934 for `small_1m` and 0.789 for `small_100k_long`,
against the pair's 1.062 and 0.817 on the "all" band. Different evaluation sets,
different draws, the same numbers to within a tenth, and the same ordering
between the two corpora.

**Pre-registered for block 2, and free.** That windowed trace exponent is the
one way to ask whether capacity changes the step law, because `small_1m` and
`medium_1m_full` train on the same shard and evaluate on the same validation
draw every 1,500 steps. Pinning the window to 8,508–21,117 makes their
exponents comparable without any extrapolation, and the window is necessary
rather than tidy: on an accelerating curve an unwindowed exponent mostly reports
how far each run happened to get. Registered: if capacity is a separate dial
from training length, the 15.1M model's windowed exponent should exceed
`small_1m`'s 0.934; if the two lie together, then capacity buys a level and
training length owns the slope. Wired into block 3 as part of stage 5b, where it
costs nothing.

> **Void, and not resolvable from anything on disk.** The two runs do not share
> a validation protocol, and the sentence above asserting that they do was never
> checked. The in-training evaluation changed on 2026-10-14 (`6c585e5`, "Top up
> evaluation sampling until k distinct candidates"): before it, an evaluation
> drew a fixed 40 strings per query and scored rec@20 over whatever distinct
> molecules that produced — **13.5 of 20** by the end of `small_1m` — and after
> it the sampler tops up until it has 20, reaching 18.4 on `medium_1m_full` at
> 128 draws per query. The newer run is scored with a 37% larger list, so its
> faster-falling deficit is partly a budget difference. It measured 1.143
> against `small_1m`'s 0.934, and that is not a comparison.
>
> `matched_steps.py` refused to print its half of stage 5b for exactly this
> reason and exited 1; `step_curve.py` had no such guard and printed anyway, so
> it has one now, with the same signature and the same refusal. Neither needed
> a result to catch this — the guard was written on night 2, after the same
> class of error, and only one of the two scripts had it.
>
> No other checkpoint is post-top-up: `medium_1m` at 2,500 steps is on the old
> protocol too, so a step exponent at 15.1M capacity cannot be built from
> existing artefacts at all. The question needs a second 15.1M checkpoint at a
> different step count, scored by `compare_checkpoints.py` rather than from a
> trace. It is not answered this weekend, and the capacity pre-registration
> that *is* answerable — the level, on the holdout protocol, both models in one
> call with identical settings — is what stage 6 is measuring.

### A bug this exposed

`budget_curve.py` crashed on the fourth run with `OverflowError: math range
error`. The T=1.0 50+ band fits b = 0.003 — a deficit that does not fall at
all — and inverting that for a 0.99 target asks for e^1500 molecules, which
`math.exp` raises on rather than returning a number. Fixed by reporting an
infinite budget above the float range, with the inversion guarded and a test
covering the saturated-band case. The three runs that mattered to the 2×2 had
already written their reports; only the T=1.0 curve had to be re-run, off the
dump, at no GPU cost.

### What this does to block 2

Block 2 is `medium_1m_full`: 15.1M parameters, the 1M shard, 21,117 steps —
`small_1m`'s corpus and `small_1m`'s step budget, with only the parameter count
moved. As a capacity contrast that is the right design, and it was the right
design before block 1 ran.

What block 1 changes is how a null would have to be read. Recovery is still
climbing steeply in steps at 21,117 — 2.5× the steps buys +0.34 rec@20, with no
sign of flattening — so neither model is near its own asymptote, and a larger
model at a matched step count is further from its asymptote than a smaller one.
If the 15M model comes out flat, that is consistent with capacity not helping
*and* with 15M-at-21,117-steps sitting where 8M-at-13,000-steps sat. Matched
steps is not matched training when nothing is converged.

The pre-registrations stand as registered — the gain concentrates above 35
atoms with 0–24 moving under a point, and the exponent at 35+ exceeds 0.303 —
but a third reading is added now, before the result exists, and it is the one
that can distinguish the two stories: both runs evaluate every 1,500 steps, so
each has its own recovery-against-steps trace. **If the 15M model's trace sits
above `small_1m`'s at every matched step and is still rising at 21,117, then
capacity pays per step regardless of where either run stopped.** If the traces
lie on top of each other, capacity is not paying at this budget. That
comparison does not depend on either run having converged, which is the defect
in the endpoint comparison that block 1 just exposed.

The tool for it already existed: `scripts/matched_steps.py`, written on night 2
after an endpoint comparison credited 10× the data with a gain that 2.5× the
steps had produced — the same error, two weeks earlier, in the same project.
Its one standing caveat is that each run is scored against the validation split
of its own shard, which for this pair does not apply: `small_1m` and
`medium_1m_full` share `data/shards/1m` and evaluate on it every 1,500 steps,
so the columns are matched on data and cadence and the only variable between
them is the parameter count. It is wired into the block 3 driver as stage 5b,
ahead of the scoring, because it costs nothing and runs even if block 2 is
truncated.

## Block 3 — capacity pays, but it is not a dial on anything

`medium_1m_full` reached the full 21,117 steps in 11.2 h, the same step count
and the same shard as `small_1m`, so this is the comparison the night-5 claim
was mislabelled as: 8.0M against 15.1M parameters with everything else held.
Both were scored in one `compare_checkpoints.py` call on the common protocol at
T=0.6, so they share the 2,000-molecule draw and the 1,956 fingerprint-unseen
subset exactly.

| run | params | rec@1 | rec@5 | rec@20 | struct@20 | validity | uniq/query |
|---|---|---|---|---|---|---|---|
| `small_1m` | 8.0M | 0.5920 | 0.8344 | 0.9131 | 0.9018 | 0.948 | 14.7 |
| `medium_1m_full` | 15.1M | **0.6483** | **0.8650** | **0.9264** | **0.9131** | 0.966 | 13.6 |
| gain (points) | | +5.63 | +3.06 | +1.33 | +1.12 | +1.8 | −1.1 |

Capacity pays. It is the first thing in this project to move rec@1 by more than
five points. The overall rec@20 gain is +1.33 points at 2.9 SE (p = 0.005).

Note the last two columns before reading anything else: the larger model
proposes **fewer distinct molecules** per query, 13.6 against 14.7, while
proposing more valid ones. It is more confident and more repetitive, and it
wins anyway. Whatever capacity bought here, it was not coverage.

One asymmetry survives in the comparison and is worth stating before the
analysis rather than after it. `medium_1m_full` trains at lr 4.5×10⁻⁴ with 400
warmup steps, `small_1m` at 5×10⁻⁴ with 300 — a choice made when the larger
config was written, to be safe at the wider model, and not a variable anyone
intended to move. So "1.9× the parameters" is strictly 1.9× the parameters and
0.9× the learning rate. Nothing in this project has shown recovery to be
sensitive to a 10% learning-rate change, and the effect sizes below are far
larger than any plausible lr contribution, but the clean statement is that this
is a capacity-plus-schedule step and not capacity alone.

### The gain is a constant fraction of the deficit, which is not what was registered

The standing pre-registration, from night 5, verbatim:

> if the limit is capacity the gain concentrates above 35 atoms and the 0–24
> band moves by less than a point; if the gain is flat across bands it is not
> the size cliff that got better and the cliff is in the fingerprint or the
> data.

Band table, common protocol, k=20, generation order, 1,956 queries:

| band | n | `small_1m` | `medium_1m_full` | gain | SE | p |
|---|---|---|---|---|---|---|
| 0–24 | 712 | 0.9579 | 0.9719 | **+1.40** | 0.63 | 0.041 |
| 25–29 | 512 | 0.9629 | 0.9668 | +0.39 | 0.73 | 0.791 |
| 30–34 | 373 | 0.9008 | 0.9035 | +0.27 | 0.89 | 1.000 |
| 35–39 | 195 | 0.8718 | 0.8872 | +1.54 | 1.85 | 0.581 |
| 40–49 | 123 | 0.6992 | 0.7724 | **+7.32** | 3.35 | 0.049 |
| 50+ | 41 | 0.4634 | 0.4878 | +2.44 | 5.45 | 1.000 |
| 35+ | 359 | 0.7660 | 0.8022 | **+3.62** | 1.65 | 0.041 |
| all | 1,956 | 0.9131 | 0.9264 | +1.33 | 0.46 | 0.005 |

**The first clause passes and the second fails.** The 35+ gain is +3.62 against
0–24's +1.40, so it does concentrate above 35; but 0–24 moved by 1.40 points,
not under one, and it is tied with 35+ as the second-most significant band in
the table. The registered dichotomy does not resolve: the result is neither
concentrated nor flat, and the gain is not monotone in size — 25–34 is dead
(+0.39, +0.27) with live bands on both sides of it.

The dichotomy does not resolve because it was registered on the wrong scale.
Both dumps run to k=60 on the large protocol, so the deficit ratio can be read
band by band and budget by budget. **This is the whole result in one table:**

| band | n | k=1 | k=2 | k=5 | k=10 | k=20 | k=30 | k=40 | k=60 |
|---|---|---|---|---|---|---|---|---|---|
| 30–34 | 1,189 | 0.912 | 0.868 | 0.791 | 0.760 | 0.762 | 0.766 | 0.790 | 0.757 |
| 35–39 | 625 | 0.931 | 0.866 | 0.878 | 0.837 | 0.772 | 0.815 | 0.810 | 0.845 |
| 40–49 | 380 | 0.958 | 0.899 | 0.849 | 0.844 | 0.849 | 0.798 | 0.785 | 0.815 |
| 50+ | 127 | 0.942 | 0.948 | 0.961 | 0.946 | 0.907 | 0.875 | 0.883 | 0.914 |
| 35+ | 1,132 | 0.942 | 0.892 | 0.882 | 0.864 | 0.835 | 0.823 | 0.819 | 0.851 |
| all | 2,321 | 0.929 | 0.882 | 0.851 | 0.830 | 0.812 | 0.806 | 0.811 | 0.825 |

Each cell is `medium_1m_full`'s shortfall divided by `small_1m`'s on the same
queries; 1.00 means capacity bought nothing. Thirty-two cells over the four
bands and eight budgets, every one between 0.76 and 0.96, with no trend in
either direction across a 2× range in target size and a 0.45-to-0.93 range in
recovery. **Doubling the parameters cuts the shortfall by a roughly constant
17%, at every size and every budget.**

This table is the large protocol, which draws only molecules of 30 heavy atoms
and up, so on its own it says nothing about the two bands the registration was
actually about. The common protocol covers them, and the same ratio can be read
off the band table above at k=20. The last two columns test the uniform cut as
a one-parameter model: what a flat 17% predicts, and how far the measurement
lands from it in units of its own SE.

| band | n | deficit | ratio | cut | gain | SE | 17% predicts | off by |
|---|---|---|---|---|---|---|---|---|
| 0–24 | 712 | 4.21 | 0.667 | 33.3% | +1.40 | 0.63 | +0.72 | **+1.1 SE** |
| 25–29 | 512 | 3.71 | 0.895 | 10.5% | +0.39 | 0.73 | +0.63 | −0.3 SE |
| 30–34 | 373 | 9.92 | 0.973 | 2.7% | +0.27 | 0.89 | +1.69 | −1.6 SE |
| 35–39 | 195 | 12.82 | 0.880 | 12.0% | +1.54 | 1.85 | +2.18 | −0.3 SE |
| 40–49 | 123 | 30.08 | 0.757 | 24.3% | +7.32 | 3.35 | +5.11 | +0.7 SE |
| 50+ | 41 | 53.66 | 0.955 | 4.5% | +2.44 | 5.45 | +9.12 | −1.2 SE |
| 35+ | 359 | 23.40 | 0.845 | 15.5% | +3.62 | 1.65 | +3.98 | −0.2 SE |
| all | 1,956 | 8.69 | 0.847 | 15.3% | +1.33 | 0.46 | +1.48 | −0.3 SE |

The per-band cuts scatter from 2.7% to 33.3%, but the bands below 40 atoms have
four to thirteen points of deficit to work with, so a tenth of a point of noise
moves the ratio by several percent. **Every one of the nine rows is within 1.6
SE of a flat 17% cut.** One number, no size dependence, fits the entire table.

That is also what makes the registration ill-posed, and in a way worth
recording. A uniform multiplicative cut yields a *point* gain proportional to
the deficit, so it is automatically largest wherever recovery is lowest:
"concentrates above 35 atoms" was not a prediction about chemistry but about
arithmetic, and it would have come out true of any intervention that helped
uniformly at all. Worse for the clause that failed, a flat 17% predicts **+0.72
points** in the 0–24 band — the registered threshold of "less than a point" sat
almost exactly on the uniform-cut prediction, and the measurement came in 1.1
SE above it. The clause failed by one standard error, not because 0–24 turned
out to be special.

Read on the scale where "flat" means something, then, the registration's second
disjunct is the one that fires: **it is not the size cliff that got better.**
Nothing here is size-specific. The only hint of drift is the wrong way — the
well-powered 50+ row on the large protocol sits at 0.88–0.96, the closest to
1.00 of any band, so if capacity favours anything it is the easy end. The cliff
is still there, 17% shallower.

### The exponent prediction passes, and the pass means nothing

The second standing pre-registration:

> **the exponent at 35+ should land above 0.303**, `small_1m`'s value

0.303 is `small_1m`'s k ≤ 20 window fit, so the matched quantity is the
`b(<=20)` column. `small_1m`'s night-5 dump was re-scored through the identical
`miss_anatomy.py` → `budget_curve.py` path for this comparison, reproducing its
published numbers to the digit.

| band | `small_1m` b | `medium` b | `small_1m` b(≤20) | `medium` b(≤20) | b/rec small | b/rec medium |
|---|---|---|---|---|---|---|
| 30–34 | 0.396 | 0.404 | 0.399 | 0.425 | 0.434 | 0.432 |
| 35–39 | 0.387 | 0.408 | 0.403 | 0.496 | 0.447 | 0.460 |
| 40–49 | 0.263 | 0.291 | 0.304 | 0.305 | 0.367 | 0.379 |
| 50+ | 0.144 | 0.176 | 0.123 | 0.165 | 0.321 | 0.355 |
| **35+** | 0.281 | 0.305 | **0.303** | **0.343** | 0.366 | 0.380 |
| all | 0.317 | 0.333 | 0.334 | 0.368 | 0.376 | 0.383 |

**Confirmed: 0.343 against the registered 0.303.** The full-range fit agrees,
0.305 against 0.281.

And it is worth nothing, for the reason block 1 established two days ago. The
last two columns divide each exponent by its band's recovery at k=60: they move
by −0.001, +0.013, +0.012, +0.034, +0.014 and +0.006. The spread of that same
ratio across the five block-1 runs was 0.334–0.366, a range of 0.032 — wider
than five of these six differences. **The exponent rose by almost exactly the
amount its higher recovery accounts for.** The prediction was written when I
believed the exponent was a capacity dial; it is confirmed as a number and void
as an inference, and it was confirmed by the quantity it was meant to rule out.

The residual is real but tiny and points the other way from the earlier
reading: the deficit ratio falls from 0.94 at k=1 to 0.82 at k=40, so capacity
helps slightly *more* at large budgets, which is what tilts the fit to a
steeper slope. In points the opposite holds — +4.31 at k=1 against +2.76 at
k=60 — because the deficit it is shrinking is itself shrinking faster. Both
statements are true and they are about different scales; the night-5 heading
"budget dilutes the match rate" is true in points only.

### A null here would have proved nothing, and this is not a null

The caveat committed with the registration still applies, now with its sign
flipped. At 21,117 steps nothing in this project is converged, and the step
traces show both runs still falling, so a 15.1M model at matched steps is
further from its own asymptote than an 8.0M one. A flat result would therefore
have been unreadable: consistent with capacity not helping, and equally with
15M-at-21k sitting where 8M-at-13k sat.

It did not come out flat, which means the caveat now works as a floor rather
than an alibi: **+1.33 points and a 17% deficit cut are a lower bound on what
this capacity step is eventually worth**, measured at the point least
favourable to the larger model.

The third reading registered alongside them — whether the 15.1M trace sits
above `small_1m`'s at every matched step — remains unanswerable, for the
protocol reason recorded in the Void block above, not for want of trying.

### Two models beat two seeds of one, at the same price

`seed_union.py` was run over the two k=60 dumps, treating capacity as the axis
a seed usually occupies. Both were scored on the large protocol's same
2,400-molecule draw, which the script verifies.

| band | n | one model | union of two | luck | 1×60 | 2×30 |
|---|---|---|---|---|---|---|
| 30–34 | 1,189 | 0.9357 | 0.9495 | 21.6% | 0.9357 | **0.9411** |
| 35–39 | 625 | 0.8976 | 0.9280 | 29.7% | 0.8976 | **0.9072** |
| 40–49 | 380 | 0.7763 | 0.8184 | 18.8% | 0.7763 | **0.7921** |
| 50+ | 127 | 0.5079 | 0.5669 | 12.0% | 0.5079 | 0.5039 |
| 35+ | 1,132 | 0.8132 | 0.8507 | 20.1% | 0.8132 | **0.8233** |
| all | 2,321 | 0.8759 | 0.9013 | 20.5% | 0.8759 | **0.8837** |

(These are `seed_union.py`'s first-k-slots convention, ~0.5 points above the
protocol's molecule-budget figures. Read the columns against each other.)

**One fifth of what either model misses, the other one finds**, and splitting a
fixed 60 molecules of budget across the two beats spending all 60 on the better
of them in five of six bands, by +0.78 points overall and +1.01 at 35+. The
exception is 50+, where halving the budget costs more than the second model
brings — the one band where a single model's 60 slots are still the binding
constraint.

The honest limit on this: the comparable same-model seed unions from night 5
were run at k=20 on the 100k models, where recovery is near 0.35 and the
equal-spend gain was +0.06 to +0.55 points. They are not a control for this at
k=60 on 1M-shard models, so "a second architecture beats a second seed" is
*suggested* by the two tables and not established by either. A matched run
would be `seed_union.py` over two seeds of `small_1m` at k=60, which does not
exist.

### What block 3 settles

Three claims about the exponent have now been made and two retracted. The
surviving picture is simpler than any of them: **the exponent is not an axis.**
Training length moves it (block 1, 4:1 over corpus), capacity moves it (0.303 →
0.343), and in both cases it moves by the amount the recovery level moved,
leaving `b/rec` inside its own run-to-run spread. Nothing in six runs has
changed the shape of the budget curve; interventions slide a model along it.

Capacity's contribution, stated in the one form that survives all three
scales: **a 17% cut in the shortfall, uniform in size and budget, bought with
1.9× the parameters and 1.5× the inference cost** (1.5 against 2.3 queries/s).
Against the prices in block 1's third-route table, that is a poor trade per
unit of compute and a good one per unit of budget — and it is the only
intervention so far that does anything at k=1.

## Stage 7 — the second dose's bill, cooled

Twenty minutes for a number the project has been quoting from the wrong
measurement. Night 5 found that the first size-mix dose's exchange rate roughly
halves when the decoder is cooled to the adopted T=0.6 — 2.3 small molecules
given up per large one gained at T=1.0, 1.3 cooled — but the second dose's 4.4
was never re-measured, so every statement about the second dose's cost has been
a hot number sitting in a cooled table. `size_mix_t35` scored on the common
protocol at T=0.6 closes that, and the four-arm exposure table is re-fitted
with it.

| dose | exposure | bill, T=1.0 | bill, T=0.6 | pts/doubling, T=0.6 | r | net over 1,956 |
|---|---|---|---|---|---|---|
| `mix3x30` (×3, 30+) | 1.69× | 2.3 | **1.3** | +3.39 | 0.742 | −0.28 |
| `mix6x35` (×6, 35+) | 3.06× | 4.4 | **3.5** | +4.21 | 0.988 | −2.76 |
| marginal, dose 1 → 2 | | 10.7 | **25.2** | | | −2.48 |

"Bill" is small molecules given up per large molecule gained. Both doses get
cheaper cooled, as the first one did — and **the marginal step between them
gets more than twice as expensive**, from 10.7 to 25.2 molecules given up per
one gained. Cooled, the second dose buys 2.0 molecules for 50.5.

That combination is not a contradiction and it is the most useful thing in the
stage. Cooling and the first dose buy overlapping things: both work by raising
the number of right-sized candidates in the budget, which night 5 measured
directly (1.93 per query at baseline, 2.15 with the mix, 2.44 cooled, 2.56 with
both). Once the decoder is cold, the first dose has already collected most of
what re-weighting can collect, so the second dose is paying full price for a
remainder that has shrunk. **Each dose is cheaper and the second dose is worth
less — the interventions are substitutes at the margin, not complements**, even
though night 5 showed them additive in points band by band.

The exposure line is also better behaved at the second dose than the first:
r = 0.988 against 0.742, and the two doses' slopes bracket the +3.4 the law was
fitted at. The first dose's poor fit is the 30–34 band, which sits at 1.69×
exposure and moves +0.27 points — an exposure increase that bought nothing,
while 35–39 at the same exposure bought +7.69. That is the one point in this
table that the single-exchange-rate story does not explain, and it is the band
the reverse-direction control in stage 8 puts the most weight on.

Stage 8's pre-registration is unchanged by this, because it was written against
the T=0.6 dose-1 column, which night 5 had already measured and stage 7 did not
touch.

## Stage 8 — the exposure law survives as a slope and fails as a law

`size_mix_rev` trained to its full 8,508 steps in 2.9 h and was scored on the
common protocol at T=0.6. It de-weights 30+ heavy atoms by 1/3, the reciprocal
of `size_mix_s1`'s factor 3, with the same seed, shard, schedule and step count
— so this is night 5's one quantitative law run backwards, out of sample, in
the direction no dose had ever tested.

### First: the registration's own premise was wrong

The config predicted that "every band sits at the reciprocal exposure." It does
not, and the error is mine:

| band | forward ×3 | reverse ÷3 | product | log₂ fwd | log₂ rev | lever |
|---|---|---|---|---|---|---|
| 0–24, 25–29 | 0.563× | 1.350× | 0.759 | −0.830 | +0.433 | **0.52×** |
| 30–34 … 50+ | 1.688× | 0.450× | 0.759 | +0.755 | −1.152 | **1.53×** |

Re-weighting renormalises, so the 30+ share `s` maps to `3s/(1+2s)` under the
forward dose and to `s/(3−2s)` under the reverse. Those are not reciprocal
multipliers. The product is 0.759 in every band, and lopsidedly: the reverse
dose pulls the bands it starves 1.53× further in log-exposure than the forward
dose pushed them, while moving the bands it feeds only 0.52× as far. **A factor
and its reciprocal do not produce mirror exposures, and I registered a
prediction that assumed they would.**

### The band prediction is falsified, and correcting the premise makes it worse

> each band's gap should land within 2 points of minus its mirror-dose gap

| band | forward gap | predicted | measured | off by | |
|---|---|---|---|---|---|
| 0–24 | −2.74 | +2.74 | **+0.28** | −2.46 | FAIL |
| 25–29 | −1.17 | +1.17 | −0.39 | −1.56 | pass |
| 30–34 | +0.27 | −0.27 | **−9.38** | −9.12 | FAIL |
| 35–39 | +7.69 | −7.69 | −5.64 | +2.05 | FAIL |
| 40–49 | +2.03 | −2.03 | −5.69 | −3.66 | FAIL |
| 50+ | +3.66 | −3.66 | −2.44 | +1.22 | pass |

**Two of six.** And the exposure error above is not an alibi: predicting each
band instead from the forward dose's own fitted line, evaluated at the exposure
the reverse dose actually realised, gives +2.32 / +2.32 / −3.05 / −3.05 /
−3.05 / −3.05 against the measured values — **one of six** within 2 points.
Pricing the lever correctly makes the band-level law fit worse, not better.

### The slope prediction is confirmed

> the fitted points-per-doubling should come back within 1.5 points of +3.4
> with the same sign

**+3.62, against +3.4.** Inside 0.22 of the registered value, same sign, on a
dose that moves every band the opposite way. The three doses now read +3.39
(r = 0.742), +4.21 (r = 0.988) and +3.62 (r = 0.802).

So the aggregate exchange rate is real and transfers out of sample, in a
direction it was never fitted to. What does not transfer is any claim about
*which* band pays or collects how much.

### Why: taking exposure away costs far more than adding it buys

The reverse dose probes the same baseline from the same threshold in the
opposite direction, so the two directions can be priced against each other
band by band:

| band | forward | pts/2× | reverse | pts/2× | steeper going down |
|---|---|---|---|---|---|
| 0–24 | loss | 3.30 | gain | 0.65 | **5.1×** |
| 25–29 | loss | 1.41 | gain | −0.90 | **wrong sign** |
| 30–34 | gain | 0.36 | loss | 8.14 | **22.9×** |
| 35–39 | gain | 10.19 | loss | 4.90 | 0.5× |
| 40–49 | gain | 2.69 | loss | 4.94 | 1.8× |
| 50+ | gain | 4.85 | loss | 2.12 | 0.4× |

For the three bands around the threshold — the 1,597 queries that are 82% of
the protocol — **losing exposure hurts and gaining it does nothing.** 0–24
loses 2.74 points when starved and gains 0.28 when fed; 25–29 loses 1.17 and
then moves the *wrong way*, −0.39, when fed; 30–34 gains 0.27 when fed and
loses 9.38 when starved, a factor of 23 between the two directions from an
identical starting point. Above 35 atoms the asymmetry is absent or reversed,
but those are 195, 123 and 41 queries.

That is a coherent picture and it is not what a single exchange rate describes.
The small and middle bands are **saturated in exposure**: they already see more
examples than they can use, so more buys nothing, while less still costs. The
large bands are starved in both directions, so they respond both ways. A law
fitted inside one dose averages a saturated side against a starved side and
recovers a slope that happens to be stable — which is exactly what survived
here, and exactly why it survived while every band-level number failed.

It also retrospectively explains the forward dose's poor fit, r = 0.742: the
outlier was always 30–34, which bought nothing at 1.69× exposure. Night 5 read
that as noise in a band of 373 queries. It was the saturation point, visible in
the one cell that straddles it.

### The reverse dose is strictly dominated, and two opposite doses coincide

`size_mix_rev` gives up 56 molecules to gain 2 — **28 given up per one gained**,
against the forward dose's 1.3. The marginal step from reverse to forward is
−1.7, a negative price: moving to the forward dose gains molecules on *both*
sides. There is no regime in which de-weighting large molecules is the right
trade, which is worth having measured rather than assumed.

And a coincidence that makes night 5's methodological point better than night 5
did:

| run | rec@20, whole protocol | struct@20 | net points |
|---|---|---|---|
| `variance_s1` (baseline) | 0.6534 | 0.6396 | — |
| `size_mix_s1` (×3, 30+) | 0.6498 | 0.6375 | −0.28 |
| `size_mix_t35` (×6, 35+) | **0.6258** | 0.6115 | −2.76 |
| `size_mix_rev` (÷3, 30+) | **0.6258** | 0.6166 | −2.76 |

Up-weighting large molecules sixfold and down-weighting them threefold produce
**the same whole-protocol recovery to four decimal places**, while doing
opposite things in every band. Night 5 argued from first principles that the
common protocol cannot describe a redistributive intervention. Here are two
interventions it cannot tell apart, moving in opposite directions. (Structure
accuracy does separate them, 0.6115 against 0.6166 — a reminder that the two
metrics are not interchangeable even when recovery coincides.)

## Stage 9 — the corpus axis is convex, which revises block 1

The third point on the corpus axis: `small_full`, 1,881,996 molecules, the same
8M architecture and the same 8,508 steps as the other two, scored at T=0.6 and
k=60 on the large protocol. Block 1 read the corpus axis off two points. The
third one does not lie on the line between them.

| molecules | epochs | rec@60, all | 35+ | b, all | b, 35+ |
|---|---|---|---|---|---|
| 90,682 | 12.01 | 0.4752 | 0.3101 | 0.157 | 0.104 |
| 900,917 | 1.21 | 0.5205 | 0.3613 | 0.178 | 0.122 |
| **1,881,996** | **0.58** | **0.6424** | **0.4982** | **0.216** | **0.160** |

Per doubling of corpus, at matched steps and matched parameters:

| segment | × | doublings | points | per doubling | deficit cut/doubling |
|---|---|---|---|---|---|
| 90.7k → 900.9k | 9.93× | 3.31 | +4.52 | **+1.37** | 2.7% |
| 900.9k → 1.88M | 2.09× | 1.06 | +12.19 | **+11.47** | 24.1% |

**The second segment is 8.4 times steeper than the first.** It is not a
points-scale artefact — in deficit terms the cut per doubling goes from 2.7% to
24.1%, a factor of nine — and it is not a composition artefact either. The
three shards were sampled and measured: the 30+ share is 38.81%, 38.70% and
38.82%, the 35+ share 19.08%, 18.92% and 18.95%, and mean heavy atoms 28.24,
28.27 and 28.30. The bigger shards are not quietly better size mixes. They are
the same distribution, more of it.

### What this does to block 1's headline

Block 1 concluded that training length beats corpus and that these models were
under-trained rather than corpus-limited. Scored per doubling on the same
numbers:

| | per doubling | steps : corpus |
|---|---|---|
| steps, averaged over both corpus rows | +23.55 | — |
| corpus, 90.7k → 900.9k | +1.37 | **17.2 : 1** |
| corpus, 900.9k → 1.88M | +11.47 | **2.1 : 1** |

**The ordering survives and the margin does not.** Training length is still the
better buy, but at 17:1 only on the corpus segment block 1 happened to measure;
past 900k molecules it is 2:1. Block 1's "these models were under-trained, not
corpus-limited" was read off the flat part of a convex curve, and said without
knowing the curve was convex. The honest version is that both axes pay, steps
pay more, and the corpus axis was measured where it pays least.

One asymmetry in that comparison: the corpus slopes are measured only at 8,508
steps, and the steps slope is averaged over corpora that both sit on the flat
segment. Whether the corpus axis is still this steep at 21,117 steps is not
measured — there is no full-shard long run — so 2.1:1 is a figure for short
training.

### The confound that cannot be removed at constant steps

The epochs column is the whole difficulty. At a fixed step count, `steps ×
batch = corpus × passes`, so a larger corpus is necessarily a lower repetition
rate: 12.01 passes, then 1.21, then 0.58. The steepening coincides with
crossing one epoch — `small_full` never sees a molecule twice.

Two readings, and nothing here separates them. Either diversity is what pays
and repetition is nearly worthless, so the gain accelerates as repetition falls
toward zero; or something specific happens at and below a single pass. Both
predict exactly what was measured. This is open question 2 in the README, and
stage 9 has made it the most valuable unanswered question in the project rather
than a methodological footnote: the quantity everyone would want to quote from
this table — points per doubling of corpus — is not identified by it.

What stage 9 does establish, without needing that disambiguation, is narrower
and solid: **at a fixed compute budget of 8,508 steps, spending it on 1.88M
distinct molecules seen 0.58 times each beats spending it on 90,682 molecules
seen twelve times each by 16.7 points of rec@60**, and the exponent rises with
it, 0.157 → 0.216. At fixed compute, prefer more molecules to more passes.

### The confound is separable after all, and the answer changes the reading

The section above said points-per-doubling-of-corpus is not identified by three
points. That was too pessimistic, and the fix costs no GPU time: **at a fixed
corpus, the steps axis *is* the passes axis.** Those runs already exist.

| corpus | passes at 8,508 | at 21,117 | rec@60 | → | points | per doubling |
|---|---|---|---|---|---|---|
| 90,682 | 12.01 | 29.81 | 0.4752 | 0.7708 | +29.56 | **+22.54** |
| 900,917 | 1.21 | 3.00 | 0.5205 | 0.8427 | +32.23 | **+24.57** |

Two things fall out of this table before any modelling. First, **repetition is
not worthless** — going from twelve passes to thirty over the *same* 90,682
molecules buys +29.6 points, nearly what going from 1.2 passes to 3.0 over ten
times the data buys. The simplest reading of the convexity, that gains
accelerate because repetition is nearly free to give up, is wrong. Second, the
slope is stable at +22.54 against +24.57 across a tenfold change in the
repetition regime, which is exactly what an additively separable law in log
space predicts and is the licence to fit one.

So take `value = f(log distinct molecules) + g(log passes)` with g′ = 23.55
points per doubling, and read the corpus segments at constant steps, where a
corpus doubling *is* a passes halving:

| segment | doublings | net measured | passes cost | f′ implied | f′ per doubling |
|---|---|---|---|---|---|
| 90.7k → 900.9k | 3.31 | +4.52 | −78.02 | +82.55 | **+24.92** |
| 900.9k → 1.88M | 1.06 | +12.19 | −25.03 | +37.23 | **+35.03** |

This reverses the emphasis of the section above in three ways.

**The corpus axis at constant steps is a near-cancellation, so it is a terrible
instrument.** Distinct molecules are worth +24.92 points per doubling on the
first segment and the passes they cost are worth −23.55, which nets +1.37. The
observable is a small difference of two large numbers, and that is the whole
reason it looked flat. Nothing about the first segment says data does not
matter; it says data and repetition were trading off at almost exactly par.

**Most of the 8.4× convexity is amplification, not acceleration.** f′ rises
from +24.92 to +35.03, a factor of 1.4. The net rises from +1.37 to +11.47, a
factor of 8.4. A near-cancellation multiplies a mild convexity in the
underlying quantity by about six. The headline above — "the second segment is
8.4 times steeper" — is true of the observable and badly overstates what moved
underneath it.

**And the number worth extrapolating from is far larger than the raw axis
suggested.** For anything asking what a bigger corpus buys at a *bigger compute
budget* — where the extra data need not be paid for out of passes — the
relevant figure is f′ ≈ 25 to 35 points per doubling of distinct molecules, not
+1.37. The two are not in conflict; they answer different questions, and this
project has been quoting the one that answers almost nobody's.

Three caveats, since this is an inference and not a measurement. Additive
separability is assumed, supported only by g′ holding to 9% across the two
rows. g′ is measured over 1.2–30 passes and the second segment needs it down at
0.58, a modest extrapolation. And f′ is two segments, so its convexity is one
comparison, not a curve. The constant-epochs sweep in README open question 2
remains the thing that would measure f′ directly rather than inferring it —
but the inference is sharp enough that the question is now "is f′ really
convex", not "is any of this identified".

### A third reading for stage 10, registered before it lands

Stage 9's decomposition adds a mechanism to the stage-10 pre-registration that
was not in the config, so it goes on record now, while `medium_1m_8k` is still
training and no number exists.

The two cells stage 10 compares differ in repetition as well as steps: at 8,508
steps on the 1M shard a model makes 1.21 passes, at 21,117 steps it makes 3.00.
If part of what extra parameters buy is a better fit to molecules the model has
already seen, then capacity should pay *more* where there is more repetition to
exploit — at 21,117 steps — and the deficit ratio at 8,508 steps should come
out **above** the 0.825 measured at 21,117. That is the falsified-high branch of
the registration, and it would carry the consequence already recorded there:
block 3's +1.33 points is a floor that widens with further training.

The uniform-cut null predicts no such dependence. So the three branches now
have mechanisms attached rather than only directions, and the registration is
unchanged: ratio 0.76–0.96 confirms, below 0.76 falsifies low, above 0.96
falsifies high. Pre-registered 18:30 Sunday; training ends about 22:45.

## Stage 10 — the 2x2 closes: capacity cuts a fixed fraction, and points are the wrong unit

`medium_1m_8k` reached its 8,508-step budget at 00:26 Monday and scored clean.
The cell it fills was the whole point of the stage: the capacity-versus-steps
number from night 5 had to be voided because the two runs were scored under
different eval protocols, and this replaces it with four cells measured under
one protocol by `compare_checkpoints.py`, so nothing depends on either run's
training history.

Large protocol, k=60, T=0.6, 2,321 fingerprint-unseen queries common to all
four cells:

| rec@60 (all) | 8,508 steps | 21,117 steps |
| --- | --- | --- |
| 8.0M | 0.5205 | 0.8427 |
| 15.1M | **0.6127** | 0.8703 |
| deficit ratio | **0.808** | 0.825 |

The registration predicted 0.6045. Measured 0.6127, high by 0.82 points on a
quantity whose binomial SE is about one point. **CONFIRMED**, and the 35+
clause too: predicted 0.4564, measured 0.4629.

The second clause also passes — the step exponent comes back 1.204 against the
8.0M row's 1.226, and 1.103 against 1.117 at 35+, both inside the registered
0.10. It should be recorded that this is not independent evidence. If the
deficit ratio is constant in steps, then `c` is *algebraically* identical
between the two rows, because `c` is built from the same two deficits whose
ratio clause 1 already tested. Two clauses, one fact. The same criticism night
5's write-up made of the b-divided-by-rec confirmation applies here to my own
registration.

### The registered mechanism is falsified, and decisively

The third reading, put on record at 18:30 before the number existed, predicted
that capacity should pay *more* where there is more repetition to exploit — so
the ratio at 8,508 steps (1.21 passes) should come out above the 0.825 measured
at 21,117 steps (3.00 passes). It came out **below**, at 0.808, and a paired
bootstrap over queries puts that at [0.778, 0.837], which excludes 0.96 and
excludes 0.825's point value as well. The sign is wrong and the magnitude is
small.

So "part of what extra parameters buy is a better fit to molecules already
seen" earns no support here. What the four cells say instead is that the
deficit ratio does not depend on training length at all:

| band | n | ratio @ 8,508 | ratio @ 21,117 | difference (paired) |
| --- | --- | --- | --- | --- |
| all | 2,321 | 0.808 [0.778, 0.837] | 0.825 [0.766, 0.888] | −0.017 [−0.088, +0.048] |
| 30–34 | 1,189 | 0.746 [0.690, 0.802] | 0.757 [0.650, 0.874] | −0.011 [−0.140, +0.110] |
| 35–39 | 625 | 0.777 [0.716, 0.836] | 0.845 [0.701, 1.024] | −0.069 [−0.255, +0.091] |
| 40–49 | 380 | 0.853 [0.807, 0.898] | 0.815 [0.705, 0.932] | +0.038 [−0.087, +0.160] |
| 50+ | 127 | 0.983 [0.933, 1.035] | 0.914 [0.816, 1.015] | +0.069 [−0.042, +0.179] |

Every difference straddles zero. Across a 2.48-fold change in training length
and a 2.5-fold change in repetition regime, the fraction of the recovery
deficit that capacity removes is the same number.

### The same comparison is worth +1.33 points or +7.11 points

This is the part worth taking out of the weekend. On the common protocol at
k=20, the identical pair of architectures compared at the identical temperature
gives:

| steps | 8.0M rec@20 | 15.1M rec@20 | gain | deficit ratio |
| --- | --- | --- | --- | --- |
| 8,508 | 0.6825 | 0.7536 | **+7.11 pts** | 0.776 |
| 21,117 | 0.9131 | 0.9264 | **+1.33 pts** | 0.847 |

A 5.3-fold difference in the headline number, from a multiplicative cut that
barely moves. "Capacity is worth N points" is therefore not a property of
capacity; it is a property of how long the baseline trained. Block 3's +1.33
was never a floor or a ceiling — it was a reading taken where the deficit
happened to be small.

The ranking-not-coverage finding from block 3 reproduces at the shorter budget
and more strongly. The 15.1M model proposes *fewer* distinct molecules per
query (20.69 against 22.22), fills less of its budget (0.701 against 0.792),
and still wins by +7.67 points at rec@1 and +8.03 at rec@20 on a paired
first-k-slots count (296 up / 146 down, p = 8e-13; 219 up / 62 down, p = 1e-21,
n = 1,956). Capacity buys ordering, not reach, at both step counts.

### What the new cell actually overturns: the cut is not uniform at 50+

Block 3 described capacity as a flat ~17% cut in the deficit, uniform across 32
size-by-budget cells spanning 0.76–0.96. The new row has enough power to test
that properly, and it fails. Fitting one pooled ratio and asking each band to
match it:

| band | n | 8.0M | 15.1M | uniform-cut prediction | residual | z | discordant pairs | p |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 30–34 | 1,189 | 0.6720 | 0.7553 | 0.7351 | +2.02 | +1.62 | 136 up / 37 dn | <0.001 |
| 35–39 | 625 | 0.4912 | 0.6048 | 0.5890 | +1.58 | +0.81 | 94 up / 23 dn | <0.001 |
| 40–49 | 380 | 0.2474 | 0.3579 | 0.3921 | −3.42 | −1.39 | 47 up / 5 dn | <0.001 |
| 50+ | 127 | 0.0630 | 0.0787 | 0.2432 | **−16.44** | **−6.88** | 6 up / 4 dn | 0.754 |

Three bands fit inside 1.6 SE. The fourth misses by sixteen and a half points
at z = −6.9, and the reason is plain in the last two columns: at 50+ heavy
atoms the 15.1M model recovers 6 molecules the 8.0M model missed and loses 4 it
had, which is nothing at all (p = 0.75). **Above about 50 heavy atoms, doubling
the parameters buys no measurable recovery.**

Block 3 could not have seen this. At 21,117 steps the same band sits at 0.4488
recovery, so the uniform cut predicts a 9.6-point gain with a 4.4-point SE and
the residual is −4.94, z = −1.11 — consistent with the law and consistent with
no gain, simultaneously. At 8,508 steps the band sits at 0.0630, the predicted
gain is 18 points, the SE is 2.4, and the two hypotheses finally separate. The
new cell is informative about the *law* precisely because its baseline is
worse: a multiplicative claim is hardest to satisfy where the deficit is
largest, and the undertrained row is where the deficits are large.

So the uniform-cut description survives over 30–49 heavy atoms, at two training
lengths, and should be stated with that restriction from now on rather than as
a property of the model pair. The "uniform across 32 cells" claim in block 3 is
withdrawn as stated; the cells were there, the power was not.

### What block 3's registration got right and wrong, finally

Both standing clauses confirmed, one of them vacuously. The mechanism I added
on top of them was falsified with the sign reversed. And the finding that
replaces it — no step dependence in the ratio, no capacity gain at all above 50
heavy atoms — was not registered by anyone, which is the ordinary outcome of
building a 2x2 for one reason and reading all four cells.

### A correction found while adding the new cells to the b-divided-by-rec table

Adding `medium_1m_8k` to the `b ÷ rec@60` table surfaced a defect in the
README's own wording, not in any measurement. The sentence read "the exponent
at 35+ rises from 0.303 to 0.343, and `b ÷ rec@60` goes with it, from 0.366 to
0.380". Those two ratios are correct, and they are built from the **full-range**
`b` (0.2815 and 0.3049). The exponents quoted immediately before them are the
**k ≤ 20 refits**. Numerator and quoted exponent were from different columns in
one sentence — the exact conflation night 5 warned about after scoring the
0.303 threshold against the wrong column.

Fixed by stating one convention and giving both. Full-range `b ÷ rec@60` at 35+
across the eight cells that now exist runs 0.320 to 0.380; in the k ≤ 20
convention the same cells run 0.290 to 0.427. The conclusion is unchanged —
proportionality to within about ±9%, no monotone trend in recovery, four
interventions and none of them bending the curve — but the two ranges are not
interchangeable and neither is a subset of the other.

Worth noting which cells moved the range: `small_full` and `medium_1m_8k`, at
0.321 and 0.320, are the two newest and the two most undertrained, and they sit
below the 0.334–0.366 band that six cells supported. That is a widening, not a
trend; the ratio is not monotone in recovery across the eight.

## Stage 11 — registering a powered test of the 50+ null, before it runs

The strongest new claim of stage 10 is also its weakest-powered: "above about
50 heavy atoms, doubling the parameters buys no measurable recovery" rests on
127 queries and a 6-up/4-down discordant split. That is enough to reject the
uniform cut's 18-point prediction and nowhere near enough to measure what the
true gain is. It should not sit in the README at that power when the fix costs
no training at all.

The clean pool holds **1,068** molecules at 50+ heavy atoms, against the 127
the 30+ protocol happened to draw. So the test is `compare_checkpoints.py` with
`--min-heavy-atoms 50 --eval-n 1000 --eval-k 60` at T=0.6 on the two 8,508-step
checkpoints — the pair where the null was found, and the pair with the power,
because its 50+ deficit is 0.937 rather than the 21,117-step pair's 0.551.

This is a **new protocol**: a different query set from the 30+ large protocol,
so its absolute numbers are not comparable with any table above. What it
measures is a paired difference between two models on identical queries, which
needs no such comparability.

**Pre-registered, 02:40 Monday, before the run starts.** From the 127-query
read, `small_1m_matched` should land near 0.063 and `medium_1m_8k` near 0.079,
and the paired difference near **+1.6 points**. With about 1,000 queries the
discordant count should be roughly 48 up and 32 down, which puts the SE of the
paired difference near 1.0 point.

- **CONFIRMED** if the paired difference is **below +5.0 points**. That rejects
  the uniform cut's +18.0-point prediction at 50+ by a wide margin and makes
  the stage-10 finding safe to state: the multiplicative description of
  capacity holds over 30–49 heavy atoms and fails above 50.
- **FALSIFIED** if the difference is **above +5.0 points**, which would mean the
  n=127 null was a sampling accident, the uniform cut survives at 50+ after
  all, and stage 10's withdrawal of "uniform across 32 cells" was itself
  premature and has to be un-withdrawn.

A secondary question is registered with an explicit expectation of failure:
whether the gain at 50+ is distinguishable from **zero**. At the predicted
effect size and n it probably is not — the registered CI straddles zero — so
the honest output is an interval on a small positive number, not a second null.
Recording that in advance so that an inconclusive result cannot be presented
afterwards as evidence for zero.
