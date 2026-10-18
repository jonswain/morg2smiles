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
   ambiguity a 20-atom molecule has under binary bits.

   **It does not reach recovery.** Re-scored on the large-molecule protocol —
   the common protocol's p = 0.32 null having been read on 63% small molecules
   — `count_fp_100k` is **4.18 points worse** than its binary twin over 2,321
   queries above 30 heavy atoms (3.7 SE against the three same-recipe seeds),
   −6.81 at 30–34, and −1.41 at 35+, which is nothing either way. The null was
   hiding a loss, not a gain. What counts do deliver is precision in what
   recovery means: a quarter fewer of their recoveries are a different molecule
   with the same fingerprint (13.3% → 9.6% at 35+), and their proposals land
   closer to the target when they fail (0.651 → 0.681, against a between-seed
   sd of 0.0018). Ambiguity was never what made the size cliff — 1.63% of
   molecules at 35–39 share a fingerprint against 75% of queries failing there
   — so the question is closed again, for a better reason than p = 0.32. See
   `docs/overnight-2026-10-16.md`.

Collisions still make `recovery` *easier*, not harder — a fingerprint with many
preimages has many ways to be right — so they do not explain the recovery
cliff. What they bound is `structure_accuracy`, and what they undermine is the
use of `recovery` alone as a description of what the model does to large
molecules.

### What the size cliff is, as far as it has been measured

Three explanations for it are dead. It is **not the budget** — the full-k rate
is 1.000 in every size band, so the model is not running out of slots. It is
**not ranking** — the mean rank of a hit drifts only 4.4 to 8.4 across the
range. And it is **not that the model nearly gets there** — the best Tanimoto
on a miss is 0.69 at 35–39 heavy atoms, 0.64 at 40–49 and 0.57 above 50, which
recedes nothing like as fast as recovery falls (0.28 → 0.10 → 0.02).

What is left is combinatorial. At every size the decoder proposes about twenty
molecules roughly 0.65 Tanimoto from the target, and recovery asks whether that
cloud happens to contain an exact preimage — which is exponentially less likely
the bigger the molecule. Two independent predictions of that account have held:

- **Both interventions that work above 35 atoms work by tightening the cloud**,
  and specifically by putting more right-sized molecules in the budget: 1.93
  per query at 35+ heavy atoms, 2.56 with both applied, out of 20. Nothing that
  only improves ranking has moved the cliff.
- **The same tightening buys less recovery as molecules grow.** Recovery points
  per point of Tanimoto run 2.2–2.8 at 40–49 heavy atoms and 0.4–0.9 above 50,
  where the stronger training mix bought the largest cloud gain of any band
  (+4.05 points) and the smallest recovery gain (+1.57)
  (`scripts/cloud_quality.py`).

**The brute-force route is measured, not extrapolated, and it runs out at 40
heavy atoms.** Generating to k=60 on 2,321 large molecules, the recovery
*deficit* follows a power law in budget — `1 − rec(k) = A·k^−b` with |r| ≥ 0.991
in every band — whose exponent falls as molecules grow: 0.40 at 30–34 heavy
atoms against 0.14 above 50. Big molecules start lower on the curve *and* gain
less per doubling. Inverting the fits (`scripts/budget_curve.py`):

| band | k for 0.90 | k for 0.95 |
|---|---|---|
| 30–34 | 41 | 238 |
| 35–39 | 128 | 768 |
| 40–49 | 3,080 | 42,917 |
| 50+ | 1.0 × 10⁷ | 1.2 × 10⁹ |

So k=128 is a few seconds per fingerprint and takes 35–39 to 0.90; above 50
atoms the route is arithmetic rather than engineering.

**What moves the exponent is training length, and the exponent is not a
separate dial.** Four checkpoints of the *same* 7.95M-parameter architecture,
crossing corpus against training length and scored identically to k=60, give
the exponent at 35+ heavy atoms:

| | 8,508 steps | 21,117 steps |
|---|---|---|
| **100k molecules** | 0.104 | 0.229 |
| **900k molecules** | 0.122 | 0.281 |

Averaged over the two rows and two columns, 2.5× the training steps is worth
+0.142 and 10× the corpus +0.036 — a 4:1 split, the same ordering in every
size band, and 5:1 on recovery itself. The exponent also carries no information
the recovery level does not: across those four cells plus a temperature change, spanning
threefold in the exponent, `b ÷ rec@60` stays between 0.334 and 0.366. "Level
and slope as separate dials" was the wrong frame, and an earlier version of
this section attributed the step to capacity, which never varied between the
two checkpoints it compared.

