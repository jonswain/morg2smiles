# Night 7 — f′ measured directly

One job, one number. Item 1 of
[next-steps-2026-10-19.md](next-steps-2026-10-19.md): measure points per
doubling of distinct molecules at **constant passes**, so the corpus axis is
read without the steps confound that made every earlier reading an inference.

Driver `scripts/overnight7.sh`, six stages, finished 02:00 with 389 minutes to
spare. Both trainings stopped on `stopped_because = "step budget reached"`, not
on `max_hours` — so both cosine schedules ran to their own horizon and the
matched construction of §6 of [methodology.md](methodology.md) holds.

| | corpus | steps | passes | cost |
|---|---|---|---|---|
| `small_1m_matched` (existed) | 900,917 | 8,508 | 1.2087 | — |
| **`small_full_1p2`** | 1,881,996 | 17,772 | 1.2087 | 5.27 h |
| `small_100k_1p2` (floor check) | 90,682 | 856 | 1.2087 | 0.39 h |

---

## The result

Large protocol, k = 60, T = 0.6, the same 2,321 fingerprint-unseen queries,
`miss_anatomy` convention throughout (see [the convention near-miss](#the-convention-near-miss-which-is-the-fourth)):

| band | n | 900,917 | 1,881,996 | Δ | per doubling | deficit cut / doubling |
|---|---|---|---|---|---|---|
| 30–34 | 1,189 | 0.6720 | 0.8671 | +19.51 | +18.36 | 56.0% |
| 35–39 | 625 | 0.4912 | 0.7744 | +28.32 | +26.65 | 52.4% |
| 40–49 | 380 | 0.2474 | 0.5395 | +29.21 | +27.48 | 36.5% |
| 50–64 | 127 | 0.0630 | 0.2598 | +19.69 | +18.52 | 19.8% |
| 30–39 | 1,814 | 0.6097 | 0.8352 | +22.55 | +21.21 | 54.4% |
| 35+ | 1,132 | 0.3613 | 0.6378 | +27.65 | +26.02 | 40.7% |
| **all** | **2,321** | **0.5205** | **0.7553** | **+23.48** | **+22.09** | **46.1%** |

The corpus ratio is 2.0890×, or 1.0628 doublings. Binomial SE on the "all" row
is 0.89 points.

**f′ = +22.09 points per doubling of distinct molecules**, measured, with
nothing subtracted and no separability assumed.

It replicates in the two other conventions this project reports, which is the
check that matters most given what nearly went wrong below:

| convention | 900,917 | 1,881,996 | per doubling |
|---|---|---|---|
| raw slots (`miss_anatomy`, k=60) | 0.5205 | 0.7553 | **+22.09** |
| molecule budget (`band_analysis`, k=60) | 0.5618 | 0.7846 | **+20.96** |
| common protocol, k=20 (stage 6) | 0.6825 | 0.8609 | **+16.79** |

The common-protocol figure is lower for the reason §2 of
[methodology.md](methodology.md) gives — it is 63% molecules under 30 heavy
atoms, and the 30–34 band is the slowest-gaining band in the table above — and
it is *understated* on top of that: `small_full_1p2` fills only 53.3% of its
20-slot budget at `--max-oversample 10`, against `small_1m_matched`'s 79.2%,
because the better model duplicates more (§4, "better models explore less").
The large protocol's cap of 12 leaves it at 91.0% filled.

## Scoring the pre-registration

Registered in `configs/small_full_1p2.yaml` before the run, as intervals:

| branch | predicted rec@60 | outcome |
|---|---|---|
| f′ convex, +35.03/doubling | 0.86–0.92 | **FALSIFIED** — 10.5 points below the band |
| f′ flat, +24.92/doubling | 0.76–0.82 | the reading, but see below |
| separability fails | outside both, below 0.72 or above 0.95 | not this |

Measured **0.7553**. The convex branch is dead by a margin of twelve standard
errors, and that is the finding: **f′ does not rise along the corpus axis.**

The flat branch is the honest reading, with one blemish I am not going to round
away. The flat branch's *point* prediction was 0.5205 + 26.5 = 0.7855 and its
band ran 0.76–0.82; the measurement lands **0.5 points below the band's lower
edge** — 0.6 binomial SE, and well inside the 1.6-point threshold this repo
applies to its own training comparisons, but outside the interval as written.
Measured f′ is +22.09 against the flat account's +24.92: flat, and a little
flatter than flat.

And the registration had a hole. It assigned 0.76–0.82, 0.86–0.92, the
0.82–0.86 gap ("uninformative"), and below 0.72 / above 0.95 ("separability
fails") — leaving **0.72–0.76 and 0.92–0.95 unassigned**, which is exactly
where the result landed. Logged as entry 26 of
[retractions.md](retractions.md): adjacent registered intervals have to tile
the line, or the registration cannot be scored without a judgement call made
after seeing the number. Writing "flat if below 0.82, convex if above 0.86"
would have cost nothing and been complete.

## The floor check

`small_100k_1p2`, 90,682 molecules at the same 1.2087 passes, registered
asymmetrically — able to falsify, not to confirm. Separability predicts this
cell about 82 points below 0.5205, i.e. at the floor.

**0.0000**, at k = 1, 20 and 60, in both orderings, in all seven bands, on 571
fingerprint-unseen queries. Validity 0.175, mean best Tanimoto on misses 0.293:
856 steps does not produce a model that recovers anything. As registered, this
is consistent with separability and is weak evidence for it — the two handicaps
(100 warmup steps of 856, and a draw capped at 4 rather than 12) can only push
the number down, and a number pushed to a floor it was predicted to be below
agrees without evidence.

What it does rule out: any account in which the 90.7k cell at 1.21 passes still
recovers a few percent, which would have put f′ on the first segment far below
the second and revived convexity from the other end.

## The convention near-miss, which is the fourth

§1 of [methodology.md](methodology.md) says to assume there will be a fourth
collision between the two recovery conventions. This is it, and it was caught
with the number already on screen.

Stage 4's band table reports `small_full_1p2` at rec@60 **0.7846**. The
registration's baseline, `small_1m_matched` at **0.5205**, comes from
`miss_anatomy` — raw slots. Scoring 0.7846 against 0.5205 gives +26.4 points
per 1.06 doublings, lands the result *inside* the registered flat band, and
agrees with the flat account's +24.92 to within 1.5 points. It would have read
as a clean CONFIRMED.

It is wrong. 0.7846 is the molecule-budget convention and 0.5205 is not; the
like-for-like pair is 0.5205 → 0.7553 or 0.5618 → 0.7846, and both give f′ ≈
+21 to +22, not +26.4. The mixed pair inflates f′ by about 4 points — enough to
move the verdict from "flat, and a little flatter than flat" to "flat, dead
centre", and enough to have been quoted as the project's measured f′ for good.

The conclusion does not change, because the convex branch dies in every
convention. The lesson is that it did not change *this* time. Three of the five
numbers in the two tables above came from a tool whose k-list stops at 20:
`compare_checkpoints.py` computes `ks = [n for n in (1, 5, 20, 100) if n <=
eval_k]`, so an `--eval-k 60` run reports rec@1/5/20 **under a 60-slot budget**
and never prints rec@60 at all. Every rec@60 in this project therefore comes
from a second tool, and the two tools do not share a convention. That is the
structural reason this keeps happening.

## What this does to the corpus axis

The remaining live claim in §2.9 of [results.md](results.md) was that f′ itself
is mildly convex — rising 1.4× from +24.92 to +35.03 — with the observable's
8.4× convexity being that mild rise amplified by a near-cancellation against
passes. Half of that is now retracted and half is confirmed:

- **The cancellation is real and is the whole story.** At constant steps a
  corpus doubling is a passes halving, so the observable nets +1.37 from
  +22.09 against −23.55. Two large numbers, a small difference, and the sign of
  the difference is not robust.
- **f′ is not convex.** Measured +22.09 on the 900.9k → 1.88M segment against
  the +35.03 that the decomposition inferred for it. The inference overstated
  the far segment by 13 points, which is 60% of the measured value.

So the corpus axis, over 90.7k → 1.88M molecules of ChEMBL at 8M parameters, is
**flat at roughly +22 points of rec@60 per doubling**, and the convexity that
survived three nights was an artefact of reading a difference of two large
numbers. `small_full`'s 0.6424 at 0.58 passes and `small_full_1p2`'s 0.7553 at
1.21 passes are the same corpus at two repetition rates, and the gap between
them (+11.29 points for 1.063 doublings of passes) is a third estimate of g′ at
**+10.62** — which does *not* match the +23.55 from the fixed-corpus rows, and
is the one loose thread left here. The two fixed-corpus estimates (+22.54,
+24.57) were both taken at ≥1.21 passes; this one straddles a single pass. A
model that sees each molecule less than once is not in the same regime, and
nothing in this project's g′ should be extrapolated below one pass.

## What this does to job 4

The final full-ChEMBL run was to be 3 or 6 passes at 1,881,996 molecules,
chosen by the step-saturation job. With f′ measured, that cell can now be
priced — and pricing it exposes a limit of the law itself.

**In points, the additive law predicts the impossible.** 0.7553 + 1.3115
doublings of passes × g′ 23.55 = **1.06**. It is worse per band: four of six
bands come out above 1.0. A law fitted in points cannot be extrapolated toward
a bounded metric's ceiling, and §2.9's decomposition is entirely in points.

**In deficit terms it behaves.** The rest of this project fits deficits, not
points, and the 1M shard already supplies the 1.21 → 3.00 passes transition at
every band — `small_1m_matched` to `small_1m`, same 2,321 queries. Applying its
*per-band deficit cut* to the full shard's measured cell:

| band | 1M @1.21 | 1M @3.00 | deficit cut | full @1.21 | **predicted @3.00** | additive |
|---|---|---|---|---|---|---|
| 30–34 | 0.6720 | 0.9134 | 73.6% | 0.8671 | **0.9649** | 1.11 ✗ |
| 35–39 | 0.4912 | 0.8656 | 73.6% | 0.7744 | **0.9404** | 1.15 ✗ |
| 40–49 | 0.2474 | 0.7158 | 62.2% | 0.5395 | **0.8261** | 1.01 ✗ |
| **50–64** | 0.0630 | 0.4488 | 41.2% | 0.2598 | ~~0.5646~~ | 0.65 |
| 35+ | 0.3613 | 0.7686 | 63.8% | 0.6378 | **0.8687** | 1.05 ✗ |
| all | 0.5205 | 0.8427 | 67.2% | 0.7553 | **0.9197** | 1.08 ✗ |

So the 3-pass full-ChEMBL run is predicted at **rec@60 ≈ 0.92** whole-protocol,
with 8 points of headroom, and that is the number to register. The 50–64 row is
struck through because night 7c re-derived it on 893 queries at **0.5052**
rather than 0.5646; use that one. Note the deficit
cut is itself size-dependent — 73.6% at 30–39 against 41.2% at 50–64 — so this
is six predictions, not one scaled six ways.

**The run should still not be headlined on rec@60 "all".** At 0.92 predicted
against 0.7553 measured, three quarters of the remaining deficit lives in bands
holding a quarter of the protocol, and a whole-protocol number 8 points from the
ceiling is where this project has twice mistaken a null for a result. The
50–64 band is the one with room — 0.2598 now, 0.5646 predicted, 30 points of
swing — and at n = 127 it is also the thinnest; 127 queries is the sample size
that produced two of the overturned nulls. A 50+-restricted protocol in the
style of night 6's 893-query run is the right instrument, and sizing it is now a
prerequisite for job 4 rather than an optional extra.

One caution against the 0.92. The nearest thing to a matched-compute check runs
the other way: `small_1m` at 21,117 steps on 900,917 molecules scores 0.8427,
while `small_full_1p2` at 17,772 steps on 1,881,996 scores 0.7553 — the smaller
corpus ahead by 8.7 points with 19% more steps. The additive law accounts for
this exactly (the 1M cell has 1.31 doublings more passes, worth +31 points,
against 1.06 doublings less corpus, worth −22), so nothing is inconsistent; but
it is a reminder that **at these budgets passes still beat molecules**, and the
"prefer more molecules to more passes" line in §2.9 holds only at fixed steps,
which is not a budget anyone has.

---

## Night 7b — the 50+ band, on 893 queries instead of 127

The table at the top rests on 2,321 queries, but its 50–64 row rests on 127 —
the sample size that produced entries 13 and 15 of
[retractions.md](retractions.md). Night 6 built a dedicated 50+ protocol for
exactly that reason and scored `small_1m_matched` on it, and
`small_1m_matched` is tonight's constant-passes partner, so the better-powered
reading cost one generation pass: 19 minutes.

Same invocation as night 6 stage 11 — `--eval-n 1000 --min-heavy-atoms 50
--eval-k 60 -T 0.6 --top-p 1.0 --max-oversample 10`, 893 fingerprint-unseen
queries, `miss_anatomy` convention.

| band | n | 900,917 | 1,881,996 | Δ | per doubling | SE |
|---|---|---|---|---|---|---|
| 50–54 | 433 | 0.0647 | 0.2910 | +22.63 | **+21.30** | 2.18 |
| 55–59 | 257 | 0.0428 | 0.1946 | +15.18 | **+14.28** | 2.47 |
| 60–64 | 203 | 0.0099 | 0.1232 | +11.33 | **+10.66** | 2.31 |
| **all 50+** | **893** | **0.0459** | **0.2251** | **+17.92** | **+16.86** | **1.40** |

**The thin estimate held.** The 30+ protocol's 127 queries gave +18.52 per
doubling; 893 queries give **+16.86**, a difference of 1.66 points against an
SE of 1.40. For once a number read on ~130 queries survived being re-measured
with power — worth recording precisely because the two previous times it did
not, and the practice of re-measuring is what distinguishes the two outcomes
rather than the result.

**f′ declines with molecule size, monotonically, inside the 50–64 window.**
+21.30 at 50–54, +14.28 at 55–59, +10.66 at 60–64. Each gap is about 3 SE, so
the trend is real and not a reading of noise. Set beside the whole-protocol
+22.09, the corpus axis pays progressively less the larger the molecule, and at
60–64 it pays less than half the headline rate.

That is the sharpest statement this project has of why more data does not fix
the size cliff: **the returns to data are themselves size-dependent, and they
fall off in the same direction the cliff does.** The 60–64 cell is the extreme
case — 0.0099 to 0.1232, so a doubling of corpus takes it from one recovery in
a hundred to one in eight, which is a large multiple of a very small number.

A level note, since the same checkpoint appears at two values: `small_full_1p2`
at 50–64 is 0.2598 on the 30+ protocol and 0.2251 here. Both are correct. The
protocols cap the draw at 12 and 10 respectively, and §4 of
[methodology.md](methodology.md) is explicit that a capped draw and an uncapped
one are different protocols. The invocation was matched to night 6's on
purpose, so the comparison within this table is prefix-to-prefix; it is the
cross-table comparison that is not available.

## Night 7c — the cell job 4's registration was missing

The deficit-cut extrapolation above applies the 1M shard's 1.21 → 3.00 passes
transition to the full shard. At 50–64 that transition was read on 127
queries, so the prediction of 0.5646 inherited the thin sample even though both
other cells are now well powered. `small_1m` — the 3.00-passes end — was not on
the 50+ protocol, so it was scored there too: 20 minutes, 893 queries.

| band | n | 1M @1.21 | 1M @3.00 | deficit cut | full @1.21 | **predicted @3.00** |
|---|---|---|---|---|---|---|
| 50–54 | 433 | 0.0647 | 0.4896 | 45.4% | 0.2910 | **0.6131** |
| 55–59 | 257 | 0.0428 | 0.3580 | 32.9% | 0.1946 | **0.4598** |
| 60–64 | 203 | 0.0099 | 0.2217 | 21.4% | 0.1232 | **0.3107** |
| all 50+ | 893 | 0.0459 | 0.3908 | 36.2% | 0.2251 | **0.5052** |

**The thin sample was optimistic, by six points.** The 127-query route
predicted 0.5646 at 50–64; the 893-query route predicts **0.5052**. Both the
f′ cell and the deficit cut moved down, and the error compounded because the
prediction multiplies them. This is the number to register for job 4, and it
is the clearest argument in this night's work for not registering anything off
127 queries — the estimate held within its error bar, and the *prediction built
on it* was still six points out.

### Both scaling axes pay less on large molecules, and in the same proportion

With `small_1m` on this protocol, both slopes are measurable in every band:

| band | n | f′ (per corpus doubling) | g′ (per passes doubling) | g′ / f′ |
|---|---|---|---|---|
| 50–54 | 433 | +21.30 | +32.40 | 1.52 |
| 55–59 | 257 | +14.28 | +24.03 | 1.68 |
| 60–64 | 203 | +10.66 | +16.15 | 1.52 |
| all 50+ | 893 | +16.86 | +26.30 | 1.56 |

**Neither axis closes the size cliff, and both decay in the direction the cliff
does.** More distinct molecules and more passes over them both pay roughly half
as much at 60–64 as at 50–54. Nothing in this project's two scaling levers
reaches the far end of the cliff, which is the strongest form of the "capability
ceiling on large molecules" claim and the reason the ceiling is not a data
problem.

The ratio column is the interesting part and the part to be careful with. It
sits at 1.52–1.68 across a band where both slopes halve, which *looks* like a
size-invariant exchange rate of about 1.55 passes-doublings per
corpus-doubling. But each slope carries an SE of roughly 2.2 points, so the
ratio's SE is about 0.2, and 1.52 against 1.68 is well inside it. **The honest
statement is that the ratio is consistent with being size-invariant, not that
it was measured to be** — which is the distinction entries 12, 13 and 24 of
[retractions.md](retractions.md) were all paid for.

A reader who wants the invariant tested properly needs a third passes point at
50+, which is item 2's territory and does not exist.

### Read on structure accuracy, both axes pay about a fifth less

Rule 3 of §7 of [methodology.md](methodology.md) says to read every size claim
on `structure_accuracy` as well as `recovery`, because above 35 atoms one
recovery in eight is a different preimage. The dumps were already on disk, so
this cost nothing:

| band | n | f′ on recovery | f′ on structure | g′ on recovery | g′ on structure | collisions among hits |
|---|---|---|---|---|---|---|
| 50–54 | 433 | +21.30 | **+17.60** | +32.40 | **+28.17** | 26.2% |
| 55–59 | 257 | +14.28 | **+12.45** | +24.03 | **+19.88** | 24.0% |
| 60–64 | 203 | +10.66 | **+6.03** | +16.15 | **+12.02** | 44.0% |
| all 50+ | 893 | +16.86 | **+13.49** | +26.30 | **+22.11** | 27.9% |

**Rule 3 fires, and in the direction the rule did not anticipate.** The rule was
written because two working interventions turned out to be *understated* by
recovery. Here recovery **overstates** both scaling slopes — by about a fifth
whole-band, and by 43% at 60–64, where +10.66 points of recovery per corpus
doubling is only +6.03 points of getting the right molecule. So the rule's
value is that the two metrics must both be read, not that the gap has a known
sign.

The mechanism is in the last column. At 50+ a large minority of recoveries are
a *different* molecule sharing the fingerprint, and the share depends on the
model as much as on the size:

| cell | rec@60 | struct@60 | collisions among hits |
|---|---|---|---|
| 1M, 1.21 passes | 0.0459 | 0.0190 | **58.5%** |
| 1M, 3.00 passes | 0.3908 | 0.3091 | 20.9% |
| full, 1.21 passes | 0.2251 | 0.1624 | 27.9% |

**The weaker the model, the larger the share of its recoveries that are the
wrong molecule** — 58.5% for the weakest cell. A weak model's few hits are
concentrated on the ambiguous fingerprints, which are the easy ones to satisfy
and the ones where satisfying them proves least. Any slope computed from a cell
near the floor therefore flatters itself on recovery, and that is exactly the
regime the constant-passes design puts the small cells in.

None of this disturbs the headline — f′ is flat on both metrics and the convex
branch dies on both — but it does mean **job 4 must register both metrics**:

| band | n | predicted rec@60 | predicted struct@60 |
|---|---|---|---|
| 50–54 | 433 | 0.6131 | **0.5132** |
| 55–59 | 257 | 0.4598 | **0.3735** |
| 60–64 | 203 | 0.3107 | **0.2165** |
| all 50+ | 893 | 0.5052 | **0.4100** |

## Artefacts

| file | what |
|---|---|
| `results/overnight7/comparison_k60_full_1p2.json` | large protocol, 2,321 queries, rec@1/5/20 under a 60-slot budget |
| `results/overnight7/miss_anatomy_full_1p2.json` | **rec@60 per band, the registered convention** |
| `results/overnight7/band_k60_full_1p2{,_structure}.json` | rec@60 and structure accuracy, molecule budget |
| `results/overnight7/budget_curve_full_1p2.json` | the k-curve for the deficit power law |
| `results/overnight7/comparison_k60_100k_1p2.json` | the floor check, 571 queries |
| `results/overnight7/comparison_common_1p2.json` | both cells on the common protocol, re-scored together |
| `results/overnight7/outcomes_*/` | per-query dumps for all of the above |
| `configs/small_full_1p2.yaml`, `configs/small_100k_1p2.yaml` | the registrations, written before the runs |
