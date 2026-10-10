# Night 2 — 2026-10-10 into 2026-10-11

## Why this night happened

The night-1 write-up led with this:

> **`recovery@20` 0.5892 → 0.8927 for 10× the data at the same parameter count.**

The table behind that sentence is correct. The sentence is not. The two runs it
compares differed in **two** things:

| run | train molecules | optimiser steps |
|---|---|---|
| `small_100k` | 90,682 | 8,508 |
| `small_1m` | 909,800 | **21,117** |

Ten times the data *and* two and a half times the compute. Attributing the whole
30-point gap to data was a claim the experiment could not support.
`configs/small_1m.yaml` had written down, before the run, that its curve should
be read at step ~8,500 for exactly this reason; the write-up quoted the endpoint
instead.

This night ran the missing control — the same 100k shard, the same 8M-parameter
model, the same learning rate, the same cosine horizon, for the same 21,117
steps — plus a full-ChEMBL run at 8,508 steps. `configs/small_100k_long.yaml`
committed in advance to how the result would be read:

> If it plateaus near 0.60 then data is what makes extra compute pay, and the
> conclusion survives restatement. If it climbs to 0.80 then compute was the
> lever and the claim was wrong.

It climbed to 0.8384.

## The runs

```
stage 1  build full shard   16:41 -> 16:52   2,091,106 mols, 109,152 excluded
stage 2  small_100k_long    16:52 -> 01:01   21,117 steps, 30 epochs, completed
stage 3  small_full         01:01 -> 03:51   8,508 steps, 1st epoch, completed
stage 4  comparison         03:51 -> 04:46
stage 5  scaffolds          04:46 -> 05:14
stage 6  small_1m_matched   SKIPPED -- 209 min left, needed 294
stage 6' small_1m_matched   05:23 -> 08:28   8,508 steps, 1.2 epochs, completed
stage 9' scoring (--only)   08:24 -> 09:19   stage-4 protocol, one checkpoint
```

The full ChEMBL shard is 2,200,258 unique standardised molecules minus the
109,152 held out by `prepare --exclude`, split 1,881,996 / 104,555 / 104,555.
Every holdout was verified absent from all three splits.

## The headline

One common protocol: 2,000 held-out molecules (1,956 fingerprint-unseen) in
**no** model's training set, `fp_unseen` computed against the union of all
1,989,502 training fingerprints, fixed seed, molecule budget, identical k.
**These are the only numbers here that compare across runs.**

| run | params | steps | data | rec@1 | rec@5 | **rec@20** | struct@20 | validity | uniq/q | tanimoto | hit rank |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `small_1m` | 7.96M | 21,117 | 909,800 | 0.5302 | 0.7996 | **0.8926** | 0.8834 | 0.903 | 12.6 | 0.974 | 1.72 |
| `small_100k_long` | 7.95M | 21,117 | 90,682 | 0.4519 | 0.7214 | **0.8384** | 0.8252 | 0.887 | 14.2 | 0.961 | 2.23 |
| `small_full` | 7.96M | 8,508 | 1,881,996 | 0.3113 | 0.5808 | **0.7347** | 0.7224 | 0.820 | 18.7 | 0.929 | 3.34 |
| `small_1m_matched` | 7.96M | 8,508 | 909,800 | 0.2091 | 0.4755 | **0.6299** | 0.6161 | 0.794 | 20.4 | 0.898 | 4.08 |
| `small_100k` | 7.95M | 8,508 | 90,682 | 0.1800 | 0.4182 | **0.5890** | 0.5787 | 0.794 | 21.3 | 0.884 | 4.69 |
| `medium_1m` | 15.12M | 2,500 | 909,800 | 0.0527 | 0.1554 | **0.2735** | 0.2669 | 0.520 | 18.7 | 0.722 | 6.75 |

This table contains **two** clean matched-compute data comparisons, because
`small_100k` and `small_full` both ran exactly 8,508 steps with their cosine
horizons set to 8,508, and `small_100k_long` and `small_1m` both ran exactly
21,117 with horizons of 21,117. All four completed their schedules.

### Corpus size, at fixed compute: not a single variable

> **This section originally reported "data is worth ~1.45× error reduction per
> decade", fitted through two points. A third point, predicted in advance and
> measured afterwards, falsified it. The retraction and what replaces it are
> below; the original fit was 1.39×/decade at 8,508 steps and 1.50× at 21,117.**

Three runs at 8,508 steps, all with cosine horizons of 8,508, all scored under
the common protocol:

| corpus | passes over each molecule | rec@20 | error ratio to previous | per decade |
|---|---|---|---|---|
| 90,682 | 12.01 | 0.5890 | — | — |
| 909,800 | 1.20 | **0.6299** | 1.111× | 1.11× |
| 1,881,996 | 0.58 | 0.7347 | 1.395× | **2.87×** |

