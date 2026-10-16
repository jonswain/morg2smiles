# Night 5 — 2026-10-16 into 2026-10-17

Executes the working-day items from
[night 4's revised plan](overnight-2026-10-15.md) — the size-weighted training
mix, the per-band temperature question, and the pooled-sampling `generate` —
after re-sizing the first of them, because night 4's own error bar turned out
not to apply where the plan proposed to read it.

```
GPU queue
  stage 1  size-weighted mix, seed 1 (8,508 steps, 100k shard)   20:17 -> 23:10
  stage 2  size-weighted mix, seed 2                             23:10 -> 02:04
  stage 3  5 checkpoints on a new large-molecule protocol        02:04 -> 02:55
  stage 4  both mix seeds on the common protocol (the cost)      02:55 -> 03:14
  stage 5  temperature sweep on a large-molecule tuning set      03:15 -> 03:40
  stage 6  T=0.3 and T=0.6 on the large protocol                 03:40 -> 04:22
  stage 7  T=0.3 on the common protocol (the cost)               04:22 -> 04:40
  stage 8  size mix at threshold 35, factor 6 (8,508 steps)      04:40 -> 07:33
  stage 9  score it on both protocols                            07:33 -> 07:58
  stage 10 every arm on the large protocol at T=0.6              07:58 -> 09:08
  stage 11 count fingerprints on the large protocol              09:08 -> 09:36
  stage 12 small_1m at k=60, to measure the budget curve         09:36 -> 10:52
  stage 13 three arms on the common protocol at T=0.6, the cost  10:52 -> TBD

free, from dumps that already existed
  stage 0  the error bar inside each size band                   20:08 -> 20:17
  stage 0b the temperature gain, band by band                       "
  stage 0c size from the fingerprint, and a routing threshold    -> 20:24
  the anatomy of the cliff, and what it reframes                 04:45 -> 05:20
```

**Everything that has ever moved large-molecule recovery in this project moves
it by narrowing the decoder's proposal cloud, and the cloud is narrow in the
same place for every model trained here.** At every size the decoder proposes
about twenty molecules roughly 0.65 Tanimoto from the target, and recovery is
whether that cloud happens to contain an exact preimage — exponentially less
likely the bigger the molecule. Tonight the account displaced three others and
then survived two predictions and a test it could have failed:

- Not the budget (the full-k rate is 1.000 in every band), not ranking (a hit's
  mean rank drifts 4.4 → 8.4 across the whole size range), and not that the
  model nearly gets there (the cloud's distance recedes from 0.69 to 0.57 while
  recovery falls from 0.28 to 0.02).
- Both working interventions tighten the cloud, and in proportion to the
  exposure each band is given: best Tanimoto on a miss moves with exposure in
  every band, at seven times its between-seed sd.
- The same tightening buys less recovery as molecules grow — 2.2 to 2.8
  recovery points per Tanimoto point at 40–49 heavy atoms, 0.4 to 0.9 above 50,
  where the stronger training mix bought the largest cloud gain of any band and
  the smallest recovery gain.
- And the narrowness is in the learned conditional, not the draw: of one seed's
  misses above 50 atoms, 1.6% are recovered by either of two other seeds, three
  differently *trained* models do no better, and at equal spend one model given
  twenty candidates beats three given six each.

The account holds for the 100k checkpoints every one of those measurements was
made on. **On the 1M model at a 60-slot budget it is the wrong account**, and
stage 12 at the end of this document replaces it: there the cloud is the right
*size* almost always (89.8% of queries above 50 atoms get a right-sized
proposal, against 37.8% at 100k) and the exact-preimage rate given the right
size is flat at 11–13% in every band rather than collapsing. What falls with
molecule size is not how many preimages the decoder draws — 1.53 per query at
30–34 against 1.31 above 50 — but how evenly they are spread: above 50 atoms
52% of queries draw none at all while the successful ones draw 2.72 each. The
population splits into fingerprints the conditional can reach and ones it
cannot, and extra budget mostly re-finds what it already found.

The practical ledger is short. **T=0.6, top_p 1.0, everywhere** — free, +1.99
points overall and +7.5 above 35 heavy atoms, and the size-conditional version
of it is dead because cooling never hurts small molecules. **The size-weighted
training mix is a trade, not a gain**, and the trade gets worse the harder it
is pushed: 2.3 small molecules given up per large one gained at threshold 30
×3, 4.4 at threshold 35 ×6, and 10.7 for the step between them, with the
second dose buying nothing the error bar can see above 35 atoms. **The two
compose.** Cooling and the threshold-30 mix stack additively or better in every
band — the mix is worth +3.28 above 35 heavy atoms at T=0.6 against +2.75 at
T=1.0 — which is what two factors of a product do, and which is why the
night's first prediction about them was wrong. **Ensembling is not a route.**
**Widening k inside one model is affordable up to about 40
heavy atoms and nowhere above it**: stage 12 measured the curve to k=60 instead
of extrapolating it, and the recovery deficit is a clean power law in budget
(|r| ≥ 0.991 in every band) whose exponent falls with molecule size, so k=128
reaches 0.90 at 35–39 and 0.95 above 50 atoms costs 10⁹. **And that exponent is
the one quantity capacity moves** — the training mix does not touch it (0.073
against 0.083 at 35+, on a between-seed sd of 0.006) while moving the level,
cooling nudges it to 0.094, and the 1M model sits at 0.303 in the same window
at the same temperature. Level and slope are separate dials; only capacity has
bent the curve. What is left is changing what the model can represent, which
may be the same thing as affording the budget.

Underneath all of it is one measurement error, found five times in one night.
The common protocol draws 2,000 molecules at random and 63% of them are under
30 heavy atoms, so it cannot see anything that acts on part of the size
distribution. It reported the size mix as a flat −1.13 when band by band it is
+4.60 above 35 atoms and −3.11 below 24; it supplied a whole-protocol error bar
of 1.6 points that the 30–34 band contradicts at 2.99; it called fingerprint
degeneracy rare from an 11,669-molecule corpus where the real figure at scale
is 1.40%, and 6.13% at 50–59 atoms; and it closed the count-fingerprint
question at p = 0.32, which turned out to be hiding a four-point *loss* rather
than the gain that re-opening it was meant to find. Tonight's own plan item — the 30–39 band, chosen because
night 4's error bar was small there — was the same error a fifth time, and it
did not clear. Though only half of that was the band's fault: scored at T=0.6
rather than the T=1.0 night 4 had already superseded, the same pre-registered
metric reports +2.25 at 2.4 SE with all six pairs agreeing.

---

## Stage 0 — the plan's metric could not have carried the plan's experiment

Night 4 measured a 0.75-point between-seed sd on `rec@20` and wrote down a rule:
a gap below about 1.6 points between two independently trained runs is not
evidence. It then proposed the size-weighted mix and, correctly, fixed the
metric in advance — *the 30–39 heavy-atom band, 568 queries* — on the grounds
that the 41 queries above 50 atoms have a 7-point standard error.

The rule and the metric were measured on different things, and nothing checked
that they fit together. They do not. `scripts/band_analysis.py` re-reads the
three variance seeds' dumps band by band:

| band | queries | s1 | s2 | s3 | between-seed sd | widest pair |
|---|---|---|---|---|---|---|
| 0–24 | 712 | — | — | — | 0.23 | +0.39, p = 0.91 |
| 25–29 | 512 | — | — | — | 0.23 | +0.39, p = 0.90 |
| 30–34 | 373 | 0.5228 | 0.5121 | 0.4665 | **2.99** | −5.63, p = 0.022 |
| 35–39 | 195 | 0.2462 | 0.2769 | 0.2667 | 1.57 | +3.08, p = 0.33 |
| 40–49 | 123 | 0.1057 | 0.1220 | 0.1057 | 0.94 | +1.63, p = 0.75 |
| 50+ | 41 | 0.0244 | 0.0244 | 0.0244 | 0.00 | 0.00, p = 1 |
| **30–39** | **568** | **0.4278** | **0.4313** | **0.3979** | **1.84** | **−3.35, p = 0.081** |
| all | 1,956 | 0.6053 | 0.6084 | 0.5941 | 0.75 | −1.43, p = 0.10 |

(sd and gaps in points of `rec@20`, generation order, so they sit directly
beside night 4's 0.75.)

**In the 30–39 band the between-seed sd is 1.84 points, not 0.75**, and two
runs differing only in `train.seed` are 3.35 points apart with p = 0.081 — a
gap that would read as a result if it came from an experiment. A single
size-mix run against a single baseline would have needed about 4 points in that
band to be distinguishable from seed luck, and three hours of training would
have bought a number nobody could interpret. This is the same mistake night 4
caught in reverse: there, the global 1.6-point rule was nearly applied to a
paired comparison whose real error bar was 0.4 points. **An error bar belongs to
a comparison, not to a project, and the band is part of the comparison.**

The 30–34 band is worth a second look: 2.99 points of sd on 373 queries, with
one pair at p = 0.022. That is the single noisiest band in the protocol, and it
sits exactly where recovery is steepest in size (0.50 at 30–34 against 0.26 at
35–39). Where the curve is steep, which molecules a run happens to get right is
most sensitive to the run, so this is what one should expect — but it means the
cliff's *shoulder*, not its foot, is where a training experiment is hardest to
measure.

Two design changes followed, both made before anything was trained:

* **Two seeds per arm**, sharing initialisations with `variance_s1` and
  `variance_s2`, so the comparison is two runs against two runs rather than one
  against one.
* **A second evaluation protocol**, 2,400 molecules of 30+ heavy atoms drawn
  from the same clean pool as the common protocol (which holds 17,633 of them),
  where the same comparison carries roughly a 1-point standard error instead of
  1.84. `compare_checkpoints.py --min-heavy-atoms` builds it; its numbers are a
  different protocol and do not join the common table.

Night 4 estimated that stratifying the existing 2,000-molecule set would buy
only ~25% more power and was not worth it. That was right, and this is not the
same move: the set is not re-stratified, it is *enlarged* where it was thin, and
the extra power comes from new queries rather than from re-weighting old ones.
It costs eval time, which is cheap, instead of training time, which is not.

## Stage 0b — the temperature gain grows monotonically with molecule size

The same script, pointed at night 4's three temperature dumps, answers the
plan's second working-day question for free. All three are one checkpoint
(`small_1m`) on the same 1,956 molecules, so every comparison is paired and the
error bars are small.

| band | queries | T=1.0 | T=0.7 | T=0.6 | 1.0 → 0.6 | McNemar p |
|---|---|---|---|---|---|---|
| 0–24 | 712 | 0.9537 | 0.9579 | 0.9579 | +0.42 | 0.61 |
| 25–29 | 512 | 0.9570 | 0.9590 | 0.9648 | +0.78 | 0.42 |
| 30–34 | 373 | 0.8901 | 0.8981 | 0.9035 | +1.34 | 0.23 |
| 35–39 | 195 | 0.8154 | 0.8513 | 0.8821 | +6.67 | 0.002 |
| 40–49 | 123 | 0.6341 | 0.6992 | 0.7154 | +8.13 | 0.031 |
| 50+ | 41 | 0.3659 | 0.3902 | 0.4634 | +9.76 | 0.13 |
| 30–39 | 568 | 0.8644 | 0.8820 | 0.8961 | +3.17 | 9.1e-04 |
| all | 1,956 | 0.8962 | 0.9080 | 0.9162 | +1.99 | 1.3e-05 |

Night 4 reported this as "+7.5 points above 35 heavy atoms, +0.75 below" and
read it as an effect *concentrated* in large molecules. The band-by-band view
says something stronger and more useful: the gain **rises monotonically with
size across six bands**, from under half a point below 24 atoms to nearly ten
points above 50. Nothing in the small bands is distinguishable from zero.

That is a dose-response curve, and it makes the obvious hypothesis testable:
if cooling helps more the larger the molecule, the optimum temperature is
*lower* for large molecules than the 0.6 chosen on a random draw where 64% of
queries are under 30 atoms. Night 4 measured 0.5 once, on such a draw, and
found it worse overall — which is consistent with 0.5 being worse on the small
molecules that dominated that draw and better on the large ones it barely
contained. Stages 5 and 6 settle it: sweep on large molecules held out of the
common protocol, verify the pick on the large protocol.

If it holds, it is free: a fingerprint's bit count predicts its molecule's size
without the molecule, so the decoder can pick its own temperature per query
before generating anything.

## Stage 0c — the decoder can estimate size from its own input

A size-dependent temperature is only deployable if size can be read off the
fingerprint, since at generation time the molecule is what is unknown. It can:
`scripts/size_from_fingerprint.py` on 5,000 clean-pool molecules gives
**r = 0.83** between set-bit count and heavy-atom count, rising monotonically
across every band with no sign of folding flattening it over the range that
matters.

| band | molecules | mean set bits | sd |
|---|---|---|---|
| 0–24 | 1,836 | 38.7 | 7.4 |
| 25–29 | 1,286 | 48.6 | 6.2 |
| 30–34 | 955 | 55.5 | 7.0 |
| 35–39 | 530 | 61.3 | 8.4 |
| 40–49 | 292 | 66.1 | 12.9 |
| 50+ | 101 | 78.8 | 17.0 |

As a classifier for "at least 35 heavy atoms" the best single threshold is
**62 set bits**: precision 0.77, recall 0.64, accuracy 0.90 against a base rate
of 0.19. That is imprecise, and it does not matter much, because the error is
asymmetric — cooling a small molecule by mistake costs under half a point and
is not distinguishable from zero (p = 0.61 at 0–24 atoms), while cooling a
large one is worth up to ten. A routing rule with this accuracy keeps most of
the upside and risks almost nothing.

The threshold is fixed *against molecule size*, on the pool, not against
recovery on the evaluation set, so a policy built from it is not fitted to the
set it is scored on. `scripts/temperature_policy.py` scores it from dumps.
Validated on night 4's existing arms, where it reproduces the arithmetic one
would predict — routing the 300 of 1,956 queries with 62+ bits from T=1.0 to
T=0.6 captures +0.97 points of the +1.99 that routing everything captures —
and prints the bound any input-only rule is working against: **0.9264**, the
per-query best of the two arms chosen with hindsight.

That bound is worth a moment. Night 4's pooled-temperature scheme reaches
**0.9279**, which is *above* it. Pooling is not choosing between two orderings;
it merges the candidate lists and re-ranks the union, so it can beat the better
of the two arms on a query where neither arm's own ordering puts the answer in
the top 20. Routing is the cheap approximation to pooling — one forward pass
instead of three — and the gap between 0.9264 and 0.9279 is the price of the
approximation, before any routing error.

---

## Stages 1–3 — the size-weighted mix works, above 35 heavy atoms

Two runs at 8,508 steps on the 100k shard, identical to `variance_s1` and
`variance_s2` in schedule and initialisation, differing only in the sampler:
a molecule of 30 or more heavy atoms is three times as likely to be drawn,
which takes that group from 38.9% of the shard to **65.6% of draws**. Sampling
is with replacement, so the epoch length, the step count and the cosine horizon
are unchanged.

Read on the new protocol: 2,400 molecules of 30+ heavy atoms from the same clean
pool, 2,321 of them fingerprint-unseen, `rec@20` in generation order.

| band | queries | baseline (3 seeds) | mix (2 seeds) | gap | SE | |
|---|---|---|---|---|---|---|
| 30–34 | 1,189 | 0.4886 | 0.4933 | +0.46 | 0.60 | 0.8 SE |
| 35–39 | 625 | 0.2757 | 0.3008 | **+2.51** | 0.76 | 3.3 SE |
| 40–49 | 380 | 0.1026 | 0.1368 | **+3.42** | 1.52 | 2.3 SE |
| 50+ | 127 | 0.0157 | 0.0354 | **+1.97** | 0.88 | 2.2 SE |
| **30–39 (pre-registered)** | 1,814 | 0.4153 | 0.4270 | +1.17 | 0.65 | 1.8 SE |
| 35+ | 1,132 | 0.1885 | 0.2160 | **+2.75** | 0.86 | 3.2 SE |
| all 30+ | 2,321 | 0.3422 | 0.3580 | +1.58 | 0.72 | 2.2 SE |

(Arm means; SE from the between-seed sd of each arm, three against two. The
individual runs and all 10 pairwise McNemar tests are in
`results/overnight5/band_large_generation.json`.)

**The pre-registered metric did not clear.** The 30–39 band gives +1.17 points
at 1.8 SE, which by the rule written down before the run is not evidence. That
has to be said first, because it is what the experiment was defined to report.

**The band structure says why, and it is not a rescue.** The 30–39 band is
three-fifths 30–34 molecules, and the 30–34 band moves +0.46 points — nothing.
The band was chosen for *power*, because it was the largest band on the common
protocol, not because the effect was expected there. The effect starts at 35:
+2.51 at 35–39, +3.42 at 40–49, +1.97 above 50 where the baseline recovers 1.6%
of molecules and the mix recovers 3.5%. On the 35+ band — which is the band
night 4 reported its decode result on, not a band invented tonight — the gap is
**+2.75 points at 3.2 SE**, and all six cross-arm pairs favour the mix.

So the honest summary is: **over-sampling large molecules improves large-molecule
recovery, by about 2.5 to 3.5 points in the bands above 35 heavy atoms, and the
pre-registered test of it failed because the band it named was half composed of
molecules the intervention does not affect.** The right lesson is not that
pre-registration is inconvenient; it is that the metric was chosen on the error
bar alone, when it should have been chosen on the error bar *and* a prediction
about where the effect would be. Night 4 fixed the band because the error bar
demanded a decision in advance, and made that decision with the only
information it had — power. Tonight adds the missing half: the mix's effect
should have been predicted to start where the over-sampling starts biting, not
where the queries are.

**This is the first training-side intervention in the project to move the
cliff.** Night 4's decode result moved the same bands by more (+6.7 at 35–39,
+8.1 at 40–49) and cost nothing, but it was a decoder setting applied to a
fixed model. This changes what the model knows.

The two were *measured* independently — the mix arms at the protocol's T=1.0,
the temperature result on a model without the mix — which is not the same thing
as the two gains adding, and nothing here establishes that they do. Both work
on the same bands and both plausibly work the same way, by spending more of the
sampling budget on fewer and likelier strings. Stage 10 tests it directly.

A caveat that cuts the other way: 2.47% of the shard has 50+ heavy atoms, and
the mix gives that group 4.2% of draws. Recovery there went from 2 molecules in
127 to 4.5. Both numbers are tiny, the comparison is 2.2 SE, and nothing about
the 50+ band is settled by this.

## Stage 4 — what the mix costs: the exchange rate, and why the common protocol cannot see it

The large protocol only holds molecules of 30+ heavy atoms, so by construction
it cannot show what the mix gave up to get them. Scoring both mix seeds on the
common protocol — the same 2,000 random pool molecules, against the same three
baseline seeds — shows it, band by band.

| band | queries | baseline | mix | gap | SE | | pairs favouring |
|---|---|---|---|---|---|---|---|
| 0–24 | 712 | 0.8001 | 0.7690 | **−3.11** | 0.97 | 3.2 SE | 0/6 |
| 25–29 | 512 | 0.6960 | 0.6670 | **−2.90** | 0.32 | 9.0 SE | 0/6 |
| 30–34 | 373 | 0.5004 | 0.4960 | −0.45 | 2.03 | 0.2 SE | 2/6 |
| 35–39 | 195 | 0.2632 | 0.2949 | **+3.16** | 1.57 | 2.0 SE | 6/6 |
| 40–49 | 123 | 0.1111 | 0.1870 | **+7.59** | 1.71 | 4.4 SE | 6/6 |
| 50+ | 41 | 0.0244 | 0.0488 | +2.44 | 0.00 | — | 6/6 |
| 30–39 | 568 | 0.4190 | 0.4269 | +0.79 | 1.56 | 0.5 SE | 4/6 |
| 35+ | 359 | 0.1838 | 0.2298 | **+4.60** | 0.66 | 7.0 SE | 6/6 |
| all | 1,956 | 0.6026 | 0.5913 | −1.13 | 0.77 | 1.5 SE | 1/6 |

**The mix is not a gain, it is a trade, and both sides of it are clean.** Every
one of the six cross-arm pairs is worse below 30 heavy atoms and every one is
better above 35. The sign is not in doubt in either direction; only the size is.

In molecules rather than points, on the 1,956 fingerprint-unseen queries:

```
0-24    -22.2        35-39    +6.2
25-29   -14.8        40-49    +9.3
30-34    -1.7        50+      +1.0
        ------                -----
        -38.7                +16.5     net -22.2 molecules = -1.13 points
```

**Roughly 2.3 small molecules are given up per large molecule gained.** Whether
that is a good trade is not a fact about the model. It depends on what the
inversion is for: 2.3 molecules under 30 heavy atoms against one above 35 is a
bad deal for a screening-library round-trip and a good one for anything aimed
at the molecules the model currently cannot invert at all. The project has no
stated answer, and it should stop pretending the question does not exist.

**This is where the common protocol fails as the project's one table.** It
reports −1.13 points and reads as "the size mix slightly hurt the model". The
reported number is the trade's weighted average, and the weights are the
ChEMBL pool's size distribution: 63% of its queries are under 30 heavy atoms.
Nothing recommends that weighting except that it is what the pool happens to
contain. A protocol with a different draw would report the same model as a
clear improvement, and neither number would be wrong. The common protocol is
still the right comparable table for *capacity* questions, where the effect is
expected to be flat in size (more parameters, more steps, more data all moved
every band together on nights 1–3), and it is the wrong summary for anything
that redistributes.

Two details worth keeping:

**The exposure accounting does not explain the pattern.** Over-sampling took
the under-30 group from 61.1% of draws to 34.4% — nearly halved — and it lost
about 3 points. It took 30–34 from 21.3% to 36.0% — nearly doubled — and that
band moved +0.46 on the large protocol and −0.45 here, which is to say not at
all. So recovery is not a function of exposure. What the extra exposure bought
was concentrated where the model was failing worst (0.18 at 35+), and it bought
nothing in the band where the model was already at 0.50. Exposure is necessary
and not sufficient; something else binds at 30–34, and this is the second night
running that the 30–34 band has refused to respond to an intervention that
moved every band above it.

**The two protocols agree on the 35+ gap, within their error bars**: +2.75 ±
0.86 on the large protocol's 1,132 queries, +4.60 ± 0.66 on the common
protocol's 359. They are different draws from the same pool, so this is a
consistency check rather than a replication, and it passes.

## Stages 5–7 — the decoder does not want a size-conditional temperature

Night 4 cooled the decoder from T=1.0 to 0.6 and gained +1.99 points overall,
all of it above 30 heavy atoms. Stage 0b turned that into a monotone
dose-response, which suggested the optimum is colder still for large molecules,
and stage 0c showed a fingerprint's bit count can predict size well enough to
route on. Stages 5–7 tested the whole chain and **none of it survives**.

**Stage 5, the sweep** — 500 molecules of 30+ heavy atoms from the tuning pool,
disjoint from the common protocol, `con@20`:

| T | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 1.0 |
|---|---|---|---|---|---|---|
| con@20 | 0.8392 | 0.8247 | 0.8392 | 0.8309 | 0.8144 | 0.8041 |
| budget filled | 0.501 | 0.590 | 0.649 | 0.709 | 0.738 | 0.852 |
| samples/query | 138 | 126 | 119 | 110 | 104 | 87 |

The script's pick was T=0.3, +3.51 points over the default. That pick is an
artefact of tie-breaking: 0.3 and 0.5 are *identical* to four decimals, the top
four settings span 1.45 points on 485 queries, and 0.3 is the edge of the grid.
So stage 6 treated it as a question — is colder than night 4's verified 0.6
better? — rather than as a finding.

**Stage 6, on the large protocol** (2,321 queries, one checkpoint, paired, so
these error bars are the small ones):

| band | queries | T=0.6 | T=0.3 | gap | McNemar p |
|---|---|---|---|---|---|
| 30–34 | 1,189 | 0.8949 | 0.8923 | −0.25 | 0.77 |
| 35–39 | 625 | 0.8336 | 0.8512 | +1.76 | 0.099 |
| 40–49 | 380 | 0.6789 | 0.7053 | +2.63 | 0.164 |
| 50+ | 127 | 0.3465 | 0.3622 | +1.57 | 0.754 |
| 35+ | 1,132 | 0.7270 | 0.7473 | **+2.03** | **0.019** |
| all 30+ | 2,321 | 0.8130 | 0.8216 | +0.86 | 0.103 |

The dose-response does continue below 0.6, and again only above 35 atoms.

**Stage 7, on the common protocol**, which is where it falls apart. Four
temperatures on the same 1,956 molecules, `con@20`:

| band | queries | T=1.0 | T=0.7 | T=0.6 | T=0.3 |
|---|---|---|---|---|---|
| 0–24 | 712 | 0.9537 | 0.9579 | 0.9579 | 0.9607 |
| 25–29 | 512 | 0.9570 | 0.9590 | 0.9648 | 0.9609 |
| 30–34 | 373 | 0.8901 | 0.8981 | 0.9035 | 0.8901 |
| 35–39 | 195 | 0.8154 | 0.8513 | 0.8821 | 0.8667 |
| 40–49 | 123 | 0.6341 | 0.6992 | 0.7154 | 0.7317 |
| 50+ | 41 | 0.3659 | 0.3902 | 0.4634 | 0.4390 |
| 35+ | 359 | 0.7019 | 0.7465 | 0.7772 | 0.7716 |
| all | 1,956 | 0.8962 | 0.9080 | **0.9162** | 0.9126 |

Here 0.6 is the peak and 0.3 is 0.36 points below it (p = 0.46), and on this
set's 35+ slice 0.3 is 0.56 points *behind* 0.6 — the opposite sign to the
large protocol, though the two are compatible within the common protocol's
1.62-point error bar there. The large protocol has three times the queries
above 35 atoms and is the better measurement; the fair statement is that
**0.6 → 0.3 is worth at most about 2 points on large molecules, measured once,
with a sign disagreement between two draws from the same pool**, against the
1.0 → 0.6 step which is +6.96 at 35+ with p = 2.5e-04 and +1.64 overall with
p = 9.7e-04. One of those is a result and the other is a lead.

And T=0.3 is not free. On the common protocol it draws 167 samples per query
against 146 at 0.6 and 123 at 1.0, and only 28.5% of queries manage to fill
their 20-slot budget at all — the decoder has become so peaked it cannot
propose 20 distinct molecules. 14% more compute for no measurable gain.

**The routing rule is dead, and the reason is worth more than the rule.**
Scoring the pre-registered policy — 62+ set bits sampled at 0.3, the rest at
0.6 — over the paired dumps:

```
T=0.3 everywhere            0.9126
T=0.6 everywhere            0.9162
policy (bits >= 62)         0.9172    300 of 1,956 routed cold   +0.10 +/- 0.25
per-query oracle (bound)    0.9315
```

+0.10 points, standard error 0.25. The best threshold anywhere on the curve is
+0.36 at 72 bits, chosen with hindsight on 93 queries, and that is the ceiling
on the whole idea. The cause is visible in the 0–24 band above: cooling to 0.3
scores 0.9607 there against 0.9537 at T=1.0 — cooling does not hurt small
molecules, it just does not help them. **An intervention that only helps
subgroup X is worth conditioning on X only if it hurts not-X.** Night 4's
monotone dose-response made routing look obviously right; the missing
measurement was the cost side, and the cost side is flat. Stage 0c's whole
apparatus — the bit-count regression, the 62-bit threshold, the oracle bound —
answered a question that did not need answering, and it took three cheap stages
to find that out instead of one.

**Adopted: T=0.6, top_p 1.0, everywhere.** No routing. `TEMPERATURE_POOL` and
the pooled-sampling `generate` stay opt-in and unrecommended: pooling three
temperatures reaches 0.9279 against 0.9162 for a flat 0.6, which is +1.17
points for three times the forward passes, and nothing in the project yet
needs that trade.

---

## The anatomy of the cliff — written while stage 8 trained

Everything in this part is free: it re-reads dumps that already exist, so it
cost no GPU and ran on the CPU while the `size_mix_t35` arm was training. It
began as one question — what is a large-molecule miss actually made of — and
turned into the night's main thread, because the answer reframes both of the
results above and one of the README's claims.

Five nights have measured how far recovery falls with molecule size and none
has asked what the failure consists of. The dumps answer it for nothing.
`scripts/miss_anatomy.py` separates four candidate explanations, reading
`variance_s1` on the large protocol (2,321 queries of 30+ heavy atoms) and on
the common protocol (1,956 of every size):

| band | queries | rec@20 | struct@20 | collisions among hits | best Tanimoto on a miss | misses ≥ 0.9 | budget full | mean hit rank |
|---|---|---|---|---|---|---|---|---|
| 0–24 | 712 | 0.7711 | 0.7626 | 1.1% | 0.672 | 8.6% | 0.999 | 4.4 |
| 25–29 | 512 | 0.6445 | 0.6406 | 0.6% | 0.702 | 7.1% | 1.000 | 5.3 |
| 30–34 | 1,189 | 0.4491 | 0.4289 | 4.5% | 0.703 | 8.7% | 1.000 | 6.1 |
| 35–39 | 625 | 0.2384 | 0.2080 | 12.8% | 0.691 | 8.4% | 1.000 | 7.7 |
| 40–49 | 380 | 0.0947 | 0.0816 | 13.9% | 0.645 | 7.0% | 1.000 | 8.4 |
| 50–59 | 95 | 0.0000 | 0.0000 | — | 0.574 | 3.2% | 1.000 | — |
| 60+ | 32 | 0.0000 | 0.0000 | — | 0.527 | 0.0% | 1.000 | — |

(Rows up to 29 atoms from the common protocol, 30+ from the large one.)

Three of the four explanations die here.

**It is not the budget.** Every band fills its 20 slots for essentially every
query — 1.000 at every size, on a protocol where `small_1m` manages only 0.639.
The weak 100k models have no trouble producing 20 distinct valid molecules for a
60-atom fingerprint. They are simply the wrong 20. "It runs out of guesses" is
the intuitive story and it is false.

**It is not near-missing.** On queries never matched, the best Tanimoto reached
anywhere in the 20 is ~0.68 and **flat across every band** from 0–24 to 40–49,
with the ≥ 0.9 tail at 7–9% throughout. The model is not creeping closer to
large molecules and failing at the last step; it is the same distance away at
every size. Whatever changes with size, it is not the model's aim.

**It is not ranking.** The mean rank of a hit drifts from 4.4 to 8.4, which
says large recoveries use more of the budget, but a hit at rank 8 of 20 is not
a hit being lost.

**What does change is the fourth thing, and it is the metric's own footing.**
The fraction of recoveries that are a *different molecule carrying the same
fingerprint* goes 1.1% → 0.6% → 4.5% → 12.8% → 13.9%. Above 35 heavy atoms
about one in eight successes is not the query's molecule. `recovery` counts
those as hits, correctly — the task is inverting a fingerprint, and a different
preimage is a valid answer — but it means `recovery` and
`structure_accuracy` are drifting apart exactly where the project's attention
now is, and that the honest reading of the cliff depends on which one is meant.

So the shape of the failure is: at every size the model proposes a cloud of
twenty molecules roughly 0.68 Tanimoto from the target; recovery is whether
that cloud happens to contain an exact preimage. That cloud is as close for a
60-atom molecule as for a 20-atom one, and exponentially less likely to contain
an exact hit, because the number of molecules within a Tanimoto radius grows
with the size of the molecule at its centre. That is a combinatorial account of
the cliff rather than a capability one, and it predicts something testable:
what large molecules need is not a model that aims better but one that
proposes a far narrower cloud — which is precisely what cooling the decoder
does, and why cooling bought 7–10 points above 35 atoms and nothing below 30.
The size mix fits the same account from the other side: more exposure to large
molecules tightens the cloud where it was widest.

The 50–59 and 60+ rows are worth splitting out from the usual 50+ band:
`variance_s1` recovers **zero of 127** molecules above 50 heavy atoms. The
+1.97 points the size mix showed in the 50+ band earlier is three molecules at
50–59 out of 95, one of them an exact structure and two of them collisions.
Nothing above 50 atoms is working yet, and nothing in this project has moved it.

### A prediction, registered before stage 10 ran

The account above — that both working interventions narrow the proposal cloud
rather than aim it better — makes a falsifiable claim about the experiment that
was still training when this was written. Stage 10 scores every arm on the
large protocol at T=0.6 instead of 1.0, which is the first time the mix and the
cooled decoder are applied together.

* **If both work by narrowing the cloud**, they compete for the same points.
  The mix's +2.75 above 35 heavy atoms should *shrink* when measured on top of
  a decoder that has already been cooled — call it under +1.5 — because cooling
  has already collected much of what tightening the distribution can collect.
* **If they are independent mechanisms**, the gap should survive at roughly its
  T=1.0 size, +2.5 to +3.

Written at 05:30 on 2026-10-17, before stage 8 finished training, with the
prediction being *the first one*. A result either way is worth more than the
+2.75 figure on its own, because the project is about to choose what to spend
an 18-hour full-ChEMBL run on, and "these two gains add" is an assumption that
would otherwise be made silently.

### Is the collision trend the model's, or the fingerprint's?

Partly the fingerprint's, and that part is measurable without a model at all.
`scripts/fingerprint_ambiguity.py` groups all 950,967 molecules of the 1M shard
by folded Morgan r=2/2048 key and counts how many share theirs with at least
one other molecule:

| band | molecules | share their fingerprint | mean group | largest group |
|---|---|---|---|---|
| 0–24 | 334,112 | 1.02% | 1.019 | 39 |
| 25–29 | 248,002 | 1.11% | 1.019 | 16 |
| 30–34 | 186,942 | 1.25% | 1.023 | 39 |
| 35–39 | 96,549 | 1.63% | 1.032 | 39 |
| 40–49 | 62,456 | 2.97% | 1.064 | 39 |
| 50–59 | 17,670 | **6.13%** | 1.118 | 39 |
| 60+ | 5,236 | 5.94% | 1.102 | 8 |
| all | 950,967 | 1.40% | 1.026 | 39 |

**The representation does lose its grip on large molecules**: a six-fold rise
in ambiguity from the smallest band to 50–59, in ChEMBL alone, with 943,177
distinct fingerprints for 950,967 distinct molecules. So the collision trend in
the dumps is not an artefact of a weak decoder — it is there in the input
before any model sees it, and it rises with size in the same direction and over
the same bands.

**What cannot be concluded is the level.** The corpus rate and the model's
collision rate are different quantities, and the fact that they happen to agree
below 24 heavy atoms (1.02% against 1.1%) is not evidence of anything. The
corpus figure is a *lower bound*: it counts twins that exist in these 950k
molecules, while the decoder draws from all of chemical space, where a 50-atom
fingerprint has vastly more preimages than ChEMBL happens to contain. The
honest statement is that ambiguity grows with molecule size in the fingerprint
itself, by at least this much, and that the model's collisions grow with size
too.

Two consequences for how this project reports itself:

**`recovery` and `structure_accuracy` must both be quoted above 35 heavy
atoms.** They differ by 2 points overall and by 12–14% of the hits in the large
bands, and they answer different questions — "did the model invert this
fingerprint" against "did it find the molecule". The first is the task; the
second is what a chemist would ask. Reporting only the first, in a regime where
one hit in eight is a different molecule, overstates what the model does.

**It makes counts worth re-testing.** Night 3 trained a count-fingerprint arm
and closed the question on the common protocol: 0.5890 against 0.5890, p = 0.32.
That protocol is 63% molecules under 30 heavy atoms, where ambiguity is 1% and
counts have nothing to fix. Counts are the cheapest way to make a fingerprint
pin a large molecule harder, and the checkpoint already exists, so stage 11
re-reads it on the large protocol — for recovery by band, and for the collision
rate among its hits, which is the reading the harder count-match oracle does
not confound. *(It did, and the answer was no: counts are 4.18 points worse
there, and the stage 11 section at the end of this document takes this
reasoning apart.)*

### What the budget is worth, per band

A full budget is not a saturated budget, and the same ranks answer that too.
`rec@k` per band, `variance_s1`, bands to 29 atoms from the common protocol and
30+ from the large one:

| band | queries | @1 | @2 | @5 | @10 | @20 | × per doubling (10→20) | hits in slots 11–20 |
|---|---|---|---|---|---|---|---|---|
| 0–24 | 712 | 0.2935 | 0.4129 | 0.5730 | 0.6770 | 0.7711 | 1.14 | 12.2% |
| 25–29 | 512 | 0.1973 | 0.2734 | 0.4277 | 0.5332 | 0.6445 | 1.21 | 17.3% |
| 30–34 | 1,189 | 0.1001 | 0.1564 | 0.2700 | 0.3524 | 0.4491 | 1.27 | 21.5% |
| 35–39 | 625 | 0.0288 | 0.0528 | 0.1056 | 0.1696 | 0.2384 | **1.41** | 28.9% |
| 40–49 | 380 | 0.0079 | 0.0105 | 0.0289 | 0.0658 | 0.0947 | **1.44** | 30.6% |
| 50–59 | 95 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | — | — |

**The return on budget rises monotonically with size**, 1.14× per doubling below
24 heavy atoms to 1.44× at 40–49, and nearly a third of large-molecule hits are
found in the second half of the budget against an eighth of small-molecule
hits. That is the combinatorial account's prediction and it holds across five
bands. It needed the large protocol to see: on the common protocol's 123
queries at 40–49 the same quantity reads 1.22 and breaks the monotonicity, a
reminder that this protocol's thin tail has been producing noise all along.

It also prices the obvious route, and the price is bad. At 1.41× per doubling,
lifting 35+ recovery from 0.163 to 0.50 takes 3.3 doublings — **k ≈ 200**, ten
times the current budget — and that is a *lower* bound, because each doubling's
return decays (at 35–39 the ladder gives 1.83× from 5→10 and 1.41× from 10→20).
So "just sample more" is worth about a factor of ten in compute for perhaps
half the gap, and nothing at all above 50 heavy atoms, where recovery is 0.0000
at every k from 1 to 20 and no rate exists to extrapolate. The budget is the
cheapest knob in the project and it is not the answer.

The honest caveat on this section: it is one checkpoint's ranks, and `rec@k` at
k < 20 is read off a candidate list generated under a 20-molecule budget rather
than from runs actually given budget k. Oversampling means a run with k=5 would
draw fewer samples and land in a different place; these numbers assume the
prefix of a 20-slot list behaves like a 5-slot run, which is right for
generation order and not exactly right for anything else.

### What counts actually buy, and what stage 11 can therefore show

The same scan with `--counts` answers the README's "+0.0002" properly, on
950,967 molecules instead of 11,669:

| band | binary | counts | reduction |
|---|---|---|---|
| 0–24 | 1.02% | 0.16% | 6.4× |
| 25–29 | 1.11% | 0.20% | 5.5× |
| 30–34 | 1.25% | 0.26% | 4.8× |
| 35–39 | 1.63% | 0.28% | 5.8× |
| 40–49 | 2.97% | 0.55% | 5.4× |
| 50–59 | 6.13% | 1.11% | 5.5× |
| 60+ | 5.94% | 1.03% | 5.8× |
| all | 1.40% | 0.25% | 5.6× |
| largest group | 39 molecules | 5 molecules | |

**Counts carry real information that binary bits throw away** — 5.6× less
ambiguity, uniformly — which is a very different statement from +0.0002. The
reduction *factor* is flat across the size distribution, so counts are not
specifically a large-molecule fix; the absolute gain is largest there only
because there is more ambiguity to remove (5.0 points at 50–59 against 0.86
below 24). Counts take a 50-atom molecule back to roughly the ambiguity a
20-atom molecule has under binary bits.

**This revises what stage 11 should be expected to show, so it is recorded
before the run.** Ambiguity is not what makes the cliff: at 35–39 heavy atoms
binary ambiguity is 1.63% while 76% of queries fail, and collisions make
`recovery` *easier* rather than harder. So the mechanism by which counts could
help is the **input** side — the encoder gets a multiplicity per bit, and it is
inverting a less lossy description of the molecule — not collision relief. Two
predictions follow, and they point opposite ways:

* On **`recovery`**, counts should be neutral or slightly *worse*, mechanically,
  on two counts: the oracle demands an exact count match, which is a strictly
  harder target, and 5.6× fewer collisions means 5.6× fewer lucky hits on a
  different preimage. Night 3's exact parity (0.5890 against 0.5890) is, read
  this way, already a win for counts that was scored as a null.
* On **`structure_accuracy` relative to `recovery`** — the collision rate among
  hits — counts should show a clear drop, because that quantity is what the
  ambiguity table directly governs. This is the reading the harder oracle does
  not confound, and it is the one worth looking at first.

If counts also lift recovery above 35 heavy atoms, that is the input-side
bottleneck showing up where it was always most likely to be visible, and it
costs a config flag. If they do not, the input is not the constraint and the
project can stop asking.

### The mix result, re-read on structure accuracy

Tonight's collision finding puts a question to tonight's other finding: if one
recovery in eight above 35 heavy atoms is a different preimage, is the mix's
gain partly collisions? `band_analysis.py --metric structure` asks for the
query's own molecule instead, over the same dumps.

| band | queries | recovery gap | structure gap | pairs (structure) |
|---|---|---|---|---|
| 30–34 | 1,189 | +0.46 | +0.06 | 3/6 |
| 35–39 | 625 | +2.51 | **+3.28** | 6/6 |
| 40–49 | 380 | +3.42 | **+3.46** | 6/6 |
| 50+ | 127 | +1.97 | +1.05 | 4/6 |
| 30–39 | 1,814 | +1.17 | +1.17 | 6/6 |
| 35+ | 1,132 | +2.75 | **+3.09** | 6/6 |
| all 30+ | 2,321 | +1.58 | +1.54 | 6/6 |

**The gain is not collision-driven — it is larger when the query's own molecule
is demanded**, +3.09 against +2.75 above 35 heavy atoms, with all six cross-arm
pairs agreeing. The one band that shrinks is 50+, from +1.97 to +1.05, which is
exactly what stage 0d predicted: two of the mix's three hits above 50 atoms were
different preimages, so most of that band's apparent gain was the metric being
generous. The 50+ claim was already the weakest thing in this write-up and it
is now weaker.

The cost side is unchanged by the same re-reading — −2.83 at 0–24 and −3.09 at
25–29 on the common protocol, 0/6 pairs both ways — so the trade is a trade on
either metric.

One detail in the pre-registered band is worth noting without making anything
of it: on structure accuracy, 30–39 gives the same +1.17 but now **6/6** pairs
favour the mix rather than 4/6. It is still 1.7 SE and still does not clear the
rule written down in advance. A sign test over six non-independent pairs is not
a rescue, and the band is still three-fifths molecules the intervention does
not move.

### Both interventions gain more on structure accuracy than on recovery, for the same reason

Doing the same re-reading to night 4's temperature dumps gives the matching
result. Cooling `small_1m` from T=1.0 to 0.6, consensus order:

| band | queries | recovery gain | structure gain |
|---|---|---|---|
| 0–24 | 712 | +0.42 | +0.28 |
| 25–29 | 512 | +0.78 | +0.39 |
| 30–34 | 373 | +1.34 | +0.54 |
| 35–39 | 195 | +6.67 | **+7.69** |
| 40–49 | 123 | +8.13 | **+12.19** |
| 50+ | 41 | +9.76 | +4.88 |
| 35+ | 359 | +7.53 | **+8.91** |
| all | 1,956 | +1.99 | +1.94 |

So both of the project's working interventions — one a decode setting, one a
training mix — are *understated* by the metric the project reports. The
mechanism is visible directly in the collision rates among each arm's own hits:

| at 35+ heavy atoms | T=1.0 | T=0.6 | T=0.3 |
|---|---|---|---|
| recovery | 0.6574 | 0.7354 | 0.7187 |
| structure accuracy | 0.6156 | 0.7047 | 0.6769 |
| collisions among hits | 6.4% | **4.2%** | 5.8% |
| collisions at 40–49 | 9.2% | **3.7%** | 4.9% |

**Cooling roughly halves the share of large-molecule hits that are a different
preimage.** A hot decoder scores some of its large-molecule recoveries by
landing on a near-twin; a cooled one lands on the molecule itself. Since
`recovery` credits both, it gives the hot arm hits the cooled arm is not
credited extra for, and the gap it reports is smaller than the gap in molecules
found.

That also separates the two components of the collision rate, which stage 0d
could not. Ambiguity in the fingerprint is fixed for a given query set — the
same 1,956 molecules here — so any difference between these three arms is the
*model's* imprecision, not the representation's. The collision rate among hits
is therefore readable as a precision measure: 13.0% for a 100k-shard model at
35+ (stage 0d), 6.4% for `small_1m` at T=1.0, 4.2% for the same checkpoint
cooled. Better and sharper models collide less, and the floor underneath them
is the fingerprint's own 2.65% at 35+ — which is a floor for structure
accuracy, and for the *corpus*; the decoder's floor is higher, since it may
propose preimages ChEMBL does not contain.

---

## Stages 8–9 — a second dose, and the price of exposure

Stage 8 trained the same architecture on the same 100k shard for the same
8,508 steps with the sampler re-weighted harder and higher: threshold 35
heavy atoms, factor 6, one seed (`size_mix_t35`, 2 h 53 min). The two mixes
now in hand differ only in how much of the model's training diet comes from
which size band:

| band | share of shard | mix3x30 (thr 30, ×3) | mix6x35 (thr 35, ×6) |
|---|---|---|---|
| 0–24 | 35.2% | 19.8% (0.56×) | 17.9% (0.51×) |
| 25–29 | 25.9% | 14.6% (0.56×) | 13.2% (0.51×) |
| 30–34 | 19.6% | 33.1% (1.69×) | 10.0% (0.51×) |
| 35–39 | 10.3% | 17.3% (1.69×) | 31.4% (3.06×) |
| 40–49 | 6.5% | 11.0% (1.69×) | 19.9% (3.06×) |
| 50+ | 2.5% | 4.2% (1.69×) | 7.6% (3.06×) |

The point of the second dose was to ask whether the response keeps growing.
It does not. On the large protocol, which has 1,132 fingerprint-unseen queries
above 35 heavy atoms, `rec@20` in generation order:

| band | queries | baseline | mix3x30 | mix6x35 |
|---|---|---|---|---|
| 30–34 | 1,189 | 0.4886 | +0.46 | **−1.43** |
| 35–39 | 625 | 0.2757 | +2.51 | +2.19 |
| 40–49 | 380 | 0.1026 | +3.42 | +4.47 |
| 50+ | 127 | 0.0157 | +1.97 | +1.57 |
| 35+ | 1,132 | 0.1885 | **+2.75** | **+2.89** |
| all 30+ | 2,321 | 0.3422 | +1.58 | +0.67 |

Tripling the large-molecule exposure again — 1.69× to 3.06×, and 19.3% of the
diet to 58.9% — moved 35+ recovery by +0.14 points, which is a tenth of its
error bar. On structure accuracy it moved it the other way, +3.09 to +2.74.
The common protocol's 359 queries above 35 atoms read the second dose as
larger (+4.60 to +6.13, and +3.71 to +5.66 on structure), but that is a third
as many queries and the two readings are compatible; the better-powered
protocol is the one to quote, and it says the first dose had already taken
what exposure has to give above 35 atoms.

### What it cost, and the price of a doubling

`scripts/exposure_response.py` (new) puts each band's gap next to that band's
exposure ratio, converts points into molecules, and divides. On the common
protocol, which is the only one of the two that contains the bands being paid
from:

| band | queries | exposure | gap | molecules | points per doubling |
|---|---|---|---|---|---|
| 0–24 | 712 | 0.51× | −6.55 | −46.7 | +6.74 |
| 25–29 | 512 | 0.51× | −6.71 | −34.3 | +6.89 |
| 30–34 | 373 | 0.51× | −4.47 | −16.7 | +4.59 |
| 35–39 | 195 | 3.06× | +6.50 | +12.7 | +4.03 |
| 40–49 | 123 | 3.06× | +5.96 | +7.3 | +3.70 |
| 50+ | 41 | 3.06× | +4.88 | +2.0 | +3.03 |
| all | 1,956 | — | **−3.87** | **−75.7** | — |

Six bands, gaps running from −6.71 to +6.50, and a straight line through
log₂ exposure fits them at **+4.52 points per doubling with r = 0.989**. For
this mix there is no band that defies its exposure: tell me how much more or
less often the model saw a size band and I can tell you what happened to that
band's recovery. The lower dose fits the same line less well (+3.91 per
doubling, r = 0.779), and the band that spoils it is 30–34, the one band
whose exposure the two mixes move in opposite directions.

