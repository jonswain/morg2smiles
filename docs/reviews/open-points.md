# Open points register

Every numbered point from every review round, carried forward so that nothing
raised in one round is lost in the next. Status is one of `fixed`, `rejected`
(with a reason), `deferred`, or `open`.

Round 3's reviewer must return a verdict on every row that is not `fixed`.

## Counts by round

| round | blocker | major | minor | total numbered |
|---|---|---|---|---|
| 1 | 4 | 10 | 3 | 16 (+28 line edits, 17 consistency, ~70 comprehensibility) |

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
| R1-A8 | 1 | addition | validity-by-band table | `open` | a few minutes of CPU over the dumps; §5.10's argument turns on validity and no band-level figures exist |
