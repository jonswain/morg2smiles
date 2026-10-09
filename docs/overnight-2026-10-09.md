# Overnight run, 2026-10-09

Fifteen hours of unattended M2 time. This records what was run, why, and what
went wrong — including the two mistakes that would have produced confidently
wrong numbers if they had not been caught.

Results are appended at the end, after the runs finished.

## The question

Phase 1 ended with an 8M-parameter model recovering `recovery@20` 0.5367 on
fingerprint-unseen validation molecules, trained on the 100k ChEMBL shard for
12 epochs. The curve was still rising when the epoch budget ran out, so the
obvious next step was "train it longer". The less obvious and more interesting
question is **where the ceiling actually comes from**: not enough training, not
enough data, or not enough model.

So the night is a two-point experiment on the 1M shard, holding everything else
fixed:

| run | params | data | what it isolates |
|---|---|---|---|
| `small_1m` | 8M | 1M shard | **data** — same architecture and similar step count as the 100k run |
| `medium_1m` | 15M | 1M shard | **capacity** — same data as run 1 |

Because evaluation is now step-based, each run yields a whole curve rather than
one point, so the effect of *longer training* is read off the same runs instead
of needing separate ones.

## Three fixes made first, because they change what the numbers mean

### 1. `recovery@k` was counting strings, not molecules

A model trained on randomised SMILES emits one molecule many ways. Asking the
Phase 1 model to invert aspirin's fingerprint returns 18 exact matches that are
*all aspirin*, written 18 ways. Under the old raw-string deduplication each
respelling occupied a slot in the k budget: 19.7 distinct strings standing in
for 11.5 distinct molecules.

Unparseable candidates no longer consume a slot either. RDKit rejects them
locally and for free, so no caller spending oracle queries would ever spend one
on a string it already knows does not parse.

Measured effect on the unchanged Phase 1 checkpoint: **0.5367 → 0.5508**. I had
predicted 0.60–0.62 by interpolating the recovery curve; the real gain is about
a third of that, which is worth recording as a calibration failure.

A subtlety found while doing it: deduplication must *mark* same-molecule
candidates rather than drop them, or validity's denominator silently changes.
Dropping removes mostly *valid* candidates, which made validity read 0.714
against a true 0.785 — a model looking less valid the more it repeats itself.

### 2. Evaluation was unseeded

Two evaluations of the *same checkpoint* returned 0.5729 and 0.5508. That is
2.2 points, about 1.4 standard errors at n=995, and easily enough to invent or
hide a difference between two training runs. Evaluation now seeds the sampler
(`seed=0`), and the same seed twice agrees exactly.

**Nothing smaller than ~4 points on n≈1000 should be read as a real
difference.** This applies to every number in this document.

### 3. Epochs are the wrong unit at this scale

