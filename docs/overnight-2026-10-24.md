# Night 8 — 2026-10-24/25: item 2, the step-saturation third point

Item 2 of [next-steps-2026-10-19.md](next-steps-2026-10-19.md), the whole of it.
Launched 10:43 Saturday at git c4b2062, training finished 03:55 Sunday, scored
08:35. 52,500 steps on the 100k shard, complete cosine schedule, stopped on the
step budget rather than the clock, so the pre-registration in
`configs/small_100k_52k.yaml` applies to it.

The headline is that **saturation has appeared, the registered test did not
detect it, and the arm cannot settle the question it was built to settle.**

## The registered number

Pre-registered: rec@60 in **0.88–0.95** on the large protocol at T=0.6, naive
log-log extrapolation 0.93, **below 0.85** counting as the first step saturation
this project has found.

Measured, on the same `band_analysis.py` read as the arm's other two cells
(fp_unseen slice, n = 2,321, generation order, k = 60):

| quantity | value |
|---|---|
| **rec@60, all** | **0.8789** |
| structure@60, all | 0.8656 |
| rec@60, 35+ | 0.8260 |
| rec@60, 50+ (n=127) | 0.5669 |
| structure@60, 35+ | 0.8012 |

**0.8789 is 0.11 points below the registered interval's floor**, and 2.89 points
above the saturation threshold. So the pre-registration returns "miss, low" on
a quantity whose own whole-protocol difference threshold is 1.6 points — the
miss is a sixth of the smallest gap this project is willing to call a gap.

