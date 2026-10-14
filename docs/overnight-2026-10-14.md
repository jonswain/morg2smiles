# Night 3 — 2026-10-14 into 2026-10-15

Work against the plan in [next-steps-2026-10-13.md](next-steps-2026-10-13.md):
its item 1 (the gate), item 2 (failure analysis and likelihood ranking), the
bit-flip probe from the generative-model section, item 5 (the constant-epoch
corpus point) and item 3's cheap signal (count fingerprints).

```
stage 1  re-score every checkpoint, adaptive top-up   20:13 -> 21:29
stage 2  failure taxonomy + likelihood ranking        21:29 -> 21:35
stage 3  bit-flip probe                               21:35 -> 21:47
stage 4  small_100k_3ep, 2,127 steps + scoring        21:47 -> 23:12
stage 5  count_fp_100k, 8,508 steps + scoring         23:12 -> 02:22
```

Every stage completed; the driver finished with 257 minutes of its window
unused.

The headline is not the gate. It is that **ranking candidates by how often the
model proposes them lifts `rec@1` from 0.5302 to 0.7520**, and that the
remaining misses are a capability limit rather than an information one.

---

## Stage 1 — the gate, and why it barely mattered

`generate_outcomes` drew a fixed `k × oversample = 40` strings per query. The
plan's reading was that this under-filled the 20-slot budget for the strongest
model (12.6 distinct molecules of 20) and so understated it, and understated
every cross-run gap, because better models explore less.

The fix is adaptive rather than a larger constant: draw `k × oversample` first,
then top up k strings at a time until the query has k distinct scored candidates
or hits `max_oversample × k` (default 200). Top-ups draw from a second RNG
stream, so the first 40 strings are bit-identical to the old protocol and only
the extra candidates are new — `rec@1` and `rec@5` are therefore unchanged by
construction, which is what the table shows.

Re-scored on the same common protocol — 2,000 held-out molecules, 1,956
fingerprint-unseen, `fp_unseen` against the union of 1,989,502 training
fingerprints:

| run | params | steps | rec@20 old | **rec@20 new** | uniq/q old | uniq/q new | fill rate |
|---|---|---|---|---|---|---|---|
| `small_100k` | 8.0M | 8,508 | 0.5890 | **0.5982** | 21.3 | 25.2 | 0.955 |
| `small_1m` | 8.0M | 21,117 | 0.8926 | **0.8947** | 12.6 | 18.9 | 0.639 |
| `medium_1m` | 15.1M | 21,117 | 0.2735 | **0.2822** | 18.7 | 24.5 | 0.969 |
| `small_100k_long` | 8.0M | 21,117 | 0.8384 | **0.8446** | 14.2 | 20.1 | 0.694 |
| `small_1m_matched` | 8.0M | 8,508 | 0.6299 | **0.6324** | 20.4 | 24.8 | 0.946 |
| `small_full` | 8.0M | 8,508 | 0.7347 | **0.7403** | 18.7 | 23.8 | 0.898 |

Every run gained, all between +0.20 and +0.92 points, and **the gains run
opposite to the prediction**: the models that were under-filled worst gained
least. `small_1m` was filling 12.6 of 20 slots and gained +0.20; `small_100k`
was filling 21.3 and gained +0.92.

The reason is in the per-query detail. 706 of 1,956 queries still fail to fill
the budget even with a 200-string cap, and **their recovery is 0.9929**.
Under-filling happens precisely where the model has locked onto one answer and
is right about it. Candidates 13 through 20 were never where the strong model's
hits came from — its mean hit rank is 1.76. Extra candidates on a query the
model has already solved buy nothing.

So the plan's reasoning was sound and its conclusion was wrong, for a reason
worth keeping: *under-filling is not uniformly distributed across queries, it is
concentrated on the easy ones*. A diagnostic averaged over all queries (12.6 of
20) looked like a measurement bug affecting the headline. Resolved per query it
is a property of easy queries, which the headline is not sensitive to.

The headline therefore stands, and the direction of the correction is the
opposite of what was feared: the 100k → 1M gaps are very slightly *overstated*,
not understated: the `small_100k` → `small_1m` gap narrows from 0.3036 to
0.2965, by 0.71 points.

