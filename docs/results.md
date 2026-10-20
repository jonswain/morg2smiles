# Results: the measured laws, in one place

The README tells the story and the night logs record how each number was
arrived at, including the wrong turns. This document is neither: it is a
reference sheet. Every quantity this project claims, with its domain of
validity, its error bar, the script that produced it and the log that argued
it out.

Read it with two warnings in view. **Every number here lives inside a 3–64
heavy-atom window**, because `src/morg2smiles/data/prepare.py` sets
`max_heavy_atoms: int = 64` and every shard was built with the default — so
"50+" always means 50–64, and nothing in this project says anything about
molecules larger than that. And **recovery has two conventions** that differ by
several points; each table below names which one it is in. See
[methodology.md](methodology.md).

---

## 1. Headline

One protocol: 2,000 held-out molecules (1,956 fingerprint-unseen), in no
model's training set, `fp_unseen` against the union of 1,989,502 training
fingerprints, fixed seed, molecule budget.

| model | rec@1 | rec@20 | struct@20 | validity |
|---|---|---|---|---|
| 8M, ChEMBL 1M, 21,117 steps, T=1.0 | 0.7526 | **0.8962** | 0.8860 | 0.921 |
| the same at the adopted T=0.6 | 0.7730 | **0.9162** | — | — |
| three-temperature vote, still 20 oracle calls | — | **0.9279** | — | — |
| retrieval baseline | 0.0000 | 0.0000 | 0.0000 | 1.000 |

The baseline is zero **by construction** on `fp_unseen`, so the primary metric
cannot be gamed by memorisation: any score above zero is reconstruction.

## 2. The laws

### 2.1 The budget deficit is a power law in k

`1 − rec(k) = A·k^−b`, fitted over a twelvefold range of k, |r| ≥ 0.991 in
every size band. `small_1m` at T=0.6 on the large protocol, read at k=20:

| band | b |
|---|---|
| 30–34 | 0.396 |
| 35–39 | 0.387 |
| 40–49 | 0.263 |
| 50+ | 0.144 |
| 35+ | 0.281 |
| all | 0.317 |

Domain: 5 ≤ k ≤ 60, measured; extrapolation beyond that is an extrapolation.
Script: `scripts/budget_curve.py`. Inverting the fits gives the brute-force
price, and it is a measurement rather than a guess up to k=60:

| band | k for rec 0.90 | k for 0.95 |
|---|---|---|
| 30–34 | 41 | 238 |
| 35–39 | 128 | 768 |
| 40–49 | 3,080 | 42,917 |
| 50+ | 1.0 × 10⁷ | 1.2 × 10⁹ |

**Brute force is a real route below 40 heavy atoms and arithmetic above 50.**

### 2.2 The step deficit is also a power law, and it is 3.1× steeper

Same queries, same k, two checkpoints differing only in step count:
`c = log(D₈₅₀₈ / D₂₁₁₁₇) / log(2.482)`.

| band | b (budget) | c (steps) | c / b |
|---|---|---|---|
| 30–34 | 0.396 | 1.294 | 3.27 |
| 35–39 | 0.387 | 1.240 | 3.20 |
| 40–49 | 0.263 | 0.893 | 3.39 |
| 50+ | 0.144 | 0.366 | 2.54 |
| 35+ | 0.281 | 0.937 | 3.33 |
| all | 0.317 | 1.062 | 3.35 |

The 100k pair gives 2.86, 3.10, 2.92, 3.08, 3.13, 3.03 for the same bands.
**A doubling of training steps cuts the deficit about 3.1 times as far as a
doubling of inference budget, across two corpora and every band** — and the
ratio is flat in size even though both exponents fall threefold across it.
Script: `scripts/step_curve.py`.

Caveat, and it is the script's own: the step law is the weaker of the two. The
budget deficit is straight in log-log to |r| ≥ 0.991; the step deficit is not.
Fitting a 15-point trace to its first half underestimates its last point by
4.33 points on `small_1m`, with the exponent climbing from 0.568 to 0.805 as
more range is included. `c` is a local slope, not a law.

