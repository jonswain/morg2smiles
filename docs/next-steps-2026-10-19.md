# Next steps — 2026-10-19: the plan to done

Written the morning after the 2026-10-17 weekend closed. Supersedes
[next-steps-2026-10-13.md](next-steps-2026-10-13.md), whose schedule has been
overtaken: of its five items, 1, 2, 3 and 5 ran, item 4 (step saturation) did
not, and the full-ChEMBL deliverable it was built around was demoted on night
5 and is reinstated here, in a different form and for a different reason.

Unlike its predecessors this is not an open-ended research plan. It is a
closing plan: four GPU jobs and a write-up, after which the project is
**complete** and everything else is an extension taken up deliberately rather
than by momentum.

## Definition of done

The project is done when all five of these are true:

1. **The corpus question is answered directly**, not inferred under an
   assumption of additive separability (item 1).
2. **The step budget for the final run is chosen from a measurement** rather
   than from extrapolating a curve known to bend (item 2).
3. **The 64-heavy-atom cap is either raised or documented as a deliberate
   boundary** — decided *before* the final shard is built, because the final
   run bakes the shard (item 3).
4. **One full-ChEMBL run exists**, at a step budget scaled to the corpus, with
   a pre-registered prediction, reported per size band (item 4).
5. **The write-up stands on its own** — a results document that a reader who
   has not read seven night logs can follow, and a README that matches it
   (item 5).

What done does *not* require: beating any particular number. Item 4's headline
is predicted to saturate (see below), and the project's result is the set of
measured laws, not a leaderboard row.

## Why this is a sensible place to stop

Two of the three axes have run out, and the third is the one being bought:

- **Corpus.** ChEMBL 35 is 2,474,590 raw records. The full shard — 1,881,996
  training molecules — is already only ~0.3 decades past the 1M shard, and
  there is no more of it. Going further means a different data source, which
  is a different project.
- **Capacity.** Scaling is linear in wall clock to 15M parameters and
  superlinear beyond; `medium_1m` costs 2.66 s/step on this hardware.
- **Steps.** Still paying, still uncharacterised, and item 2 is what ends that.

## The cost model everything below is priced with

All measured on this M2, all from runs on disk:

| quantity | value | source |
|---|---|---|
| 8.0M training, 1M/full shard | 1.337 s/step | `small_1m`, 7.84 h for 21,117 steps |
| 8.0M training, 100k shard | 1.26 s/step | `count_fp_100k`, 2.98 h for 8,508 steps |
| 15.1M training | 1.91 s/step | `medium_1m_full`, 11.2 h for 21,117 steps |
| generation | 0.016 s/slot/query | `small_1m_matched`, 2,298 s for 2,400 × 60 |
| one scoring arm, large protocol at k=60 | ~0.64 h | 2,400 queries × 60 slots |

Corpus sizes, for converting passes to steps at batch 128: 90,682 / 900,917 /
1,881,996 molecules, so one pass is 709 / 7,039 / 14,703 steps.

## What has and has not been trained on ChEMBL

`checkpoints/small_full` is all of ChEMBL 35, built with `--exclude` so the 1M
and 100k shards' valid and test molecules stay out of its training set — but
it ran **8,508 steps, which is 0.58 passes**, about 3.2 h. Most of the corpus
is seen once and the rest not at all. It was the fixed-compute third point on
the corpus axis, not a deliverable. The headline model is still `small_1m`:
900,917 molecules, 3 passes, 21,117 steps.

So the final run is new, and the clean evaluation sets already exist for it.

---

# The four jobs

## 1. Measure f′ directly, at constant passes — 7.5 h GPU

> **DONE, night 7 ([overnight-2026-10-20.md](overnight-2026-10-20.md)).**
> f′ = **+22.09** points of rec@60 per doubling (0.5205 → 0.7553, n = 2,321,
> SE 0.89). The convex branch is falsified; f′ is flat, and marginally flatter
> than the flat account's +24.92. The floor check came in at 0.0000 at every k
> and band, as registered. Two consequences below: §4 gains a scoring-protocol
> prerequisite, and `results.md` §2.9's convexity claim is retracted (entry 27).

Stage 9 inferred `value = f(log distinct molecules) + g(log passes)` with
g′ = +23.55 points per doubling, and backed out f′ = +24.92 on the first corpus
segment and +35.03 on the second. Both rest on additive separability, checked
to 9% on two rows. The direct measurement is cheap because **at constant
passes, the comparison is f′ with nothing to subtract**.

Hold passes at 1.21, the rate `small_1m_matched` already sits at:

