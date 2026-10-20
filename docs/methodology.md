# Methodology: the conventions, and the ones that have bitten

This project has retracted more claims to measurement error than to bad
science, and nearly every one came from a convention — a budget counted two
ways, two protocols read against each other, a constant calibrated on one run
and applied across runs. This document is the list, written so the next
session does not pay for them again.

If you read only one section, read [§1](#1-recovery-has-two-conventions-and-they-differ-by-points).

---

## 1. Recovery has two conventions, and they differ by points

The same checkpoint, the same queries, the same k, two numbers:

| convention | what one of the k slots is | example |
|---|---|---|
| **molecule budget** (`--budget molecules`, what `compare_checkpoints.py` prints) | one distinct valid molecule | `variance_s1` at 35+, k=20: **0.1885** |
| **raw slots** (`miss_anatomy.py`'s first-k-proposals) | one proposal, duplicates and invalid strings included | the same cell: **0.1634** |

Both are correct and they answer different questions. Conflating them has cost
this project two pre-registrations: stage 12 of night 5 computed its prediction
in one convention and scored it in the other, which voided it before the GPU
started, and the 50+ capacity gain reads +3.70 or +4.48 points depending only
on which is used.

**The rule: read columns against each other, never across tools.** A comparison
is prefix-to-prefix or it is nothing. Four collisions of this kind are logged in
the night documents; assume there will be a fifth.

**Why this one recurs, structurally.** `compare_checkpoints.py` computes its
k-list as `ks = [n for n in (1, 5, 20, 100) if n <= eval_k]`, so a run invoked
with `--eval-k 60` reports rec@1, rec@5 and rec@20 **under a 60-slot budget**
and never prints rec@60 at all. Every rec@60 figure in this project therefore
comes from a second tool — `miss_anatomy.py` (raw slots) or `band_analysis.py`
(molecule budget) — and those two disagree by about 4 points at k=60. A rec@60
baseline quoted from a night document is in whichever convention that night's
table used, and the only safe move is to **recompute both sides from their
dumps with one tool** before comparing. Night 7 did, and that is the only
reason its registration was scored correctly.

## 2. There are two protocols, and their numbers are not comparable

| | common protocol | large-molecule protocol |
|---|---|---|
| molecules | 2,000 random held-out | 2,400 drawn from 30+ heavy atoms only |
| `fp_unseen` | 1,956 of them | — |
| k | 20 | 60 |
| temperature | 1.0 historically, 0.6 now | 0.6 |
| invocation | `--eval-n 2000 --eval-k 20` | `--eval-n 2400 --min-heavy-atoms 30 --eval-k 60 --max-oversample 12` |

The common protocol is 63% molecules under 30 heavy atoms, so **it cannot
describe an intervention that acts on part of the size distribution.** It
reported the size-weighted mix as a flat −1.13 points, which is the average of
+4.60 above 35 atoms and −3.11 below 24. It also hid a 4.18-point loss from
count fingerprints behind p = 0.32.

The large protocol buys power exactly where the common one has none, and its
"all" column means *all molecules in that protocol* — 30+ heavy atoms — not all
molecules. Every rec@60 figure in this project is on that protocol unless it
says otherwise.

**Each protocol is blind in its own direction.** Report per band
(`scripts/arm_table.py`, `scripts/band_analysis.py`), always.

## 3. Shards are nested, so per-run numbers are not comparable at all

The 10k, 100k and 1M shards are drawn in order from one fixed shuffle and each
splits within itself, so a molecule held out of the 100k shard is usually
*inside* the 1M shard's training set — measured at 4,540 of 5,037, or 90%.
Evaluating a 1M-trained model on the 100k shard's validation split measures
memorisation.

`scripts/compare_checkpoints.py` exists for this reason alone: it builds one
evaluation set held out of *every* model's training data, computes `fp_unseen`
against the **union** of all training fingerprints, and scores every checkpoint
on identical molecules with an identical seed, budget and k. Nothing in the
per-run leaderboard numbers is wrong; they simply answer a different question
each.

The full shard is built with `--exclude` so the 1M and 100k shards' valid and
test molecules stay out of its training set. Without that the shards nest and
there is no evaluation set clean for every model.

**Test splits have never been touched.** Everything reported anywhere in this
project is validation.

## 4. One slot buys a distinct molecule, and that is load-bearing

Two spellings of one molecule are **one** guess. An unparseable string is **not
a guess at all** — RDKit rejects it locally and for free, so no caller spending
oracle queries would spend one on it.

Both facts are easy to get wrong and each moves the headline by several points.
An early version deduplicated by string and reported "18 of 20 exact matches"
for aspirin that were 18 spellings of one molecule.

**The budget has to be filled, and the oversample that fills it is model-
dependent.** `generate_outcomes` draws `k × oversample` strings and tops up
short queries. The default 2.0 was calibrated on the 100k model and silently
stopped filling the budget as models improved:

| model | duplicate rate | distinct valid / query, k=20 |
|---|---|---|
| `small_100k` | 0.247 | 21.3 |
| `small_1m` | **0.569** | **12.6** |

**Better models explore less**, so a constant oversample hands the *stronger*
model fewer effective candidates — understating every cross-run gap, in the
direction of the conclusion the project wanted. Use `--max-oversample` to cap
strings per query and let top-up do the work; name the cap wherever a number is
quoted, because a capped draw and an uncapped one are different protocols.

## 5. How big a gap counts as a difference

Three runs identical but for `train.seed` scored 0.6053, 0.6084 and 0.5941, so
single-run rec@20 carries an sd of about 0.75 points; and since runs are scored
on the *same* molecules, comparing two of them is McNemar's paired SE of ~0.8.

**Gaps below about 1.6 points between two training runs are not evidence of
anything.** Unseeded, two evaluations of the same checkpoint differed by 2.2
points, which is why evaluation is seeded.

**That threshold is whole-protocol and does not survive slicing.** The same
three seeds read inside bands give a between-seed sd of 0.23 points below 29
heavy atoms and **2.99 at 30–34**, where two runs differing only in seed are
5.63 points apart at p = 0.022.

Comparisons that share candidates — two rankings of one model's samples — cancel
almost everything and are discriminable well below a point. So: **an error bar
belongs to a comparison, not to a project**, and the slice is part of the
comparison. Test each gap against its own discordance (`scripts/paired_tests.py`).

**A discordant-pair count in single digits is not evidence of absence, however
good the p-value looks.** Two nulls have been called here on ~130 queries and
both were overturned by enlarging the sample.

## 6. Matched construction: a mid-run checkpoint is not a short run

The learning rate is a cosine decay over `min(total_steps, max_steps)`, so a
run with `max_steps = 8,508` anneals to zero at 8,508 and **is not** a longer
run's step 8,508. Comparing a step count across two runs means two complete
runs, each annealed to its own horizon — which is what `small_1m_matched` is to
`small_1m`, and `medium_1m_8k` to `medium_1m_full`.

Two further traps in the same family:

- **Scoring protocols changed mid-project.** The post-2026-10-14 top-up
  protocol makes earlier training traces incomparable to later ones at any
  step, which is what voided one trace comparison. Score checkpoints with one
  tool under one protocol instead of reading histories against each other.
- **A run that stops on `max_hours` instead of `max_steps` has an unfinished
  schedule**, so it is not the run its config pre-registered. Set the wall-clock
  brake above the expected cost with margin, and check `stopped_because` before
  believing a number.

## 7. Pre-registration, as practised here

Three rules, each earned by being broken:

1. **Register the interval, not the point.** Stage 12 of the 2026-10-17 weekend
   wrote three branches separated by point estimates of a quantity whose paired
   SE was ~1.7 points, so two of the three were inside the noise before the run
   started — and the registration fired FALSIFIED HIGH on a
   difference-in-differences of +1.01 points [−0.90, +2.91]. A well-posed
   version registers the CI: *confirmed if the interval contains zero*.
2. **Register the band and the predicted location of the effect**, not just the
   direction. A metric chosen on its error bar alone (the 30–39 band) failed to
   clear because three fifths of it is molecules that do not respond. An error
   bar is a necessary condition for choosing a metric, not a sufficient one.
3. **Read any size claim on `structure_accuracy` as well as `recovery`.** The
   two part company above 35 atoms, where one recovery in eight is a different
   preimage. Both working interventions turned out to be *understated* by the
   metric this project reports by default — **but the gap has no fixed sign.**
   Night 7's scaling slopes at 50+ run the other way: recovery *overstates* f′
   and g′ by about a fifth, and by 43% at 60–64. The rule is that both metrics
   must be read, not that one direction is safe.

   The reason is worth knowing, because it biases any cell near the floor.
   Among hits at 50+, the fraction that are a different molecule with the same
   fingerprint is **58.5%** for a model at rec@60 0.0459, 27.9% at 0.2251 and
   20.9% at 0.3908. A weak model's few hits land on the ambiguous
   fingerprints — the easy ones to satisfy and the ones where satisfying them
   proves least — so **a slope measured from a floor cell flatters itself on
   recovery.** Constant-passes designs put their small cells exactly there.

A registration also has to say what each branch would *mean*. Both mechanisms
registered for stage 12 were eliminated, and the useful output was the null —
which only reads as useful because the branches carried mechanisms rather than
directions.

## 8. The domain every number lives in

`src/morg2smiles/data/prepare.py` sets `max_heavy_atoms: int = 64` and every
shard was built with the default. **"50+" means 50–64 everywhere in this
project**, and nothing here speaks to molecules larger than that. The clean
pools are 1,068 molecules at 50+ and 243 at 60+ in the 1M shard, 1,421 and 308
in the full shard, and **zero** above 64 in either.

**What the cap costs, measured rather than assumed.** On a 120,000-row
reservoir sample of the raw ChEMBL 35 chemreps file, 2.558% of the corpus is
above 64 heavy atoms — about 63,000 molecules, tailing to 508. So the cap is a
real exclusion and not a no-op, and an earlier claim that nothing above 64
exists here was circular.

But `max_tokens: 128` binds first. Running `standardize` at both caps over the
molecules the atom cap discards: **73.0% of them exceed 128 tokens**, 0.1% hit
the element whitelist, and only 26.8% — about 16,465 molecules, 0.87% of the
1.88M corpus — would survive a raised cap. They sit at 65–79 heavy atoms, and
every band's longest survivor tokenises to exactly 128, so what gets in is
selected by SMILES compactness rather than by chemistry. Widening the domain
therefore means raising the context length and retraining, not editing one
default, which is why the cap was kept (item 3 of
[next-steps-2026-10-19.md](next-steps-2026-10-19.md)).

Stereochemistry is stripped (`strip_stereo: true`), elements are restricted to
a twelve-element set, and tokens are capped at 128.

## 9. Reproducing CI before committing

```bash
pytest -q                               # the 5 tests needing a shard self-skip
ruff check src tests scripts
ruff format --check src tests scripts
```

CI runs exactly these on Python 3.11 and 3.12 and **`format` gates `pytest`**,
so a formatting miss hides every test result behind it. Run them on the whole
tree, not on the files you touched: checking per-file is how CI stayed red from
2026-10-17 to 2026-10-19 with the test step never executing.