In molecules the trade got worse exactly as fast as the dose grew:

| | molecules lost | molecules gained | given up per one gained | whole protocol |
|---|---|---|---|---|
| mix3x30 | 38.7 | 16.5 | 2.3 | −1.13 |
| mix6x35 | 97.7 | 22.0 | **4.4** | **−3.87** |
| the step between them | +59.0 | +5.5 | **10.7** | −2.74 |

**The second dose bought five and a half molecules for fifty-nine.** That is
the whole result. Re-weighting a fixed corpus is a transfer at a roughly
constant price in points, and a transfer at a constant price in points is a
losing trade in molecules, because the bands being paid from hold 1,597 of
the protocol's queries and the bands being bought hold 359. No setting of
threshold and factor escapes that arithmetic; the only question a mix can
answer is which population the project is willing to pay for.

### The band that changed sides changed sign

30–34 is the internal control. It is above the first mix's threshold and
below the second's, so it is the one band that goes from up-weighted to
down-weighted while everything else keeps its direction, and it tracks its own
exposure both times — +0.46 at 1.69× and −1.43 at 0.51× on the large protocol,
−0.45 and −4.47 on the common one. The response is also clearly asymmetric:
nearly doubling this band's exposure bought it nothing measurable, halving it
cost 1.4 to 4.5 points. Three bands at 1.69× in the first mix gained 2.5 and
3.4 points per doubling while 30–34 at the same dose gained none, so the
asymmetry is specific to this band rather than a general law, and it is
recorded here rather than explained.

