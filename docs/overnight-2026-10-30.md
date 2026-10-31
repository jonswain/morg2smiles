# Night 9 — 2026-10-30/31: the final run, full ChEMBL at six passes

Item 4 of [next-steps-2026-10-19.md](next-steps-2026-10-19.md) and the last
experiment of the programme, run to the plan in
[final-run-plan.md](final-run-plan.md). Launched 18:50 Friday at git `b9f2045`,
training finished 20:18 Saturday, everything scored by 22:43 — 27 h 53 m end to
end, with 307 minutes still to spare against the deadline.

8.0M parameters (7,963,767), `data/shards/full` — 1,881,996 train / 104,555
valid — batch 128, **88,218 steps = 6.00 passes**, cosine to zero, eval cadence
8,000. Stage 1 exited on `step budget of 88218 reached / 25.36 h`, so it stopped
where the pre-registration said it would and not on the `max_hours` guard, which
still had 5.6 h of headroom. The five registrations in
`configs/small_full_6p.yaml` therefore apply.

The headline is that **the model is much better than registered on the hard
part of the problem and slightly worse on the easy part, and the two invariants
this run tested for the first time on a second corpus did not both survive.**

## The oracle picked the last checkpoint

Worth stating before any metric, because across eight previous sessions the
oracle-based selector has usually preferred an earlier checkpoint to the final
one. Here it chose **step 88,218, the last**. Six passes over full ChEMBL had
not stopped paying when the registered budget ended the run. Nothing in this
report measures where it would have stopped.

## The registered numbers

Scored mechanically by `scripts/score_job4.py`, written before the result
existed so that the verdict is a lookup rather than a judgement, and refusing by
construction to read a registration against a band table measured in a
different convention. Full output in `results/overnight9/job4_scored.json`.

**9 of 26 registered intervals landed inside.** Six of them — the 50–54 /
55–59 / 60–64 sub-bands of registration (2), on both metrics — were **not scored
on the night**, because `band_analysis.py`'s default band list does not contain
that split, so stage 4b produced only the pooled 50+ row. They were computed
later from the dump already on disk, at no GPU cost, and they are the sharpest
result of the run: see "the registration of record" below. The night's own
figure was "9 of 20".

The misses are not scattered:

| registration | band | registered | measured | verdict |
|---|---|---|---|---|
| (2) 50+ instrument, rec@60 | 50+ (893) | 0.6310–0.6912 | **0.7615** | miss high, 7.03 pts (4.9 SE) |
| (2) 50+ instrument, struct@60 | 50+ (893) | 0.5403–0.6025 | **0.6809** | miss high, 7.83 pts (5.0 SE) |
| (3) 30+, rec@1 consensus | 50+ (127) | 0.3283–0.4401 | **0.5984** | miss high, 15.83 pts (3.6 SE) |
| (3) 30+, rec@1 consensus | 40–49 (380) | 0.6705–0.7445 | **0.7842** | miss high, 3.97 pts (1.9 SE) |
| (3) 30+, rec@1 consensus | 30–34 (1,189) | 0.9073–0.9354 | 0.9083 | hit |
| (3) 30+, rec@1 consensus | all (2,321) | 0.8405–0.8732 | 0.8591 | hit |
| (3) 30+, struct@1 consensus | 50+ (127) | 0.2331–0.3338 | **0.4331** | miss high, 9.93 pts (2.3 SE) |
| (3) 30+, struct@1 consensus | 30–34 (1,189) | 0.8808–0.9129 | **0.8671** | miss **low**, 1.37 pts (1.4 SE) |
| (3) 30+, struct@1 consensus | 30–39 (1,814) | 0.8578–0.8900 | **0.8479** | miss **low**, 1.00 pts (1.2 SE) |
| (4) 30+, rec@60 | 40–49 (380) | 0.9140–0.9522 | 0.9184 | hit |
| (4) 30+, rec@60 | 35+ (1,132) | 0.9368–0.9599 | **0.9329** | miss **low**, 0.39 pts (0.5 SE) |

**The direction is the result.** Every miss on a hard band is high; every miss
on an easy or pooled band is low. Registration (1), the all-slice rec@60, was
declared a ceiling reading in advance by §4a of the config and is reported, not
scored: 0.9582 against a registered 0.9634–0.9767, which is 0.5 points under the
floor of an interval narrower than the 1.6-point threshold that governs the
metric. That is what a ceiling reading looks like and it resolves nothing.

What it means is that **the size extrapolation was too steep**. The laws were
fitted where the cliff is severe and projected onto a run five times longer; the
cliff flattened faster than they predicted. A registration built from those laws
under-promised at 50+ by 7 to 16 points and over-promised on the saturated bands
by 1. Both are errors in the same model, read in opposite directions.