Capacity has since been measured properly, with a 15.1M-parameter model trained
on the same shard for the same 21,117 steps, and it behaves the same way. Stated
in one convention throughout — full-range `b` over `rec@60`, at 35+ — the ratio
goes from 0.366 to 0.380 when capacity doubles, a move smaller than the spread
across the other cells. Eight cells now, four interventions (corpus, steps,
capacity, temperature), spanning 0.249 to 0.870 in recovery and 2.9-fold in the
exponent, and `b ÷ rec@60` stays between **0.320 and 0.380** with no monotone
trend in recovery. Not one intervention has changed the shape of the budget
curve; they slide a model along it.

The two cells added last — `small_full` and `medium_1m_8k`, both undertrained —
sit at the bottom of that range at 0.321 and 0.320, which widens it from the
0.334–0.366 quoted here earlier. Also corrected: an earlier version of this
paragraph put the `k ≤ 20` refit exponents (0.303 rising to 0.343) in the same
sentence as a ratio built from the full-range ones, which is the precise
column-mixing this repo warns about elsewhere. In the `k ≤ 20` convention the
same two cells read 0.395 and 0.427, and the eight-cell range is 0.290–0.427 —
the conclusion is unchanged either way, but the numbers are not interchangeable.

**The corpus axis is convex, so that 4:1 is a figure for one segment of it.** A
third point — `small_full`, 1,881,996 molecules at the same 8,508 steps and the
same architecture — does not lie on the line through the other two. Per
doubling of corpus, 90.7k → 900.9k is worth **+1.37 points** of rec@60 and
900.9k → 1.88M is worth **+11.47**, a segment 8.4× steeper, and in deficit
terms a 2.7% cut per doubling against 24.1%. Against training length's +23.55
points per doubling, the ratio therefore goes from 17:1 on the segment measured
first to **2.1:1** past 900k molecules. Training length is still the better
buy; "under-trained, not corpus-limited" was read off the flat part of a convex
curve and is withdrawn as stated.

This is not a composition artefact — the three shards were sampled and are the
same distribution, with 30+ shares of 38.81%, 38.70% and 38.82% and mean heavy
atoms of 28.24, 28.27 and 28.30. At a fixed step count, though, `steps × batch =
corpus × passes` forces the repetition rate down as the corpus grows — 12.01
passes, then 1.21, then 0.58 — so the axis is corpus and repetition together.

**That confound separates, because at a fixed corpus the steps axis *is* the
passes axis.** Those runs exist: 12.01 → 29.81 passes over 90,682 molecules buys
+29.56 points and 1.21 → 3.00 passes over 900,917 buys +32.23, so **repetition
is not worthless**, and the slope holds at +22.54 against +24.57 per doubling
across a tenfold change in repetition regime — which is what an additively
separable law in log space predicts. Fitting `value = f(log distinct) + g(log
passes)` with g′ = 23.55 gives distinct molecules **+24.92 points per doubling**
on the first segment and **+35.03** on the second.

That reverses the emphasis. The corpus axis at constant steps is a
near-cancellation — +24.92 for the data against −23.55 for the passes it costs,
netting +1.37 — so it is a small difference of two large numbers and a terrible
instrument. Most of the apparent 8.4× convexity is that cancellation amplifying
a 1.4× convexity in f′ about sixfold. And the figure worth extrapolating from,
for any question where extra data is not paid for out of passes, is
**f′ ≈ 25–35 points per doubling of distinct molecules**, not +1.37 — the two
answer different questions and this repo had been quoting the one that answers
almost nobody's. Separability is an assumption, supported by g′ holding to 9%
across the two rows; measuring f′ directly still needs the constant-epochs
sweep.

**What capacity buys is a constant fraction of the shortfall — between 30 and
49 heavy atoms, at any training length, and nothing at all above 50.** Doubling
the parameters to 15.1M at matched steps and shard cuts the recovery deficit by
a fraction that is stable to within the noise across four size bands, eight
budgets from k=1 to k=60, and a 2.48-fold change in training length: the larger
model's deficit divided by the smaller's is 0.808 [0.778, 0.837] at 8,508 steps
and 0.825 [0.766, 0.888] at 21,117, every band-level difference between the two
straddling zero. The gain is ordering, not reach — the larger model proposes
*fewer* distinct molecules per query at both step counts (13.6 against 14.7 at
21,117 steps, 20.69 against 22.22 at 8,508) while proposing more valid ones.