`budget_filled_rate` is now reported on every evaluation so this is visible
rather than inferred. `small_1m`'s 0.639 under a 10× cap is a real diversity
property of the model, not an artefact of the draw size.

### What this cost

Sampling per query roughly doubled — 123 strings against 40 for `small_1m` —
and six checkpoints went from 55 min (night 2, 03:51 → 04:46) to **76 min**, up
38%. Indexing 1,989,502 fingerprints is a fixed ~20 min of that either way.
Budget ~1.5 h per re-score, as the plan already did; the fix fits inside the
existing allowance.

---

## Stage 2 — the remaining 10.5%

206 of 1,956 fingerprint-unseen queries are never inverted within 20
candidates. Each is placed in the first bucket that explains it:

| bucket | n | share of misses |
|---|---|---|
| `too_long` (reference exceeds the decoder's 128 tokens) | **0** | — |
| `beyond_budget` (right answer drawn, ranked past slot 20) | 18 | 8.7% |
| `collision` (another ChEMBL molecule shares the fingerprint) | **2** | 1.0% |
| `near` (best candidate Tanimoto ≥ 0.9) | 35 | 17.0% |
| `analogue` (0.7 ≤ Tanimoto < 0.9) | 91 | 44.2% |
| `far` (Tanimoto < 0.7) | 60 | 29.1% |

**This is a capability ceiling, not an information ceiling.** The plan framed
the question as: if failures concentrate on fingerprints that genuinely
underdetermine structure, more scaling is wasted; if they are large or unusual
molecules, scaling helps. The answer is unambiguous — **2 of 206 misses are
collisions**, and the 3 queries in the whole evaluation set that do have a
fingerprint twin in ChEMBL recover at 0.333 against 0.896 for the rest, which is
3 molecules and means nothing. Degeneracy is not what is stopping this model.

What is stopping it is size and complexity, sharply:

| heavy atoms | n | recovery | | potential stereocentres | n | recovery |
|---|---|---|---|---|---|---|
| < 15 | 54 | 0.981 | | 0 | 1,127 | 0.953 |
| 15–19 | 193 | 0.984 | | 1 | 434 | 0.931 |
| 20–24 | 465 | 0.938 | | 2 | 178 | 0.876 |
| 25–29 | 512 | 0.953 | | 3–4 | 107 | 0.720 |
| 30–34 | 373 | 0.890 | | ≥ 5 | 110 | **0.355** |
| 35–39 | 195 | 0.815 | | | | |
| 40–49 | 123 | 0.626 | | **largest ring** | | |
| 50–69 | 41 | **0.366** | | ≤ 6 | 1,862 | 0.904 |
| | | | | 7–8 | 73 | 0.822 |
| | | | | 9–12 | 8 | 0.375 |
| | | | | ≥ 13 (macrocycles) | 13 | **0.231** |

Recovery falls from 0.98 to 0.37 across the size range. Median miss is 35 heavy
atoms and 64 tokens against 26 and 46 for a hit.

Size itself, rather than any one chemotype, is what the misses have in common.
Peptide-like and macrocyclic molecules are a minority of them — 20 of 206 carry
four or more amide bonds, 13 are macrocyclic (largest ring ≥ 12), 29 are one or
the other — but they are enriched among the largest: of the 72 misses with 40+
heavy atoms, 17 are amide-rich, 10 macrocyclic and 9 have no aromatic ring at
all.

One caveat on the stereocentre column: the data pipeline strips stereochemistry
and the fingerprint is stereo-blind, so this counts *potential* stereocentres —
sp3 carbons with four distinct substituents — on an already-flattened molecule.
It is a measure of saturated structural complexity, not of stereochemical
information the model was denied. Sites like these are exactly where a folded
Morgan fingerprint is least informative per bit, since saturated carbon
environments are both numerous and similar.

Nothing is unreachable by construction: zero misses exceed the token limit, and
the longest failing reference is 125 tokens against a 128 limit. **Scaling
should help, and it should help most on big molecules** — which is also where
the full-ChEMBL corpus adds the most examples.

### First-candidate validity

One of the two questions the stored aggregates could not answer. Validity of the
*first* candidate specifically is **0.9044**, against 0.9027 pooled across all
draws. There is no first-candidate penalty; the model's opening guess is as
well-formed as any other.

### Likelihood ranking — the night's real result

The candidate set is fixed at the first 20 scored, and only the order changes:

| ordering | rec@1 | rec@5 | struct@1 | struct@5 |
|---|---|---|---|---|
| generation order (baseline) | 0.5302 | 0.7996 | 0.5087 | 0.7837 |
| log P(sampled string) | 0.5153 | 0.8298 | 0.4964 | 0.8119 |
| log P per token | 0.5327 | 0.8364 | 0.5061 | 0.8175 |
| **log P(canonical form)** | **0.6580** | **0.8701** | 0.6370 | 0.8584 |
| **sampling frequency (consensus)** | **0.7520** | 0.8666 | 0.7249 | 0.8528 |

Two findings.

**Consensus ranking is worth +22.2 points of `rec@1`.** Ordering by how many
distinct SMILES spellings the model emitted for a molecule — how often it
arrived at that answer by different routes — takes `rec@1` from 0.5302 to
0.7520. It needs no extra forward passes: the count falls out of the samples
already drawn. The model's confidence is encoded in *repetition*, not in the
per-string probability of the particular spelling it happened to emit.

**Scoring the sampled string is the wrong thing to score.** Log-probability of
the string as emitted is *worse* than generation order at k=1 (0.5153 against
0.5302). Scoring the same molecule's canonical form instead gains +12.8 points.
Randomised-SMILES training spreads a molecule's probability mass across its
spellings, so an unusual traversal of the right molecule scores below a common
traversal of a wrong one. Canonicalising before scoring collapses that.

### The caveat that belongs beside these numbers

For exact inversion, `rec@1` is not a real constraint. The oracle is
fingerprint equality, and anyone holding the query fingerprint can compute it
locally for every candidate at no cost — so in practice you check all 20 and
get `rec@20` = 0.8947. Ranking matters in the cases where verification is *not*
free:

- a perturbed or partial fingerprint, where no candidate will match exactly;
- choosing which of several fingerprint matches is the original molecule, which
  is `struct@1` — and consensus lifts that from 0.5087 to 0.7249;
- any setting where the oracle is a cost rather than a local computation.

It also says something about the model independent of its use: the information
needed to pick the right answer is already in the samples, and generation order
wastes it.

---

## Stage 3 — is there a generative model in here? No.

The plan's cheapest test of latent generative capability: perturb a known
fingerprint, ask what the model produces for it, and see whether it moves
towards the perturbed target or snaps back to the molecule it knows. 300
fingerprint-unseen molecules, 40 raw strings per query, bits dropped, added or
swapped.

| condition | validity | distinct/q | hit perturbed | exact original | Tanimoto to perturbed | Tanimoto to original | beats original |
|---|---|---|---|---|---|---|---|
| unperturbed | 0.906 | 12.2 | 0.913 | 0.907 | 0.976 | 0.976 | — |
| drop 1 | 0.882 | 13.9 | 0.007 | 0.810 | 0.932 | 0.950 | 0.007 |
| drop 2 | 0.845 | 16.3 | 0.000 | 0.687 | 0.888 | 0.921 | 0.007 |
| drop 4 | 0.786 | 18.3 | 0.000 | 0.470 | 0.795 | 0.850 | 0.007 |
| drop 8 | 0.643 | 19.6 | 0.000 | 0.143 | 0.603 | 0.664 | 0.010 |
| drop 16 | 0.462 | 16.3 | 0.000 | 0.000 | 0.376 | 0.418 | 0.007 |
| add 1 | 0.900 | 12.3 | 0.000 | 0.910 | 0.955 | 0.975 | 0.000 |
| add 4 | 0.880 | 14.4 | 0.000 | 0.877 | 0.892 | 0.969 | 0.000 |
| add 16 | 0.643 | 21.8 | 0.000 | 0.597 | 0.677 | 0.892 | 0.003 |
| swap 2 | 0.876 | 14.7 | 0.000 | 0.817 | 0.916 | 0.954 | 0.007 |
| swap 8 | 0.733 | 20.1 | 0.000 | 0.447 | 0.714 | 0.827 | 0.000 |
| swap 16 | 0.503 | 18.3 | 0.000 | 0.107 | 0.491 | 0.621 | 0.003 |

`beats original` is the fraction of queries where some *novel* candidate sits
closer to the perturbed target than the original molecule does. It is **≤ 0.010
in every condition**. That is the whole result:

- **It snaps back.** Tanimoto to the original fingerprint exceeds Tanimoto to
  the perturbed target in every single condition. The model is not chasing the
  perturbation; it is reconstructing the molecule it recognises, slightly worse.
- **Added bits are nearly ignored.** With 16 bits added — a target at Tanimoto
  0.745 from the original — it still returns the original molecule exactly
  59.7% of the time, and stays at 0.892 Tanimoto to the original. Extra
  substructure evidence does not make it build the substructure.
- **Dropped bits degrade it rather than redirect it.** Validity falls from 0.906
  to 0.462 at 16 dropped bits. Removing evidence pushes it off-manifold into
  malformed strings, not towards a different valid molecule.
- **Essentially nothing lands on the perturbed target** (≤ 0.007). Expected for
  `add`, where usually no molecule has that fingerprint — but also true for
  `drop`, where sub-fingerprints of real molecules often are realisable.

**The cheapest generative route does not work on this model.** The plan's
evidence for latent capability was that failures land at mean Tanimoto 0.760,
read as "producing analogues when it cannot hit exactly". Stage 3 shows that is
better explained as degradation than as generation: the near-misses are failed
reconstructions of one target, not exploration of a neighbourhood. The model has
learned a near-deterministic inverse, and perturbing its input degrades the
inverse rather than steering it.

This does not rule out the more ambitious routes in the plan — interpolation and
partial specification — but it removes their cheap proxy, and it suggests both
would need training against a loosened oracle (Tanimoto ≥ threshold, or masked
bits) rather than being read out of a model trained on exact equality. That is a
training change, not a probe.

---

## Stage 4 — the constant-epoch corpus point, and why it is degenerate

Item 5 of the plan. At a fixed step budget `steps × batch = corpus × passes` is
an identity, so corpus size and repetition rate cannot be separated — the reason
night 2's data-scaling fit was withdrawn. The plan's proposed fix was to hold
*passes* fixed instead: `small_1m` already is 3 epochs at 21,117 steps, so the
cheap companion point is 3 epochs on the 100k shard, 2,127 steps.

`small_100k_3ep`, 21:47 → 22:56: 2,127 steps in 69 min, completed on its step
budget. That is 1.95 s/step wall-clock, but ~1.2 s/step of training — three
in-training oracle evaluations account for the rest. Common protocol:
**`rec@20` = 0.0603**.

| | steps | corpus | epochs | rec@1 | rec@20 | validity |
|---|---|---|---|---|---|---|
| `small_100k_3ep` | 2,127 | 90,682 | 3 | 0.0046 | **0.0603** | 0.262 |
| `small_1m` | 21,117 | 909,800 | 3 | 0.5302 | **0.8947** | 0.903 |

The run is healthy and simply undertrained. Its curve climbs monotonically —
0.0000 at step 709, 0.0321 at 1,418, 0.0621 at 2,127, on the in-training
500-molecule evaluation — train loss is still
falling (1.43 → 0.77 → 0.61, valid 0.91 → 0.61 → 0.53), and it stopped because
it hit `max_steps` while still improving. Nothing is broken.

**But the comparison is worthless, and the reason matters.** Validity is 0.262:
after 2,127 steps the model has not yet learned SMILES syntax, let alone
fingerprint inversion. `rec@1` is 0.0046 — essentially zero. The 0.0603 → 0.8947
difference is therefore dominated by *crossing the threshold of basic
competence*, not by corpus size.

So holding passes fixed does not rescue the corpus question; it relocates the
confound. Fixing epochs makes compute scale with corpus, and at the small end
there is not enough compute left to produce a model worth comparing. The two
framings fail in complementary ways:

| framing | what it confounds | verdict |
|---|---|---|
| fixed steps, vary corpus | repetition rate moves with corpus (identity) | night 2's retraction |
| fixed epochs, vary corpus | compute moves with corpus; small end is pre-competent | this run |

**The corpus question is already answered as well as it can be, by runs
already on disk.** `small_100k_long` and `small_1m` are matched at 21,117 steps
and differ tenfold in corpus:

| run | corpus | steps | rec@20 |
|---|---|---|---|
| `small_100k_long` | 90,682 | 21,117 | 0.8446 |
| `small_1m` | 909,800 | 21,117 | **0.8947** |

**A decade more data is worth +5.0 points at matched compute**, against +24.9
points for 2.5× the compute on a fixed corpus. Repetition rate differs between
them (30 epochs against 3) and cannot be removed — but both models are competent,
which is what makes the number readable at all. That is the honest version of
item 5, and it needed no new run.

The practical consequence: **do not spend further machine time on the small end
of the corpus axis.** The full-ChEMBL run will supply a third constant-epoch
point at 44,112 steps, and it will carry the same confound; it is worth running
as a deliverable, as the plan already says, not as an experiment.

## Stage 5 — count fingerprints do not help

Item 3, named as item 6 in the Phase 1 results and never run until now. Counts
retain substructure multiplicity, so they carry strictly more information than
bits. The plan framed this as item 2's question from the opposite side: if
recovery jumps, the bottleneck is the input representation; if not, it is model
capability.

`count_fp_100k`, 23:12 → 02:11: 8,508 steps in 2.98 h, 1.26 s/step. Identical to
`small_100k` in every respect — same 7,951,945 parameters, same 100k shard, same
12 epochs, same learning rate and horizon — except `counts: true`.

| run | fingerprint | rec@1 | rec@5 | **rec@20** | struct@20 | validity |
|---|---|---|---|---|---|---|
| `small_100k` | binary | 0.1800 | 0.4182 | **0.5982** | 0.5879 | 0.790 |
| `count_fp_100k` | count | 0.1687 | 0.3962 | **0.5890** | 0.5818 | 0.733 |
| `count_fp_100k` re-judged under binary | — | 0.1708 | 0.4003 | **0.5920** | — | — |

**Counts buy nothing.** The count model is 0.9 points *below* the binary model
on its own oracle and 0.6 points below when its candidates are re-judged against
the binary fingerprint — so the stricter target is not the explanation. Strictly
more input information produced no gain at all.

Two notes on making this comparison fair:

- **The oracle.** A count model's own oracle demands an exact *count* match,
  which is a harder question than bit equality. Scoring only that would penalise
  the richer input for being asked more. `scripts/rejudge_binary.py` re-scores
  the same candidates, in the same order, against the binary fingerprint; the
  conclusion is unchanged.
- **The `fp_unseen` slice** is defined under the binary fingerprint, taken from
  the first present run before `--only` narrows the list. That is valid for the
  count model and slightly conservative: two molecules sharing a count
  fingerprint necessarily share a binary one, so binary-unseen is a subset of
  count-unseen. The count model is never credited with a query its own
  fingerprint had seen.

What should *not* be claimed: that counts are worse. This is a cross-run
comparison, the pattern behind all three of this project's retracted claims, and
single-run training variance at this scale has never been measured. A 0.6–0.9
point gap is small enough to be variance. The defensible reading is **no large
gain, in a setup designed to show one** — and that is enough for the decision it
was run to inform.

**Cancel the comparable-scale count run.** The plan allocated night 1 to counts
at 1M / 21,117 steps, ~8 h, "only if the cheap signal justifies it". It does not.

### Both sides of the question now agree

Item 2 and item 3 were designed to attack the same question from opposite
directions, and they answer it the same way:

| evidence | reading |
|---|---|
| 2 of 206 misses are fingerprint collisions | the input is not ambiguous where the model fails |
| recovery 0.98 → 0.37 across the size range | failures track molecular size and complexity |
| strictly richer input buys 0.0 points | more input information is not the limiting factor |

**The bottleneck is model capability, not the fingerprint.** Information-theoretic
headroom exists — ~98% of ChEMBL fingerprints are unique — and the model is not
using the information it already has.

---

## What this changes about the plan

### Settled, and off the list

| plan item | status |
|---|---|
| 1 — oversample fix + re-score | **done.** Headline 0.8926 → 0.8947; ordering unchanged; `rec@1`/`rec@5` unchanged by construction. The gate is clear. |
| 2 — failure taxonomy + likelihood ranking | **done.** Capability ceiling, not information. Consensus ranking worth +22.2 points of `rec@1`. |
| 3 — count fingerprints, cheap signal | **done, negative.** No gain. |
| 3 — counts at comparable scale (~8 h) | **cancelled.** The cheap signal does not justify it. |
| 5 — constant-epoch corpus point | **done, degenerate.** 2,127 steps is below the competence floor; the question is already answered by `small_100k_long` vs `small_1m` (+5.0 points per decade of data at matched compute). |
| bit-flip probe | **done, negative.** No latent generative behaviour; the model snaps back. |

That clears one night of machine time (counts at scale) and the small end of the
corpus axis, and it leaves the two weekend runs as the plan had them.

### Unchanged

- **Full ChEMBL, 3 epochs, 44,112 steps, ~18 h, a ~20 h window.** Still the
  deliverable, still not an experiment, and now better motivated: failures
  concentrate on large molecules, and the full corpus is where the large
  molecules are. Everything the plan said about readiness holds, and item 1 —
  its only stated prerequisite — is done.
- **Item 4, step saturation (100k, 52,500 steps, ~21 h).** Still the science,
  and stage 4 sharpens why: compute is the one lever that moves this model, and
  the third point has to sit on the 100k corpus where the other two already are.
- **Capacity (15M) stays last, and remains uncharacterised.** `medium_1m`
  re-scores at 0.2822 against `small_1m`'s 0.8947, which is tempting to read as
  the 15M configuration being broken. It is not evidence of that: `medium_1m`
  stopped on `max_hours` at **2,500 steps**, 8.4× short of `small_1m`'s 21,117,
  and `small_1m` at 2,500 steps would have been comparably bad — `small_100k_3ep`
  reached only 0.0603 at 2,127. The two runs differ in capacity *and* compute, so
  the comparison says nothing, exactly like the three claims this project has
  already retracted. Capacity is untested, not disproven. The plan's reason for
  deferring it — compute is the measured lever, MPS scaling goes superlinear past
  15M, and `medium_1m` costs 2.66 s/step — is unaffected and still right.

### New, and cheap

- **Ship consensus ranking.** Ordering candidates by sampling frequency lifts
  `rec@1` 0.5302 → 0.7520 and `struct@1` 0.5087 → 0.7249 with no extra forward
  passes and no retraining. `Morg2Smiles.generate` currently sorts by
  `(fp_match, tanimoto)`, which is right when the oracle is free and wrong when
  it is not; frequency is the better tiebreak within each group. ~1 h.
- **Report `rec@1` under consensus ordering from now on.** Generation order is
  not a neutral baseline — it discards information already present in the
  samples.
- **Measure single-run training variance.** Every retraction here came from a
  cross-run comparison, and the stage 5 null result is limited by not knowing
  the noise floor. Two identical runs at 2,127–8,508 steps on the 100k shard
  would cost ~3–6 h and would put an error bar on every comparison in this
  repository. This is the highest-value cheap run that is not yet scheduled.

### If the generative direction is still wanted

Stage 3 says it will not fall out of this model. Interpolation and partial
specification would need **training against a loosened oracle** — Tanimoto ≥
threshold, or a masked subset of bits — rather than probing a model trained on
exact equality. That is a new training objective and a new success criterion,
and it should be scoped as such rather than as an afternoon's probe.

### Revised schedule

| slot | job | machine | note |
|---|---|---|---|
| **Working day** | Consensus ranking in `generate` + tests | ~1 h | ships the night's result |
| | Variance pair on the 100k shard | ~3–6 h | puts an error bar on everything |
| **Weekend 1** | Full ChEMBL, 3 epochs, 44,112 steps | ~18 h (~20 h window) | the deliverable |
| **Weekend 2** | Item 4 step saturation, 52,500 steps | ~21 h | the science |
| *Deferred* | 15M capacity | — | debug, not scale |