## What the run actually buys, against the same protocol at 1.2 passes

`small_full_1p2` from nights 7 and 7b is the same architecture on the same
shard, scored by the same invocation on the same queries — 17,772 steps against
88,218, which on a fixed corpus is 1.2087 against 6.00 passes. Raw-slot
convention throughout this table (`miss_anatomy.py`), so read it against itself
and not against the band tables above, which run ~1–2 points higher.

| | 30+ protocol (2,321) | 50+ instrument (893) |
|---|---|---|
| rec@1 | 0.2783 → **0.6963** | 0.0258 → **0.3180** |
| rec@20 | 0.6829 → **0.9302** | 0.1501 → **0.6685** |
| rec@60 | 0.7553 → **0.9496** | 0.2251 → **0.7402** |
| structure@60 | 0.7376 → **0.9375** | 0.1624 → **0.6428** |
| collision rate among hits | 0.023 → 0.013 | 0.279 → **0.132** |
| mean fp hit rank | 7.0 → 2.5 | 16.3 → **6.6** |

The 50+ column is the one worth pausing on. A metric that read 0.0258 at rec@1
a fortnight ago reads 0.3180, and the collision rate — the share of recoveries
made by a *different* molecule with the same fingerprint, the irreducible part
of the task — **halved**, from 0.279 to 0.132. Earlier sessions could not tell
the irreducible floor from the model's own weakness at 50+ because the model
was too weak to see past. At six passes the floor is visible: 13.2% of 50+
recoveries are collisions, and that part is not a modelling problem.

Per-band, and this is the flattening in one place:

| band | n | rec@1 | rec@60 | struct@60 | collide | hit rank |
|---|---|---|---|---|---|---|
| 30–34 | 1,189 | 0.7788 | 0.9756 | 0.9731 | 0.003 | 2.0 |
| 35–39 | 625 | 0.7088 | 0.9600 | 0.9520 | 0.008 | 2.3 |
| 40–49 | 380 | 0.5447 | 0.9026 | 0.8842 | 0.020 | 3.6 |
| 50+ | 127 | 0.3150 | 0.7953 | 0.6929 | 0.129 | 6.9 |

The two independent reads of 50+ agree, compared **within one convention** as
§1 of [methodology.md](methodology.md) requires. In the molecule budget: 0.8110
on the 127 queries inside the 30+ protocol against 0.7615 on the 893-query
instrument, 4.95 points apart against a combined SE of 3.76 — **1.3 SE**. In raw
slots: 0.7953 against 0.7402, 1.4 SE. The protocols are blind in opposite
directions and they do not disagree.