The curve is **convex**: returns to corpus size *accelerate*. No plausible
data-scaling law does that, and the obvious candidate explanation fails — the
full-shard run sees only 1,089,024 distinct molecules against the 1M run's
909,800, a factor of 1.20, for +10.5 points.

The uncontrolled variable is in the third column, and it is not possible to
control it:

    steps × batch_size = corpus_size × passes

That is an identity. At a fixed step budget, corpus size and repetition rate are
perfectly anti-correlated, so every one of these comparisons varies both:

| 8,508 steps | 90,682 → 909,800 → 1,881,996 molecules | 12.0 → 1.2 → 0.58 passes |
| 21,117 steps | 90,682 → 909,800 molecules | 29.8 → 3.0 passes |

**"Data's contribution at fixed compute" is therefore not a well-posed quantity
in this design, and the 1.45×/decade figure should not be used.** In both pairs
the larger corpus also received about ten times fewer passes over each molecule,
and nothing here can say which of the two did the work. The convexity is most
likely the signature of those two effects pulling in opposite directions at
different rates, not a property of data.

Separating them requires varying corpus size while holding *passes* fixed, which
necessarily varies compute — so the clean experiment is a corpus sweep at
constant epochs, not at constant steps, and it costs proportionally more for
each larger shard.

### Compute, at genuinely fixed data

| at fixed data | steps | rec@20 | absolute | error ratio | per decade |
|---|---|---|---|---|---|
| 90,682 molecules | 8,508 → 21,117 (2.48×) | 0.5890 → 0.8384 | +24.9 pts | 2.543× | **10.6×** |

This one is clean: the corpus is identical and only the step budget moves (the
pass count rises with it, which is what "more compute on the same data" means).
**+24.9 points from compute alone on 90,682 molecules.**

That is enough to settle the night-1 question even without a usable data axis.
Night 1 compared 100k@8,508 against 1M@21,117 and credited the whole 30.4-point
gap to 10× data; 24.9 of those points are available from compute on the small
corpus alone, so the attribution was wrong regardless of how the remainder
divides.

It also explains night 1's "3.81× per decade of data": that pair is an error
ratio of 3.83× over one decade, which is the figure that document fitted and
extrapolated to 0.993 at PubChem scale. **Both that extrapolation and the 0.949
I replaced it with are withdrawn** — the first was compute wearing data's label,
the second rested on a two-point fit that a third point has now broken. There is
currently no defensible scaling law here in the corpus direction.

### Novel scaffolds: that was compute too

| run | seen rec@20 | novel rec@20 | penalty |
|---|---|---|---|
| `small_1m` | 0.9043 | 0.8421 | 6.2 pts |
| `small_100k_long` | 0.8652 | 0.8236 | **4.2 pts** |
| `small_full` | 0.7382 | 0.6811 | 5.7 pts |
| `small_100k` | 0.6740 | 0.5471 | 12.7 pts |
| `medium_1m` | 0.2912 | 0.2065 | 8.5 pts |

Night 1 said:

> The novel-scaffold penalty **halves** with 10× data, 12.7 points to 6.2 […]
> More data did not merely let the model interpolate better.

Also wrong, and this one is worse, because the correction inverts the ranking:
the **lowest** penalty of any run belongs to `small_100k_long`, which has the
*least* data of the three strong runs. On an identical 90,682 molecules the
penalty fell 12.7 → 4.2 points with nothing changed but training length. Novel
chemotypes are not a data-coverage problem in this range; they get better as the
model gets better, by whatever means.

The conclusion night 1 drew from this — that the model is not merely memorising
— still stands, and is in fact strengthened: a model that has seen 90,682
molecules thirty times over recovers 82% of fingerprints whose Bemis–Murcko
scaffold it has never encountered.

### Diversity tracks skill, monotonically

Across all five trained runs, distinct valid molecules per query falls
monotonically as recovery rises:

| rec@20 | 0.589 | 0.630 | 0.735 | 0.838 | 0.893 |
|---|---|---|---|---|---|
| distinct valid / query | 21.3 | 20.4 | 18.7 | 14.2 | 12.6 |

Night 1 saw two of these points and read it as "extra data bought confidence,
not diversity". With five it is clearly a property of model quality by whatever
route — the 0.630 run and the 0.589 run have corpora differing by 10×, and sit
adjacent here. Better models spend less of the budget on respellings of a wrong
answer.

### A prediction, recorded before the measurement

The 8,508-step data axis rests on two points, so "1.39× per decade" is a slope
through two measurements rather than a fit. A third point at 909,800 molecules —
the same 8,508 steps, horizon 8,508 — tests it, and is running as this is
written (`configs/small_1m_matched.yaml`, launched 05:23).