### Each protocol is blind in its own direction

Running the same analysis on the large protocol prints a refusal:

```
every band here sits at the same exposure, so this protocol cannot price a doubling
```

Under a threshold-30 mix, every band the large protocol contains is above the
threshold and sits at 1.69×, so the protocol has no contrast in the quantity
that explains the result and no band on the paying side — it reports the
mix as a free +1.58 with nothing given up. The common protocol has the
contrast but only 359 queries where the gain lives, and reports the same mix
as −1.13. Neither number is wrong and neither is the answer. This is the
night's recurring error in its clearest form: the protocol decides what can
be seen, and the band table is the only place both halves of a size-dependent
result appear at once.

### Verdict on the size-weighted mix

Adopt neither as a default. `mix3x30` is the better of the two on every
summary that includes small molecules, `mix6x35` is the strongest arm the
project has above 35 heavy atoms (+6.13 on the common protocol, +2.89 on the
large one, +5.66 and +2.74 on structure accuracy), and both lose on the
headline metric. If large-molecule recovery becomes the deliverable, the
checkpoint to ship is `mix6x35` and the number to report is per-band. If the
headline stays as it is, the baseline stands and this line of work is closed:
exposure has been pushed 3× and then 3× again, and the second push bought
nothing the error bar can see.

### Does the mix actually narrow the cloud? Yes, and that is the problem