(The first draft of this paragraph compared 0.7953 against 0.7615 — raw slots
against molecule budget. That is the convention collision of
[methodology §1](methodology.md#1-recovery-has-two-conventions-and-they-differ-by-points),
caught for the fifth time, here by proof-reading rather than by a guard. The
conclusion is unchanged in either convention, which is luck and not a defence.)

## The registration of record, scored late

§4b of [final-run-plan.md](final-run-plan.md) registers rec@60 and struct@60 for
50–54, 55–59 and 60–64 on the 50+ instrument and calls them "the registration
**of record** for large molecules". **Stage 4b did not measure them.**
`band_analysis.py`'s default band list is
`0-24,25-29,30-34,35-39,40-49,50+,30-39,35+,all`, with no 50–54/55–59/60–64
split, and the driver passed no `--bands`, so the only row produced was the
pooled 50+ one. Nothing failed; six registered intervals simply were not scored,
and the night's headline read "9 of 20" against 26 registered.

Recomputed from `outcomes_50plus_full_6p/small_full_6p.jsonl`, which was already
on disk — no GPU, generation order, molecule budget, k=60:

| band | n | metric | registered | measured | verdict |
|---|---|---|---|---|---|
| 50–54 | 433 | rec@60 | 0.7325–0.7997 | 0.8037 | MISS HIGH 0.40 pts (0.2 SE) |
| 55–59 | 257 | rec@60 | 0.5804–0.6696 | 0.7549 | MISS HIGH 8.53 pts (3.2 SE) |
| 60–64 | 203 | rec@60 | 0.3841–0.4785 | **0.6798** | **MISS HIGH 20.13 pts (6.1 SE)** |
| 50–54 | 433 | struct@60 | 0.6482–0.7222 | 0.7436 | MISS HIGH 2.14 pts (1.0 SE) |
| 55–59 | 257 | struct@60 | 0.4979–0.5884 | 0.6537 | MISS HIGH 6.53 pts (2.2 SE) |
| 60–64 | 203 | struct@60 | 0.2682–0.3542 | **0.5813** | **MISS HIGH 22.71 pts (6.6 SE)** |

**The miss grows monotonically with size on both metrics**, 0.40 → 8.53 → 20.13
and 2.14 → 6.53 → 22.71. That is the night's directional finding stated as
sharply as the data can state it, and it was sitting unscored. The further the
extrapolation reached, the worse it over-predicted the cliff.

**The method failure is worth its own line.** This project's rule has been to
write the number down before the run. These numbers *were* written down, on
night 8, and still went unscored — because the tool that scores them has a
default argument that does not contain the registered bands. **The defaults of
the scoring tool are part of the registration**, and `score_job4.py`'s guard
could not catch this: it verifies that a registration and a measurement share a
convention, and it reported the three sub-bands as "absent" in its own output,
which nobody read as a failure. A guard that reports a gap without failing is a
log line.

## Stage 6: the exponents, on the protocol rather than the trace

Stage 5b of the driver **failed, exit 1**, for precisely the reason registered
in advance: it fits each run's own in-training history, and `small_full_1p2` has
only 2 usable trace points, so the guard refused the pair rather than publish
one. It did fit the two valid traces. Stage 6, registered in §8 of
[final-run-plan.md](final-run-plan.md) before any of these numbers existed, is
the replacement, and it reads the matched pair of protocol dumps instead.
Scored by `scripts/score_stage6.py`; output in
`results/overnight9/stage6_scored.json`.

| quantity | read against | measured | |
|---|---|---|---|
| `b` from `budget_curve.py` | 0.144–0.396 | 0.299–0.385, **every band** | hit |
| `b ÷ rec@60` | 0.320–0.380 | 5 of 6 inside; 35–39 at 0.401 | essentially holds |
| `c` at k=60, all bands | 0.7008–0.9113 | **0.986** (30+), 0.682 (50+) | miss high, as registered to expect |
| `c` per band | 1.092 / 1.083 / 0.770 / 0.381 | 1.058 / 1.080 / **0.970** / **0.802** | easy bands reproduce, hard bands do not |
| `g′` at 50+, full shard | +26.30 | **+22.28** | 4.02 lower on the larger corpus |
| `g′ / f′` at 50+ | 1.52–1.68 | **1.322** | miss low, 0.198 |

Four things follow, in increasing order of how much they cost.

**The budget law transports again, to a ninth cell.** `b` inside 0.144–0.396 in
every band, correlations |r| ≥ 0.985. This is now the most robust quantity in
the project.

**`c` is confirmed to be a local slope, not a law.** The registration said in
advance that the honest expectation for that row was a miss, because night 8
measured `c` falling with range and there is no reason a slope read at 30–74
passes should hold at 1.2–6. It missed high. The registration was right about
being wrong, which is the only way that row could have been informative.

**But the *size dependence* of `c` is not a property of the decoding problem.**
That was the registered interpretation of a match on the per-band row, and it
fails in an instructive way: the two easy bands reproduce the 100k corpus's
exponents to within 3% (1.058 vs 1.092; 1.080 vs 1.083) while 40–49 comes in
1.26× and 50+ **2.11×** higher. So the exponent transports where the task is
easy and does not where it is hard. On a bigger corpus the hard bands improve
with steps far faster than the small-corpus fit said they would — the same
flattening the registration misses showed, measured a second way.

**The exchange rate between the two axes does not transport.** `g′` at 50+ fell
from +26.30 on the 1M shard to +22.28 on the full shard, and against the 1M
shard's `f′` of +16.86 the ratio is 1.322 where 1.52–1.68 was registered. The
registration named what a miss would mean: *passes and molecules substitute
rather than add.* That is the first direct evidence against the additive law in
[results.md §2.9a](results.md#29a-f-measured-directly-at-constant-passes), and it should be read as one
pair on one corpus with no error bar, not as a refutation. What survives intact
is the `b ÷ rec@60` invariant — interventions still slide the model along one
curve rather than bending it. What does not survive is the claim that the price
of a doubling is the same on either axis regardless of corpus.

## The budget the fitted law now asks for

| band | k for 0.9 | k for 0.95 | k for 0.99 |
|---|---|---|---|
| 30–34 | 1 | 9 | 669 |
| 35–39 | 5 | 30 | 1,929 |
| 40–49 | 50 | 437 | 66,912 |
| 50+ | 654 | 6,640 | 1,444,900 |
| all | 8 | 58 | 6,277 |

Extrapolations, every one, and lower bounds. 30–34 reaching 0.9 in a **single
slot** is new. 50+ needing 654 slots for the same cut is the size cliff
surviving everything this project threw at it, 50 times cheaper than a fortnight
ago and still three orders of magnitude from the easy bands.

And the concentration finding holds, which is why more budget does not close it:

| band | preimages / query | if Poisson | none | per hit |
|---|---|---|---|---|
| 30–34 | 1.627 | 0.8036 | 0.018 | 1.66 |
| 40–49 | 2.100 | 0.8775 | 0.082 | 2.29 |
| 50+ | 2.874 | 0.9435 | **0.189** | 3.54 |

Preimages per query *rise* with size — 50+ queries draw more of them, not fewer
— while 18.9% of 50+ queries draw none at all.

The Poisson column needs reading more carefully than this report first did.
Measured recovery sits **above** the Poisson expectation in every band except
50+ (0.9823 against 0.8036 at 30–34, 0.9184 against 0.8775 at 40–49), and
**below** it only at 50+ (0.8110 against 0.9435). So below 50 atoms the
preimages are spread *more* evenly across queries than chance, and concentration
is a large-molecule phenomenon rather than a general one. An earlier version of
this paragraph said the proposals are "concentrated on fewer queries than chance
everywhere", which the dump contradicts in five bands of six. The cliff is still
a concentration problem at its far end, and six passes made it much smaller
without changing that.

## Process notes

Two, both worth recording because the point of the ledger is that method
failures are findings.

**The stage 6 command registered in the plan was not runnable.** `step_curve.py`
requires `--runs` even when `--pair` does the work, and §8 omitted it. The fix
is additive and touches nothing in the pair arithmetic, but a registered command
that has never been executed is a registration of intent, not of procedure.
Night 8's cost came from a config omission discovered *after* a 17-hour run; this
one cost nothing only because the stage was free.

**Scoring was mechanical, and that is the first time it has been.** Both scorers
were written before their inputs existed, and `score_job4.py` carries a guard
that refuses a convention mismatch rather than reporting one. Entries 22 and 26
of [retractions.md](retractions.md) are both post-hoc readings of a registration;
this night had no opportunity to add a third.

## What this night changes

- The final run exists. `rec@1 = 0.6963` and `rec@60 = 0.9496` on the 30+
  protocol, `0.3180` and `0.7402` on the 50+ instrument.
- **The size extrapolation was too steep.** Hard bands beat their registrations
  by 7–16 points, saturated bands missed low by ~1. The cliff flattens with
  scale faster than the laws fitted at small scale predict.
- **The irreducible floor at 50+ is now visible**: 13.2% of recoveries there are
  fingerprint collisions, down from 27.9%, and that share is not a modelling
  problem.
- **`g′ / f′` is not corpus-invariant** (1.322 vs 1.52–1.68), and `g′` falls on
  the larger corpus. The additive law of §2.9 has its first direct
  counter-evidence. One pair, one corpus, no error bar.
- **`c`'s size dependence is corpus-dependent.** It transports in the easy bands
  and not in the hard ones.
- `b` transports to a ninth cell; `b ÷ rec@60` holds in 5 of 6 bands.
- The oracle selected the final checkpoint, so **the step axis was still paying
  when the run ended**. Where it stops is not measured and is now the leading
  open question.

## Stage log

| stage | what | exit | wall |
|---|---|---|---|
| 1 | train 88,218 steps | 0 | 25.36 h |
| 2 | 30+ large protocol, k=60, T=0.6, 2,400 queries | 0 | 1.91 h |
| 3 | 50+ instrument, k=60, T=0.6, 1,000 queries | 0 | 0.49 h |
| 4 / 4b | band tables, both metrics, k=60 and k=1 consensus | 0 | 7 s |
| 5 | miss anatomy and budget curve | 0 | 12 s |
| 5b | step exponent from in-training traces | **1** | 0 s — guard refused the pair |
| 6 | matched-pair exponents on the protocol | 0 | post hoc, zero GPU |

Validity 0.972 at 30+ and 0.890 at 50+; 28.7 and 65.5 unique valid candidates
per query against `--max-oversample` 12 and 10, so the oversample was calibrated
and neither protocol ran short of slots. `budget_filled_rate` 1.000 everywhere.

## Sources

- `configs/small_full_6p.yaml` — the five registrations
- [final-run-plan.md](final-run-plan.md) — the plan, and §8's stage 6
- `results/overnight9/job4_scored.json`, `stage6_scored.json` — the verdicts
- `results/overnight9/miss_anatomy_full_6p.json`, `miss_anatomy_50plus_full_6p.json`,
  `budget_curve_full_6p.json`, `step_curve_pair_30plus.json`,
  `step_curve_pair_50plus.json`
- `results/overnight9/comparison_k60_full_6p.json`, `comparison_50plus_full_6p.json`
- [report.md](report.md) — the whole programme, of which this is the last session