| corpus | passes | steps | status | cost |
|---|---|---|---|---|
| 900,917 | 1.21 | 8,508 | **exists** (`small_1m_matched`, rec@60 0.5205) | — |
| 1,881,996 | 1.21 | 17,791 | to run | **6.6 h** + 0.64 h scoring |
| 90,682 | 1.21 | 857 | floor check | 0.3 h + 0.64 h |

Why 1.21 passes and not 3: at 3 epochs the 1M cell *is* `small_1m` at rec@60
0.8427, and f′ ≈ 35 over 1.06 doublings would predict the full-shard cell above
1.0. The top of the range saturates, so the segment has to be read lower down.
1.21 passes puts both cells in the unsaturated regime and reuses an existing
checkpoint for one of them.

This cannot be read off item 4's training trace instead. Block 1 established
that a cosine-annealed checkpoint at step *n* is not the same object as a
complete *n*-step run, which is what voided the earlier trace comparison.

**Pre-registered, as an interval rather than a point** — the lesson stage 12
paid for. Quantity: rec@60 on the large protocol at T=0.6, 8.0M parameters,
full shard, 17,791 steps, against `small_1m_matched`'s 0.5205.

| account | f′ per doubling | predicted rec@60 |
|---|---|---|
| separable model with convex f′ | +35.03 | 0.86–0.92 |
| separable model with flat f′ | +24.92 | 0.76–0.82 |
| separability fails | — | outside both |

The bands are eight points apart, well clear of the 1.6-point whole-protocol
threshold. A result in the 0.82–0.86 gap is uninformative about convexity and
is to be reported as such, not rounded toward the nearer band.

The 857-step floor check is a 20-minute add-on with a sharp consequence: the
separable model predicts that cell near zero (3.31 doublings × ~25 points below
0.5205 is below the floor). Anything above rec@60 ≈ 0.05 falsifies separability
itself, and the decomposition with it.

## 2. Step saturation, the third point on the 100k arm — 19 h GPU

This is what picks item 4's step budget. The 100k arm has 8,508 steps (rec@60
0.4752) and 21,117 (0.7708); the third point is 52,500, another 2.48×, at
**18.4 h** plus scoring.

Register an interval, and note why the obvious extrapolation is untrustworthy:
`step_curve.py` showed the step deficit is *not* straight in log-log — fitting
the first half of a 15-point trace underestimates its last point by 4.33 points
on `small_1m`, with the exponent climbing from 0.568 to 0.805 as more range is
included. A curve accelerating in log-log space cannot continue, since recovery
is bounded by 1. Naive extrapolation at c ≈ 1.06 gives rec@60 ≈ 0.93; register
**0.88–0.95**, with anything below 0.85 counting as the first evidence of
saturation this project has found.

One caveat to carry into item 4: this is measured on the 100k corpus, so its
transfer to the full shard is an assumption. Item 4's budget should be set from
it, and the assumption stated where the budget is justified.

## 3. Decide the 64-heavy-atom cap — a decision now, a weekend if yes

`src/morg2smiles/data/prepare.py:68` sets `max_heavy_atoms: int = 64` and every
shard was built with the default, so every size claim in this project lives
inside a 3–64 atom window and "50+" has always meant 50–64. A good deal of
medicinal chemistry sits above that line.

**This is a decide-before-item-4 item**, because the final run bakes the shard
and raising the cap afterwards means redoing it. Two defensible answers:

- **Raise it.** Shard rebuild (time it first — unmeasured) plus the final run
  trained on the wider corpus. Buys no new science on the existing questions;
  widens the domain the headline claim is entitled to.
- **Keep it and document it.** Cheaper and honest, provided the window appears
  in the README's size claims and in the results document rather than only in
  a night log.

Recommendation: **keep and document**, unless the shard rebuild turns out to be
under about two hours. The 60+ pool does not exist at any cap this corpus can
supply — nothing above 64 atoms exists in ChEMBL 35 as standardised here — so
raising the cap widens the window without populating the band that was actually
unanswerable.

## 4. The final run: full ChEMBL, step budget from item 2 — 16–33 h GPU

> **New prerequisite from night 7: this run cannot be scored on rec@60 "all".**
> With f′ measured and g′ = +23.55, the 3-pass full-shard cell lands at
> 0.7553 + 1.3115 × 0.2355 = **1.06** — the whole-protocol metric saturates
> before the run finishes, and a ceiling is where this project has twice
> mistaken a null for a result. The headroom is in the large bands: 50–64 sits
> at 0.2598, 40–49 at 0.5395. Size a 50+-restricted protocol in the style of
> night 6's 893-query run **before** committing 16 h of GPU, because 127
> queries is the sample size that produced two of the overturned nulls.
>
> Fitted in *deficit* rather than points — the points form returns >1.0 in four
> of six bands — the 3-pass cell registers at rec@60 **0.92** whole-protocol,
> **0.56** at 50–64, **0.83** at 40–49. Those are the numbers to write down
> before the run.

