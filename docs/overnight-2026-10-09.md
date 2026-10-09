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

*(appended after the runs completed — see below.)*

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