The combinatorial account above says the mix works by tightening the cloud of
molecules the decoder proposes, and makes two predictions that the dumps can
check without any more GPU time. `scripts/cloud_quality.py` (new) groups the
`miss_anatomy.py` reports into the same three arms and reads the between-seed
spread off the three baseline seeds.

The first prediction holds, and sharply. Mean best Tanimoto to the target
among the queries an arm *missed* — how close the cloud got when it failed:

| band | queries | baseline | sd | mix3x30 | mix6x35 | exposure, 3×/6× |
|---|---|---|---|---|---|---|
| 30–34 | 1,189 | 0.7017 | 0.0014 | −0.36 | **−0.71** | 1.69× / 0.51× |
| 35–39 | 625 | 0.6942 | 0.0025 | +0.69 | +0.25 | 1.69× / 3.06× |
| 40–49 | 380 | 0.6408 | 0.0041 | +1.37 | +1.60 | 1.69× / 3.06× |
| 50+ | 127 | 0.5690 | 0.0066 | +1.74 | **+4.05** | 1.69× / 3.06× |
| 35+ | 1,132 | 0.6582 | 0.0018 | +1.05 | +1.24 | 1.69× / 3.06× |

The between-seed sd of this quantity is 0.0018 at 35+, so a +1.24 move is
roughly seven sd — far better resolved than any recovery number in this
document, because it averages over every miss instead of counting a rare
success. The cloud moves in the direction of the band's exposure in every row,
including the one row where exposure went down.

