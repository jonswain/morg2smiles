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