### 2.3 Where the two kinds of spend cross over

Budget is charged on every query forever, training once. Cutting the deficit by
a factor f needs `f^(−1/b)` times the budget or `f^(−1/c)` times the steps, so
there is a query count above which the longer run is cheaper. At 1.337 s/step
and 0.016 s/slot/query, from 21,117 steps and k=20:

| band | queries for a ×0.75 cut | for a ×0.5 cut |
|---|---|---|
| 35–39 | 20,900 | 13,300 |
| 40–49 | 16,900 | 8,000 |
| 50+ | 16,600 | 4,100 |
| 35+ | 17,900 | 9,000 |

**Below roughly ten thousand queries, buy budget; above it, train longer.**
This project's own protocols are 2,000 and 2,400 queries — an order of
magnitude below the crossover — so "brute force is affordable" is true *for a
benchmark* and is the wrong advice for anyone inverting fingerprints at scale.

### 2.4 Nothing changes the shape of the budget curve

Eight cells, four interventions (corpus, steps, capacity, temperature),
spanning 0.249 to 0.870 in recovery and 2.9-fold in the exponent: `b ÷ rec@60`
stays between **0.320 and 0.380** with no monotone trend. Interventions slide a
model along one curve rather than bending it. In the `k ≤ 20` refit convention
the same eight cells read 0.290–0.427; the two conventions are not
interchangeable and the conclusion is the same in both.

### 2.5 Capacity cuts a constant fraction of the deficit

15.1M against 8.0M parameters, same shard, at two step counts — the closed
2×2:

| | deficit ratio, 15.1M / 8.0M | 95% CI |
|---|---|---|
| at 8,508 steps | 0.808 | [0.778, 0.837] |
| at 21,117 steps | 0.825 | [0.766, 0.888] |

**The cut does not depend on training length** (every band-level difference
straddles zero), so the 21,117-step figure was not a lower bound. In points on
the common protocol it is +5.63 at rec@1 and +1.33 at rec@20 between 30 and 49
heavy atoms.

**It is not uniform across size.** The cut declines from 25.4% at 30–34 to 3.9%
at 50+. At 50+ specifically, measured on a dedicated 893-query protocol, the
capacity gain is **+3.70 points** in raw-slot units (+4.48 in molecule-budget
units), and structure accuracy moves more than recovery does. A first pass on
127 queries reported no gain there at all; the null did not survive enlarging
the sample, which is the second time that has happened in this project.

Caveat carried from the configs: the two architectures train at lr 4.5e-4 and
5e-4, so each column's capacity comparison carries a 10% difference in learning
rate alongside the 1.9× in parameters.

### 2.6 Decoding: T=0.6, top_p 1.0, everywhere

Cooling from T=1.0 to T=0.6 is worth +1.99 points of rec@20 (p = 1.3e-05), and
essentially all of it is large molecules: +7.5 points at 35+ heavy atoms
against +0.75 below. Pushing further buys nothing: at most +2 points above 35
atoms at T=0.3 for 14% more sampling, and a size-conditional temperature is
worth +0.10 ± 0.25 points over a flat 0.6.

Tested where it was most likely to fail — 893 queries at 50–64 heavy atoms, the
worst-validity band in the corpus — T=0.3 moves recovery by **−0.34 to +1.34
points** depending on model and budget, every interval straddling zero.

The mechanism is a cancellation worth stating on its own: cooling raises
validity by 6.6 and 2.8 points for the two models and *lowers* distinct
molecules per query by 3.3 and 6.1. **Validity is not the binding constraint on
large molecules** — the invalid strings cooling removes are replaced by valid
wrong answers, not by right ones.

### 2.7 Consensus ranking is free and worth 22 points of rec@1

Rank candidates by how many of the model's samples spell the same molecule.
No extra oracle call, no extra sampling: **+22 points of rec@1** on the best
model, +11 to +26 on every other checkpoint measured. `rec@20` is nearly
insensitive to it, as it should be.

### 2.8 Training-side size re-weighting is a trade, and cooled it is nearly free