**So "capacity is worth N points" is a statement about the baseline, not about
capacity.** The same two architectures at the same temperature on the same
protocol are worth +1.33 points of rec@20 at 21,117 steps and **+7.11 points at
8,508** — a 5.3-fold difference in the headline from a multiplicative cut that
moves from 0.847 to 0.776. Point gains likewise look concentrated in large
molecules purely because the deficit is larger there; the size cliff is not
what improved.

**The fraction is not constant in size, though: it declines about sixfold from
the smallest band to the largest.** Fitting one pooled ratio to the
undertrained row, 30–34, 35–39 and 40–49 come in within 1.6 SE while 50+ misses
by 16.4 points at z = −6.9, so a dedicated 50+ protocol was run to measure that
band properly — 893 fingerprint-unseen queries against the 127 the 30+ protocol
happened to draw. The cut runs **25.4% / 22.3% / 14.7% / 3.9%** across 30–34,
35–39, 40–49 and 50+. At 50+ that is +3.70 points of rec@60 [+2.13, +5.26],
p = 9e-6, against the +18.32 a pooled ratio would predict: capacity helps at
every size, and the multiplicative description holds only over 30–49. An
earlier version of this section called the cut uniform across all 32 cells;
that is withdrawn.

Two corrections to earlier readings of that band, both mine. The 21,117-step
row cannot test it at all — the predicted gain there is 9.6 points against a
4.4-point SE, so the law and a flat null are indistinguishable, and a
multiplicative claim is hardest to satisfy where the deficit is biggest, which
is why the *undertrained* row is the informative one. And a first pass on the
30+ protocol's 127 queries at 50+ reported **no measurable gain** (6 up, 4
down, p = 0.75); the powered protocol shows a real one, so that sentence is
withdrawn. A single-digit discordant-pair count is not evidence of absence.
60+ stays unresolved at +1.48 points [−0.49, +3.94] on 203 queries — recorded
as underpowered, not as a null, and unanswerable from this data: the largest
clean pool holds 308 molecules at 60+ and none at all above 64.

On these large molecules capacity separates the two failure modes cleanly:
exact-structure accuracy at 50+ nearly triples (0.0190 → 0.0538, p = 1e-7) and
validity rises from 0.616 to 0.720, so the structure gain of +3.47 points is
almost the whole of the +3.70 recovery gain. The 8.0M model is emitting invalid
and near-miss strings where the 15.1M model emits right answers.

One part of that claim survives under the right label. The fit's other
parameter, `A`, is the deficit extrapolated back to k=1, so `A` = 1 means
nothing is ever found in a single try — and above 50 heavy atoms `A` is 1.00 to
1.02 in all four cells. There the exponent is the only quantity that can move,
and training length is what moves it. Below 35 atoms `A` falls from 0.98 to
0.44 and carries half the gain.

**Training steps are about three times more efficient per doubling than
inference budget, and the crossover is near ten thousand queries.** The deficit
also follows a power law in training steps, and its exponent can be read on
exactly the same queries at the same k by taking two checkpoints that differ
only in step count (`scripts/step_curve.py`). At k=20 on the 1M-corpus pair the
step exponent runs 1.29 / 1.24 / 0.89 / 0.37 across the size bands against the
budget exponent's 0.40 / 0.39 / 0.26 / 0.14 — a ratio of 2.5 to 3.4, flat in
molecule size, and reproduced on the 100k pair at 2.9 to 3.1. Above 50 atoms,
where budget is nearly dead at b = 0.14, steps still move at 0.37.

The two are not the same kind of spend: budget is charged per query forever,
training once. At 1.337 s/step and 0.016 s/slot/query on this hardware, cutting
the deficit by a quarter is cheaper to buy with budget below ~18,000 queries
and with training above it; for halving it, the crossover is ~9,000. So the
brute-force route is the right answer for a 2,000-query benchmark and the wrong
answer at scale.

