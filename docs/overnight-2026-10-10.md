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
stage 6  small_1m_matched   SKIPPED -- 209 min left, needed 294 (rerun 05:23, below)
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
| `small_100k` | 7.95M | 8,508 | 90,682 | 0.1800 | 0.4182 | **0.5890** | 0.5787 | 0.794 | 21.3 | 0.884 | 4.69 |
| `medium_1m` | 15.12M | 2,500 | 909,800 | 0.0527 | 0.1554 | **0.2735** | 0.2669 | 0.520 | 18.7 | 0.722 | 6.75 |

This table contains **two** clean matched-compute data comparisons, because
`small_100k` and `small_full` both ran exactly 8,508 steps with their cosine
horizons set to 8,508, and `small_100k_long` and `small_1m` both ran exactly
21,117 with horizons of 21,117. All four completed their schedules.

### Data is worth ~1.45× error reduction per decade

| at fixed compute | data | rec@20 | absolute | error ratio | per decade |
|---|---|---|---|---|---|
| 8,508 steps | 90,682 → 1,881,996 (20.8×) | 0.5890 → 0.7347 | +14.6 pts | 1.549× | **1.39×** |
| 21,117 steps | 90,682 → 909,800 (10.0×) | 0.8384 → 0.8926 | +5.4 pts | 1.505× | **1.50×** |

Two independent measurements, two different shard pairs, two different compute
budgets, and they agree to within 0.11× per decade. In *absolute* points they
look nothing alike — +14.6 against +5.4 — and that difference is an artifact of
how close 0.84 is to the ceiling, not a change in how much data is worth. Error
reduction is the right scale for this metric and the absolute-points framing is
what made night 1's number look so large.

### Compute is worth ~10.6× per decade in this regime

| at fixed data | steps | rec@20 | absolute | error ratio | per decade |
|---|---|---|---|---|---|
| 90,682 molecules | 8,508 → 21,117 (2.48×) | 0.5890 → 0.8384 | +24.9 pts | 2.543× | **10.6×** |

An order of magnitude steeper than the data axis. **Of the 30.4-point gap night
1 attributed to data, 5.4 points are data and 24.9 are compute.**

And the confounded pair reproduces night 1's "scaling law" exactly: 100k@8,508
against 1M@21,117 is an error ratio of 3.83× across one decade of data, which is
the 3.81×/decade that document fitted and extrapolated from. That fit was
compute's contribution wearing data's label. Corrected to 1.45×/decade, the
extrapolation changes a great deal:

| train molecules | night 1 predicted | corrected |
|---|---|---|
| 9.1M | 0.936 | 0.926 |
| 91M (PubChem scale) | **0.993** | **0.949** |

The PubChem ambition survives but stops being a near-solve. Getting the last few
points will be a compute and architecture problem, not a corpus problem.

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

Across all five runs, distinct valid molecules per query falls as recovery
rises: 21.3 → 18.7 → 14.2 → 12.6 for 0.589 → 0.735 → 0.838 → 0.893. Night 1 saw
this as two points and read it as "extra data bought confidence, not diversity".
With five points it is clearly a property of model quality, not of data. Better
models spend less of the budget on respellings of a wrong answer.

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

Any of the three is informative. The result is in the final section.

## What this night does not answer

- **Full ChEMBL at 21,117 steps.** The data axis has two points at 8,508 steps
  and two at 21,117, but no run combines the largest corpus with the longest
  schedule. That run is ~8.3 h and did not fit tonight.
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