Over-sampling 30+ heavy atoms threefold during training, scored at the adopted
T=0.6 against T=1.0:

| | T=1.0 | T=0.6 |
|---|---|---|
| small molecules given up | 38.7 | 25.5 |
| large molecules gained | 16.5 | 20.0 |
| exchange rate | 2.34 per one gained | **1.28** |
| whole-protocol net | −1.13 points | **−0.28 points** |
| gain above 35 heavy atoms | +4.60 | **+5.29** (+5.15 structure) |

−0.28 is indistinguishable from zero against the 1.6-point threshold, so **at
the decode setting this project uses, the mix is close to free.** The cost side
is the reliable part: 712 queries and a between-seed sd of 0.57 below 24 atoms,
512 and 0.23 at 25–29.

**The exposure is already spent.** A second, harder dose (threshold 35, factor
6 — 58.9% of the diet from 35+ atoms against 19.3%) bought +0.14 points above
35 atoms over the first dose, a tenth of its error bar, while the exchange rate
went from 2.3 to 4.4 small molecules per large one. Cooled, the marginal step
between doses costs 25.2 given up per one gained.

**The exposure response is a slope and not a law.** Per-band gaps fit a
straight line in log₂ exposure at +4.52 points per doubling (r = 0.989) hot,
+3.39 (r = 0.742) and +4.21 (r = 0.988) cooled for the two doses. Run backwards
— `size_mix_rev`, de-weighting 30+ by ⅓ — the *rate* replicates out of sample
at +3.62 points per doubling, and **every band-level prediction fails**: one of
six lands within 2 points when priced from the forward fit. The asymmetry a
single rate cannot hold is that losing exposure hurts far more than gaining it
helps, around a threshold where 82% of the protocol's queries sit.

### 2.9 The corpus axis is convex, and at constant steps it is a near-cancellation

Three points, same architecture, same 8,508 steps, rec@60 on the large
protocol:

| molecules | passes | rec@60, all | 35+ | b, all |
|---|---|---|---|---|
| 90,682 | 12.01 | 0.4752 | 0.3101 | 0.157 |
| 900,917 | 1.21 | 0.5205 | 0.3613 | 0.178 |
| 1,881,996 | 0.58 | 0.6424 | 0.4982 | 0.216 |

Per doubling of corpus: **+1.37 points** on the first segment, **+11.47** on
the second — 8.4× steeper, and 2.7% against 24.1% in deficit terms. Not a
composition artefact: the three shards' 30+ share is 38.81 / 38.70 / 38.82%
and mean heavy atoms 28.24 / 28.27 / 28.30. The same distribution, more of it.

At a fixed corpus, the steps axis *is* the passes axis, and those runs exist:

| corpus | 8,508 → 21,117 steps | points | per doubling |
|---|---|---|---|
| 90,682 | 12.01 → 29.81 passes | +29.56 | **+22.54** |
| 900,917 | 1.21 → 3.00 passes | +32.23 | **+24.57** |

Repetition is **not** worthless, and the slope is stable to 9% across a tenfold
change in repetition regime — which is the licence to fit an additively
separable law, `value = f(log distinct molecules) + g(log passes)` with
g′ = +23.55 points per doubling. Reading the corpus segments at constant steps,
where a corpus doubling *is* a passes halving:

| segment | net measured | passes cost | f′ implied | per doubling |
|---|---|---|---|---|
| 90.7k → 900.9k | +4.52 | −78.02 | +82.55 | **+24.92** |
| 900.9k → 1.88M | +12.19 | −25.03 | +37.23 | ~~+35.03~~ |

