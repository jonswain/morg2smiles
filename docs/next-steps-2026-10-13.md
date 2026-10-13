# Next steps — 2026-10-13

A snapshot of the development plan, and the analysis that informed it. Dated
rather than named `roadmap.md` because the estimates below are tied to
measurements that will go stale as soon as anything else runs.

## Where things stand

Best model is `small_1m`: 7.96M parameters, 21,117 steps, 909,800 training
molecules. On the common protocol — 2,000 held-out molecules, 1,956 of them
fingerprint-unseen, held out of all three shards, `fp_unseen` computed against
the union of 1,989,502 training fingerprints:

| | rec@1 | rec@5 | **rec@20** | struct@20 | validity |
|---|---|---|---|---|---|
| `small_1m` | 0.5302 | 0.7996 | **0.8926** | 0.8834 | 0.903 |

Two nights of scaling work produced one durable result and three retractions.
The result: **compute is worth +24.9 points on a fixed corpus** (90,682
molecules, 8,508 → 21,117 steps, 0.5890 → 0.8384, error ratio 2.543×). The
retractions are in [night 1](overnight-2026-10-09.md) and
[night 2](overnight-2026-10-10.md); all three were cross-run comparisons, and
the pattern is worth stating because it shapes the ordering below:

> Every claim that broke was a comparison *between* runs. Every claim that
> survived was measured *within* one.

---

# The plan

## 0. The gate: a measurement bug in my own favour's opposite direction

`generate_outcomes` draws `k × oversample` strings with `oversample=2.0`. That
default was calibrated on the 100k model, and its docstring says so:
*"measurement says 20 samples yield only about 11.5 distinct molecules, so the
default of 2.0 roughly fills the budget."*

It no longer does:

| model | duplicate rate | distinct valid / query | budget filled? |
|---|---|---|---|
| `small_100k` | 0.247 | 21.3 | yes |
| `small_1m` (best) | **0.569** | **12.6** | **no — 12.6 of 20** |

The strong model hits the 40-sample cap before finding 20 distinct molecules,
so `rec@20` = 0.8926 was measured over ~12.6 candidates rather than 20. It
needs roughly `oversample=3.5` to fill the budget.

Two consequences. The headline is **pessimistic**. And every cross-run
comparison hands the *stronger* model fewer effective candidates than the
weaker one, because better models explore less — the one finding that survived
all five runs. The 100k → 1M gaps are understated.

This is the same failure shape as the other three: a constant calibrated on one
run and applied across runs that differ. It gates everything else, because the
next big run will be the strongest model and therefore the one whose headline
is measured most wrongly.

## Items and estimates

| | item | my time | machine time |
|---|---|---|---|
| 1 | Oversample fix + re-score every checkpoint | ~1 h | ~1.5 h |
| 2 | Failure taxonomy + likelihood ranking | ~3 h | ~1 h |
| 3 | Count fingerprints — cheap signal (100k, 8,508 steps) | ~30 min | ~3 h |
| | Count fingerprints — comparable (1M, 21,117 steps) | — | ~8 h |
| 4 | Step saturation (100k, 52,500 steps) | ~30 min | ~21 h |
| 5 | Constant-epoch corpus point (100k, 2,127 steps) | ~30 min | ~1 h |
| | …with the full-shard point (44,112 steps) | — | ~18 h |

**Item 2 — failure analysis.** What are the remaining ~11%?
`docs/phase1-results.md` already has a recoverability ceiling from collision
analysis to compare against. If failures concentrate on fingerprints that
genuinely underdetermine structure, there is an information ceiling and more
scaling is wasted; if they are large or unusual molecules, it is capability and
scaling helps. Also worth testing whether `rec@1` 0.5302 against `rec@20`
0.8926 can be closed by ranking candidates on model likelihood rather than
generation order.

**Item 3 — count fingerprints.** Named as item 6 in the Phase 1 results and
never run. Counts carry strictly more information, so this tests the same
question as item 2 from the opposite side: if recovery jumps, the bottleneck is
the input representation; if not, it is model capability.

**Item 4 — step saturation.** Compute is the only lever cleanly measured and it
is uncharacterised. Every run that finished its schedule was still improving,
and 30 epochs of 90k molecules showed *no* overfitting — probably SMILES
randomisation making every epoch a fresh target string. 52,500 steps is the
natural third point: another 2.5× on top of the 8,508 → 21,117 step that bought
+24.9 points.