Two caveats the script prints rather than hides. Unlike the budget law, the step
law is *not* straight in log-log — fitting a trace's first half underpredicts
its last point by 2.6 to 4.3 points and the exponent climbs as range is added —
so the step exponent is a local slope, and every number here is computed inside
the measured interval. *Capacity* does not move this exponent. Measuring that
needed two checkpoints of one size at different step counts scored under one
protocol, because the in-training traces cannot stand in — the evaluation
protocol changed partway through the project and only the newest runs are on
the far side of it. That pair is `medium_1m_8k` against `medium_1m_full`,
pre-registered in `configs/medium_1m_8k.yaml`, and the 15.1M row comes back at
1.204 against the 8.0M row's 1.226 (1.103 against 1.117 at 35+), inside the
registered 0.10. The registration called this a test of "a constant factor
cannot change a slope" and it is better described as a restatement: if the
deficit ratio is constant in steps — which the same four cells establish
directly — then the two rows' exponents are algebraically equal, since both are
built from those same deficits. It is a consistency check, not a second
finding.

Independence is ruled out by a wide margin — the model's own first-slot rate
would have finished 35+ by k=20 (0.9986 predicted against 0.6890 measured) —
and refitting on k ≤ 20 to predict k=60 lands within half a point where n is
large. On the 100k arm, generated to k=60 for the first time, the law fitted to
its own k ≤ 20 rungs predicted 0.232 at 35+ against 0.249 measured, where
independence said 0.47. That is the evidence that the extrapolated prices are
lower bounds rather than fiction.

**Every size statement below is bounded at 64 heavy atoms.** Preprocessing
filters the corpus to 3–64 heavy atoms (`max_heavy_atoms`, default 64 in
`src/morg2smiles/data/prepare.py`), so "50+" throughout this README means
50–64, and the deepest band the data can reach holds 0.54% of it — 308
molecules at 60+ across the largest clean validation pool, with nothing above
64 anywhere. This bounds what the "capability ceiling on large molecules"
finding can mean: it is a ceiling measured inside a window that stops just
past 60 atoms, and the project has no evidence about drug-sized molecules
beyond it. It also closes the 60+ question raised below as unanswerable from
this data rather than merely unmeasured.

**The size defect is not the target it looked like, and the cliff is a split in
the query population.** The clearest-looking lever — the decoder offers 45-atom
molecules for 56-atom fingerprints, and on the 100k-molecule arm only 42% of
queries above 50 atoms get even one right-sized candidate out of twenty — does
not survive longer training. Across the four matched-architecture cells, at an
identical 20-slot budget above 50 heavy atoms:

| | right-sized per query | queries with any | of those, match |
|---|---|---|---|
| 100k molecules, 8,508 steps | 0.58 | 42.5% | 1.4% |
| 100k molecules, 21,117 steps | 2.17 | 71.7% | 14.6% |
| 900k molecules, 8,508 steps | 0.73 | 40.2% | 7.5% |
| 900k molecules, 21,117 steps | 2.54 | 76.4% | 14.6% |

Read the second row against the third. Training 2.5× longer on the *same* 100k
molecules closes 81% of the gap in right-sized proposals and essentially all of
the gap in match rate, while 10× the corpus at a fixed step count closes 8% of
it and leaves the truncation on misses slightly *worse* (−10.3 atoms against
−9.7). The decoder learns the length conditional late in training, and neither a
length prior nor more data is what fixes it. Budget is not what fixes it either:
going to k=60 adds right-sized proposals while *lowering* the rate at which they
match (14.6% to 11.0%), since the ones a model proposes first are the ones it is
most confident about. What
falls with molecule size is not how many preimages the decoder draws — 1.53 per
query at 30–34 against 1.31 above 50 — but how evenly they land: above 50 atoms
52% of queries draw none at all while the ones that succeed draw 2.72 each,
against a Poisson reference that would put recovery at 0.73 where it measures
0.48. The population is splitting into fingerprints this conditional can reach
and ones it cannot, which is why extra budget buys so little: it mostly
re-finds molecules already found.

**Ensembling is not a route, and that is informative.** The cloud is narrow in
the same place for every model: the share of one seed's misses that a second
seed recovers falls from 25.3% at 30–34 heavy atoms to **1.6% above 50**, where
96.9% of molecules are missed by all three seeds against the 95.3% that chance
alone would give. At equal spend one model given 20 candidates beats two given
10 each and three given 6 each in almost every band, and three *differently
trained* models — a baseline and both size mixes — do no better
(`scripts/seed_union.py`). So the twenty molecules a checkpoint proposes for a
55-atom fingerprint are not an unlucky draw from a wide distribution of
neighbourhoods; they are the neighbourhood this architecture on this data has
learned, and a differently initialised copy proposes the same one.

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
as a flat −1.13, because 63% of its queries are under 30 heavy atoms.