The second prediction also holds, and it is the more interesting one. Dividing
each arm's recovery gain by its cloud gain gives recovery points bought per
point of Tanimoto:

| band | mix3x30 | mix6x35 |
|---|---|---|
| 35–39 | +3.20 / +0.69 = **4.6** | +2.24 / +0.25 = 8.8 |
| 40–49 | +3.07 / +1.37 = **2.2** | +4.39 / +1.60 = **2.8** |
| 50+ | +1.57 / +1.74 = **0.9** | +1.57 / +4.05 = **0.4** |

(The 35–39 column for `mix6x35` divides by a cloud gain of 0.25 points and
should not be read closely; the 40–49 and 50+ rows rest on gains of 1.6 to 4.1
points. These recovery levels come from `miss_anatomy.py`, which reads rec@k
off the first k slots rather than off a budget of k unique molecules, so they
run about four points below the protocol's own; the arms are read alike, so
the gaps and the ratios stand.)

**Above 50 heavy atoms the mix buys the largest improvement in proposal
quality of any band and the smallest improvement in recovery.** Tripling the
exposure of those molecules moved the cloud 4.05 points closer to the target
and recovery 1.57 points, a conversion five to seven times worse than at
40–49. That is the cliff restated as an exchange rate, and it is what the
combinatorial account predicts: the cloud closing in on a 55-atom molecule
from 0.569 to 0.610 Tanimoto is still nowhere near containing its exact
preimage, so the proposal quality is real and the recovery is not there to
collect.

It also corrects something from the free analysis earlier tonight, which read
the cloud's distance as flat across bands at about 0.68. On 41 queries above
50 atoms it looked flat; on 127 it is not — 0.694 at 35–39, 0.641 at 40–49,
0.569 at 50+. The cloud does get further away as molecules grow. It just gets
further away far more slowly than recovery falls, which is why the distance
cannot be the whole story and the combinatorics has to be.

The collision rate among hits is the one quantity here that cannot be read
across these arms: its between-seed sd is 0.0139 at 35+ and 0.2887 at 50+,
where an arm has one to three hits to compute it from. The cooled-decoder
comparison reported above is the one to trust on collisions, because it is
three temperatures of a single checkpoint on a single query set rather than
six separately trained models.

### More models, or more samples? The misses are shared

The cloud account has a reading that would be good news, and it is wrong. If
recovery above 35 heavy atoms is a matter of whether twenty draws happen to
contain an exact preimage, then two models trained from different
initialisations should be unlucky on *different* molecules, and an ensemble
should be worth more above 35 atoms than anywhere else. Three baseline seeds
on the large protocol, `scripts/seed_union.py` (new):

| band | queries | one seed | union of 3 | if independent | all three miss | luck |
|---|---|---|---|---|---|---|
| 30–34 | 1,189 | 0.4886 | 0.6182 | 0.8663 | 38.2% | 25.3% |
| 35–39 | 625 | 0.2757 | 0.4208 | 0.6202 | 57.9% | 20.0% |
| 40–49 | 380 | 0.1026 | 0.1842 | 0.2777 | 81.6% | 9.1% |
| 50+ | 127 | 0.0157 | 0.0315 | 0.0467 | **96.9%** | **1.6%** |
| 35+ | 1,132 | 0.1885 | 0.2977 | 0.4656 | 70.2% | 13.5% |

"Luck" is the share of one seed's misses that one of the other two recovered,
and it goes the *opposite* way to the prediction: a quarter of the misses are
seed-specific at 30–34 and 1.6% above 50 atoms. Where the cliff is steepest the
misses are almost perfectly shared — 96.9% of molecules above 50 heavy atoms
are missed by all three models, against the 95.3% that would be missed by
chance alone if each model failed independently, which is to say there is
essentially nothing left for a second model to find. Structure accuracy says
the same thing more strongly still: 0.3% luck above 50 atoms.

Splitting a fixed budget settles the spending question without any
extrapolation. Three models asked for six candidates each spend what one model
asked for twenty spends:

| band | 1 × 20 | 2 × 10 | 3 × 6 |
|---|---|---|---|
| 30–34 | 0.4886 | 0.4903 | 0.4752 |
| 35–39 | **0.2757** | 0.2640 | 0.2576 |
| 40–49 | 0.1026 | **0.1092** | 0.0895 |
| 50+ | 0.0157 | 0.0118 | 0.0079 |
| 35+ | **0.1885** | 0.1837 | 0.1731 |
| all 30+ | **0.3422** | 0.3408 | 0.3279 |

**Ensembling independently-seeded models is a wash at best and a loss at
three ways.** And it is not that these three models are too similar: running
the same test across three *differently trained* models — a baseline, the
threshold-30 mix and the threshold-6 mix, which differ in a third of their
training diet — moves the luck at 35+ from 13.5% to 14.2%, and the equal-spend
split from 0.1885 to 0.2120, a gain of 0.4 points. Model diversity is not a
lever here, whether it comes from initialisation or from data.

That refines the cloud account rather than refuting it. The cloud is narrow,
and it is narrow **in the same place for every model**: the twenty molecules
one checkpoint proposes for a 55-atom fingerprint are not a lucky or unlucky
draw from a wide distribution of possible neighbourhoods, they are the
neighbourhood that this architecture on this data has learned to propose, and a
differently initialised or differently fed copy proposes the same one. Which
leaves the two routes already priced tonight — widening k within one model,
where returns per doubling are 1.41 to 1.44 and k ≈ 200 reaches 0.50 above 35
atoms, and changing what the model can represent. Spending on more models is
not a third route.

### The budget price, replicated on three seeds

The k-curve that prices the brute-force route was first read off one seed on
the common protocol, where the 50+ band holds 41 queries. The large protocol's
three baseline seeds give it properly, and the pattern is the same but steeper:

| band | queries | rec@5 | rec@10 | rec@20 | ×, 5→10 | ×, 10→20 | hits in slots 11–20 |
|---|---|---|---|---|---|---|---|
| 30–34 | 1,189 | 0.2590 | 0.3465 | 0.4435 | 1.338 | 1.280 | 21.9% |
| 35–39 | 625 | 0.1040 | 0.1621 | 0.2304 | 1.559 | 1.421 | 29.6% |
| 40–49 | 380 | 0.0298 | 0.0553 | 0.0877 | 1.853 | **1.587** | 37.0% |
| 50+ | 127 | 0.0000 | 0.0052 | 0.0079 | — | 1.500 | 33.3% |
| 35+ | 1,132 | 0.0674 | 0.1087 | 0.1575 | 1.611 | 1.450 | 31.0% |

Taking the 10 → 20 factor at face value, reaching 0.50 needs **k ≈ 92** at
35–39, **k ≈ 272** at 40–49, **k ≈ 173** at 35+ and **k ≈ 24,000** above 50
atoms. The earlier reading that the curve "does not reach the 50+ band at all"
was an artefact of a band with 41 queries and no hits below k=20; it does reach
it, at a price that says the same thing more usefully.

Every one of these numbers is an extrapolation from the last doubling of a
20-slot list, and the factors are already falling within the measured range
(1.85 → 1.59 at 40–49). The only honest way to price the one sampling route
tonight left standing is to generate past k=20 and look, which is where the
next session should start.

*(It did, in stage 12, and these four prices are all far too low — not by a
margin but by a factor. Extrapolating a multiplier on recovery is the wrong
operation when recovery is small: 1.45× per doubling of a 0.16 recovery barely
touches the 0.84 deficit, so the method reaches any target it is pointed at
cheaply. Extrapolating the deficit instead, with the power law that stage 12
measured on a real k=60 curve and fitted to this arm's own k ≤ 20 rungs at
r = −0.9999, reaching 0.50 needs **k ≈ 767** at 35–39 against the 92 below,
**k ≈ 2.4 million** at 40–49 against 272, and **k ≈ 14,900** at 35+ against
173 — 8×, 9,000× and 85× the prices in this paragraph. The 24,000 quoted for
50+ cannot be redone, since that band has no non-zero rungs below k=20 to fit.
Stage 12 also showed which method to trust: on `small_1m`, where both can be
scored against a measured k=60, the deficit power law predicted 0.779 against
0.769 measured at 35+ while the multiplier method predicted 0.805.)*