**Item 5 — the corpus question, asked properly.** At a fixed step budget
`steps × batch = corpus × passes` is an identity, so corpus size and repetition
rate cannot be separated — which is why night 2's data-scaling fit was
withdrawn. The honest version holds *passes* fixed instead. On the small side
it is cheap: 100k at 3 epochs is 2,127 steps, about 45 minutes, and `small_1m`
already *is* 3 epochs at 21,117 steps.

## Schedule

| slot | job | machine | notes |
|---|---|---|---|
| **Working day** | Item 1 oversample fix + re-score | 1.5 h | the gate |
| | Item 2 failure taxonomy + likelihood ranking | 1 h | |
| | Item 5 constant-epoch point | 1 h | |
| | Item 3 cheap signal | 3 h | start late afternoon |
| **Night 1** | Item 3 at comparable scale | ~8 h | only if the cheap signal justifies it |
| **Weekend 1** | **Full ChEMBL, 3 epochs, 44,112 steps** | ~18 h | the deliverable |
| **Weekend 2** | Item 4 step saturation | ~21 h | the science |
| *Optional* | Capacity (15M, 21,117 steps) | ~15.6 h | lowest value |

One working day, one night, two weekends. Capacity stays last: compute is the
lever that is actually measured, MPS scaling goes superlinear past 15M
parameters, and `medium_1m` costs 2.66 s/step.

Step saturation cannot be folded into the full-ChEMBL run. A 44,112-step run on
the full corpus varies data *and* steps — exactly the confound behind the three
retractions. The clean third point has to sit on the 100k corpus where the other
two points already are.

## Constraints to plan around

- **One job at a time.** Established the hard way: a benchmark running alongside
  training cost 49 minutes of a live run. Nothing here parallelises.
- **Budget the re-scoring inside each window.** Every run needs ~1.5 h of
  common-protocol evaluation to be comparable, and indexing ~2M fingerprints is
  most of that. An 18 h run wants a ~20 h window.
- **Match the cosine horizon to the actual stop step**, or a capped run is
  unfairly penalised. `max_steps` and the horizon must agree.

---

# Full ChEMBL

## Are we ready?

**Yes, once item 1 is done.** The groundwork is already in place: the full shard
is built and verified (1,881,996 train, 104,555 valid, 104,555 test, from
2,091,106 standardised molecules with 109,152 holdouts excluded and zero leakage
into any split), the recipe is known-good at this architecture, and `small_full`
already ran 8,508 steps on it — so the config, the 119-token vocabulary and the
throughput are all measured rather than guessed.

Items 2, 3 and 5 are parallel lines of enquiry, not prerequisites. They say
*why* it works and whether a different input would work better; none changes
whether the run is worth doing.

## How long?

Measured basis: `small_full` did 8,508 steps on this shard in **2.83 h = 1.20
s/step**, including six evaluations. One epoch is 14,704 steps.

| | steps | at 1.25 s/step | at 1.45 s/step |
|---|---|---|---|
| 1 epoch | 14,704 | 5.1 h | 5.9 h |
| 2 epochs | 29,408 | 10.2 h | 11.8 h |
| **3 epochs** | **44,112** | **15.3 h** | **17.8 h** |

The range matters because **throughput degrades over a long run**:
`small_1m_matched` launched at 0.89 s/step and averaged 1.30 over three hours,
46% worse; `small_100k_long` averaged 1.39 over 8.15 h. Budget a 15-hour run at
the upper end, not at the 2.83-hour measurement.

Recommendation with weekends available: **3 epochs, 44,112 steps, ~18 h**, plus
~10 min for the final evaluation and ~1.5 h of re-scoring, so a ~20 h window.

One caveat worth stating plainly: this will be the best model by a clear margin,
and it will not tell you *why*. It varies corpus and compute together, same as
every run that has produced a retracted claim here. It is the right thing to run
as a deliverable. It is not an experiment.

---

# Analysis

Three questions, measured from what was already on disk. The PubChem figure is
a fit and is labelled as such.

## How often is a fingerprint unique?

All 2,091,106 molecules of `data/shards/full`, radius 2, 2048 bits, folded,
binary — the same `FPConfig` the models use. Fingerprinted at 8,910 molecules/s
(235 s total), hashed with the project's own `_fp_key`, then clustered at seven
nested corpus sizes drawn from one seeded shuffle.