The second row is **superseded by direct measurement** — f′ on that segment is
+22.09, not +35.03 ([§2.9a](#29a-f-measured-directly-at-constant-passes)). Keep
the row for the method, not the number.

**The corpus axis at constant steps is a terrible instrument**: +22 against
−23.55 nets +1.37, so the observable is a small difference of two large
numbers, and the 8.4× convexity in it is that cancellation, not a property of
the corpus.

### 2.9a f′ measured directly, at constant passes

The decomposition above is no longer needed. Holding passes fixed at 1.2087 and
varying only the corpus removes the confound, which is item 1 of the closing
plan and [night 7](overnight-2026-10-20.md). Large protocol, k=60, T=0.6, the
same 2,321 queries, raw-slot convention:

| molecules | passes | steps | rec@60, all | 35+ | 50–64 |
|---|---|---|---|---|---|
| 90,682 | 1.2087 | 856 | 0.0000 | 0.0000 | 0.0000 |
| 900,917 | 1.2087 | 8,508 | 0.5205 | 0.3613 | 0.0630 |
| 1,881,996 | 1.2087 | 17,772 | **0.7553** | 0.6378 | 0.2598 |

**f′ = +22.09 points of rec@60 per doubling of distinct molecules** on the
900.9k → 1.88M segment (1.0628 doublings, +23.48 points, binomial SE 0.89), and
a 46.1% cut of the deficit per doubling. It replicates at +20.96 in the
molecule-budget convention and +16.79 on the common protocol at k=20, the last
being lower because that protocol is 63% small molecules and the small bands
gain least.

| band | per doubling | deficit cut / doubling |
|---|---|---|
| 30–34 | +18.36 | 56.0% |
| 35–39 | +26.65 | 52.4% |
| 40–49 | +27.48 | 36.5% |
| 50–64 | +18.52 | 19.8% |
| all | **+22.09** | 46.1% |

**f′ is itself size-dependent, and falls off in the same direction the size
cliff does.** The 50–64 row above is 127 queries; re-measured on the dedicated
893-query 50+ protocol (`--min-heavy-atoms 50 --max-oversample 10`, so the
levels are not comparable to the table above, only the slopes):

| band | n | 900,917 | 1,881,996 | per doubling | SE |
|---|---|---|---|---|---|
| 50–54 | 433 | 0.0647 | 0.2910 | **+21.30** | 2.18 |
| 55–59 | 257 | 0.0428 | 0.1946 | **+14.28** | 2.47 |
| 60–64 | 203 | 0.0099 | 0.1232 | **+10.66** | 2.31 |
| all 50+ | 893 | 0.0459 | 0.2251 | **+16.86** | 1.40 |

Each step down is about 3 SE, so the decline is a measurement rather than a
reading of noise, and at 60–64 a corpus doubling pays less than half the
whole-protocol rate. The 127-query estimate (+18.52) survived the re-measure
at +16.86, 1.2 SE away — the first time in this project a number read on
roughly 130 queries has held.

**f′ is flat, not convex.** The pre-registered convex branch (+35.03/doubling →
rec@60 0.86–0.92) is falsified by twelve standard errors; the inference
overstated the far segment by 13 points, 60% of its measured value. The 90.7k
cell is at the floor — 0.0000 at every k, in every band, on 571 queries — as
registered, which is consistent with additive separability and weak evidence
for it.

Domain: 8M parameters, ChEMBL 90.7k–1.88M molecules, 3–64 heavy atoms, at
1.2087 passes. **g′ should not be extrapolated below one pass**: the same corpus
at 0.58 and 1.21 passes gives g′ = +10.62 per doubling, half the +23.55 measured
at ≥1.21 passes.

### 2.10 Count fingerprints carry information that does not reach recovery

On the 1M shard, counts cut fingerprint ambiguity **5.6×** — 1.40% to 0.25%
overall, 6.13% to 1.11% at 50–59 heavy atoms, largest collision group 39 → 5 —
and the reduction factor is flat in size, so counts take a 50-atom molecule
back to roughly a 20-atom molecule's ambiguity under binary bits.

Recovery does not follow. On the large-molecule protocol `count_fp_100k` is
**4.18 points worse** than its binary twin over 2,321 queries above 30 heavy
atoms (3.7 SE against three same-recipe seeds), −6.81 at 30–34, −1.41 at 35+.
What counts deliver is precision in what recovery *means*: a quarter fewer
recoveries are a different molecule with the same fingerprint (13.3% → 9.6% at
35+), and failed proposals land closer (0.651 → 0.681, between-seed sd 0.0018).

## 3. The size cliff, and what it is not

Recovery falls from 0.981 below 15 heavy atoms to 0.366 at 50–64, and from
0.953 with no stereocentres to 0.355 with five or more. Three dead
explanations:

- **Not the budget.** The full-k rate is 1.000 in every band — the model never
  runs out of slots.
- **Not ranking.** The mean rank of a hit drifts only 4.4 → 8.4 across the
  range.
- **Not near-misses.** Best Tanimoto on a miss is 0.69 at 35–39, 0.64 at
  40–49, 0.57 above 50 — nowhere near as fast a decline as recovery's
  0.28 → 0.10 → 0.02.

**Not ambiguity either.** Of 206 misses, **2** are fingerprint collisions. And
1.63% of molecules at 35–39 share a fingerprint against 75% of queries failing
there.

What is left is combinatorial: at every size the decoder proposes about twenty
molecules roughly 0.65 Tanimoto from the target, and recovery asks whether that
cloud contains an exact preimage — exponentially less likely the bigger the
molecule. Two predictions of that account have held. Both interventions that
work above 35 atoms work by putting more right-sized molecules in the budget
(1.93 per query at 35+, 2.56 with both), while the chance a right-sized
candidate is the preimage stays between 10.2% and 11.2% — a constant conversion
rate, which is why two interventions that each multiply the count compose. And
the same tightening buys less as molecules grow: 2.2–2.8 recovery points per
point of Tanimoto at 40–49, 0.4–0.9 above 50.

**Ambiguity itself is 30× what the 10k shard suggested**, and rises with size:

| corpus | all | 35+ | 50–59 |
|---|---|---|---|
| 11,669 | 0.05% | 0.09% | 0.00% |
| 100,000 | 0.24% | 0.44% | 0.65% |
| 950,967 (1M shard) | **1.40%** | **2.65%** | **6.13%** |

Which is why above 35 atoms both `recovery` and `structure_accuracy` have to be
quoted: 12.8% of recoveries at 35–39 and 13.9% at 40–49 are a *different*
molecule with the same fingerprint, against 1.1% below 24 atoms.

## 4. What is dead

Claims tested and refused, so they are not re-opened by accident:

| claim | how it died |
|---|---|
| the size defect needs a size token on the encoder | no size defect left to fix at k=60: truncation 5.1 atoms, 89.8% of 50+ queries get a right-sized proposal, closest within 0.2 atoms in every band |
| the 50+ capacity gain is a decode artefact of T=0.6 | cooling to T=0.3 moves it by +1.01 points [−0.90, +2.91] |
| validity is the binding constraint on large molecules | cooling raises validity and recovery nets zero |
| successive samples are independent draws | the deficit is a power law in k with a size-dependent exponent; independence predicted 0.66 at k=100 against a measured decay |
| splitting a fixed budget across models beats spending it on the best one | measured and dead |
| counts fix the size cliff | −4.18 points at 30+; ambiguity was never what made the cliff |
| recovery level and budget slope are separate dials | `b ÷ rec@60` is invariant across eight cells |
| the exponent is a property of capacity | it is training length; the comparison that said otherwise varied no capacity |
| 60+ heavy atoms is answerable from this corpus | nothing above 64 exists in it; the largest clean pool is 308 molecules against a fourfold power requirement |

## 5. Sources

| | |
|---|---|
| `docs/phase1-results.md` | the first run, and the go/no-go gate |
| `docs/overnight-2026-10-09.md`, `-10-10.md` | scaling, and three retractions |
| `docs/overnight-2026-10-14.md` | consensus ranking, counts, the decode sweep |
| `docs/overnight-2026-10-15.md` | temperature, seeds, the 1.6-point threshold |
| `docs/overnight-2026-10-16.md` | the size cliff factorised, the budget curve, the mix |
| `docs/overnight-2026-10-17.md` | the capacity × steps 2×2, the corpus axis, the step law |
| `docs/overnight-2026-10-20.md` | f′ at constant passes |

Every claim this project published and later withdrew is listed in
[retractions.md](retractions.md), with what caused each.
