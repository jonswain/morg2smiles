# Author response to round 1

Reviewer verdict: **major revision**, 4 `blocker`, 10 `major`, 3 `minor`, plus
28 line edits, 17 consistency items and ~70 comprehensibility entries.

**The diagnosis was right and it was the diagnosis I could not have reached
myself.** §1 and §5.1–§5.12 were written before the final run, §5.13 was
appended at the end, and I never went back to retire the statements the final
run falsified. Four of them were stated as universals in Findings. I verified
every blocker and every major point against the saved dumps before responding;
**I rejected none of them on the facts.** Two I have implemented differently
from the suggestion, and one of the reviewer's "could not trace" items turned
out to be sourced — both recorded below.

The review also found a genuine scientific gap that produced a new result and a
new ledger entry: see point 11.

## Blockers

| # | point | status | what changed |
|---|---|---|---|
| 1 | "0.976 Tanimoto, even the misses are near misses" contradicts §5.12's "Not near-misses" | **accepted** | Verified: 0.976 is a mean over *all* queries, dominated by exact hits at 1.0. The among-misses figure is **0.7923** (`miss_anatomy_full_6p.json`). Removed from §1.3 and §5.1. §1.3 now gives 0.79 and the 29% above 0.9, and adds the finding the correct number exposes — the near-miss *share rises* with size, 17% → 58%, while recovery falls. §5.1 keeps the 0.976 but labels it as an all-query mean that says nothing about failures. |
| 2 | headline `rec@1` is generation order; the adopted ranking is consensus, 16 points higher | **accepted** | Verified 0.6963 vs **0.8591** on the same queries. §1.3 now leads with a two-row table giving both, and notes ranking cannot move `rec@60`. Glossary states that every `rec@1` in the report names its ranking. §1.4's table and §5.13's tables now carry the ranking per row. §5.1's 0.7526 I checked separately — it *is* consensus (`overnight-2026-10-15.md` L528) — and is now labelled. |
| 3 | "concentrated on fewer queries than chance in every band" is false in 5 of 6 bands | **accepted** | Verified from `budget_curve_full_6p.json`: measured recovery *exceeds* Poisson in every band except 50+. Replaced with the six-band table and the stronger claim the reviewer suggested — **concentration switches on with size** rather than being a general property of the decoder. Also corrected in `overnight-2026-10-30.md`, which had the same sentence. |
| 4 | §5.5's "No model ever finds a 50-atom molecule on its first proposal" is falsified by §5.13 | **accepted** | Verified: `A` at 50+ is **0.696** in the ninth cell, not ~1.00, and 50–64 `rec@1` is 0.3150 / 0.5984. Scoped the claim to the four cells it was measured on and added the break as an explicit before/after. |

## Major

| # | point | status | what changed |
|---|---|---|---|
| 5 | "+22.09 against −23.55 nets +1.37" — arithmetic | **accepted** | It is −1.46 predicted against +1.37 measured. Rewritten to the reviewer's sharper framing: a sub-threshold difference of two 23-point numbers. Inherited from `results.md` §2.9, so flagged there too. |
| 6 | §5.8's two deficit-ratio tables unlabelled | **accepted** | Both now carry metric, k, protocol and n, and the text says they are one finding on two instruments. |
| 7 | crossover "~ten thousand queries" is stale | **accepted** | The ninth cell's `break_even` was already on disk: **55,271–121,634**. §5.4's table now has both cells side by side and says the crossover is a property of the model. §1.3 updated. |
| 8 | the size-weighted mix is cited four times and never described | **accepted** | Added **§5.11a**, ten lines from `results.md` §2.8: −0.28 points whole-protocol, +5.29 above 35 atoms, the exposure already spent, and the band-level predictions failing. |
| 9 | "(entry 26)" cites night 7's tiling failure for night 8's | **accepted, fixed at the source** | The reviewer offered two fixes; I took the one in `retractions.md`, broadening entry 26 to cover both nights explicitly, because the alternative leaves the ledger with one entry for two incidents. The report now cites by night. |
| 10 | "fiftyfold" cannot be traced | **accepted** | It traces to nothing — I could not reconstruct it either. The real ratios are 144× against the previous best cell, 15,000× against §5.2's, ~10⁹ against the same shard at 1.2 passes. **Both ends of any such ratio are extrapolations beyond k=60, so the quotient is unstable and I now quote no ratio at all**, only the measured 0.2251 → 0.7402 and "at least two orders of magnitude". |
| 11 | "every miss on a pooled band is low" has a counterexample; and 6 intervals were never measured | **accepted — and this produced a new result** | Verified 35+ `rec@1` is MISS HIGH by 0.53 pts; the rule is now "16 of 17 misses, one exception, inside the noise". On the second half: the plan registers 50–54 / 55–59 / 60–64 on both metrics and calls them "the registration **of record**", and `band_analysis.py`'s default band list does not contain that split, so they were never scored. I recomputed them from the existing dump — **free, no GPU** — and **all six miss high, monotonically in size: +0.40 / +8.53 / +20.13 points on recovery, +2.14 / +6.53 / +22.71 on structure, the last at 6.6 SE.** That is the sharpest evidence in the report for its own central finding and it was sitting unscored. `score_job4.py` now reads the sub-band tables, the score is **9 of 26**, and the failure is **ledger entry 29**: *the defaults of the tool that scores a registration are part of the registration.* |
| 12 | §9 item 6's "unexplained" gap is exactly the collision rate | **accepted** | Verified to five decimals: 0.7402 × (1 − 0.13162) = 0.642777 against a measured 0.642777, residual 0.00000. Item 6 is now deliberately empty, with the identity stated and the error left visible, rather than silently deleted. |
| 13 | "the additive law" is never stated | **accepted** | The glossary now writes it down — `rec@60 ≈ f(log₂ molecules) + g(log₂ passes)` — and says `f′`/`g′` are its slopes and `g′/f′` the exchange rate between them. This was the cheapest high-value fix in the document, as the reviewer said. |
| 14 | §4's hours sum to 156.2 h against the headline 118.7 h | **accepted** | Column renamed "session" with a note that it is wall-clock including scoring. Title block corrected to 2026-10-08 (phase 1) and "118.7 hours of training time". |
| 15 | `c ÷ b` not re-tested on the ninth cell | **accepted** | Added as a row of §5.13's exponent table: target 2.54–3.39, measured 2.25–2.90, all-slice 2.75 — holds at the low edge. |
| 16 | §5.13 drops `results.md`'s caveat that `b`'s band structure flattened | **accepted** | Carried across: `b` at 50+ is 0.299 against 0.144, so extra guesses now help large molecules about twice as much — independent evidence for the section's own finding. |