---

## The plan after tonight

Tonight closed more routes than it opened, which is the useful kind of night.
Two of the three ways of spending more inference on a hard fingerprint are now
measured and dead — more models, and splitting a budget across them — and the
training-side route is measured and priced at an exchange rate that gets worse
as it is pushed. What is left is narrow and concrete.

**1. Generate past k=20 (first, and cheap), because two models of the cliff now
disagree about it.** *(Done — stage 12, at the end of this document. The item
as written below is kept because it contains the design error: the two
predictions are computed from the 100k arm's constants while the run it
specifies is `small_1m`, so the pre-registration it set was void before the GPU
started. The answer, on `small_1m`'s own numbers, is that neither account is
right — the deficit is a power law in k with a size-dependent exponent — and
the three things the next session should take from it are: brute force is a
real route below 40 heavy atoms and dead above 50; the 100k arm's own k=60
point is still unmeasured, so the factorisation's prediction has never been
scored; and the cliff's mechanism is concentration, not cloud width, which
makes item 2 the only route left.)* Every claim about the brute-force route rests on
extrapolating the 10 → 20 step of a 20-slot list. One
`compare_checkpoints.py` run at `--eval-k 100` on 400 fingerprint-unseen
molecules above 35 heavy atoms, `small_1m` at T=0.6, discriminates between two
accounts that fit everything measured so far and part company at k=100:

- *Independent draws.* The factorisation says each 20 samples yield about 1.9
  right-sized proposals at 35+, each an exact preimage with probability 0.107.
  If successive draws are independent, rec@k = 1 − (1 − 0.107)^(0.095k), which
  gives 0.191 at k=20 — the measured value is 0.1885, so the model is
  calibrated where it was fitted — and **0.66 at k=100**.
- *Decaying returns.* The measured doubling factors are already falling inside
  the window (1.61 for 5 → 10 at 35+, 1.45 for 10 → 20). Extrapolating the
  last one gives **0.35 at k=100**.

Pre-registered: the measurement lands between 0.28 and 0.38, so the decay is
real and the draws are not independent — the decoder keeps re-proposing from
the same shrinking neighbourhood. If it instead lands near 0.6, brute force is
the answer to the whole problem and the next six months are cheap.

A note on what this experiment subsumes. The obvious decode-time fix for the
size defect — reject candidates whose heavy-atom count is far from the size the
fingerprint implies, and keep sampling — turns out not to need building. A
candidate's Tanimoto to the query is computable at inference without the
answer, every exact preimage scores 1.0, and so filtering by it can never
discard a true hit: reporting the best 20 of n samples by Tanimoto is
*identical* to reporting rec@n. The size filter is the k-widening route wearing
a different hat, and it is this run that prices it. What the size defect does
leave open is the train-time version — conditioning the decoder on the size the
fingerprint implies — which is item 2b below.

**1b. Score the void pre-registration on the model it was written for, and
test the power law out of sample.** The 100k arm's k=60 point is still
unmeasured, and because stage 12 fitted the same law to that arm's existing
k ≤ 20 ladder there is now a sharp prediction to run against. `variance_s1` at
T=1.0 on the large protocol, `--eval-k 60`, scored at 35+:

| account | predicts rec@60 at 35+ |
|---|---|
| independent draws, from the factorisation | 0.47 |
| the recovery-multiplier extrapolation | 0.28 |
| **the power law fitted to its own k ≤ 20 rungs** (b = 0.078, r = −0.9999) | **0.232** |

Pre-registered: 0.21–0.26. **Mind the convention** — that table is in
`miss_anatomy.py`'s first-k-slots units, where this arm reads 0.1634 at k=20
against the protocol's molecule-budget 0.1885, and conflating the two is
exactly the slip that voided stage 12's pre-registration. The comparison to
make is prefix-to-prefix.

Two things ride on it. If the power law transports to a model whose exponent is
a fifth of `small_1m`'s, it is a property of the decoding process rather than
of one checkpoint, and every future brute-force price can be read off a k ≤ 20
ladder for free. And if the independence prediction fails here too — it is
built from this arm's own factorisation constants, so this is the one place it
was ever entitled to work — the factorisation is confirmed as arithmetic that
happens to fit at k=20 rather than a model of the sampling. Note that 0.232
against 0.28 is about 1.7 SE at the full protocol's n, so the run has to use
all 2,400 molecules to separate those two; a 600-molecule version can only kill
independence, which stage 12 has already done elsewhere.

**2. Capacity, with a pre-registered location.** The only surviving
non-sampling route is changing what the model can represent, and tonight's
ensemble result argues that the limit is in the learned conditional rather than
in the sample: every initialisation proposes the same neighbourhood. The 15M
model deferred twice is now the natural test — 1M shard, 21,117 steps, scored
on *both* protocols with the band table. Pre-registered: if the limit is
capacity the gain concentrates above 35 atoms and the 0–24 band moves by less
than a point; if the gain is flat across bands it is not the size cliff that
got better and the cliff is in the fingerprint or the data.

A second pre-registration, on the quantity the exponent section at the end of
this document says is the one capacity moves. Score the 15M model with
`--eval-k 60` on the large protocol at T=0.6 and fit the deficit power law:
**the exponent at 35+ should land above 0.303**, `small_1m`'s value, since the
step from 100k to 15M is larger than the step from 100k to 1M that produced
0.094 → 0.303. If it instead sits near `small_1m`'s, the exponent is set by the
training corpus — which `small_1m` and the 15M run share — rather than by
capacity, and the whole reading of that section is wrong in a way one number
exposes. That ambiguity is the first caveat of the section, and this run
resolves it for the price of generating to k=60 instead of k=20.

**2b. Tell the decoder how big the molecule is.** *(Retired by stage 12 — see
the end of this document. On `small_1m` at k=60 the truncation is 5.1 atoms
rather than 10.7, 89.8% of the 50+ queries get a right-sized proposal, and the
closest proposal is within 0.2 atoms of the target in every band, so there is
no size defect left for a size token to fix. The flaw below is a property of a
100k-parameter checkpoint at a 20-slot budget, not of the problem.)*

The size defect is the
sharpest single flaw tonight found — 10.7 atoms short above 50 heavy atoms, and
only 37.8% of those queries get even one right-sized proposal out of twenty —
and the information is in the input. The cheap version is a size token on the
encoder sequence, derived from the fingerprint at inference, trained on the
true count. Note that a *scalar* prediction from the set-bit count is not good
enough to steer with: r = 0.83 leaves a residual of roughly five heavy atoms,
far wider than the ±1 that a filter would need, which is why this has to be a
learned head on the encoder rather than a rule on the bit count. Worth one 3 h
run on the 100k shard, scored per band, with a pre-registered location: the
gain should appear above 40 atoms, where the truncation is, and nowhere else.

**3. Demote the full-ChEMBL run.** It was Weekend 1's deliverable at ~18 h for
3 epochs / 44,112 steps. Two things argue against it now. At a fixed step
budget more data has already *hurt* here (`small_full` 0.7347 against
`small_1m` 0.8927), so the run is really a compute experiment wearing a data
experiment's clothes; and nothing tonight suggests corpus size touches the size
cliff, which is where the interesting failure is. If it runs, it should run at
a step budget scaled to the corpus and be reported per band — not as a headline
number against models trained on a tenth of the data.

**4. The reverse-direction control (one 3 h run).** Tonight produced one
quantitative law: the stronger mix's per-band gaps sit on a straight line in
log₂ exposure at +4.52 points per doubling, r = 0.989. The cheapest way to
find out whether that is a law or a coincidence of two doses is to run it
backwards — threshold 30, factor ⅓, which *de*-weights large molecules — and
check whether the same line predicts the damage. A law that predicts out of
sample is worth having, since it prices every future re-weighting without
training anything.

**5. Measurement practice, adopted.** Three rules earned tonight, each by
being broken first:
- Report per band. `scripts/arm_table.py` and `scripts/band_analysis.py` exist
  for this, and the common protocol alone cannot describe anything that acts on
  part of the size distribution.
- Pre-register the band **and** the predicted location of the effect. The
  30–39 metric was chosen on its error bar alone and did not clear, because
  three fifths of it is molecules that do not respond. An error bar is a
  necessary condition for choosing a metric and not a sufficient one.
- Read any size claim on `structure_accuracy` as well as `recovery`. The two
  part company above 35 atoms, where one recovery in eight is a different
  preimage, and tonight both working interventions turned out to be *understated*
  by the metric the project reports.

---

## The cliff factorises, and the two interventions act on different factors

*(Written 08:20–08:30, while stage 10's third arm was still generating. The
revised prediction at the end of this section was committed before any stage 10
number existed.)*

The cloud account has been treated as one thing. It is two, and separating them
turns out to matter. `scripts/size_bias.py` (new, dumps only) asks first
whether the decoder proposes molecules of the right *size*, and then, among the
proposals that are the right size, how often one is an exact preimage.

The first half is a defect with a direction. For `variance_s1` on the large
protocol, mean proposal size minus target size, over the queries it missed:

| band | target size | mean proposal | bias | nearest-sized proposal |
|---|---|---|---|---|
| 30–34 | 32.1 | 30.5 | −1.5 | −0.0 |
| 35–39 | 36.6 | 34.0 | −2.6 | −0.1 |
| 40–49 | 43.4 | 38.3 | −5.0 | −0.3 |
| 50+ | 56.0 | 45.3 | **−10.7** | −2.0 |

**The decoder truncates, and the shortfall grows with the molecule.** Above 50
heavy atoms it offers 45-atom molecules for 56-atom fingerprints. It is a skew
rather than a shift — the best-sized of the twenty proposals is nearly right at
every size — but the mass is in the wrong place, and the information to do
better is in the input, since set-bit count predicts heavy atoms at r = 0.83.

The second half is what is left after size:

| band | right-sized proposals per query | any right-sized | exact preimage, given right size |
|---|---|---|---|
| 30–34 | 3.7 | 91.3% | 14.9% |
| 35–39 | 2.6 | 85.1% | 11.7% |
| 40–49 | 1.3 | 65.3% | 9.1% |
| 50+ | 0.5 | **37.8%** | **0.0%** |

Both halves collapse, and their product is the cliff: 3.7 × 14.9% = 0.55
expected preimages per query at 30–34 against a measured recovery of 0.449,
2.6 × 11.7% = 0.30 against 0.238, 1.3 × 9.1% = 0.12 against 0.095, and zero
against zero above 50 atoms. (The 0.0% rests on about 64 right-sized proposals
in that band, so read it as "no hits yet" rather than as a rate.) The
counterfactual is worth stating even though it is optimistic: if the size skew
were fixed so that all twenty proposals were the right size and the match rate
held, recovery would be 1 − (1 − p)²⁰ — 0.92 at 35–39 and 0.85 at 40–49. It
would not hold, because the right-sized proposals the model makes now are the
ones it is most confident about. But the factor that is missing is large.

### The two interventions pull different levers

Comparing like with like — the mix against the baseline at T=1.0 on the same
100k recipe, and one checkpoint of `small_1m` at T=1.0 against T=0.6 on the
common protocol:

| at 50+ atoms | truncation | any right-sized | preimage given right size |
|---|---|---|---|
| baseline, T=1.0 | −10.7 | 37.8% | 14.9% at 30–34 |
| **+ size mix ×6** | **−8.9** | **48.8%** | 14.5% at 30–34 |
| `small_1m`, T=1.0 | −6.6 | 65.9% | 19.7% |
| **+ cooling to T=0.6** | −5.1 | 65.9% | **23.9%** |

**The training mix buys right-sized proposals and does not improve the match
rate among them; cooling improves the match rate and barely touches the size.**
Across bands the mix moves "any right-sized" by +11.0 points at 50+ and leaves
the conditional match rate flat to a tenth of a point (14.9 → 14.5 at 30–34,
11.7 → 11.5 at 35–39, 9.1 → 8.6 at 40–49), while cooling lifts that same
conditional rate in every band (20.5 → 23.3 at 35–39, 21.5 → 22.3 at 40–49,
19.7 → 23.9 at 50+) with "any right-sized" unchanged at 65.9%.

**That half of this paragraph is wrong, and the 2×2 below replaces it.** The
mix row and the cooling row come from different models — the mix compared on
the 100k recipe, cooling on `small_1m`, which is trained on ten times the data
for two and a half times the steps. The comparison that separates the levers
has to hold the model fixed, and once stage 10 had scored the same checkpoints
at both temperatures it could be done properly. It says something different.

