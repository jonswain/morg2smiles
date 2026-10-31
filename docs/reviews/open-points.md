# Open points register

Every numbered point from every review round, carried forward so that nothing
raised in one round is lost in the next. Status is one of `fixed`, `rejected`
(with a reason), `deferred`, or `open`.

Round 3's reviewer must return a verdict on every row that is not `fixed`.

## Counts by round

| round | blocker | major | minor | total numbered |
|---|---|---|---|---|
| 1 | 4 | 10 | 3 | 16 (+28 line edits, 17 consistency, ~70 comprehensibility) |
| 2 | 3 | 12 | 2 | 17 (+20 line edits, comprehensibility log) |
| 3 | **0** | 3 | 8 | 11, plus adjudication of all 33 earlier points |

**Blockers: 4 → 3 → 0.** Round 2 found *more* majors than round 1, because two
of its three blockers were defects the round-1 revision introduced — including
the convention collision committed in the same commit that documented it as
having happened five times. Round 3 found three majors, and said that three of
its eleven new points were again defects introduced by the previous revision.

That is the real finding of the exercise: **each round's fixes introduced new
arithmetic errors at roughly a third the rate it removed them.** Reviewers do
not converge on their own. What closed it was
`tests/test_report_figures.py` — 22 tests that recompute every load-bearing
figure from the dumps — added in round 3 and which failed on its first run.

## Register

| id | round | severity | point | status | where resolved |
|---|---|---|---|---|---|
| R1-01 | 1 | blocker | "0.976, even the misses are near misses" contradicts §5.12 and is an all-query mean | `fixed` | §1.3, §5.1 rewritten; 0.7923 among misses, near-miss share rising with size |
| R1-02 | 1 | blocker | headline `rec@1` in generation order while the adopted ranking is consensus (16 pts) | `fixed` | §1.3 two-row table; ranking named on every `rec@1`; glossary rule |
| R1-03 | 1 | blocker | "concentrated on fewer queries than chance in every band" false in 5 of 6 | `fixed` | §5.13 six-band Poisson table; also corrected in `overnight-2026-10-30.md` |
| R1-04 | 1 | blocker | §5.5's "no model ever finds a 50-atom molecule on its first proposal" falsified | `fixed` | §5.5 scoped to its four cells, with the ninth-cell break stated |
| R1-05 | 1 | major | "+22.09 against −23.55 nets +1.37" arithmetic | `fixed` | §5.6: −1.46 predicted vs +1.37 measured, both sub-threshold |
| R1-06 | 1 | major | §5.8's two deficit-ratio tables unlabelled | `fixed` | both captions carry metric, k, protocol, n |
| R1-07 | 1 | major | crossover "~ten thousand queries" stale | `fixed` | §5.4 two-cell table, 55,271–121,634; §1.3 updated |
| R1-08 | 1 | major | size-weighted mix cited 4×, never described | `fixed` | new §5.11a |
| R1-09 | 1 | major | "(entry 26)" cites night 7's incident for night 8's | `fixed` | `retractions.md` entry 26 broadened to both nights; report cites by night |
| R1-10 | 1 | major | "fiftyfold" untraceable | `fixed` | no ratio quoted; measured 0.2251 → 0.7402 and "at least two orders of magnitude" |
| R1-11 | 1 | major | "every pooled-band miss is low" has a counterexample; 6 intervals never measured | `fixed` | 16-of-17 with the 35+ exception; six sub-bands computed, score now 9 of 26, ledger entry 29 |
| R1-12 | 1 | major | §9 item 6's "unexplained" gap is exactly the collision rate | `fixed` | item 6 deliberately empty, identity stated |
| R1-13 | 1 | major | "the additive law" never stated | `fixed` | glossary writes the law and defines `f′`, `g′`, `g′/f′` |
| R1-14 | 1 | minor | §4 hours sum to 156.2 h vs headline 118.7 h | `fixed` | column renamed "session" with a note; title block corrected |
| R1-15 | 1 | minor | `c ÷ b` not re-tested on the ninth cell | `fixed` | row added to §5.13's exponent table |
| R1-16 | 1 | minor | `b`'s band-structure caveat dropped from §5.13 | `fixed` | carried across from `results.md` §2.1 |
| R1-C | 1 | consistency | 17 items: the `\|r\|`/cells/range composite, eight-vs-nine cells, the 98.6% inference, the invented sixth cause, Phase 1 hours, date range, "two of them", §2.1 self-reference, shard table "total"/"clean", test count, and the untraceable numbers | `fixed` | see `round-1-response.md` |
| R1-N | 1 | naming | five names for three protocols | `fixed` | one name each, swept; aliases noted once in §3.6 |
| R1-A7 | 1 | addition | add the existing size-cliff figure to §5.12 | `deferred` | `plot_size_cliff.py` predates the final run; what the figure should show is a judgement better made with round 2 in hand |
| R1-A8 | 1 | addition | validity-by-band table | `fixed` | closed after round 3, pre-registered first — see the round-3 block below and §5.10 |

## Round 2