**That exchange rate was measured hot, and it roughly halves when the decoder
is cooled.** Re-scored at the adopted T=0.6, the same mix gives up 25.5 small
molecules for 20.0 large ones — **1.3 per one gained** — and its whole-protocol
penalty falls from −1.13 points to **−0.28**, which is indistinguishable from
zero, while it buys +5.29 above 35 heavy atoms (+5.15 on structure accuracy).
The cost bands are where this is most reliable: 712 queries and a between-seed
sd of 0.57 below 24 atoms, 512 queries and a sd of 0.23 at 25–29, and both
bands lose less cooled than hot. At the setting this project actually uses, the
mix is close to free.

The
common protocol stays the right table for capacity questions, where every band
moves together, and it cannot describe an intervention that redistributes; see
`docs/overnight-2026-10-16.md` for the large-molecule protocol it is read on.

**It composes with the cooled decoder, though.** Scored at the adopted T=0.6
rather than at T=1.0, the threshold-30 mix is worth **+3.28 points above 35
heavy atoms** (3.1 SE, 6/6 pairs; +3.56 on structure accuracy) and +2.69 across
the whole large protocol, against +2.75 and +1.58 measured hot. Band by band
the two interventions are additive to within noise or better, and the reason is
visible in the 2×2 of {baseline, mix} × {hot, cold} on identical checkpoints:
both raise the number of right-sized molecules in the 20-candidate budget —
1.93 per query, then 2.15 with the mix, 2.44 with cooling, 2.56 with both —
while the chance that a right-sized candidate is the preimage stays between
10.2% and 11.2% in all four cells. A constant conversion rate makes recovery
linear in that count, so two interventions that each multiply it compose.

**And the exposure is already spent.** A second mix pushed harder and higher —
threshold 35, factor 6, so 58.9% of the training diet comes from 35+ atoms
against the first mix's 19.3% — moved recovery above 35 atoms by +0.14 points
over the first mix on the better-powered protocol, a tenth of its error bar,
and −0.35 on structure accuracy. What it did do is double the bill: the
exchange rate goes from 2.3 small molecules per large one to **4.4**, and the
marginal step between the two doses bought 5.5 molecules for 59. Band by band
the stronger mix's effect is explained by exposure alone — a straight line
through log₂ exposure fits all six bands at **+4.52 points per doubling,
r = 0.989** (`scripts/exposure_response.py`) — and a transfer at a constant
price in points is a losing trade in molecules, because the bands being paid
from hold 1,597 of the protocol's queries and the bands being bought hold 359.

**Cooled, each dose is cheaper and the second dose is worth less.** Both doses
have now been re-scored at the adopted T=0.6: the first dose's bill falls from
2.3 small molecules per large one to 1.3, the second's from 4.4 to **3.5** —
and the marginal step between them goes the other way, from 10.7 to **25.2**
given up per one gained, buying 2.0 molecules for 50.5. Cooling and the first
dose are substitutes rather than complements at the margin, because both work
by raising the count of right-sized candidates in the budget, so once the
decoder is cold the first dose has already collected most of what re-weighting
can collect. The cooled exposure lines are +3.39 points per doubling for the
first dose (r = 0.742) and +4.21 for the second (r = 0.988); the first dose's
poor fit is entirely the 30–34 band, which gains +0.27 points at the same 1.69×
exposure that buys 35–39 its +7.69.

**Run backwards, the exposure law survives as a slope and fails as a law.**
`size_mix_rev` de-weights 30+ heavy atoms by 1/3 — `size_mix_s1`'s factor
inverted, same seed, shard and 8,508 steps — so every band moves the opposite
way. The fitted rate comes back at **+3.62 points per doubling** against the
+3.4 it was registered at, out of sample and in a direction it was never fitted
to. Every band-level prediction fails: only two of six land within 2 points of
minus their forward-dose gap, and pricing each band from the forward fit at the
exposure actually realised leaves **one of six** within 2 points. The reason is
an asymmetry a single rate cannot hold. Around the threshold — the 1,597
queries that are 82% of the protocol — **losing exposure hurts and gaining it
does nothing**: 0–24 loses 2.74 points when starved and gains 0.28 when fed,
25–29 loses 1.17 and then moves the wrong way when fed, and 30–34 gains 0.27
when fed but loses 9.38 when starved, a factor of 23 from an identical
baseline. Those bands are saturated in exposure; only 35+ responds in both
directions. A rate fitted inside one dose averages a saturated side against a
starved side, which is why the slope is stable and the bands are not.

