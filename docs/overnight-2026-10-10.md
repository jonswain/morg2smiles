# Night 2 — 2026-10-10 into 2026-10-11

## Why this night happened

The night-1 write-up led with this:

> **`recovery@20` 0.5892 → 0.8927 for 10× the data at the same parameter count.**

The table behind that sentence is correct. The sentence is not. The two runs it
compares differed in **two** things, not one:

| run | train molecules | optimiser steps |
|---|---|---|
| `small_100k` | 90,682 | 8,508 |
| `small_1m` | 909,800 | **21,117** |

Ten times the data *and* two and a half times the compute. Attributing the whole
30-point gap to data was a claim the experiment could not support, and I made it
anyway. `configs/small_1m.yaml` had even written down, before the run, that its
curve should be read at step ~8,500 for exactly this reason; the write-up quoted
the endpoint instead.

So this night ran the control that was missing: **the same 100k shard, the same
8M-parameter model, the same learning rate and the same cosine horizon, for the
same 21,117 steps.** `configs/small_100k_long.yaml` committed in advance to how
the result would be read:

> If it plateaus near 0.60 then data is what makes extra compute pay, and the
> conclusion survives restatement. If it climbs to 0.80 then compute was the
> lever and the claim was wrong.

## The answer: compute was the lever

It climbed to **0.8257**.

| step | 100k (90,682 molecules) | 1M (909,800 molecules) |
|---|---|---|
| 1,500 | 0.0361 | 0.0325 |
| 3,000 | 0.2425 | 0.3387 |
| 4,500 | 0.4489 | 0.4787 |
| 6,000 | 0.5471 | 0.5700 |
| 7,500 | 0.6152 | 0.6045 |
| 9,000 | 0.6713 | 0.7181 |
| 10,500 | 0.7014 | 0.7606 |
| 12,000 | 0.7295 | 0.7870 |
| 13,500 | 0.7475 | 0.8012 |
| 15,000 | 0.7856 | 0.7667 |
| 16,500 | 0.8096 | 0.8438 |
| 18,000 | 0.8096 | 0.8519 |
| 19,500 | 0.8216 | 0.8661 |
| 21,000 | 0.8236 | 0.8702 |
| **21,117** | **0.8257** | **0.8742** |

`rec@20`, `fp_unseen`, each run against its own shard's validation subsample, one
protocol, 30 epochs against 3. (The 1M column's dip at 15,000 is its
epoch-3 boundary, visible in night 1's curve too.)

**Ten times the data is worth 4.9 points, not 30.** The 100k shard — 90,682
molecules, seen thirty times over — gets within five points of a corpus ten
times its size, given the same number of optimiser steps. Of the ~30-point gap
reported yesterday, roughly five points are data and the rest was compute.

The claim as published was wrong, and wrong in the direction that made the
result sound more interesting than it is. "More data is the ceiling" is a
finding; "train it for longer" is not.

### What this does not say

- **Data still helps, monotonically.** 4.9 points at `rec@20` is not noise, and
  the 1M run is ahead at every step after 3,000. The ordering was never in
  question; only the size of the effect.
- **It does not say data is irrelevant at scale.** Both runs are nowhere near
  convergence and the 100k curve is still rising at step 21,117 (0.8236 →
  0.8257 over its last 117 steps, having gained 4 points over the last 6,000).
  Thirty epochs of 90k molecules has not yet started to overfit, which is
  itself surprising and is probably the SMILES randomisation doing its job: the
  model sees a different string for the same molecule every epoch, so "thirty
  epochs" is thirty *distinct* targets per molecule, not thirty repeats.
- **It is not a statement about the test set.** Everything above is validation.

## A measurement bug found on the way

Checking whether `configs/small.yaml`'s 100k run was a clean first point for a
fixed-compute curve turned up something worse than a confound. That run scored
**0.5752** at 8,508 steps. The new long 100k run scores **0.6713** at step
9,000 — same shard, identical model config, and *mid*-schedule where the old run
had finished its cosine decay. A mid-schedule run beating a completed one is
backwards.

The cause is not compute. The old run predates the molecule budget: it drew 20
**strings** per query, where every run since draws until it has 20 distinct
**molecules** (40 samples). Same weights, larger budget, several points apart.

That number, `0.575`, is quoted in `configs/small_100k_long.yaml`'s own header as
the thing to beat, and in my earlier estimate that "data is worth about a third"
of the gap. Both were comparing across evaluation protocols without knowing it.
The estimate above (4.9 points) does not use it: it compares two runs that were
scored identically.

`scripts/matched_steps.py` now refuses to put two runs in adjacent columns
unless their evaluation protocol signature matches, and refuses runs whose
history has no step field at all. The project already hashes `FPConfig` into
every artefact for precisely this reason; the evaluation protocol deserved the
same treatment and did not have it.

## Operational

Three faults in the follow-on driver, all caught before they cost a stage:

1. **`pgrep -f "overnight2.sh"` matched my own watcher shells**, whose command
   lines contain that string. The driver would have waited on a watcher instead
   of on the driver, and stage 6 would never have started. Verified live:
   `pgrep` returned two pids, one of them a watcher. Now waits on a pid with
   `kill -0`. This is the third time this pattern has cost something here, so it
   is gone rather than re-checked.
2. **The time guard assumed 4 hours** for a stage that paces at ~2.4, and would
   have skipped a run that fitted. It now reads the preceding stage's recorded
   wall time — same model, same step count, so a direct measurement — with 20%
   headroom and the old pessimistic figure as fallback.
3. **No `caffeinate` of its own.** `overnight2.sh`'s is bound to its own pid and
   dies exactly when the follow-on starts working, so stage 6 would have been
   the first run of the night free to be suspended mid-flight — the failure that
   cost night 1 its analysis slot.

Vocabulary size differs by shard (73 tokens for 100k, 119 for the full corpus),
so parameter counts differ by 0.15% between otherwise identical configs
(7,951,945 against 7,963,767). Noted rather than corrected; it is three orders of
magnitude smaller than the effects being measured.
