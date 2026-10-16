# Night 5 — 2026-10-16 into 2026-10-17

Executes the working-day items from
[night 4's revised plan](overnight-2026-10-15.md) — the size-weighted training
mix, the per-band temperature question, and the pooled-sampling `generate` —
after re-sizing the first of them, because night 4's own error bar turned out
not to apply where the plan proposed to read it.

```
stage 0  error bar inside each size band, from night 4's dumps   20:08 -> 20:17
stage 0b temperature dose-response per band, from night 4's dumps
stage 0c size from the fingerprint, and a routing threshold      -> 20:24
stage 1  size-weighted mix, seed 1 (8,508 steps, 100k shard)     20:17 -> 23:10
stage 2  size-weighted mix, seed 2                               23:10 -> 02:04
stage 3  5 checkpoints on a new large-molecule protocol          02:04 -> 02:55
stage 4  both mix seeds on the common protocol (the cost side)   02:55 -> 03:14
stage 5  temperature sweep on a large-molecule tuning set        03:15 -> 03:40
stage 6  T=0.3 and T=0.6 on the large protocol                   03:40 -> 04:22
stage 7  T=0.3 on the common protocol (the cost side)            04:22 -> 04:40
stage 8  size mix at threshold 35, factor 6 (8,508 steps)        04:40 -> TBD
stage 9  score it on both protocols                                 TBD
stage 10 every arm on the large protocol at T=0.6 (do they stack?)  TBD
```

HEADLINE TBD

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