The two-point fit predicts **`rec@20` = 0.705** for that run, under the same
common protocol. Writing it down first, because quoting an endpoint after seeing
it is precisely how the night-1 claim went wrong:

| outcome | reading |
|---|---|
| 0.695–0.715 | log-linear holds; 1.39×/decade is a fit, not a coincidence |
| above ~0.725 | data's return is not log-linear; the 100k point is anomalously low and the full-shard comparison understated data |
| below ~0.685 | returns to data diminish faster than log-linear, and the PubChem extrapolation above is optimistic |

Any of the three is informative.

**Result: 0.6299.** Low by 7.5 points, outside the band, so the third reading
applies — returns in the corpus direction are not log-linear here. Working out
why is what produced the retraction above: the prediction assumed corpus size
was an axis that could be isolated at fixed compute, and it cannot be.

The prediction failing is the only reason that was found. A two-point slope
reported as a law is the same shape of error as night 1's, and it was about to
go out with a PubChem extrapolation attached. Writing the number down first is
what turned a repeat of yesterday's mistake into a result.

## What this night does not answer

- **What corpus size is actually worth.** The design cannot say, for the reason
  above. The experiment that can is a corpus sweep at **constant epochs** rather
  than constant steps — 100k, 1M and full each trained for the same number of
  passes — which costs proportionally more for each larger shard and so needs a
  deliberate compute budget rather than a spare night.
- **Full ChEMBL at 21,117 steps.** No run combines the largest corpus with the
  longest schedule; ~8.3 h, did not fit.
- **Where the step axis saturates.** 10.6×/decade cannot continue; every run
  that finished its schedule was still improving, and 30 epochs of 90k molecules
  showed no overfitting at all. That is probably SMILES randomisation doing its
  job — every epoch is a fresh target string — and it means the cheapest
  untested lever is simply a longer run.
- **Capacity.** Still unanswered; `medium_1m` has never run to completion.
- **Anything about the test split.** All validation.

## Two measurement bugs found on the way

**The molecule budget moved and the old number did not.** Checking whether
`configs/small.yaml`'s run was a clean curve point turned up that it scored
0.5752 at 8,508 steps where the new long run scores 0.6713 at step 9,000 —
same shard, identical model, and *mid*-schedule where the old run had finished
decaying. A mid-schedule run beating a completed one is backwards. The cause is
not compute: that run predates the molecule budget, drawing 20 **strings** per
query where every run since draws until it has 20 distinct **molecules**. Same
weights, larger budget, several points apart. `0.575` is quoted as the thing to
beat in `configs/small_100k_long.yaml`'s own header and in my earlier estimate
that data was "worth about a third" of the gap; both were comparing across
protocols without knowing it. None of the numbers above use it — the common
protocol re-scores every checkpoint itself, which is exactly why it exists.

**Matched steps are not matched learning rates.** `scripts/matched_steps.py`
initially printed `small_full` in a column beside the other two. Its horizon is
8,508 and theirs is 21,117, so at step 7,500 it has finished decaying and they
are mid-decay: it led at every shared step, by an amount that was pure schedule.
The script now derives each run's horizon from its record and suppresses the
per-step table entirely when they differ, printing only the endpoints, which
remain comparable for runs that completed their schedules.

Both guards are the same shape as the `FPConfig` hash the project has had since
day one: refuse to put two numbers side by side until something has checked they
mean the same thing. The fingerprint had that guard. The evaluation protocol and
the learning-rate schedule did not.

## Operational

Three faults in the follow-on driver, all caught before they cost a stage:

1. **`pgrep -f "overnight2.sh"` matched my own watcher shells**, whose command
   lines contain that string. The driver would have waited on a watcher rather
   than on the driver, and stage 6 would never have started. Verified live:
   `pgrep` returned two pids, one a watcher. Now waits on a pid with `kill -0`.
   Third time this pattern has cost something here, so it is gone rather than
   re-checked.
2. **The time guard assumed 4 hours** for a stage that paces at ~2.4, and would
   have skipped a run that fitted. It now reads the preceding stage's recorded
   wall time — same model, same step count, a direct measurement — with 20%
   headroom. In the event it skipped stage 6 anyway, on a measured budget, which
   is the guard working rather than guessing.
3. **No `caffeinate` of its own.** `overnight2.sh`'s is bound to its own pid and
   dies exactly when the follow-on starts working, so stage 6 would have been
   the first run of the night free to be suspended — the failure that cost night
   1 its analysis slot.

Vocabulary size differs by shard (73 tokens for 100k, 119 for the full corpus),
so parameter counts differ by 0.15% between otherwise identical configs
(7,951,945 against 7,963,767). Three orders of magnitude smaller than the effects
measured; noted rather than corrected.