Two consequences worth stating. De-weighting is strictly dominated — 28
molecules given up per one gained, against the forward dose's 1.3, and the step
from reverse to forward gains molecules on *both* sides. And a factor and its
reciprocal do not produce mirror exposures: renormalisation sends the 30+ share
to `3s/(1+2s)` one way and `s/(3−2s)` the other, so the reverse dose pulls the
bands it starves 1.53× further in log-exposure than the forward dose pushed
them. The pre-registration in `configs/size_mix_rev.yaml` assumed otherwise and
was wrong to.
No threshold-and-factor escapes that arithmetic. If large molecules become the
deliverable, the strongest arm measured is the factor-6 mix (+6.13 above 35
atoms on the common protocol, +2.89 on the large one) and the reporting has to
be per band; otherwise this line is closed.

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
   0.993 and the 0.949 that briefly replaced it. The three points that exist,
   decomposed under separability, put distinct molecules at **+24.9 then +35.0
   points per doubling** against passes' +23.55; what the sweep would settle is
   whether that convexity in f′ is real, since it currently rests on two
   segments and on separability holding better than the 9% it was checked to.
3. ~~**A full-length 15M run.**~~ **Done.** `medium_1m_full` trained to
   `small_1m`'s own 21,117 steps on the same shard in 11.2 h, and capacity is
   worth a cut of roughly a fifth of the recovery deficit between 30 and 49
   heavy atoms, which was +5.63 points at rec@1 and +1.33 at rec@20 there.
   Whether that fraction holds at a second step count was item 5, and it does.
4. **The remaining 10%, now inspected.** Validity is 0.921 and `recovery@20` is
   0.8962, so almost every valid candidate is a correct one and the failures are
   not syntax errors. Of 206 misses, **2** are fingerprint collisions: the input
   nearly always determines the answer and the model cannot reach it. Recovery
   falls from 0.981 below 15 heavy atoms to 0.366 at 50–64 (the corpus ceiling;
   nothing in it exceeds 64 heavy atoms), and from 0.953 with
   no stereocentres to 0.355 with five or more. Three independently seeded runs
   then agreed on which molecules are impossible — 80% of the evaluation set is
   unanimous, and the median miss is 34 heavy atoms against 24 for the
   unanimously solved. **It is a capability ceiling on large molecules, not an
   information limit**, which is what the full-ChEMBL run is aimed at.
5. ~~**Is capacity's cut a property of the step, or of where the 8M run
   stopped?**~~ **Done, and it is neither.** The fourth cell of the capacity ×
   steps 2×2 — `medium_1m_8k`, 15.1M parameters at 8,508 steps, pre-registered
   in `configs/medium_1m_8k.yaml` — came in at rec@60 0.6127 against a
   registered 0.6045. The deficit ratio is 0.808 [0.778, 0.837] there against
   0.825 [0.766, 0.888] at 21,117 steps, with every band-level difference
   straddling zero, so the cut does not depend on training length and the
   21,117-step figure was not a lower bound. The mechanism registered on top of
   the prediction — that capacity should pay more where there is more
   repetition to exploit — was falsified with the sign reversed. What the cell
   did overturn was the claim of uniformity across size: the cut declines from
   25.4% at 30–34 to 3.9% at 50+, measured on a dedicated 893-query protocol
   after a first pass on 127 queries wrongly reported no gain at all there. What is still open is the reverse asymmetry: nothing
   has tested whether the *steps* exponent depends on capacity in a regime
   where the two models are not both far from their asymptotes.
6. **Does a second architecture beat a second seed?** One fifth of what either
   capacity arm misses, the other one finds, and splitting a fixed 60 molecules
   of budget across the two beats spending all 60 on the better of them in five
   of six size bands. This is **not** controlled: the comparable same-model
   seed unions were measured at k=20 on the 100k models, where recovery is near
   0.35, and the luck share depends strongly on the recovery level. The control
   is two seeds of `small_1m` at k=60, which is 11 h of training and does not
   exist.

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