| id | severity | point | status | where resolved |
|---|---|---|---|---|
| R2-01 | blocker | §1.3's headline table mixes conventions within a row; "16 points" subtracts across them | `fixed` | convention is now a **column**; +15.3 within the molecule budget |
| R2-02 | blocker | "Tanimoto" never defined, yet carries §5.12's central result | `fixed` | glossary row under "The task" |
| R2-03 | blocker | the "fiftyfold" retracted in §5.13 is still asserted in §1.3 | `fixed` | replaced with the measured 0.2251 → 0.7402 |
| R2-04 | major | `b` range attributed to eight cells (it is one cell's bands); §5.5's invariant is 35+ only | `fixed` | both corrected |
| R2-05 | major | §5.12's final-run Tanimoto triple skips 35–39, faking monotonicity | `fixed` | all four bands, non-monotonicity stated |
| R2-06 | major | "near-miss share rises with size" is not monotone | `fixed` | 17/24/22/58 given |
| R2-07 | major | 0.981 and 0.366 rest on n=54 and n=41, unlabelled; and the band is 50–69 | `fixed` | cell, protocol, both n, correct band |
| R2-08 | major | "full-k rate 1.000 in every band" misleading in the adopted convention | `fixed` | 46% molecule-budget fill, 28.7 distinct/query |
| R2-09 | major | "about twenty slots" is a k=20 figure presented as general | `fixed` | cells named, 28.7 given for the final run |
| R2-10 | major | registration tables name no convention | `fixed` | "molecule budget" on both, plus a note on the mismatch with the before/after table |
| R2-11 | major | the `c` per-band targets are unsourced | `fixed` | sourced inline to the 100k 2×2 at k=60 |
| R2-12 | major | glossary gives +22 and 16 for one effect | `fixed` | +22 and +15.3, each against a named cell |
| R2-13 | major | statistical vocabulary and night numbering used before introduction | `fixed` (part) / `rejected` (part) | four-row Statistics glossary added; **declined** moving §4 ahead of §3 or dating every "night N" — stated as a judgement in `round-2-response.md` |
| R2-14 | major | "entry N" never introduced | `fixed` | clause in the authority table |
| R2-15 | major | the five registrations never enumerated, so "9 of 26" is uncheckable | `fixed` | inventory table at the head of §5.13, with the 9/13/4 split |
| R2-16 | minor | §5.9's seed-pooling gain omits its 3× cost | `fixed` | cost stated and contrasted |
| R2-17 | minor | §5.11a's placement and self-diagnosing opening | `fixed` (part) / `rejected` (part) | opening rewritten; **declined** the renumber — ~40 cross-references and two heavily-cited anchors to fix a `minor` |
| R2-L | line edits | 20 items | `fixed` | all applied; see `round-2-response.md` |
| R2-X | factual | "1.46% of distinct atom environments" traces to nothing | `fixed` | **removed** from `report.md` and `README.md`, replaced by the measured 950,967 → 943,177 |
| R2-A | addition | `preimages_per_hit` column for §5.13's concentration table | `fixed` | added in round 3 — 1.66 / 1.83 / 2.29 / **3.54** |

## Round 3

Round 1's reviewer, returning with round 2's review in hand. Verdict: **minor
revision**. It adjudicated all 33 earlier numbered points: **24 resolved**, **2
rejections justified**, **8 still standing** (now fixed below), and raised 3
majors and 8 minors of its own.

| id | severity | point | status | where resolved |
|---|---|---|---|---|
| R3-01 | major | §1.4 says "eleven misses, ten run with size"; the scoring file gives nine and eight | `fixed` | verified from `job4_scored.json`; round 1 had it right, the round-2 rewrite broke it |
| R3-02 | major | the `c` per-band targets are sourced to the wrong cell | `fixed` | they are the 100k **step** pair (§5.3's), not §5.8's 1M capacity 2×2; its all-slice 0.911 is §5.3's 0.9113 |
| R3-03 | major | round 2's comprehensibility log was untracked and 17 terms unaddressed | `fixed` | 5 glossary rows, 7 inline definitions; this row is the tracking that was missing |
| R3-M | minor | 8 items: "four-tenths" is 0.86; 50–69 vs 50–64; consensus `rec@60` asserted not measured; §3.7's "four points" unnamed cell; §2.1's circular replacement; §1.4's convention column; §5.4's mixed cut factors; two surviving aliases | `fixed` | see `round-3-response.md`; consensus `rec@60` now **measured** at 0.9586 |
| R2-13b | major | the declined half — helping the reader with "night N" | `fixed` | round 3's lighter fix: one forward pointer at the first occurrence, not dating every mention |
| R1-C, R1-N | consistency | 5 consistency items and 2 aliases still standing | `fixed` | — |
| R2-07, R2-09, R2-10, R2-11 | major | the halves round 3 judged still standing | `fixed` | — |
| R2-17, R1-A7 | minor | the renumber and the stale figure | `rejected`, **judged justified by round 3** | cost verified independently: ~167 occurrences across `docs/` |
| R1-A8 | addition | validity-by-band table | **`fixed`** | done, and pre-registered first (`scripts/validity_by_band.py`'s header, committed before the script was run). 3 of 4 registered items hold; the registered *monotone* decline misses, and that miss is the finding — validity plateaus at ~0.87 above 55 heavy atoms while `rec@60` keeps falling 0.804 → 0.755 → 0.680, so it cannot be what makes the cliff. §5.10 now carries the table. |
| R2-A | addition | `preimages_per_hit` column | `fixed` | added as the last column of §5.13's concentration table — 1.66 / 1.83 / 2.29 / **3.54** |

**Closing state: zero `open` rows.** R1-A8, the last one, was closed after round
3 — see §5.10. It was pre-registered before measurement, which is how a request
arriving from review avoids becoming a post-hoc reading.
