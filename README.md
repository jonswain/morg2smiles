<img src="docs/images/banner.jpg" alt="A grid of dark tiles, a scattering of them filled teal like the set bits of a fingerprint, coming apart at the right edge into drifting tiles that carry amber skeletal structures of drug-like molecules" width="100%">

# Morg2SMILES

[![CI](https://github.com/jonswain/morg2smiles/actions/workflows/ci.yml/badge.svg)](https://github.com/jonswain/morg2smiles/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Generative recovery of SMILES strings from Morgan (ECFP) fingerprints.

**Over 91% of held-out Morgan fingerprints can be inverted exactly within 20
guesses** by an 8M-parameter model trained overnight on a laptop, and **more
than three in four on the *first* guess**.

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
missed the imatinib fragment entirely. The stronger model bought *confidence*,
not exploration — which for a k-budget metric is close to free, because the
budget stops being spent on respellings of a wrong answer.

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

**That table is measured on 11,669 molecules, and both conclusions drawn from
it were wrong.** Collisions inside a corpus grow with the corpus, and
ambiguity is not flat in molecule size. `scripts/fingerprint_ambiguity.py`
groups whole shards by fingerprint key and reports the share of molecules that
share theirs with at least one other:

| corpus | all molecules | 35+ heavy atoms | 50–59 heavy atoms |
|---|---|---|---|
| 11,669 (the table above) | 0.05% | 0.09% | 0.00% |
| 100,000 | 0.24% | 0.44% | 0.65% |
| 300,000 | 0.64% | 1.20% | 2.50% |
| **950,967 (the 1M shard)** | **1.40%** | **2.65%** | **6.13%** |

So on the corpus the models are actually trained and scored against, ambiguity
is 30× what the 10k shard suggested, and it rises six-fold across the size
distribution — 1.02% below 24 heavy atoms to 6.13% at 50–59, with one
fingerprint in the shard shared by 39 distinct molecules. All of these are
lower bounds for the decoder, which can propose any molecule and is not limited
to preimages that happen to be in ChEMBL.

What follows is the opposite of what was written here before:

1. **Degeneracy is rare for small molecules and common for large ones**, which
   is precisely the regime the project now cares about. `recovery@k` and
   `structure_accuracy@k` do *not* track each other there: in the dumps, 12.8%
   of recoveries at 35–39 heavy atoms and 13.9% at 40–49 are a different
   molecule with the same fingerprint, against 1.1% below 24. Above 35 heavy
   atoms both metrics have to be quoted, because they answer different
   questions — "did the model invert this fingerprint" and "did it find the
   molecule".
2. **Count fingerprints do carry real information**, and the +0.0002 was an
   artefact of the same 11,669 molecules. On the 1M shard, counts cut ambiguity
   **5.6×** — 1.40% to 0.25% overall, 6.13% to 1.11% at 50–59 heavy atoms, and
   the largest group of molecules sharing a fingerprint from 39 to 5. The
   reduction factor is flat in size, so counts are not specifically a
   large-molecule fix; they take a 50-atom molecule back to roughly the
   ambiguity a 20-atom molecule has under binary bits. Whether that reaches
   recovery is a separate question: `count_fp_100k` was trained and read on the
   common protocol, which is 63% molecules under 30 heavy atoms — the same
   mistake a second time. See `docs/overnight-2026-10-16.md`.

Collisions still make `recovery` *easier*, not harder — a fingerprint with many
preimages has many ways to be right — so they do not explain the recovery
cliff. What they bound is `structure_accuracy`, and what they undermine is the
use of `recovery` alone as a description of what the model does to large
molecules.

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

One common protocol: 2,000 held-out molecules (1,956 fingerprint-unseen) in
**no** model's training set, `fp_unseen` computed against the union of all
1,989,502 training fingerprints, fixed seed, molecule budget, sampled at
temperature 1.0 — held fixed across every night so the rows stay comparable.

| | data | steps | rec@1 | rec@5 | **rec@20** | struct@20 | validity |
|---|---|---|---|---|---|---|---|
| **8M, ChEMBL 1M** | 909,800 | 21,117 | 0.7526 | 0.8676 | **0.8962** | 0.8860 | 0.921 |
| 8M, ChEMBL 100k, long | 90,682 | 21,117 | 0.6764 | 0.8057 | 0.8476 | 0.8338 | 0.908 |
| 8M, ChEMBL full | 1,881,996 | 8,508 | 0.5700 | 0.6917 | 0.7444 | 0.7342 | 0.827 |
| 8M, ChEMBL 1M, short | 909,800 | 8,508 | 0.4407 | 0.5874 | 0.6401 | 0.6278 | 0.795 |
| 8M, ChEMBL 100k | 90,682 | 8,508 | 0.3793 | 0.5297 | 0.5992 | 0.5879 | 0.790 |
| retrieval baseline | — | — | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 1.000 |

**Nearly nine in ten held-out Morgan fingerprints can be inverted exactly
within 20 guesses at the protocol's settings, and three in four on the first
guess.** Mean best Tanimoto is 0.976, so even the failures are near misses.

Candidates are ranked by **consensus**: how many of the model's samples spell
the same molecule. Sampling the same answer by several routes turns out to be a
good confidence signal and it costs nothing — the spellings are already drawn,
and no extra oracle call is needed — which is worth 22 points of `rec@1` over
proposal order on this model and between 11 and 26 points on every other
checkpoint measured ([`docs/overnight-2026-10-15.md`](docs/overnight-2026-10-15.md)).
The `rec@20` column is nearly insensitive to it, as it should be.

Two further points come from decoding rather than training, which is why the
headline is above the table. Sampling the 1M model at **temperature 0.6** rather
than 1.0 takes it to `rec@1` 0.7730 and **`rec@20` 0.9162** (+1.99 points,
p = 1.3e-05), and essentially all of that is on large molecules: +7.5 points at
35 or more heavy atoms against +0.75 below. Pooling the votes of three
samplings at different temperatures, still within 20 oracle calls, reaches
**0.9279** — the best figure here, from no additional training. The protocol
table stays at 1.0 so earlier nights remain comparable; `invert` and
`Morg2Smiles.generate` default to 0.6.

0.6 has since been pushed on and holds. Sweeping down to T=0.3 on a
large-molecule tuning set, then verifying, gives at most +2 points above 35
heavy atoms for 14% more sampling and nothing overall, and a size-conditional
temperature — cold for fingerprints with many set bits, warm otherwise — is
worth +0.10 ± 0.25 points over a flat 0.6. The reason is that cooling never
*hurt* small molecules, so there was nothing to condition on. **T=0.6, top_p
1.0, everywhere.**

**How big a gap counts as a difference.** Three runs identical in everything but
`train.seed` scored 0.6053, 0.6084 and 0.5941, so single-run `rec@20` carries an
sd of about 0.75 points; and since every run here is scored on the *same* 1,956
molecules, the error bar for comparing two of them is McNemar's paired standard
error of ~0.8 points. **Gaps below about 1.6 points between two training runs
are not evidence of anything**, and that threshold is applied to every claim
below. Comparisons that share candidates — two ways of ranking one model's
samples, say — cancel almost everything and are discriminable well below a
point, so each gap is tested against its own discordance rather than against
that single threshold.

**That 1.6 points is a whole-protocol threshold and does not survive slicing.**
The same three seeds, read inside size bands, give a between-seed sd of 0.23
points below 29 heavy atoms and **2.99 points at 30–34**, where two runs
differing only in `train.seed` are 5.63 points apart with p = 0.022. A gap read
in a band has to be tested against that band's sd, which `scripts/arm_table.py`
and `scripts/band_analysis.py` report. An error bar belongs to a comparison,
not to a project, and the slice is part of the comparison.

**What training can do about large molecules, so far.** Over-sampling molecules
of 30+ heavy atoms threefold during training (`size_weight_threshold`,
`size_weight_factor`) is the first training-side change here to move the size
cliff, and it is a trade rather than a gain: measured on two seeds against three
baseline seeds, `rec@20` goes **+4.60 points above 35 heavy atoms** and
**−3.11 below 24**, −2.90 at 25–29, with every one of the six cross-arm pairs
agreeing in both directions. In molecules that is 38.7 given up for 16.5 gained
— about 2.3 small molecules per large one — which the common protocol reports
as a flat −1.13, because 63% of its queries are under 30 heavy atoms. The
common protocol stays the right table for capacity questions, where every band
moves together, and it cannot describe an intervention that redistributes; see
`docs/overnight-2026-10-16.md` for the large-molecule protocol it is read on.

The one axis these rows isolate cleanly is **compute**: the first and last rows
share an identical 90,682-molecule corpus and differ only in step budget.

| at fixed data | steps | rec@20 | absolute | error ratio |
|---|---|---|---|---|
| 90,682 molecules | 8,508 → 21,117 | 0.5992 → 0.8476 | **+24.9 pts** | 2.630× |

Night 1 compared the 100k row at 8,508 steps against the 1M row at 21,117 and
credited the whole gap — 30.4 points as the protocol then measured it — to 10×
the data. At least 24.9 of those points are available from compute on the small
corpus alone, so that attribution was wrong. The correction is in
[`docs/overnight-2026-10-10.md`](docs/overnight-2026-10-10.md), along with the
same correction to the novel-scaffold penalty — it falls 12.7 → 4.2 points on
*identical* data trained longer, a lower penalty than the 1M model's 6.2.

**What corpus size is worth, this repo cannot currently say.** At a fixed step
budget `steps × batch = corpus × passes` is an identity, so a larger shard
always comes with proportionally fewer passes over each molecule, and the two
cannot be separated. Measured at 8,508 steps the corpus direction is convex —
0.5992, 0.6401, 0.7444 for 90,682, 909,800 and 1,881,996 molecules, steps of
+4.1 and +10.4 points at 5.0 and 11.6 paired standard errors, so the shape is
real and not noise — which is not a shape any data-scaling law produces, and is
the trace of those two effects moving oppositely. An earlier version of this
section reported 1.45× error reduction per decade from a two-point fit; a third
point, predicted in advance at 0.705 and measured at 0.6299 (0.6401 on today's
protocol), falsified it. Settling it needs a corpus sweep at constant
**epochs**, not constant steps —
though night 3 found that comparison relocates the confound rather than removing
it, since a fixed-epoch budget makes the small-corpus arm pre-competent.

Full numbers, curves and caveats: [`docs/phase1-results.md`](docs/phase1-results.md)
for the first 100k run, [`docs/overnight-2026-10-09.md`](docs/overnight-2026-10-09.md)
for the scaling experiments and the two guards that failed along the way,
[`docs/overnight-2026-10-14.md`](docs/overnight-2026-10-14.md) for the failure
taxonomy — the misses are a capability ceiling on large molecules, not an
information limit, with exactly 2 of 206 explained by fingerprint collisions —
and [`docs/overnight-2026-10-15.md`](docs/overnight-2026-10-15.md) for the
error bar above and the re-test of every earlier claim against it.

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

Worse, the morning after: the headline of that write-up — "10× the data moved
recovery 0.5892 → 0.8927" — came from two runs that differed in compute as well
as data, and the controls the next night showed +24.9 of those points come from
compute on a fixed corpus. Two further claims in that document went the same way,
including one whose ranking inverted. Then the replacement claim fell too: a
1.45×/decade data-scaling fit, published here for about four hours, was
falsified by a third point it had predicted at 0.705 and which measured 0.6299. The criticism above is that the human reported a number
that could not support his conclusion. The assistant then did the same thing, in
bold, on the front page, having been handed a config file that said in advance
how to avoid it. That correction is
[`docs/overnight-2026-10-10.md`](docs/overnight-2026-10-10.md).

## Status

Phase 1 complete: harness, oracle, metrics, baseline, recoverability analysis
and a trained decoder that clears the go/no-go gate (`recovery@20` on
`fp_unseen` must beat retrieval — 0.8962 vs 0.0000).

The 2026-10-09 scaling runs looked like they had answered the "what was the
ceiling?" question — **data** — but they had varied data and compute together.
The 2026-10-10 controls show **compute** is worth at least +24.9 points on a
fixed corpus, which is most of the gap that was attributed to data. They also
show that corpus size cannot be isolated at a fixed step budget at all, so how
much data is worth here remains open. Parameters remain the wrong lever on this
hardware: scaling is linear in wall clock to 15M params and superlinear beyond.

Open questions, in rough order of expected value:

1. **How far do steps go?** Every run that completed its schedule was still
   improving, and 30 epochs of 90k molecules showed no overfitting at all —
   probably because SMILES randomisation makes every epoch a fresh target
   string. 10.6×/decade cannot continue, but nothing here has found where it
   stops, and it is the cheapest untested lever.
2. **What a bigger corpus is actually worth.** Needs a sweep at constant
   **epochs**, since at constant steps corpus size and repetition rate are
   locked together by `steps × batch = corpus × passes`. Until that runs, every
   extrapolation to PubChem scale from this repo is withdrawn — both night 1's
   0.993 and the 0.949 that briefly replaced it.
3. **A full-length 15M run.** The capacity arm was cut to 1.75 h by the deadline
   and is unanswered. Now known to be affordable at ~5.2 h per epoch.
4. **The remaining 10%, now inspected.** Validity is 0.921 and `recovery@20` is
   0.8962, so almost every valid candidate is a correct one and the failures are
   not syntax errors. Of 206 misses, **2** are fingerprint collisions: the input
   nearly always determines the answer and the model cannot reach it. Recovery
   falls from 0.981 below 15 heavy atoms to 0.366 at 50–69, and from 0.953 with
   no stereocentres to 0.355 with five or more. Three independently seeded runs
   then agreed on which molecules are impossible — 80% of the evaluation set is
   unanimous, and the median miss is 34 heavy atoms against 24 for the
   unanimously solved. **It is a capability ceiling on large molecules, not an
   information limit**, which is what the full-ChEMBL run is aimed at.

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