| corpus | distinct fps | unique (no fp twin) | collided | largest cluster |
|---|---|---|---|---|
| 50,000 | 49,986 | 99.946% | 0.054% (27) | 3 |
| 100,000 | 99,900 | 99.810% | 0.190% (190) | 4 |
| 200,000 | 199,611 | 99.625% | 0.375% (750) | 7 |
| 500,000 | 497,846 | 99.211% | 0.789% (3,943) | 10 |
| 1,000,000 | 992,482 | 98.687% | 1.313% (13,127) | 26 |
| 1,500,000 | 1,484,960 | 98.303% | 1.697% (25,448) | 38 |
| **2,091,106** | **2,064,903** | **97.926%** | **2.074% (43,371)** | **55** |

**For the whole library, ~98% of compounds have a fingerprint that identifies
them uniquely.**

The growth is sublinear and decelerating. The local power-law exponent of
collision rate against corpus size:

```
    50,000 ->   100,000   1.815   (noisy, only 27 collisions)
   100,000 ->   200,000   0.981
   200,000 ->   500,000   0.811
   500,000 -> 1,000,000   0.735
 1,000,000 -> 1,500,000   0.633
 1,500,000 -> 2,091,106   0.605
```

That is not birthday-paradox behaviour, which would be roughly linear in corpus
size. Collisions concentrate in analogue series rather than appearing at random:
ChEMBL runs out of new ways to collide as it grows.

### PubChem at 103M

Extrapolating that curve by a factor of 49.3 in corpus size:

| assumed exponent | collided | unique |
|---|---|---|
| 0.62 (last measured span) | 23.2% | 76.8% |
| 0.50 (decay continues) | 14.6% | **85.4%** |
| 0.40 (flattens) | 9.9% | 90.1% |

**~85% unique, range 77–90%.** One caveat cuts against the optimistic end:
PubChem holds far more small, simple molecules than ChEMBL, and small molecules
have sparse fingerprints that collide more readily. Treat 85% as the ceiling of
confidence rather than the centre of the estimate.

## Can this become a generative model?

As it stands, no, and the evidence is sharp:

| k | recovery | structure accuracy | gap |
|---|---|---|---|
| 1 | 0.5302 | 0.5087 | 2.15 pts |
| 5 | 0.7996 | 0.7837 | 1.58 pts |
| 20 | 0.8926 | 0.8834 | **0.92 pts** |

The 0.92-point gap at k=20 is **18 queries out of 1,956** where the model found
a *different* molecule carrying the same fingerprint. When it hits a fingerprint
match it has found the original molecule 99% of the time. There is essentially
one right answer, so there is nothing to generate.

The room does grow with scale — 2% of ChEMBL has a fingerprint twin, perhaps 15%
of PubChem would — but that is a sevenfold increase in a minority property, not
a change of character.

### The route is loosening the constraint, not enlarging the corpus

In increasing ambition:

- **Perturb the fingerprint.** Flip *n* bits of a known fingerprint and ask what
  molecules land there. The oracle becomes Tanimoto ≥ threshold rather than
  exact bit equality.
- **Interpolate.** Take two molecules' fingerprints, mix the bits, generate what
  sits between them.
- **Partial specification.** Condition on a chosen *subset* of bits — in effect
  a pharmacophore — and sample completions.

There is evidence the capability is already latent. For the 10.7% the model
never inverts, **mean best Tanimoto is 0.760**. The headline 0.974 is pooled
with the successes, which are exactly 1.000 by definition of `fp_match`, so
separating them matters. The model is producing analogues when it cannot hit
exactly — though 0.760 is "same scaffold, different substituents", not "nearly
the same molecule", so the behaviour is real but unrefined.

**The bit-flip experiment costs about an hour and needs no retraining.** It is
the cheapest way to find out whether there is a generative model in here at all.

## When it misses on the first try

A definitional note: "the correct fingerprint" *is* recovery, so when a
candidate is not recovered its fingerprint is wrong by construction. The real
question is whether the output is at least a sensible molecule. It is:

- **`rec@1` = 0.5302** — the first distinct candidate has the right fingerprint
  just over half the time.
- **mean hit rank 1.715** — when the model succeeds within 20, the hit is on
  average the 1.7th candidate, so a first-try miss is usually corrected
  immediately afterwards.
- **validity 0.9027** — about 90% of generated strings parse as molecules;
  roughly 10% are syntactically invalid.
- **failures land at Tanimoto 0.760** — wrong, but a recognisable relative.

So: usually valid, usually close, usually right on the next attempt.

Two things the stored aggregates cannot answer: whether the *first* candidate
specifically is valid, since validity is pooled across all 40 draws, and what
the failures look like structurally. Both need item 2.

## Caveat on every number in the last two sections

They were measured with `oversample=2.0`, so over ~12.6 distinct candidates
rather than 20 — see the gate at the top. They are pessimistic, and fixing that
should precede any further training run.