## Consistency items

Accepted and fixed: the `|r| ≥ 0.991 / nine cells / 0.144–0.396` composite (now
split into the eight-cell and ninth-cell readings); "eight cells" vs "nine
cells" for `b ÷ rec@60`; the 98.6% inference (the two totals give 99.2%; 98.6%
is the per-molecule statistic, now said so); the invented "sixth cause" in §9
(deleted — §7 has five, and the genuinely new one found in this review is now
§7.4's third form and ledger entry 29); Phase 1's 4.2 h vs 3.75 h; the date
range; the "two of them" with no antecedent; §2.1 referring to itself;
the shard table's undefined "total" and "clean"; the 478 test count (now 499).

**Protocol naming**, the reviewer's costliest recurring item: five names for
three protocols, now one each — "the common protocol", "the 30+ protocol", "the
50+ instrument" — swept through the document, with the old aliases noted once in
§3.6 because the night logs use them.

Numbers the reviewer could not trace, now sourced or reconciled in the text:
the `0.28 → 0.10 → 0.02` chain (named as the 100k cell it belongs to, with the
final run's figures beside it); "roughly twenty molecules" (twenty *slots*, of
which 12–21 are distinct valid molecules — two different quantities, now
distinguished); "the worst-validity band" (cited to night 6, with an explicit
note that this report carries no validity-by-band table); the `+1.01 points`
serving two descriptions (it is one measurement, now said so); §5.9's ranking
table (now carries model, protocol, k, n and T).

**One correction to the reviewer.** The 0.976 of blocker 1 was described as
untraceable to a model or protocol; it is in fact sourced — `small_1m`, common
protocol — but the reviewer is right that it is the wrong *statistic* for the
sentence it was supporting, which is the point that mattered.

## Cheap additions

| # | suggestion | status |
|---|---|---|
| 1 | score the six unmeasured registered intervals | **done** — see major 11; the single most valuable item in the review |
| 2 | add the ninth cell to §5.4's crossover table | **done** |
| 3 | give the Poisson comparison its own column | **done** — six-band table in §5.13 |
| 4 | report mean best Tanimoto among misses per band | **done** — in §1.3 and §5.12 |
| 5 | add a `c ÷ b` row | **done** |
| 6 | make convention and ranking table *columns* rather than caption prose | **done for every table I touched**; not retrofitted to every table in the document |
| 7 | add the existing size-cliff figure to §5.12 | **deferred to round 2** — `plot_size_cliff.py` predates the final run, so the figure would show an eight-cell state of the world inside a section the final run rewrote. Regenerating it is cheap but it is a judgement about what the figure should show, and I would rather make that with the round-2 reading in hand. |
| 8 | validity-by-band table | **deferred to round 2** — a few minutes of CPU over the dumps. Worth doing; §5.10's cancellation argument turns on validity and the report has no band-level figures for it. Recorded in the open-points register as `open`. |

## What this round cost and bought

No GPU. One free re-analysis of an existing dump, which added six scored
intervals, changed the headline score from 9 of 20 to 9 of 26, produced the
report's sharpest size-gradient result, and added a ledger entry.
