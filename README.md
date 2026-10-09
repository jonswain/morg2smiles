# Morg2SMILES

Generative recovery of SMILES strings from Morgan (ECFP) fingerprints.

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
python -m morg2smiles.data.prepare --subset 10k

# 2. Measure the ceiling before training anything
python scripts/analyse_recoverability.py --subset 10k

# 3. Smoke-test the whole pipeline (minutes)
python scripts/run_experiment.py --config configs/tiny.yaml --eval-n 100

# 4. The real Phase 1 run
python -m morg2smiles.data.prepare --subset 100k
python scripts/run_experiment.py --config configs/base.yaml

# 5. Read the ledger
python scripts/leaderboard.py
```

Using a trained model:

```python
from morg2smiles import Morg2Smiles, compute

model = Morg2Smiles.load("checkpoints/base/best.pt")
fp = compute("CC(=O)Oc1ccccc1C(=O)O", model.fp_config)
model.generate(fp, k=20)        # oracle-verified matches first
```

## The metric, and why the qualifier matters

The headline number is **`recovery@k` on the `fp_unseen` slice**: the fraction
of held-out fingerprints, *absent from the training set*, for which at least
one of k distinct guesses reproduces the fingerprint exactly.

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

## Status

Phase 1: harness, baseline and analysis complete; first decoder training runs
underway. The go/no-go for autonomous iteration is whether the decoder's
`recovery@20` on the `fp_unseen` slice clearly beats the retrieval baseline.