### The stage 10 prediction, revised and re-registered

The prediction written at 05:30 was that the mix and the cooled decoder would
**compete**, because both "narrow the cloud", and that the mix's +2.75 at 35+
should therefore fall below +1.5 when both are applied. The factorisation says
that was wrong about the mechanism: they are not two ways of doing one thing,
they are the two factors of a product. If so they should stack approximately
multiplicatively, and the mix's advantage should survive cooling.

Registered, before any stage 10 number exists: **the mix's 35+ recovery gap at
T=0.6 is at least +2.0 points**, against the earlier prediction of under +1.5.
If it comes in below +1.5 the factorisation is wrong about their independence,
and the first prediction was right for the wrong reason.

---

## Stage 10 — they stack, and the pre-registered metric clears after all

Five arms, each scored on the large protocol at T=0.6: the three baseline seeds
and the two threshold-30 mix seeds, one `compare_checkpoints.py` call apiece,
07:58 → 09:08.

| band | queries | baseline | mix3x30 | gap | | pairs |
|---|---|---|---|---|---|---|
| 30–34 | 1,189 | 0.5548 | 0.5761 | +2.13 | 2.0 SE | 6/6 |
| 35–39 | 625 | 0.3472 | 0.3720 | +2.48 | 2.7 SE | 6/6 |
| 40–49 | 380 | 0.1509 | 0.2013 | +5.04 | 2.3 SE | 6/6 |
| 50+ | 127 | 0.0236 | 0.0433 | +1.97 | 1.6 SE | 5/6 |
| **30–39 (pre-registered)** | 1,814 | 0.4833 | 0.5058 | **+2.25** | **2.4 SE** | 6/6 |
| 35+ | 1,132 | 0.2450 | 0.2778 | **+3.28** | 3.1 SE | 6/6 |
| all 30+ | 2,321 | 0.4037 | 0.4306 | +2.69 | 2.8 SE | 6/6 |

On structure accuracy: 35–39 +3.47, 40–49 +4.61, **35+ +3.56** at 3.0 SE, and
30–39 +2.59 at 3.0 SE — all 6/6.

**The 05:30 prediction was wrong and the 08:20 one was right.** The mix's gap
above 35 atoms did not fall below +1.5 when the decoder was cooled; it rose
from +2.75 to +3.28, and from +3.09 to +3.56 on structure. Nothing competes.
Band by band, the gain from applying both against applying neither, beside the
sum of the two applied alone:

| band | cooling alone | mix alone | both | sum of the parts |
|---|---|---|---|---|
| 30–34 | +6.62 | +0.46 | **+8.75** | +7.08 |
| 35–39 | +7.15 | +2.51 | +9.63 | +9.66 |
| 40–49 | +4.83 | +3.42 | **+9.87** | +8.25 |
| 50+ | +0.79 | +1.97 | +2.76 | +2.76 |
| 35+ | +5.65 | +2.75 | +8.93 | +8.40 |

Additive to within noise in three bands and better than additive in two, with
40–49 landing on the multiplicative prediction exactly (0.1509 × 1.333 =
0.2012 against a measured 0.2013). That is what two factors of a product look
like when each is improved independently, and it is the behaviour the size
factorisation predicted five hours after the prediction that said the
opposite. The reason the first prediction was wrong is worth keeping: "both
interventions narrow the cloud" was true and still useless, because narrowing
is not one operation — one of them makes the proposals the right size and the
other makes a right-sized proposal more likely to be the molecule.

**And the plan's own metric clears.** The 30–39 band was pre-registered on
night 4 as the place the mix would be read, it failed at 1.8 SE when measured
at T=1.0, and this document's opening section blamed the choice of metric. Half
of that blame was misplaced. The band is three-fifths 30–34 molecules, which is
still the reason the metric was a poor choice — but those molecules do respond
to the mix once the decoder is cooled (+0.46 hot, +2.13 cold), so a second
error was stacked on the first: the experiment was scored at a temperature
night 4 had already shown to be the wrong one. Had stages 1–4 been run at
T=0.6, the pre-registered metric would have reported +2.25 at 2.4 SE with all
six pairs agreeing, and the night's first finding would have been a
confirmation rather than a near miss.

The practical consequence is a correction to the stage 8–9 verdict. The size
mix at threshold 30 is worth more than it looked: at the adopted decode
setting it is +3.28 above 35 heavy atoms and +2.69 across the whole large
protocol, against the +2.75 and +1.58 measured hot. Whether the small-molecule
cost also grows with cooling is unmeasured — it needs the common protocol at
T=0.6 for both mix seeds, which is two more runs and the first thing to queue
next time.

---

## The 2×2, and a correction to the mechanism

Stage 10 scored `variance_s1` and `size_mix_s1` on the large protocol at
T=0.6, and both were already scored at T=1.0, so the four cells of
{baseline, mix} × {hot, cold} exist on identical queries and identical
checkpoints. That is the comparison the mechanism claim needed, and the one
made earlier tonight — the mix measured on a 100k model, cooling measured on
`small_1m` — was not it.

| at 35+ atoms | baseline, T=1.0 | mix, T=1.0 | baseline, T=0.6 | mix, T=0.6 |
|---|---|---|---|---|
| right-sized proposals per query | 1.93 | 2.15 | 2.44 | **2.56** |
| exact preimage, given right size | 10.7% | 10.2% | 10.7% | 11.2% |
| truncation on a miss | −4.6 | −4.4 | −4.4 | −4.4 |
| `rec@20` | 0.1885 | 0.2160 | 0.2450 | **0.2778** |

**Both interventions act on the same factor, and the other one barely moves.**
The count of right-sized proposals goes up 11% with the mix, 26% with cooling
and 33% with both, while the conditional match rate sits between 10.2% and
11.2% in all four cells and the truncation between −4.4 and −4.6 atoms. The
earlier reading that cooling works by improving the match rate is true of
`small_1m` — where cooling takes it from 19.7% to 23.9% above 50 atoms, on the
same checkpoint — and false of these 100k models, where it does nothing of the
kind. Two models in different capability regimes, and the honest thing to say
is that the mechanism of cooling differs between them, unexplained.

The prediction the earlier paragraph was used to make survives, with a better
reason behind it. If the conditional match rate is effectively constant, then
recovery ≈ (right-sized proposals) × (constant), which is *linear* in the
count — so two interventions that each multiply the count compose
multiplicatively, whatever else they do. The counts say ×1.11 and ×1.26 against
a measured ×1.15 and ×1.30 in recovery, and ×1.33 against a measured ×1.47 for
both together. The composition is real and the account of it is now the simpler
one: there is one lever, the two interventions both pull it, and the exchange
rate from pulls to recovery is constant within a band.

Which also sharpens item 2b of the plan. The quantity to attack is the number
of right-sized molecules in the budget — 2.56 of 20 even in the best cell above
35 heavy atoms, and 0.80 of 20 above 50 — and a decoder told how big the
molecule should be is the most direct way to attack it. The counterfactual from
earlier stands: with twenty right-sized proposals at the measured 11.2%
conditional rate, recovery above 35 atoms would be 0.90 rather than 0.28.

---

## Stage 11 — counts, re-opened on the right protocol, and the hypothesis was wrong

Night 3 trained `count_fp_100k` — identical to `small_100k` but for
`counts: true` — and closed the question at 0.5890 against 0.5890 on the common
protocol, p = 0.32. Tonight's whole thesis is that this protocol averages away
anything acting on part of the size distribution, and the degeneracy scan gave
a reason to expect counts to act there: they cut corpus-level fingerprint
ambiguity 5.6× overall and from 6.13% to 1.11% at 50–59 heavy atoms. So both
models were re-scored on the large protocol, 09:08 → 09:36.

Each arm is a single run, so the SE column `arm_table.py` prints is empty.
The error bars below come from the three `variance_s*` seeds, which share
`small_100k`'s recipe exactly — 100k shard, 8,508 steps — scored on these same
2,321 queries, and a one-against-one gap gets √2 times that sd.

| band | queries | binary | counts | gap | seed sd | | |
|---|---|---|---|---|---|---|---|
| 30–34 | 1,189 | 0.4920 | 0.4239 | **−6.81** | 0.67 | 0.94 SE | −7.2 |
| 35–39 | 625 | 0.2496 | 0.2320 | −1.76 | 1.03 | 1.45 SE | −1.2 |
| 40–49 | 380 | 0.0842 | 0.0658 | −1.84 | 1.90 | 2.68 SE | −0.7 |
| 50+ | 127 | 0.0079 | 0.0236 | +1.57 | 1.36 | 1.93 SE | +0.8 |
| 35+ | 1,132 | 0.1670 | 0.1528 | −1.41 | 0.94 | 1.32 SE | −1.1 |
| all 30+ | 2,321 | 0.3335 | 0.2917 | **−4.18** | 0.79 | 1.12 SE | −3.7 |

**The prediction registered at 05:30 was that counts would be neutral or worse
on recovery, and they are worse — by more than the common protocol could see.**
That protocol's null was hiding a loss, not a gain. The loss is concentrated at
30–34, where the binary model is strongest, and above 35 atoms the gap is
−1.41 at 1.1 SE, which is nothing either way.

The same prediction said the informative number is the collision rate among
each model's own hits, because that one is not confounded by the count model's
strictly harder oracle. It moves, and in the direction counts are for:

| | 30–34 | 35–39 | 40–49 | 35+ | all 30+ |
|---|---|---|---|---|---|
| collisions among hits, binary | 4.6% | 11.5% | 23.1% | 13.3% | 6.7% |
| collisions among hits, counts | **3.2%** | **7.7%** | 22.2% | **9.6%** | **4.7%** |
| best Tanimoto on a miss, binary | 0.693 | 0.682 | 0.635 | 0.651 | 0.668 |
| best Tanimoto on a miss, counts | **0.734** | **0.719** | **0.666** | **0.681** | **0.704** |

So counts do what they are supposed to do. A quarter fewer of the count model's
recoveries are a different molecule with the same fingerprint, and its
proposals land measurably closer to the target when it fails — 0.681 against
0.651 at 35+, where the between-seed sd of that quantity is 0.0018. The
representation carries more information and the decoder uses it.

It just does not convert into exact answers. The fairest single comparison is
structure accuracy, since that asks both models for the query's own molecule
rather than for a match to their own fingerprint: −3.45 points overall, −0.62
at 35+ (0.5 SE), +1.57 at 50+ on three hits against one. Counts are a wash
above 35 heavy atoms and a clear loss below, and they cost validity too (0.566
against 0.673).

**The honest summary is that the hypothesis was wrong.** The reasoning that
sent this experiment back to the GPU — that ambiguity rises steeply with size,
that counts cut it 5.6×, and that the common protocol had therefore hidden a
large-molecule gain — was sound in every step and false in its conclusion.
Ambiguity was never what made the cliff: 1.63% of molecules at 35–39 share a
fingerprint against 75% of queries failing there, a point this document already
made before the run and should have weighed more heavily against the
re-opening. What counts buy is precision in what recovery *means*, which is
worth having for the degeneracy caveat and is not a route to inverting bigger
molecules. The question is closed again, for a better reason than p = 0.32.

---

## Stage 12 — the budget curve, measured, and the pre-registration was void

The one route tonight left standing was widening k inside one model, and every
price quoted for it came from extrapolating the 10 → 20 step of a 20-slot list.
Stage 12 generated to k=60 on the large protocol's own 2,321 molecules so the
curve could be read instead of guessed.

**The protocol check passes.** `small_1m` at T=0.6 scored 0.8121 overall on
these molecules at k=20 with a 20-slot budget; the k=20 prefix of the k=60 dump
gives 0.8126. The larger budget did not change the protocol underneath it.

**The pre-registered band cannot be scored, because I registered it for a
different model.** The two accounts in the header — independence at 0.47,
decaying returns at 0.28, measurement pre-registered at 0.26–0.36 — were built
from the factorisation constants in the section above: 1.9 right-sized
proposals per twenty, an exact-preimage rate of 0.107, and a calibration check
against "the measured 0.1885 at 35+". Those are the **100k** arm's numbers.
The run is `small_1m`, which was already at 0.6890 at 35+ and k=20 before it
started. A prediction of 0.26–0.36 for a quantity that began at 0.69 was never
a prediction about this run. The plan item that specified the stage carried the
same defect, and the run executed it faithfully; the error is mine and it is in
the design, not the measurement. No credit either way, and the 100k arm's k=60
point is still unmeasured.