One epoch of the 1M shard is 7,039 steps and several hours, so epoch-based
evaluation would have given a two- or three-point curve and almost no basis for
choosing a checkpoint. Added `eval_every_steps`, plus a teacher-forced
validation loss as a *diagnostic* — never the selection criterion, which is the
specific mistake the [first attempt](https://github.com/jonswain/morg-to-smiles)
made. Validation loss does break ties in checkpoint selection, which fixes a
real bug: early in a run every evaluation recovers nothing, and without a
tie-break the first one wins and `best.pt` holds the *worst* model in the run.

## The mistake that would have faked a result

The shard subsets are **nested**: 10k, 100k and 1M are drawn in order from one
fixed shuffle, and each computes its own train/valid/test split *within itself*.
So molecules held out of the 100k shard are mostly **inside** the 1M shard's
training set:

```
100k-valid molecules inside 1m-train : 4,540 / 5,037   (90%)
1m-valid  molecules inside 100k-train: 4,522 / 50,050  (9%)
1m-valid  clean of both train sets   : 45,528
```

Comparing a 1M-trained model against the 100k-trained one on either shard's own
validation split would have measured memorisation and flattered the 1M model
badly. `fp_unseen` does not save you here: it is computed against *that shard's*
training set, so a molecule the 1M model trained on is still marked "unseen" when
the mask comes from the 100k shard.

`scripts/compare_checkpoints.py` therefore builds one evaluation set held out of
**every** model's training data, computes `fp_unseen` against the **union** of
all training fingerprints, and scores every checkpoint on identical molecules
with an identical seed, budget and k. The per-run leaderboard rows are not
wrong; they each answer a different question. Only the common-protocol table is
comparable across runs.

## The run that did not fit

`configs/base_1m.yaml` (d_model 384, 6+6 layers, 25.7M params) was the intended
capacity arm. Benchmarked on an idle machine:

| config | params | s/step | 2 epochs of the 1M shard |
|---|---|---|---|
| `small_1m` | 8.0M | **0.90** | 1.8 h per epoch |
| `base_1m` | 25.7M | **6.58** | **20.5–25.7 h** |

7.3× the time for 3.2× the parameters. That is a cliff, not a slope — something
stops fitting and the device starts thrashing, the same class of problem as the
KV-cache thrash fixed in Phase 1. `base_1m` is not an overnight run on this
hardware. It is kept in the repo as a record of what was tried.

`medium_1m` (d_model 320, 5+5, ~15M) replaces it, to find out whether the cliff
is crossed before or after that point.

Two related measurements, both of which contradicted an assumption:

- **`num_workers=4` is slower than `num_workers=0`** (1.05 vs 0.90 s/step). Data
  loading is not the bottleneck, so the RDKit work per batch is not what is
  costing the time. The DataLoader now uses a picklable `partial` instead of a
  lambda so the option at least functions — with a lambda, worker processes die
  on macOS, since spawn cannot pickle it.
- **My first step-time benchmark was wrong by 2×** (0.79 s/step against a real
  1.8). It measured six steps on a 2,000-molecule subset immediately after model
  init: cold caches excluded, warm data. `scripts/bench_step.py` now discards
  warmup steps and runs against the real shard.

## Guards against the night failing

Unattended runs fail differently from supervised ones: nobody notices for hours.

- **`TrainConfig.max_hours`** — a hard wall-clock cap checked at each
  evaluation. Step-time estimates here have been wrong by 2× in *both*
  directions. Capping a run costs the tail of one curve; overrunning costs the
  analysis that was supposed to follow it.
- **A deadline-aware driver** (`scripts/overnight.sh`) — training stages are
  skipped if there is not enough time left for the analysis stages. An
  unanalysed checkpoint is worth much less than an analysed one.
- **Fail-soft stages** — each stage logs separately and a stage that dies does
  not take the rest of the night with it.
- **Both analysis scripts smoke-tested** at tiny `--eval-n` before the night
  started, because a stage-4 crash at 06:00 is a wasted slot.

## What was run

```
stage 1  small_1m    8M params,  1M shard, 3 epochs, capped at 8.5 h
stage 2  medium_1m  15M params,  1M shard, 2 epochs, capped at 3.5 h
stage 3  compare_checkpoints.py  every checkpoint, one common protocol
stage 4  scaffold_probe.py       novel-chemotype generalisation
```

Test splits were not touched. Everything here is validation data.

## Results

### Operational: two guards that did not hold

Written up before the numbers because it is the more transferable finding.

**`max_hours` measured the wrong clock.** The cap was built on
`time.perf_counter()`, which on macOS does not advance while the process is
suspended — and an unattended overnight run is suspended repeatedly. Stage 1
recorded **6.90 h of `perf_counter` time across 10.78 h of real time**, a 36%
shortfall, so an 8.5 h cap never fired and the stage ran 2.3 h past its slot.

```
step 18,000   perf_counter 6.90 h   wall clock 10.78 h
```

`perf_counter` is the right clock for per-step rates and the wrong one for a
deadline. The budget now uses `time.time()`. `caffeinate -dimsu -w <driver pid>`
holds the machine awake for the rest of the night, which stops the time loss
rather than merely measuring it correctly.

The irony is worth recording: this is the guard that existed *specifically* so
an unattended stage could not eat the analysis window, and it was measuring the
wrong quantity from the moment it was written. A cap that is never exercised in
testing is an assertion, not a guard.

**The driver's own guard is too weak.** `have_time_for_training` checks only
that 105 minutes remain; it never compares that against the stage's actual cap,
so it would launch a 3.5 h stage with 2 h left. It could not be fixed in place:
`overnight.sh` was executing, and bash reads a script incrementally by byte
offset, so editing a running script can make the shell execute garbage. The
protection was applied through `configs/medium_1m.yaml` instead — which stage
2's fresh interpreter reads — by trimming `max_hours` to 1.75 and halving the
evaluation interval to 500 steps. The cap is only tested at an evaluation, so
the true stop is the cap plus up to one interval; halving the interval halves
the overshoot.

**And one self-inflicted wound.** Three stalls of 905 s, 1008 s and 1037 s
appeared at steps 382–821, the progress bar frozen on a single step. That window
is exactly when a worker-count benchmark of mine was running against the live
job, having loaded the 1M shard and built two models before dying. Some of that
lost wall time was suspension rather than contention, so the benchmark is not
the whole story — but the rule now has evidence behind it: **this machine runs
one job.** The earlier version of that rule was about getting clean benchmark
numbers; it cuts both ways.

All four stages exited 0, finishing with 35 minutes of the deadline to spare.

```
stage 1  small_1m    18:42 -> 06:28   3 epochs, 21,117 steps, completed schedule
stage 2  medium_1m   06:28 -> 08:27   capped at 2,500 steps by max_hours 1.75
stage 3  comparison  08:27 -> 08:56
stage 4  scaffolds   08:56 -> 09:10
```

### The headline: data was the ceiling

One common protocol, 2,000 held-out molecules (1,967 fingerprint-unseen) drawn
from neither model's training set, `fp_unseen` computed against the union of all
909,800 training fingerprints, identical seed, budget and k. **These are the only
numbers in this document that compare across runs.**

| run | params | trained | rec@1 | rec@5 | **rec@20** | struct@20 | validity | mean hit rank |
|---|---|---|---|---|---|---|---|---|
| `small_100k` | 8.0M | 12 epochs | 0.1805 | 0.4179 | **0.5892** | 0.5705 | 0.794 | 4.68 |
| `small_1m` | 8.0M | 3 epochs | 0.5308 | 0.7997 | **0.8927** | 0.8760 | 0.903 | 1.73 |
| `medium_1m` | 15.1M | 2,500 steps | 0.0524 | 0.1551 | 0.2745 | 0.2645 | 0.522 | 6.72 |

**`recovery@20` 0.5892 → 0.8927 for 10× the data at the same parameter count.**
`recovery@1` nearly tripled, 0.18 → 0.53: the 1M model usually gets it right on
the *first* sample, and its mean hit rank of 1.73 says that when it succeeds it
succeeds almost immediately. Mean best Tanimoto rose 0.885 → 0.974, so even the
failures are near misses now.

I had predicted the gap would *narrow* under the common protocol, on the
reasoning that the per-run subsamples flattered the 1M model. It did not. Both
models scored higher here than on their own subsamples (0.5508 → 0.5892 and
0.8742 → 0.8927) and the gap was unchanged. The 500-molecule in-training
subsamples were pessimistic, not optimistic, and I had the direction backwards.

A second-order finding, visible only because duplicates are marked rather than
dropped: the 1M model's duplicate rate is **0.565 against 0.246**, and it yields
12.8 distinct valid molecules per query where the 100k model yields 21.3. It
explores *less* and succeeds *more* — the extra data bought confidence, not
diversity. For a k-budget metric that is close to free: the budget stops being
spent on respellings of a wrong answer.

### Capacity is not the binding constraint — and the cliff moved

`medium_1m` only reached step 2,500, so its recovery number is an early-curve
point and not capacity evidence. It is in the table for completeness, not as a
result. What it does settle is where the performance cliff sits:

| params | s/step | ratio to previous |
|---|---|---|
| 8.0M | 1.37 | — |
| 15.1M | 2.66 | 1.89× params → **1.94× time** |
| 25.7M | 6.58 | 1.70× params → **2.47× time** |

Scaling is **linear to 15M** and superlinear beyond it. The cliff is between 15M
and 26M, not below 15M — so `medium_1m` was a feasible full-length overnight run
all along, and the planning decision to replace `base_1m` with it was right for
the wrong reason. Two measurements were extrapolated into a "cliff" that three
measurements show to be a knee somewhere further out. Had the third point been
measured before planning, stage 2 would have been a full 15M run.

At matched *steps* the 15M model is marginally ahead of the 8M one (0.2745 at
2,500 steps against roughly 0.22 interpolated), which is inside the noise floor.
At matched *wall clock* it is far behind: 8M reaches step 5,000 and about 0.50 in
the same time. On this hardware the next doubling is better spent on steps or
data than on parameters.

### Novel chemotypes: more data generalises, it does not just memorise

Validation molecules sliced by whether their Bemis–Murcko scaffold appears
anywhere in training, reported over fingerprint-unseen queries only, so the two
slices differ in scaffold novelty and nothing else.

| run | scaffold_seen rec@20 | scaffold_novel rec@20 | penalty |
|---|---|---|---|
| `small_100k` | 0.6740 | 0.5471 | **+0.1270** |
| `small_1m` | 0.9043 | 0.8421 | **+0.0622** |
| `medium_1m` | 0.2912 | 0.2065 | +0.0848 |

This is the result I would least have predicted. The novel-scaffold penalty
**halves** with 10× data, 12.7 points to 6.2, and novel-scaffold recovery rises
0.5471 → 0.8421. More data did not merely let the model interpolate better
inside chemistry it knows; it made the model *better at chemistry it has never
seen*. A memorisation story predicts the opposite — a larger training set covers
more scaffolds, so the novel slice should get harder and the penalty should grow.

`small_1m` recovers 84% of fingerprints whose scaffold appears nowhere in
909,800 training molecules. That is the number that speaks to behaviour on
chemistry a user actually brings.

### What the night did not answer

- **Full-length 15M.** Stage 2 was a 1.75 h stub. The capacity arm is open, and
  it is now known to be affordable: ~5.2 h per epoch at 2.66 s/step.
- **Where `small_1m` tops out.** It finished its schedule still improving, if
  barely — the last three increments were +1.4, +0.4, +0.4 points. Converged for
  practical purposes, but the asymptote was not reached.
- **The 10M-molecule question.** 100k → 1M bought 30 points. Nothing here says
  whether 1M → 10M buys another 10 or another 1.