That is a registration defect, and a familiar one: item 1 registered two bands
eight points apart *and named the gap between them uninformative in advance*.
This registration left 0.85–0.88 unnamed, and the result landed in it. Rule 1
of [methodology §7](methodology.md#7-pre-registration-as-practised-here) says
register the interval rather than a point; this night adds that **the intervals
must tile the line, or the reading is made after the fact.**

## Saturation did appear — on the slope, which is where a bounded metric shows it

The level test was the wrong instrument. Recovery is bounded by 1, so "did it
stay below 0.85" conflates *the curve bent* with *the curve ran out of room*.
Read as a slope instead, across the whole arm:

| segment | steps | rec@60 | doublings | points | per doubling |
|---|---|---|---|---|---|
| 1 | 8,508 → 21,117 | 0.4752 → 0.7708 | 1.3115 | +29.56 | **+22.54** |
| 2 | 21,117 → 52,500 | 0.7708 → 0.8789 | 1.3139 | +10.81 | **+8.23** |

Two nearly identical doublings, and the second buys **2.7× less** than the
first. In the deficit form this project fits precisely because it has no
ceiling:

| segment | deficit | factor | exponent c |
|---|---|---|---|
| 1 | 0.5248 → 0.2292 | ×0.4367 | **0.9113** |
| 2 | 0.2292 → 0.1211 | ×0.5282 | **0.7008** |

**The exponent falls, 0.911 → 0.701.** The deficit cannot hit a ceiling, so this
is not the ceiling talking: the law itself weakened by 23% across one doubling
of steps. That is step saturation, measured, and it is the first time this
project has seen it.

Note that this **reverses the in-training trace**, which has the exponent
*climbing* with range (0.703 on `small_100k_long`, 0.843 here) and the
extrapolation error shrinking from −2.64 to −0.43 points. Those traces are
own-shard, 500 molecules, and `step_curve.py` prints its own warning that they
are not comparable across runs with different evaluation cadences — ours ran at
4,000 steps against `small_100k_long`'s 1,500. The held-out protocol is the
authority and it says the opposite. Worth remembering the next time a trace
looks like evidence.

## The confound that stops this arm answering item 4's question

Item 2 exists to pick item 4's step budget, by the rule: *if saturation has not
appeared by 52,500 steps, take 6 passes; if it has, take 3 and report where the
curve bent.* That rule cannot be applied, and the reason is a confound this
project already documented and then walked into again.

**On a fixed corpus the steps axis *is* the passes axis.** `steps × batch =
corpus × passes`, so the three cells of this arm are:

| steps | passes over 90,682 molecules |
|---|---|
| 8,508 | 12.01 |
| 21,117 | 29.81 |
| 52,500 | **74.05** |

The bend was measured between the 30th and the 74th pass over the same 90,682
molecules. **Item 4 runs at 3 to 6 passes over 1,881,996.** Nothing here
distinguishes "optimiser steps saturate" from "the 74th look at a molecule you
have already seen 73 times is worth little", and those two have opposite
implications for a run that never sees a molecule a seventh time.

[§2.9 of results.md](results.md#29-the-corpus-axis-is-convex-and-at-constant-steps-it-is-a-near-cancellation)
states the confound plainly, and item 2's design — a third point on a fixed
100k corpus — reintroduced it. The plan's caveat anticipated the *corpus*
transfer ("this is measured on the 100k corpus, so its transfer to the full
shard is an assumption") but not the *repetition-regime* transfer, which is the
one that bites.

### What the in-regime evidence says instead

The closest thing to item 4's 3 → 6 pass doubling that exists on disk is the
1M-shard pair, and it shows no bend:

| corpus | passes | rec@60 | per doubling |
|---|---|---|---|
| 900,917 | 1.21 → 3.00 | 0.5205 → 0.8427 | **+24.57** |
| 90,682 | 12.01 → 29.81 | 0.4752 → 0.7708 | +22.54 |
| 90,682 | 29.81 → 74.05 | 0.7708 → 0.8789 | +8.23 |

Read down that table: the slope is stable near +23 while repetition is low, and
collapses only in the segment that crosses into the dozens of passes. Item 4 at
3 → 6 passes sits at the *top* of that table, not the bottom.

## Item 4 is also cheaper than the plan says

Re-priced off the right run, the same error as item 2's 18.4 h. The cost model's
"1M/full shard" row uses `small_1m`'s 1.337 s/step, which is the **1M** shard.
The full-shard cells are faster:

| run | shard | steps | s/step | eval cadence |
|---|---|---|---|---|
| `small_full_1p2` | full | 17,772 | **1.056** | 8,886 |
| `small_full` | full | 8,508 | **1.133** | 1,500 |
| `small_1m` | 1m | 21,117 | 1.337 | 1,500 |

At 1.10 s/step, a cadence-matched middle:

| budget | steps | planned | re-priced |
|---|---|---|---|
| 3 passes | 44,112 | 16.4 h | **13.5 h** |
| 6 passes | 88,224 | 32.8 h | **27.0 h** |

The 6-pass option is an overnight-plus, not a weekend.

## What this night changes

1. **Step saturation exists and is measured**, at c falling 0.911 → 0.701
   between the 30th and 74th pass on a fixed corpus. New, and the first bend
   this project has found.
2. **It does not license a 3-pass budget for item 4**, because it was measured
   24 passes past anything item 4 will do. The decision rule is void as written.
3. **`results.md` §2.2 needs the third point**, and the step law needs stating
   as a local slope with a named range rather than a single exponent.
4. **Pre-registered intervals must tile**, or the unnamed gap becomes a
   post-hoc reading. Added to methodology §7.
5. **Price a run off a cell matching its shard, fingerprint and cadence** — this
   is the second time in two days that a plan figure came from the wrong run.

## Stage log

| stage | what | outcome |
|---|---|---|
| 1 | train 52,500 steps | 17.13 h, 1.175 s/step, step budget reached |
| 2 | score k=60, large protocol | **failed first pass**, see below; rec@60 0.8789 on rerun |
| 3 | band tables, recovery and structure | both written |
| 4 | step exponent refit | written, and contradicted by stage 2 |

Stage 2 failed two seconds after the 17-hour training finished, and sat failed
for three hours: `RUNS` in `compare_checkpoints.py` is an explicit
checkpoint → shard registry and `small_100k_52k` was never added to it, so
`--only small_100k_52k` could not resolve. The driver was written without that
line. Fixed in f8ef565 and rerun at 07:15; the shard was already present via
`small_100k_long`, so the protocol draw and `fp_unseen` union are unchanged and
the arm's other cells remain the right comparisons. **A new checkpoint needs a
`RUNS` entry in the same commit as its config** — the driver's idempotent-skip
pattern saved the training but not the night.