What the run does settle, it settles on `small_1m`'s own numbers.

### Independence is dead, and not narrowly

```
   band   rec@1   independent rec@20   measured   independent rec@60   measured
  35-39  0.3536               0.9998     0.7968               1.0000     0.8656
  40-49  0.2395               0.9958     0.6342               1.0000     0.7158
    50+  0.0472               0.6201     0.3228               0.9452     0.4488
    35+  0.2809               0.9986     0.6890               1.0000     0.7686
```

If successive draws were independent at the model's own first-slot rate, 35+
would have been finished at k=20 — 0.9986 against a measured 0.6890, a gap of
31 points. The decoder re-proposes from a neighbourhood that barely moves as
the budget grows. That was the direction the pre-registration assumed, and it
is worth saying that the assumption survives even though the number testing it
does not.

### The deficit follows a power law, tightly, with a size-dependent exponent

`budget_curve.py` fits `1 − rec(k) = A·k^−b` over the rungs from k=5 up:

| band | n | rec@60 | b | r | b fitted to k≤20 | predicts k=60 | error |
|---|---|---|---|---|---|---|---|
| 30–34 | 1,189 | 0.9134 | 0.396 | −0.9992 | 0.399 | 0.9141 | −0.07 |
| 35–39 | 625 | 0.8656 | 0.387 | −0.9993 | 0.403 | 0.8700 | −0.44 |
| 40–49 | 380 | 0.7158 | 0.263 | −0.9954 | 0.304 | 0.7406 | −2.48 |
| 50+ | 127 | 0.4488 | 0.144 | −0.9917 | 0.123 | 0.4120 | **+3.68** |
| 35+ | 1,132 | 0.7686 | 0.281 | −0.9984 | 0.303 | 0.7788 | −1.02 |
| all | 2,321 | 0.8427 | 0.317 | −0.9990 | 0.334 | 0.8486 | −0.58 |

Three readings.

*The shape is right.* |r| ≥ 0.991 in every band across eight rungs spanning a
factor of 60. Nothing in the measured range looks like a floor; the pure power
law fits the data as well as the data can be fitted.

*The extrapolation method the prices rested on is roughly sound.* Refitting on
k ≤ 20 only and predicting k=60 lands within half a point in the two bands with
real n, 2.5 points low at 40–49, and 3.7 points high at 50+ — where n=127 makes
the SE on the proportion 4.4 points, so that miss is inside noise. A method
that transports a factor of three in budget to within a point or two is good
enough to quote prices from, provided the prices are labelled as the lower
bounds they are.

*The exponent falls with molecule size.* 0.40 at 30–34 against 0.14 above 50
atoms. Big molecules do not merely start lower on the curve; each doubling of
the budget buys them proportionally less as well. The cliff steepens with
spending rather than eroding.

Inverting the fits gives what the route actually costs for this model:

| band | k for 0.90 | k for 0.95 | k for 0.99 |
|---|---|---|---|
| 30–34 | 41 | 238 | 13,857 |
| 35–39 | 128 | 768 | 49,097 |
| 40–49 | 3,080 | 42,917 | 1.9 × 10⁷ |
| 50+ | 1.0 × 10⁷ | 1.2 × 10⁹ | 8.8 × 10¹³ |
| 35+ | 1,177 | 13,819 | 4.2 × 10⁶ |

Up to about 40 heavy atoms, brute force is a real and affordable answer: k=128
is a few seconds per fingerprint and takes 35–39 to 0.90. From 40 atoms it
stops being a route and above 50 it stops being arithmetic.

### What the budget buys, and the mechanism this overturns

The cloud account from earlier tonight says the cliff is a shortage of
right-sized proposals, with the match rate given the right size collapsing to
near zero above 50 atoms. Neither half of that survives on `small_1m` at k=60:

| band | right-sized proposals/query | any right-sized | match given right size |
|---|---|---|---|
| 30–34 | 7.9 | 99.9% | 13.2% |
| 35–39 | 8.8 | 98.9% | 11.7% |
| 40–49 | 8.2 | 97.6% | 11.2% |
| 50+ | 6.3 | 89.8% | 11.0% |

The match rate is **flat** — 13.2% down to 11.0%, where the 100k arm went to
about zero — and 89.8% of the 50+ queries get at least one right-sized
proposal, against 37.8% for the 100k arm at k=20. Truncation on misses is −5.1
atoms at 50+ rather than −10.7, and the single closest proposal is within 0.2
atoms of the target in every band. **For this model the size defect is
essentially gone and a length prior has nothing left to correct.** That retires
item 2b, and it also means the earlier factorisation described a property of a
100k-parameter checkpoint rather than of the problem.

*(Written first as "bought off by budget", which the next subsection shows is
the wrong attribution.)*

#### It was capacity that bought it, and budget dilutes the match rate

The comparison above changes two things at once — 100k → 1M and k=20 → k=60 —
so it cannot say which did the work. `small_1m`'s own k=20 dump at the same
temperature separates them:

| at 50+ atoms | right-sized/query | match given right size |
|---|---|---|
| `variance_s1` (100k), k=20 | 0.54 | 0.0% |
| `small_1m` (1M), k=20 | **2.54** | **14.6%** |
| `small_1m` (1M), k=60 | 6.30 | 11.0% |

**Capacity did it.** At an identical 20-slot budget the bigger model puts 4.7×
as many right-sized molecules above 50 atoms into the list and converts 14.6%
of them where the smaller model converts none. Budget then adds right-sized
proposals — 2.54 to 6.30 — and *lowers* the rate at which they match, 14.6% to
11.0%, which is precisely the caveat attached to the counterfactual earlier in
this document: the right-sized proposals a model makes first are the ones it is
most confident about, so the ones budget buys are worse.

That also qualifies the flatness. At k=20 the match rate does fall with size
across `small_1m`'s bands — 25.4%, 22.7%, 20.5%, 14.6% — and it is only at k=60
that the bands converge on 11–13%. The convergence is dilution reaching its
floor in every band rather than evidence that the rate never depended on size.
What survives unqualified is the comparison that matters: at equal budget the
1M model's rate above 50 atoms is 14.6% against the 100k model's zero, so the
collapse to zero was a property of the small checkpoint.

So where does the cliff come from? Counting exact preimages per query, rather
than pooling the rate over proposals:

| band | n | rec | preimages/query | if Poisson | none | one | two | 3+ | per hit |
|---|---|---|---|---|---|---|---|---|---|
| 30–34 | 1,189 | 0.9285 | 1.532 | 0.7840 | 0.071 | 0.748 | 0.103 | 0.078 | 1.65 |
| 35–39 | 625 | 0.8912 | 1.459 | 0.7676 | 0.109 | 0.699 | 0.118 | 0.074 | 1.64 |
| 40–49 | 380 | 0.7579 | 1.395 | 0.7521 | 0.242 | 0.571 | 0.095 | 0.092 | 1.84 |
| 50+ | 127 | 0.4803 | 1.307 | 0.7294 | 0.520 | 0.315 | 0.047 | 0.118 | **2.72** |

(Recovery here counts a preimage anywhere in the first 60 proposals, so it sits
a little above the protocol's own numbers; the columns are to be read against
each other.)

**The number of preimages the model draws barely depends on size. Their
distribution across queries depends on it enormously.** From 30–34 to 50+ the
preimages per query fall 15%, from 1.53 to 1.31, while recovery falls 48
points. What changes is concentration: above 50 atoms 52.0% of queries get
nothing at all and the ones that succeed get 2.72 preimages each, where at
30–34 three quarters of queries get exactly one. Poisson — the same preimage
count scattered independently over the band's queries — would give 0.729 above
50 atoms against a measured 0.480.

That is a different mechanism from a thin cloud, and it is the one that makes
the budget curve's small exponent intelligible. The population is splitting
into fingerprints this decoder can reach and fingerprints it cannot, and the
split sharpens with size. Extra budget spends most of itself re-finding
molecules it has already found on the queries it was always going to solve.
The route out is not more samples from this conditional; it is changing which
molecules the conditional can reach at all — which is item 2, capacity, and
tonight has just made it the only item left.

This also joins the night's two loose ends into one statement. The ensemble
result said that of one seed's misses above 50 atoms, 1.6% are recovered by
either of two other seeds, and 96.9% of that band is missed by all three
against the 95.3% chance alone would give. The concentration result says each
seed's successes pile up on a minority of queries. Put together: the reachable
set is not just small, it is **the same** small set for every seed, and a
differently initialised copy of the model reaches the same fingerprints. That
is one mechanism accounting for both measurements, and it is the reason neither
more samples nor more models is a route — both of them draw again from a
conditional whose reachable set is fixed by the architecture and the data.

A caveat the numbers themselves demand: a power law with no visible floor and a
population with unreachable members are in tension, since the second implies an
asymptote below 1 and the first denies one. k ≤ 60 cannot separate them. The
honest statement is that the fit is excellent over the measured range, that it
is a lower bound on cost, and that the concentration result is the reason to
expect the real curve to bend worse than the fit rather than better.

### The exponent is a property of capacity, not of the training mix

The fit costs nothing on a dump that already exists, so it can be run on every
arm scored tonight. Fitting `1 − rec(k) = A·k^−b` on the k = 5…20 rungs of the
large protocol, the exponent at 35+ heavy atoms:

| arm | T | b at 30–34 | b at 35–39 | b at 35+ | rec@20 at 35+ |
|---|---|---|---|---|---|
| `variance_s1` (100k) | 1.0 | 0.203 | 0.116 | 0.078 | 0.1634 |
| `variance_s2` | 1.0 | 0.210 | 0.118 | 0.076 | 0.1590 |
| `variance_s3` | 1.0 | 0.206 | 0.095 | 0.066 | 0.1502 |
| `size_mix_s1` | 1.0 | 0.216 | 0.123 | 0.081 | 0.1811 |
| `size_mix_s2` | 1.0 | 0.211 | 0.138 | 0.093 | 0.1935 |
| `size_mix_t35` | 1.0 | 0.218 | 0.113 | 0.076 | 0.1864 |
| `variance_s1` | 0.6 | 0.229 | 0.140 | 0.094 | 0.2155 |
| **`small_1m`** | 0.6 | **0.399** | **0.403** | **0.303** | 0.6890 |

(All in `miss_anatomy.py`'s first-k-slots units, and all fitted over the same
k ≤ 20 window so the comparison is not a comparison of ladder lengths —
`small_1m`'s exponents over its full k ≤ 60 range are 0.396, 0.387 and 0.281,
so the window is not doing the work either.)

Read down the column. **The training mix does not move the exponent**: three
baseline seeds give 0.078, 0.076, 0.066 at 35+ and three mix arms give 0.081,
0.093, 0.076, a gap of 0.010 against a between-seed sd of 0.006. What the mix
moves is the level — rec@20 from 0.159 to 0.187 — which is the same thing the
rest of tonight said about it in different units: it is a transfer, and
transfers change where you are on a curve, not the curve. **Cooling moves it
slightly**, 0.078 → 0.094 at 35+, consistent with cooling and the mix being two
factors of one product. **Capacity moves it threefold**, 0.094 → 0.303 at the
same temperature in the same window.

That is the sharpest argument this document has for item 2, and it is a
different argument from the one item 2 was written with. A tenfold bigger model
does not merely sit higher on the budget curve; it bends the curve, so each
doubling of inference buys it four times what it buys the small model above 35
heavy atoms. Level and slope are separate dials, and nothing found tonight
except capacity touches the slope. If the 15M model continues the trend, the
brute-force route and the capacity route are the same route — which would also
explain why the one thing that reliably helps big molecules is the thing that
helps everything.

Three caveats, in descending order of how much they ought to worry the reader.
The `small_1m` cell differs from the rest in training corpus as well as
capacity (1M molecules against 100k), so "capacity" here means the whole step
between the two models. The 100k arms' exponents at 40–49 sit between 0.040 and
0.063, where a single hit moves the fit, so only the 30–34 and 35–39 columns
carry weight. And eight points are not a trend — this is one contrast with a
seed-level error bar attached, pre-registering a prediction for the 15M run
rather than reporting a law.