8.0M parameters, `data/shards/full`, batch 128, T=0.6 at evaluation, scored on
**both** protocols with the band table.

| budget | steps | passes | cost |
|---|---|---|---|
| 3 passes | 44,112 | 3.00 | **16.4 h** |
| 6 passes | 88,224 | 6.00 | **32.8 h** |

Pick from item 2: if saturation has not appeared by 52,500 steps on the 100k
arm, take the 6-pass budget; if it has, take 3 passes and report where the
curve bent.

**Pre-register before it starts, and expect the headline to saturate.** Under
stage 9's decomposition, 1.06 doublings of corpus at constant 3 passes is worth
+26 to +37 points on top of `small_1m`'s rec@60 of 0.8427 — which is above 1.0,
so the all-slice number is not the measurement. The reportable content is:

- rec@1, where there is room to move (`small_1m` is 0.5302 at k=20);
- the 35+ and 50+ bands, where the capability ceiling lives;
- `structure_accuracy`, which the weekend showed moves more than recovery does
  on exactly these interventions;
- whether the deficit power law's exponents transport to this corpus.

Register those four before the job starts, as intervals, with the band and the
predicted location of each effect named — the three rules adopted on night 5.

## 5. The write-up — ~8 h of my time, no GPU

The project's output is currently 5,500 lines of night log plus a README that
accrued around them. Done means a reader can get the result without that.

| | task | time |
|---|---|---|
| 5a | `docs/results.md`: the measured laws in one place — budget exponent b, step exponent c, c/b ≈ 3.1, the query-count crossover, capacity's deficit cut by band, f′, the size cliff, the mix exchange rate at T=0.6 | ~3 h |
| 5b | README restructure against it: headline, method, results, limits. Fix open question 4's dangling "which is what the full-ChEMBL run is aimed at", fold the 3–64 atom window into every size claim, retire the open-questions list into "extensions" | ~2 h |
| 5c | `docs/methodology.md`: the protocol conventions that cost this project the most — molecules-budget vs raw-slot recovery, the two protocols, the 1.6-point threshold, seeded evaluation, dedup by molecule | ~1.5 h |
| 5d | The guardrail rules earned and never written down: register the **interval** not three point estimates; report per band; read size claims on structure accuracy too; run the whole tree through ruff and pytest before committing | ~1 h |
| 5e | A retractions ledger — every claim this project published and withdrew, with what caused each | ~30 min |

5d and 5e are the parts a reader of the night logs would most want and the
parts most likely to be skipped; they go in the same pass as the rest.

---

## Schedule

| slot | job | GPU | my time |
|---|---|---|---|
| **Day 1** | Item 3 decision (time the shard rebuild, then decide) | — | ~1 h |
| | Item 1 floor check, 857 steps | 0.9 h | |
| | Item 1 main run, 17,791 steps | 7.2 h | |
| **Night 1** | Item 2 step saturation, 52,500 steps | 19.0 h | |
| **Day 2** | Score item 2, set item 4's budget, write its registration | — | ~1 h |
| | Item 5a + 5c while the machine is free | — | ~4.5 h |
| **Weekend** | Item 4, the final run | 16–33 h | |
| **After** | Score item 4 per band; items 5b, 5d, 5e | 1.3 h | ~3.5 h |

Roughly **45–62 h of GPU** and **~10 h of mine**, across two nights and a
weekend. Items 1 and 2 are independent and 2 is the longer, so if the machine
is free overnight before day 1, start item 2 first and run item 1 against it.

One standing constraint, earned on 2026-10-17: run `ruff format --check`,
`ruff check` and `pytest -q` over the whole tree before committing anything,
because `format` gates `pytest` in CI and a per-file check is how CI stayed red
for two days with the test step never executing.

---

## Extensions, deliberately after the line

Not scheduled, not blocking done, and to be picked up only as a new piece of
work with its own plan:

- **Does a second architecture beat a second seed?** (~8.5 h) The uncontrolled
  ensemble result from night 5. The control is two seeds of `small_1m` at k=60.
  Inference-time ensembling; tells you nothing about the final run.
- **Does the steps exponent depend on capacity?** (~28 h) The reverse asymmetry
  left open by the capacity × steps 2×2. The most expensive question here and
  nobody is blocked on it. Interesting only if item 2 finds curvature, in which
  case the live form is "does the bend move with capacity".
- **Raising the atom cap, if item 3 says keep.** A corpus beyond ChEMBL would
  be needed to populate 65+, so this is really "a different data source".
- **Count fingerprints at full scale, and the 15M row trained out.** Both
  measured once, both at step counts where nothing is converged.
