# Phase 1 results

First real training run. The question Phase 1 exists to answer is narrow: **can
a fingerprint-conditioned decoder reconstruct molecules it has never seen, or
does it only retrieve ones it has?** Everything else is downstream of that.

## The run

`configs/small.yaml`, commit `4159e07`, Apple M2 (MPS), torch 2.13.0.

| | |
|---|---|
| fingerprint | Morgan r=2, binary, folded to 2048 bits (`465725d9dece`) |
| data | ChEMBL 35, 100k shard — 90,682 train molecules |
| model | 4 encoder + 4 decoder layers, `d_model` 256, 8 heads, **7,951,945 params** |
| training | 12 epochs, batch 128, lr 5e-4, randomised SMILES, 709 steps/epoch |
| wall clock | ~4h10m including six oracle-based evaluation passes |
| evaluation | 1,000 **validation** molecules (995 fingerprint-unseen), k=20, multinomial sampling at T=1.0 |

The test split has not been touched. Everything below is validation.

## Headline

**`recovery@20` on fingerprint-unseen molecules: 0.5367.**

Better than half of held-out fingerprints are inverted exactly, within 20
guesses, by an 8M-parameter model trained for four hours on a laptop.

| | rec@1 | rec@5 | rec@20 | struct@20 | validity | best Tanimoto |
|---|---|---|---|---|---|---|
| **model** (`fp_unseen`, n=995) | 0.1538 | 0.3729 | **0.5367** | 0.5246 | 0.782 | 0.848 |
| **model** (`all`, n=1000) | 0.1550 | 0.3750 | 0.5380 | 0.5240 | 0.783 | 0.848 |
| retrieval baseline (`fp_unseen`) | 0.0000 | 0.0000 | **0.0000** | 0.0000 | 1.000 | 0.562 |
| retrieval baseline (`all`) | 0.0050 | 0.0050 | 0.0050 | 0.0000 | 1.000 | 0.564 |

**Model − baseline on the primary metric: +0.5367.** The go/no-go gate was
"clearly exceeds the baseline". The baseline is a floor of exactly zero, so the
gate is passed by the whole margin.

## Learning curve

Validation `recovery@20` on `fp_unseen`, 500-molecule subsample, every second epoch:

| epoch | train loss | rec@1 | rec@5 | rec@20 | validity | best Tanimoto |
|---|---|---|---|---|---|---|
| 2 | 0.770 | 0.004 | 0.012 | 0.018 | 0.270 | 0.385 |
| 4 | 0.491 | 0.028 | 0.078 | 0.166 | 0.494 | 0.626 |
| 6 | 0.394 | 0.070 | 0.214 | 0.365 | 0.661 | 0.758 |
| 8 | 0.341 | 0.108 | 0.293 | 0.477 | 0.737 | 0.826 |
| 10 | 0.311 | 0.148 | 0.389 | 0.541 | 0.783 | 0.849 |
| 12 | 0.297 | 0.164 | 0.411 | 0.575 | 0.803 | 0.861 |

Increments in `recovery@20`: +0.018, +0.148, +0.199, +0.112, +0.064, +0.034.
The curve is clearly bending — the last two epochs bought a third of what the
middle two did — but it has not flattened. The run ended because it ran out of
configured epochs, not because it stopped improving, and the best checkpoint is
the final one. More epochs at this size is the cheapest untested lever.

## Five things worth knowing

**1. The baseline is a floor of zero, and that is informative rather than
anticlimactic.** Retrieval scores 0.0000 on `fp_unseen` *by construction*: that
slice is defined as fingerprints absent from training, and since the
fingerprint is near-injective, no training molecule shares one. The useful
consequence is that the primary metric cannot be gamed by memorisation at all.
Any score above zero is reconstruction.

**2. Real degeneracy exists, but it is vanishingly rare, and we caught it in
the act.** On the `all` slice the baseline scores `recovery@20` 0.0050 while
`structure_accuracy@20` is 0.0000. That gap is exactly five molecules out of
1,000 where retrieval found a training molecule with a *bit-identical
fingerprint but a different structure*. The "many SMILES per fingerprint"
premise is real at a rate of about 0.5%, not as a general property.

**3. Recovery and structure accuracy track each other to within 1.2 points**
(0.5367 vs 0.5246), exactly as the pre-training recoverability analysis
predicted from 99.97% injectivity. When this model finds a fingerprint match it
has almost always found the original molecule, not a decoy. The 1.2-point gap
is the model exploiting genuine collisions.

**4. The 20-candidate budget leaks about 40% of its slots, and none of the
leaks need a bigger model.** Two separate losses compound:

- **Invalid samples: 21.8%.** Every unparseable string is a draw that cannot
  possibly be right. Validity rose monotonically with training (0.27 → 0.80),
  so more epochs helps, and constrained decoding would help more.
- **Respellings.** Candidates are deduplicated as *raw strings*, so the same
  molecule written two ways occupies two slots. On average 19.7 distinct
  strings collapse to only 11.5 distinct molecules. Asking the model to invert
  aspirin's fingerprint is the pathological case: 18 of 20 candidates were
  exact matches, and all 18 were aspirin in different traversals — one
  molecule, 18 slots.

Canonicalising candidates before deduplication is a few lines and recovers
roughly four slots in twenty. This is a direct, foreseeable cost of training on
randomised SMILES, which otherwise pays for itself; the augmentation teaches
the decoder many traversals and then the budget pays for that diversity twice.

**5. Failures are near-misses, not noise.** Mean best Tanimoto is 0.848 across
all queries including the 46% that fail outright. Mean hit rank is 3.98, so
when the model succeeds, it usually succeeds early — the 4th candidate on
average. That shape argues the sampling budget is being spent on genuine
near-misses rather than flailing, and that a better search over the same model
would pay.

## What this does not show

- **Nothing here is a test-split number.** By design; the harness defaults to
  validation so an iteration loop cannot erode the held-out split.
- **One seed, one configuration.** No error bars.
- **100k molecules is small.** ChEMBL has ~2.4M, PubChem ~119M.
- **Stereochemistry is stripped** during standardisation, because default
  Morgan fingerprints are stereo-blind and leaving it in makes a fraction of
  every target unlearnable by construction. So this recovers constitution, not
  full stereochemistry. The 103M-compound PubChem round-trip that motivated the
  project would need that caveat stated plainly.
- **`recovery@20` is a 20-guess metric.** `recovery@1`, the number you would
  care about if you wanted *the* answer rather than *an* answer, is 0.1538.

## Next levers, cheapest first

1. **Canonicalise candidates before deduplication.** A few lines, recovers
   ~4 slots in 20, costs nothing. Do this first.
2. **More epochs at 8M params.** The curve was still climbing. No new code.
3. **Fix validity.** 21.8% waste. Constrained decoding, or simply a longer
   schedule, since validity rose monotonically with training.
4. **Better search.** Beam search and temperature sweeps, measured rather than
   assumed — mean hit rank 3.98 says successes come early, so the back half of
   the budget is mostly being wasted on near-misses and respellings.
5. **`configs/base.yaml`** — 25M params, ~13h. The obvious move, and the one
   most likely to be a waste while levers 1–4 are unexhausted.
6. **Count fingerprints** (`configs/count_fp.yaml`). The recoverability
   analysis predicts near-zero gain (+0.0002 injectivity); worth one run to
   confirm the prediction rather than assume it.
