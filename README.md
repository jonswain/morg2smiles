# Morg2SMILES

[![CI](https://github.com/jonswain/morg2smiles/actions/workflows/ci.yml/badge.svg)](https://github.com/jonswain/morg2smiles/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Generative recovery of SMILES strings from Morgan (ECFP) fingerprints.

**89% of held-out Morgan fingerprints can be inverted exactly within 20
guesses** by an 8M-parameter model trained overnight on a laptop. Over half are
recovered on the *first* guess.

Morgan fingerprints are normally treated as one-way: hash atom environments
into bits, and the molecule is gone. This project tests how true that is, by
training a fingerprint-conditioned decoder to generate molecules and checking
them against an exact oracle.

The task suits autonomous iteration unusually well:

* **Correctness is decidable.** RDKit recomputes any candidate's fingerprint
  and compares it bit-for-bit. No proxy metric, no human judgement.
* **Many guesses are allowed.** The oracle is free, so the model generates k
  candidates and the oracle filters them. The metric, `recovery@k`, is defined
  on exactly that.

Inspired by [NISPO](https://github.com/oxpig/nispo), which reached 98.1%
OPSIN round-trip accuracy on 103M PubChem compounds via an autonomous coding
loop against an oracle. Note that NISPO and the comparable
[openclatura](https://github.com/lamalab-org/openclatura) are *rule-based*
packages, not neural models — what this project borrows is the
loop-plus-oracle methodology.

## Install

```bash
conda env create -f environment.yml
conda activate morg2smiles
pip install -e .
```

## Quickstart

```bash
# 1. Build a shard (downloads ChEMBL 35 on first run, ~600 MB)
morg2smiles prepare --subset 10k

# 2. Measure the ceiling before training anything
python scripts/analyse_recoverability.py --subset 10k

# 3. Smoke-test the whole pipeline (minutes)
python scripts/run_experiment.py --config configs/tiny.yaml --eval-n 100

# 4. The headline run in the results table below (~8h on an M2)
morg2smiles prepare --subset 1m
python scripts/run_experiment.py --config configs/small_1m.yaml --eval-n 2000

# 5. Read the ledger
python scripts/leaderboard.py
```

Round-trip a molecule through its own fingerprint — the model sees only the
bits, never the string:

```console
$ morg2smiles invert "CC(=O)Oc1ccccc1C(=O)O" --checkpoint checkpoints/small_1m/best.pt --k 20
    =  c1(OC(C)=O)c(C(=O)O)cccc1
 0.86  O(C(c1ccccc1OC(C)=O)=O)c1c(C(O)=O)cccc1
 0.26  O(C(C)=O)C(C)=O
```

A line marked `=` is an exact fingerprint match; anything else shows its
Tanimoto to the target. Aspirin is recovered first try.

Three candidates come back from a budget of 20, and that is the honest output
rather than a bug: candidates are deduplicated **by molecule**, and 40 sampled
strings collapse to three distinct molecules. The better model is the *less*
diverse one — across the full evaluation its duplicate rate is 0.565 against the
100k model's 0.246, and it returns 12.8 distinct valid molecules per query where
the weaker model returns 21.3:

| target | distinct molecules from 40 draws | exact matches |
|---|---|---|
| aspirin | 3 | 1 |
| caffeine | 8 | 1 |
| an imatinib fragment | 4 | 1 |

The 100k model spread the same budget over 6, 20 and 20 distinct molecules and
missed the imatinib fragment entirely. Extra data bought *confidence*, not
exploration — which for a k-budget metric is close to free, because the budget
stops being spent on respellings of a wrong answer.

Deduplicating by molecule is what makes any of this visible. Earlier versions
deduplicated by *string*, and inverting aspirin returned "18 of 20 exact
matches" that were 18 spellings of one molecule.

Or from Python:

```python
from morg2smiles import Morg2Smiles, compute

model = Morg2Smiles.load("checkpoints/small_1m/best.pt")
fp = compute("CC(=O)Oc1ccccc1C(=O)O", model.fp_config)
model.generate(fp, k=20)        # oracle-verified matches first
```

## The metric, and why the qualifier matters

The headline number is **`recovery@k` on the `fp_unseen` slice**: the fraction
of held-out fingerprints, *absent from the training set*, for which at least
one of k distinct guesses reproduces the fingerprint exactly.

One of the k slots buys a **distinct molecule**, not a distinct string. Two
spellings of one molecule are one guess, and an unparseable string is not a
guess at all — RDKit rejects it locally and for free, so no caller spending
oracle queries would ever spend one on it. Both facts are easy to get wrong and
each inflates or deflates the headline by several points, so every report
records which budget produced it and the leaderboard refuses to rank rows from
different budgets together.

**Evaluation is seeded.** Unseeded, two evaluations of the same checkpoint
differed by 2.2 points — about 1.4 standard errors at n≈1000. Nothing smaller
than roughly 4 points on that sample size is a real difference.

Every metric is reported on two slices:

| slice | meaning |
|---|---|
| `all` | every molecule in the split |
| `fp_unseen` | only molecules whose fingerprint never appears in training |

The gap between them is the point. A model can score well on `all` by
memorising, and the included nearest-neighbour baseline does exactly that —
when a held-out fingerprint collides with a training one, retrieval returns a
verified exact match for free. **A model that does not beat retrieval on the
`fp_unseen` slice has learned retrieval, not chemistry.** `run_experiment.py`
prints that delta on every run.

Secondary metrics: `structure_accuracy@k` (recovers the *original* molecule,
not merely a fingerprint-equivalent one), validity, unique valid candidates per
query, and mean best Tanimoto — the graceful-degradation signal that separates
"nearly right" from "generating noise".

## What the fingerprint actually determines

From `scripts/analyse_recoverability.py` on the 10k shard (11,669 molecules):

| mode | distinct fps | uniquely determined | mean bits set |
|---|---|---|---|
| folded binary 2048 | 11,667 | 0.9997 | 49.8 |
| folded count 2048 | 11,668 | 0.9998 | 49.8 |
| unfolded binary | 11,667 | 0.9997 | 50.5 |

Folding to 2048 bits loses 1.46% of atom environments and affects 50% of
molecules; at 4096 bits that falls to 0.48% and 21%.

Two things follow, and both cut against the intuition that motivated the
project:

1. **Degeneracy is rare.** At this corpus size the fingerprint very nearly
   determines the molecule — 99.97% of molecules are the only molecule with
   their fingerprint. So `recovery@k` and `structure_accuracy@k` should track
   each other closely, and the difficulty is the hardness of the inverse
   problem, not ambiguity in the answer.
2. **Count fingerprints add almost nothing** (+0.0002 uniquely determined), so
   the extra input channel is unlikely to be worth much. `configs/count_fp.yaml`
   tests that directly.

Note that collisions make `recovery` *easier*, not harder — a fingerprint with
many preimages has many ways to be right. Collisions only bound
`structure_accuracy`.

## Architecture

A fingerprint is a **set**, so it is encoded as one. Each set bit becomes a
token (`bit_embedding[index] + count_embedding[count]`), with no positional
encoding, and a transformer encoder over that short sequence (~50 tokens, not
2048) produces the cross-attention memory for a causal SMILES decoder. The
decoder can then attend to the specific atom environments that imply each atom
it emits.

This is permutation-invariant by construction, spends no compute on the 98% of
bits that are zero, and serves binary, count, folded and unfolded fingerprints
through one code path.

Training uses **SMILES randomisation**: a fresh random traversal of each
molecule every epoch. The fingerprint is always computed from the canonical
molecule, so the input is unchanged while the target varies — which stops the
decoder collapsing onto one string and gives the sampling diversity
`recovery@k` rewards.

## Layout

```
src/morg2smiles/
  fingerprints.py   FPConfig + compute -- the single source of truth
  tokenizer.py      atom-level SMILES tokenizer (lossless by assertion)
  model.py          set encoder + conditional decoder
  train.py          training loop, oracle-based checkpoint selection
  generate.py       sampling, beam search, the Morg2Smiles public API
  oracle.py         the exact fingerprint-match oracle
  metrics.py        recovery@k and the two slices
  evaluation.py     generate -> judge -> score
  data/             ChEMBL download, standardisation, splits, augmentation
  baselines/        nearest-neighbour retrieval control
scripts/            analyse_recoverability, run_experiment, leaderboard
configs/            tiny (smoke test), base (Phase 1), count_fp (ablation)
```

Every artefact — shard mask, checkpoint, leaderboard row — carries the
`fingerprint_id` hash of the `FPConfig` that produced it, and loading a
mismatched one is a hard error. A silent fingerprint mismatch between training
and evaluation would make every number meaningless rather than merely wrong.

## Guardrails for autonomous iteration

* `run_experiment.py` evaluates on **validation** by default. The test split
  needs `--split test` and prints a warning. An iteration loop makes hundreds
  of choices against whatever number it can see; if that number comes from the
  test split, the split stops being held out.
* `leaderboard.py` sorts on the `fp_unseen` metric, never the memorisable one.
* The nearest-neighbour baseline runs alongside every experiment, so
  "better than retrieval" is checked rather than assumed.
* Shards are deduplicated before splitting, and the split-disjointness
  invariants are under test.

## Scale

Development is on an Apple M2 (MPS), so Phase 1 works at 100k–1M molecules with
a ~20M parameter model. Nothing is MPS-specific — device selection is
`mps → cuda → cpu` and configs are portable. The 103M-compound PubChem
round-trip that motivated the project is a long-term aspiration, not a Phase 1
target.

## Results

One common protocol: 2,000 held-out molecules (1,967 fingerprint-unseen) in
neither model's training set, `fp_unseen` computed against the union of all
909,800 training fingerprints, fixed seed, molecule budget.

| | rec@1 | rec@5 | **rec@20** | struct@20 | validity |
|---|---|---|---|---|---|
| **8M, ChEMBL 1M**, 3 epochs | 0.5308 | 0.7997 | **0.8927** | 0.8760 | 0.903 |
| 8M, ChEMBL 100k, 12 epochs | 0.1805 | 0.4179 | 0.5892 | 0.5705 | 0.794 |
| retrieval baseline | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.000 |

**Nearly nine in ten held-out Morgan fingerprints can be inverted exactly
within 20 guesses, and more than half on the first guess.** Mean best Tanimoto
is 0.974, so even the failures are near misses.

The jump from 0.5892 came from *data*, not from training longer or building
bigger: identical architecture, 10× the molecules, and the 1M model passes the
100k model's final score inside its first epoch. The novel-scaffold penalty also
halved (12.7 → 6.2 points), so the extra data improved generalisation to unseen
chemotypes rather than just coverage of known ones.

Full numbers, curves and caveats: [`docs/phase1-results.md`](docs/phase1-results.md)
for the first 100k run, [`docs/overnight-2026-10-09.md`](docs/overnight-2026-10-09.md)
for the scaling experiments and the two guards that failed along the way.

The retrieval baseline scores exactly zero on the primary slice, which is the
point of that slice: since the fingerprint is near-injective, a held-out
fingerprint never collides with a training one, so memorisation earns nothing
and anything above zero is reconstruction.

## Prior art, including my own

This is the second attempt. The first was
[`jonswain/morg-to-smiles`](https://github.com/jonswain/morg-to-smiles),
written by a human being with a chemistry background and no AI assistant, and
it is now archived. Its lifespan, from `Initial commit` to final push, was
**three hours and ten minutes**. The last committed output in its notebook is a
progress bar frozen at 12%.

In its defence, it got the hard part right: the right problem, the right
dataset (same ChEMBL 35 URL, in fact), and a reasonable-looking VAE — dense
encoder → 128-dimensional stochastic latent → GRU decoder. Three things went
wrong, and only one of them is about the architecture:

1. **It had no oracle.** It selected checkpoints on validation loss and
   reported mean Tanimoto similarity at generation time. Neither answers "did
   we get the molecule back". This repo's own run shows why that is fatal: at
   epoch 2 mean Tanimoto was 0.385 while `recovery@20` was **0.018**; by epoch
   12, Tanimoto 0.861 and recovery 0.575. Tanimoto is smooth, flattering and
   lagging — it would have read "0.86, pretty good" over a model failing
   two-fifths of the time. You cannot iterate toward a target you are not
   measuring, and the whole TODO list was headed *"For minimising loss
   function"*.
2. **It generated one candidate, by greedy argmax.** For a task whose natural
   formulation is "generate k, keep what the oracle accepts", that is a
   self-imposed `recovery@1`, the hardest version of the metric. Here
   `recovery@1` is 0.531 and `recovery@20` is 0.893 — the same model, a 1.7×
   difference, and it was 3.5× before the model got good enough to usually
   succeed on the first try. "Generate multiple SMILES from each ECFP" was
   sitting in the TODO file, unticked.
3. **The fingerprint reached the decoder only as the GRU's initial hidden
   state** — one 256-d vector, squeezed through a *stochastic* 128-d latent,
   expected to survive up to 242 decoding steps. A VAE's job is to compress; a
   conditional decoder's job is to keep the condition addressable. The input
   here is not something to compress, it is the entire specification of the
   answer. This version keeps all ~50 set bits available to cross-attention at
   every single step.

A fourth, quieter problem: no standardisation. No salt stripping, no
uncharging, and no stereochemistry removal — and since default Morgan
fingerprints are stereo-blind, every stereocentre in a ChEMBL target string was
noise the input could not possibly determine.

So: the human got the problem right and the measurement wrong, which is the
more interesting failure of the two. The agentic loop's real contribution was
not a cleverer model — it was building the oracle, the two metric slices and
the memorisation baseline *before* training anything, so that every subsequent
number meant something. Everything else followed from being able to see.

Credit where due, though. jonswain, three hours, no assistant, correct problem
selection. Claude, with the oracle he didn't build, fifteen hours of M2 time,
and the benefit of reading his TODO list to find out what he already knew was
missing.

And lest the moral land too comfortably: the overnight run that produced the
0.893 was supposed to stop after 8.5 hours and ran for 10.8, because the
wall-clock guard was built on a clock that stops when the laptop sleeps. The
assistant that lectures the human about measuring the wrong thing spent a night
measuring the wrong thing. It is in
[`docs/overnight-2026-10-09.md`](docs/overnight-2026-10-09.md), under the
heading "two guards that did not hold".

## Status

Phase 1 complete: harness, oracle, metrics, baseline, recoverability analysis
and a trained decoder that clears the go/no-go gate (`recovery@20` on
`fp_unseen` must beat retrieval — 0.8927 vs 0.0000).

The 2026-10-09 scaling runs answered the "what was the ceiling?" question: it
was **data**. 10× the molecules at the same parameter count moved `recovery@20`
0.5892 → 0.8927, and parameters turned out to be the wrong lever on this
hardware — scaling is linear in wall clock to 15M params and superlinear beyond,
so the next doubling is better spent on steps or data.

Open questions, in rough order of expected value:

1. **1M → 10M molecules.** 100k → 1M bought 30 points. Nothing yet says whether
   the next decade buys 10 or 1.
2. **A full-length 15M run.** The capacity arm was cut to 1.75 h by the deadline
   and is unanswered. Now known to be affordable at ~5.2 h per epoch.
3. **The remaining 10%.** Validity is 0.903 and `recovery@20` is 0.8927, so
   almost every valid candidate is now a correct one. The failures are no longer
   syntax errors, which moves the bottleneck from decoding to fingerprint
   reasoning and makes them worth inspecting directly.

## Development

```bash
pytest -q                          # 323 tests, offline; data-dependent ones self-skip
ruff check src tests scripts
ruff format src tests scripts
```

CI runs the same three on Python 3.11 and 3.12.

## Licence

MIT — see [LICENSE](LICENSE). ChEMBL data is CC BY-SA 3.0 and is downloaded,
not redistributed here.
