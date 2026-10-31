# Review of `docs/report.md` — "Inverting Morgan fingerprints: the complete report"

Reviewer brief: readability and comprehensibility for a first-time reader with no prior
knowledge of the project. Read end to end before writing. Line numbers are approximate and
refer to `docs/report.md` as it stands.

---

## 1. Assessment

This is an unusually good technical report, and the thing it does best is the thing most
reports of this kind do worst: it tells you what it does not know. The structure is right —
a self-contained summary, methods that actually precede findings, findings that each name a
cell and an error bar, a limitations section written "in the order a sceptical reader would
ask", and a next-steps section that registers its own readings in advance. The decision to
make measurement failure a first-class result (§7) rather than an embarrassment is the
report's real contribution and is transferable well beyond this task. The glossary at the
front, the one-paragraph domain statement that governs the whole document, and the explicit
rule that `§n` always means this report are all excellent instincts, and I used all three.
Numerically it holds up well: I traced roughly thirty assertions to `results/` dumps or the
night logs and the overwhelming majority reproduce exactly (the §5.4 crossover table, the
§5.13 band table, the §5.13 cliff prices, the six registration-of-record rows, f′ and g′,
the 118.7 h total, the Poisson table, 0.9986/0.6890, the twelvefold preimage rise).

What most needs work is, ironically, the one convention the report itself identifies as its
most expensive piece of plumbing. **The headline table in §1.3 (lines 157–161) mixes the two
recovery conventions inside a single row**, and the "16 points" ranking gap drawn from it
(line 162) is a cross-convention subtraction. The report's own §3.7 forbids exactly this, and
§7.2 says the error has been caught five times — this would be the sixth. Separately, **the
"~50× cheaper" figure that §5.13 explicitly retracts as tracing to nothing (line 1485) is
still asserted as fact in §1.3 (line 228)**. Both are free to fix from data already on disk,
but both sit in the summary, which is the part most readers will take away, and a reader who
notices either will stop trusting the rest. There is also a scatter of smaller factual slips
that look like late-draft edits: a Tanimoto triple in §5.12 that does not match the dump
(line 1270), a `b` range attributed to the wrong population (line 192), an `n` of 41 behind
the most-quoted cliff number, and a "full-k rate is 1.000" claim (line 1261) that is true in
one convention and badly false in the adopted one.

Would a newcomer come away understanding what was done and what was found? Mostly yes, and
that is a real achievement for a 1,800-line document covering nine sessions. But it is a
near miss rather than a clean pass, for three reasons that are all cheap to fix. First,
**"Tanimoto" is never defined anywhere** and is load-bearing for §5.12's central negative
result. Second, the report cites "entry 18", "entry 27", "entries 12, 13" about twenty times
without ever telling the reader that these are numbered rows of `retractions.md` — the first
occurrence is at line 355, long before §7. Third, the five pre-registrations of the final run
are referred to throughout §1.4 and §5.13 as "registration (1)", "(2)", "(3)", "(4)" and
never enumerated, so the reader cannot reconstruct what was registered without opening
`final-run-plan.md`. Fix those three, correct the convention mix and the 50× contradiction,
and this is an accept.

---

## 2. Comprehensibility log

The most important section. Grouped by kind; exhaustive as far as I could make it.

### 2a. Terms, symbols and notations used before they are defined, or never defined

| line | quoted text | problem |
|---|---|---|
| 175 | "The closest proposal to a missed target averages **0.79** Tanimoto" | **"Tanimoto" is never defined in the document.** It is the glossary's most conspicuous absence and it carries §5.12's whole "not near-misses" bullet. A newcomer cannot tell whether 0.79 is close or far, nor what "0.65 Tanimoto from the target" (1276) means. |
| 355 | "Both early conclusions were withdrawn (entry 18)." | First of ~20 bare "entry N" citations. The reader has been told (line 21) that `retractions.md` holds "all 29 withdrawn claims", but never that they are numbered or that the report will cite them by number. The notation is never introduced. |
| 1412, 1395, 246 | "Registration (1), the all-slice rec@60…"; "`final-run-plan.md` §4b registers them" | The **five registrations are never enumerated in this report.** §1.4 describes them by elimination ("one of the five was declared… one was registered as questions…"), and §5.13 then refers to "(1)", "(2)", "(3)", "(4)" as if they had been listed. They have not. The reader must open `final-run-plan.md` to know what was predicted. |
| 262, 1373, 1390 | "ten run with size in exactly this way"; "16 run with size" | "runs with size" is used as a term of art and never defined. It appears to mean "the sign and magnitude of the miss increase monotonically with the band's heavy-atom count", but the reader has to infer it. |
| 298, 956, 1428, 1463, 1530 | "the ratio `b ÷ rec@60` held across the eight cells" | The quantity is used five times as the report's central invariance claim and is **never motivated**. Why should an exponent divided by a recovery level be the natural invariant? What would a value outside 0.320–0.380 mean? One sentence of justification is needed the first time it appears. |
| 640–641, 658, 663, 1123 | "McNemar's paired SE on the discordant pairs — about **0.8 points** at 13% discordance"; "ten discordant pairs" | "McNemar", "discordant pair" and "discordance" are never defined. §3.8 is the section a sceptical reader will lean on hardest and it is the densest in undefined statistics. |
| 1000, 640, 1366, 1383 | "binomial SE 0.89"; "paired SE"; "a combined SE of 3.76"; "(6.1 SE)" | **Four different standard errors** are in play (binomial, paired/McNemar, combined, and whatever the registration tables use) and the report never says which is which or when each applies. A reader comparing "6.1 SE" in §1.4 with "0.8 points" in §3.8 has no way to know they are different estimators. |
| 222, 1489–1499 | "95.8% recovery against a Poisson 83.6%" | The Poisson comparison is **used in §1.3 at line 222 and explained only at line 1490**, 1,270 lines later, parenthetically. §1.3 is explicitly written to be readable cold; this is the one place it is not. |
| 1174 (heading) | "### 5.10 Decoding: T=0.6, top_p 1.0, everywhere" | `top_p` is never defined. The glossary defines `temperature` but not its companion, and the section never says what setting `top_p 1.0` means (no nucleus truncation). |
| 510 | "with teacher-forced validation loss kept only as a diagnostic" | "teacher-forced" undefined. |
| 379 | "reached 98.1% OPSIN round-trip accuracy on 103M PubChem compounds" | "OPSIN round-trip accuracy" undefined. A reader cannot tell whether 98.1% here is comparable to the 95.0% claimed for this project — which matters, because the sentence invites the comparison. |
| 718 | "One Apple M2 (MPS)" | "MPS" undefined. |
| 755 | "A new checkpoint needs its `RUNS` entry in the same commit as its config." | `RUNS` is never introduced. The reader cannot tell what artefact this is. |
| 556 | "`generate_outcomes` draws `k × oversample` strings" | A function name dropped with no indication of where it lives or what calls it; and the relationship between the constant `oversample=2.0` and the `max_oversample` of 10/12 in §3.6 is never stated. |
| 866 | "fitted on the 100k arm's k ≤ 20 rungs" | "rungs" undefined (it means the measured k values). |
| 728, 1762 | "one 2,400-query k=60 scoring arm"; "the capacity arm" | "arm" is used throughout and never defined. The glossary defines **cell** but not **arm**, and the two are used almost interchangeably. |
| 632 | "A comparison is prefix-to-prefix or it is nothing." | "prefix-to-prefix" is an idiom, not an explanation. What is a prefix here? The reader cannot act on the rule as stated. |
| 1094 | "at two step counts — the closed 2×2" | "the closed 2×2" undefined (2 capacities × 2 step counts, all four cells trained). Dropped as if established. |
| 1523 | "truncation 5.1 atoms" | "truncation" is never defined as a quantity. Truncation of what, relative to what? |
| 1533 | "`beats original` ≤ 0.010 in every condition" | A metric name in backticks that appears nowhere else in the document. Unreadable as written. |
| 789 | "The remaining 10.5%, and count fingerprints" | "The remaining 10.5%" of what? (Presumably `1 − 0.895` on the common protocol.) Never stated. |
| 253, 813, 1348, 1357, 1386 | "`struct@1`", "struct@20", "structure@60", "`struct@60`" | The glossary defines `structure_accuracy@k`. The four abbreviations are never tied back to it, and both "struct@" and "structure@" are used for the same metric. |
| 499 | "cosine decay to zero over `min(total_steps, max_steps)`" | `max_steps` is never introduced; the reader cannot tell what the min is protecting against. |
| 446 | "The full shard was built with `--exclude`" | A flag of an unnamed tool. |
| 461 | "the `fingerprint_id` hash of the `FPConfig` that produced it" | `FPConfig` undefined. |
| 1243–1249 | "the per-band gaps fit log₂ exposure at +4.21 points per doubling" | "exposure" is used as a measured axis but never defined. Exposure to what, measured how? (It appears to be the fraction of the training diet drawn from the up-weighted size range.) |
| 4, 786 | "a phase-1 gate and nine overnight sessions" | "phase-1 gate" appears in the subtitle and is explained only in §4's table, 780 lines later. |
| 633, 645, 676–710 | "On night 7 the mixed pair would have inflated f′"; "Night 8 registered rec@60 in 0.88–0.95" | §3.8 and §3.9 refer to nights 7 and 8 by number **before §4 introduces the session numbering**. A reader going front to back has no map yet. |
| 1769 | "`base_1m` (25.7M parameters) is kept in the repo" | The largest config is called "base", which reads backwards; and the reader has only met it as "~~25.7M~~" in a struck-through table row at line 485. |

### 2b. Passages I had to re-read to understand

| line | quoted text | why |
|---|---|---|
| 67 | "It is the project's adopted ranking… **every `rec@1` in this report names its ranking**… The two differ by 16 points." | The same glossary entry says consensus is "worth +22 points of `rec@1`" and then that "the two differ by 16 points". Two different numbers for what reads like the same quantity, in adjacent sentences, with no indication that they are different cells. I read this three times and still had to go to §5.9 and §5.13 to resolve it. |
| 76 | "`steps × batch = corpus × passes` is an **identity**, so the steps axis *is* the passes axis — which is why 'what is data worth at fixed compute' is not a well-posed question" | Three logical steps compressed into one clause in a glossary cell. This is the single most important idea in §5.6 and it deserves the two sentences §5.6 gives it, not a parenthesis. |
| 106–107 | "The two pairs are in different units because they were asked as different questions" | Correct and necessary, but the explanation arrives after the table that creates the confusion. Consider putting the units sentence before the table. |
| 200–203 | "The crossover depends on the model: about **ten thousand queries** for the cell it was first measured on, and **55,000–122,000** for the final one, because training got cheaper per point faster than budget did." | "cheaper per point" needs unpacking. Also an over-long line that breaks the file's wrap. |
| 270–272 | "They cost nothing to compute from the dump that was already on disk. They are the sharpest result in the section, and a reader would never have seen them." | "a reader would never have seen them" — but the reader is seeing them, in the table immediately above. The intended meaning (had the omission not been caught in review) has to be reconstructed. |
| 342–344 | "Folding 2,048 bits loses 1.46% of distinct atom environments and affects half of all molecules, but rarely enough to make two molecules collide." | I could not parse "affects half of all molecules, but rarely enough to". Also an over-long line. See §5 below: I could not trace 1.46%. |
| 530–536 | "Deduplication must *mark* same-molecule candidates rather than drop them, or validity's denominator silently changes — dropping removes mostly *valid* candidates, which made validity read 0.714 against a true 0.785." | Dense. Three clauses and two numbers doing different jobs. Worth splitting. |
| 556–569 | the whole "Filling the budget" block | The interaction of `oversample`, `max_oversample`, "tops up k at a time", and the duplicate-rate table took three passes. The punchline ("better models explore less") is excellent and currently buried. |
| 589–597 | "Each protocol is blind in its own direction." | Five separate figures (63%, −1.13, +4.60, −3.11, 4.18, p = 0.32, 127) in one paragraph, each a pointer to a different finding. Consider making it a short table. |
| 684–691 | rule 3 of §3.9, "The reason biases any cell near the floor: among hits at 50+…" | The most important methodological rule in the document and the hardest paragraph in it. Four nested clauses and three ratios. It needs to be two or three sentences with the mechanism stated first ("a weak model's few hits land on the ambiguous fingerprints") and the numbers second. |
| 711–714 | "Both mechanisms registered for one stage were eliminated, and the useful output was the null — which only reads as useful because the branches carried mechanisms rather than directions." | "one stage" of what? Which mechanisms? This paragraph has no referents and I could not fix its meaning. |
| 731–735 | "the final run's cost model was therefore *solved* from two same-shard cells rather than quoted — two equations in per-step and per-eval cost — and independently confirmed against the measured final-eval times (~216 s solved, 180.3 s and 224.6 s measured)." | Dense, and the "confirmation" reads at first glance like a miss until you notice 216 lies between 180.3 and 224.6. Say so. |
| 743–744 | "It now uses `time.time()`, and `caffeinate -dimsu -w <pid>` holds the machine awake rather than merely measuring the loss correctly." | "rather than merely measuring the loss correctly" — I could not determine the meaning of this clause at all. See §2d. |
| 867–871 | "(Entry 10 of the ledger records the retraction this caused; its own headline figure is the rec@100 version of the same error.)" | Opaque without `retractions.md` open. "its own" has no clear antecedent. Also an over-long line. |
| 977–979 | "This is one of the better before/after contrasts in the report and it was originally written here as a universal." | "written here as a universal" — meaning unclear on first read. |
| 1019–1020 | "since a number pushed to a floor it was predicted to be below agrees without evidence" | The point is good (a floor reading cannot discriminate) but the sentence is a tongue-twister. |
| 1107–1110 | "The most useful thing in the comparison is that the *same* comparison is worth +1.33 or +7.11 points. **This is the same finding read on the other instrument**" | Took three passes. The two numbers are introduced before the table that produces them, and "the other instrument" has to be resolved backwards. Put the table first. |
| 1226–1227 | "Referenced three times above and never described, so stated here for completeness" | An admission that the document's order is wrong. The size-weighted mix is cited in §3.6 (599–602), §5.11a and §7.3; it should be described where it is first used, not in a lettered subsection afterwards. |
| 1278–1284 | "Two predictions of that account held…" | Dense: two interventions, a per-query count, a constant conversion rate, and a composition claim in four lines. |
| 1296–1302 | "**The number of preimages the model draws barely depends on size — 15% across the range.**" | This flatly contradicts §5.13's "Preimages per query *rise* with size (1.63 → 2.87)" at line 1488, 190 lines later. §5.13 says it "sharpens" §5.12 rather than confirming it, but never says that the *direction of the size dependence inverted between the two models* or why (the final model is strong enough to draw many preimages on big molecules). A reader will take this as a contradiction. |
| 1364–1369 | "in the molecule budget, 0.8110 on the 127 queries inside the 30+ protocol against 0.7615 on the 50+ instrument — 4.95 points apart against a combined SE of 3.76, so **1.3 SE**. In raw slots the same pair reads 0.7953 against 0.7402, 1.4 SE." | Four numbers in two conventions across two protocols in one sentence. Correct, careful, and very hard. A 2×2 table would read in five seconds. |
| 1402–1405 | "A registration is not scored because it was written down" | Needs "merely": as written it reads as the opposite of what is meant. |
| 1593 | "Nothing flagged it, because every interval that *was* computed scored cleanly. And register the **slope, not the level**, whenever the metric is bounded" | The "And register the slope…" rule is tacked onto the end of an unrelated paragraph with no transition. Also an over-long line. |
| 1724–1731 | §9 item 6, "Nothing — this slot is deliberately empty." | The point is good but the arithmetic is definitional: `struct = rec × (1 − collision rate)` by construction, so "0.642777 against a measured 0.642777" is an identity, not a discovery, and "to five decimal places" overstates it when the inputs are quoted to four. Say that the identity is definitional and the finding is that there is no residual beyond it. |

### 2c. Points where I had to leave the document, or scroll a long way inside it

1. **Line 355 onward, every "entry N".** Resolvable only in `retractions.md`. ~20 occurrences.
2. **Line 1395, the five registrations.** Only `final-run-plan.md` §4b and `configs/small_full_6p.yaml` say what they were. §1.4 and §5.13 are both unreadable in detail without them.
3. **Lines 633, 645, 676–710: "night 7", "night 8".** Needs §4's table, 70–130 lines later.
4. **Line 222, the Poisson comparison.** Needs line 1490.
5. **Lines 157–161, the headline table.** I had to open `results/overnight9/comparison_k60_full_6p.json` and `band_k60_full_6p.json` to work out which convention each cell was in. A reader cannot do that.
6. **Lines 1183–1184:** "(measured in [night 6](overnight-2026-10-17.md); **this report carries no validity-by-band table**)". An explicit hand-off for a supporting fact. The claim is that 50–64 is "the corpus's worst-validity band"; one number (the band's validity) would keep the reader in the document.
7. **Line 1254, "Recovery falls from 0.981 below 15 heavy atoms to 0.366 at 50–64".** No cell, no protocol, no `n`. I had to go to `docs/overnight-2026-10-14.md` to find that these rest on 54 and 41 queries respectively.
8. **Line 1250:** "Full detail in [results.md §2.8]". This one is legitimate and well-signposted.
9. **Line 192, "across the eight cells it was first fitted on".** I had to go to `docs/overnight-2026-10-17.md` to discover that the eight-cell table is measured at 35+ only, and that 0.144–0.396 is not the eight-cell range at all (see §5).
10. **Line 1430, "`c` per band | 1.092 / 1.083 / 0.770 / 0.381".** These four target numbers appear nowhere else in the report and do not match §5.3's table. I could not source them from the report alone.
11. **Line 1227, the size-weighted mix.** §3.6 uses it as its worked example 630 lines before §5.11a describes it.

### 2d. Sentences whose meaning I could not determine with confidence

- Line 342–344: "Folding 2,048 bits loses 1.46% of distinct atom environments and affects half of all molecules, but rarely enough to make two molecules collide."
- Line 743–744: "…and `caffeinate -dimsu -w <pid>` holds the machine awake rather than merely measuring the loss correctly."
- Line 711–714: "Both mechanisms registered for one stage were eliminated, and the useful output was the null — which only reads as useful because the branches carried mechanisms rather than directions."
- Line 977–979: "…and it was originally written here as a universal."
- Line 272: "They are the sharpest result in the section, and a reader would never have seen them."
- Line 1402: "A registration is not scored because it was written down."
- Line 1483–1485: "The defensible statement is the measured one… An earlier draft said '~50× cheaper', which traces to nothing." — I understand the sentence, but not how it coexists with line 228 (see major point 3).

---

## 3. Major points

**1. §1.3, lines 157–162 — the headline table mixes the two recovery conventions inside one row, and the "16 points" figure is a cross-convention subtraction.** `blocker`

The table reads:

```
| | first guess (`rec@1`) | within 60 guesses (`rec@60`) |
| **consensus ranking** (adopted) | **85.9%** | 95.0% |
| generation order (unranked) | 69.6% | 95.0% |
```

From the dumps: 0.8591 (`results/overnight9/band_k1_full_6p.json`, `comparison_k60_full_6p.json`)
is **molecule budget**; 0.6963 and 0.9496 (`miss_anatomy_full_6p.json`) are **raw slots**. The
molecule-budget rec@60 is **0.9582** (`band_k60_full_6p.json`) and the molecule-budget
generation-order rec@1 is **0.7066** (`comparison_k60_full_6p.json`, `fp_unseen` slice). So the
consensus row pairs a molecule-budget rec@1 with a raw-slot rec@60, and the 16-point gap at
line 162 (85.9 − 69.6) subtracts across conventions. This is the error §3.7 is written to
prevent and §7.2 says has already been caught five times.

*Fix (free, numbers already on disk):* state one convention for the table and label it.
In the molecule budget: consensus 85.9% / 95.8%, generation order **70.7%** / 95.8%, ranking
gain **+15.3 points**. Optionally add the raw-slot row (69.6% / 95.0%) beneath, labelled, to
demonstrate the four-point convention gap in the headline where it will be remembered. Then
correct line 162 and the glossary entry at line 67, which propagates the same 16 points.

**2. Glossary (line 39 ff.) and §5.12 — "Tanimoto" is never defined.** `blocker`

First use is line 175, in §1.3, which the report says is written to be read cold. It then
carries §5.12's central negative result ("Not near-misses", lines 1265–1272) and §2.3's
critique of the predecessor (lines 393–396). A reader who does not already know what a
Tanimoto coefficient is cannot evaluate any of it.

*Fix:* add a glossary row under "The task" — e.g. "**Tanimoto similarity** — the overlap
between two molecules' fingerprints, from 0 (no shared bits) to 1 (identical fingerprints).
Used here only to describe *how close* a wrong answer was; it is never the correctness
criterion, which is the oracle." Two lines, and it also sets up §2.3's "Tanimoto is smooth,
flattering and lagging".

**3. §1.3 line 228 contradicts §5.13 line 1485 — the retracted "~50×" is still asserted in the summary.** `blocker`

Line 228: "the final run pushed it back roughly **fiftyfold** and left its shape intact."
Line 1485: "An earlier draft said '~50× cheaper', **which traces to nothing**."

§5.13 goes to some trouble to explain why no such ratio is defensible ("No single ratio is
quoted here on purpose… it ranges from ~10² to ~10⁹ depending on which pair is chosen") and
then §1.3 states the retracted version as fact. This is the most trust-damaging thing in the
document, because the summary is where a reader forms their view and §5.13 is where they
discover they were misled.

*Fix:* replace line 228's clause with §5.13's own defensible statement — e.g. "nothing tried
here dissolves the cliff — the final run cut `rec@60`'s shortfall at 50–64 from 0.2251 to
0.7402 and left the cliff's shape intact". Then grep the document for any other surviving
ratio of two extrapolations.

**4. §1.3 line 192 — the `b` range 0.144–0.396 is attributed to the wrong population; and §5.5's eight-cell invariant is measured at 35+ only, which is never said.** `major`

Line 192: "|r| ≥ 0.991 with `b` in 0.144–0.396 **across the eight cells it was first fitted
on**". But §5.2's table (lines 839–845) shows 0.144–0.396 is the range **across size bands of
a single cell** (`small_1m`). §5.13's registration table (line 1427) uses it the same way
("0.144–0.396" vs "0.299–0.385, every band"). Separately, `docs/overnight-2026-10-17.md`
line 1056 shows the eight-cell `b ÷ rec@60` range of 0.320–0.380 is measured **at 35+**;
§5.5 (lines 955–959) reports it as if it were whole-protocol.

*Fix:* line 192 → "with `b` in 0.144–0.396 across the size bands of the cell it was first
fitted on". §5.5 line 955 → "Eight cells, four interventions…, read at 35+ heavy atoms:".

**5. §5.12 line 1270 — the final-run Tanimoto triple does not match the dump, and its monotonicity comes from skipping a band.** `major`

"The final run reproduces the pattern at a much higher level — **0.75 / 0.78 / 0.86** among
misses". `results/overnight9/miss_anatomy_full_6p.json` gives
`mean_best_tanimoto_among_misses` of 0.7494 (30–34), **0.7976** (35–39), 0.7782 (40–49),
0.8550 (50+). The preceding clause lists the 100k cell at "0.69 at 35–39, 0.64 at 40–49 and
0.57 above 50", so the reader reads the new triple as the same three bands — which would be
0.80 / 0.78 / 0.86, not monotone. As printed, 0.75 is the 30–34 figure.

*Fix:* give all four bands and say plainly that the rise is not monotone: "0.75 / 0.80 / 0.78
/ 0.86 across 30–34 / 35–39 / 40–49 / 50–64 — higher everywhere than the 100k cell, and
highest where recovery is lowest."

**6. §1.3 line 176 — "rises with size" is not monotone.** `major`

"strikingly, that near-miss share *rises* with size, from 17% at 30–34 to 58% at 50–64". The
dump gives 17.2% / 24.0% / 21.6% / 57.7%. The 40–49 band falls below 35–39. The report is
scrupulous about monotonicity elsewhere (lines 255, 1178, 1390), so the looseness stands out.

*Fix:* "that near-miss share is *higher* at the top of the range than the bottom — 17% at
30–34 against 58% at 50–64, with the two middle bands at 24% and 22%".

**7. §5.12 line 1254 and §1.3 line 210 — the most-quoted cliff numbers have no `n` and no named cell.** `major`

"Recovery falls from 0.981 below 15 heavy atoms to 0.366 at 50–64" (1254) and "98.1% below 15
heavy atoms, 36.6% at 50–64 for the model that was current when it was characterised" (210).
`docs/overnight-2026-10-14.md` lines 115 and 122 show these rest on **54 and 41 queries**
respectively, on the common protocol, and the 0.366 row is labelled "50–69" there. The 36.6%
is quoted in the summary as the headline statement of the cliff while §8 warns that "127 is
the sample size that produced two overturned nulls" — 41 is a third of that.

*Fix:* name the cell, the protocol and both `n` in both places: "0.981 on 54 queries below 15
heavy atoms to 0.366 on 41 at 50–64, `small_1m` on the common protocol". Given §8's own
warning about thin samples, this is not a detail.

**8. §5.12 line 1261 — "the full-k rate is 1.000 in every band" is true in raw slots and badly false in the adopted convention.** `major`

"**Not the budget.** The full-k rate is 1.000 in every band — the model never runs out of
slots." In raw slots this is right. But `comparison_k60_full_6p.json` records
`budget_filled_rate` of **0.462** for the final run on the 30+ protocol in the molecule-budget
convention — i.e. fewer than half of queries yield 60 *distinct valid molecules*, with
`unique_valid_per_query` 28.7 and `duplicate_rate` 0.905. A reader will take "never runs out
of slots" to mean "never runs out of molecules to propose", which is exactly the claim the
molecule budget refutes. This also matters for §5.2's caveat about an asymptote and for §9
item 3's concentration argument.

*Fix (free):* keep the bullet but qualify it — "the raw-slot budget is always filled; in the
molecule budget the strongest model fills only 46% of a 60-slot budget (28.7 distinct valid
molecules per query), which is the concentration result of the next subsection seen from the
supply side, not a budget ceiling on recovery."

**9. §1.3 lines 215–216 — "about twenty slots, of which 12 to 21 are distinct valid molecules" is a k=20-era figure presented as a general property.** `major`

The sentence describes the cliff's mechanism for the whole project, citing §3.5, whose table
is `small_100k`/`small_1m` at k=20. The final run at k=60 proposes **28.7** distinct valid
molecules per query. Since §1.3's subject is the final model, the reader will attach "twenty
slots" to it.

*Fix:* say which cells the "twenty slots" characterise, and give the final run's figure —
"about twenty slots in the k=20 cells where the mechanism was characterised (12 to 21 of them
distinct valid molecules, §3.5), and 28.7 in the final run at k=60".

**10. §1.4 (lines 246–253) and §5.13 (lines 1381–1393) — the registration tables do not name their convention, and the six sub-band rows are in a different one from the table above them.** `major`

`results/overnight9/b50_subbands_recovery.json` records `"budget": "molecules"` for the six
registration-of-record rows (0.8037 / 0.7549 / 0.6798 and the structure trio). They appear in
§5.13 immediately after a before/after table declared "raw-slot convention throughout"
(line 1341) and are labelled only "`rec@60`, generation". §1.4's table has no convention
column at all. Given that §3.7 makes convention-naming a rule and §1.4 says "Every number
here carries the convention it was measured in" (line 26), the omission is conspicuous.

*Fix:* add "molecule budget" to both table captions, and a one-line note in §5.13 that the
registration tables and the before/after table are in different conventions by design,
because the registration was written against `band_analysis.py`'s output.

**11. §5.13 line 1430 — the `c` per band targets are unsourced and inconsistent with §5.3.** `major`

"| `c` per band | 1.092 / 1.083 / 0.770 / 0.381 | 1.058 / 1.080 / **0.970** / **0.802** |".
The measured column reproduces `step_curve_pair_30plus.json` exactly. The target column
appears nowhere else in the report; §5.3's table gives `c` = 1.294 / 1.240 / 0.893 / 0.366 for
the 1M pair. A reader cannot tell where the registered targets came from, and the §5.13
conclusion ("50+ **2.11×** higher") depends entirely on them (0.802 / 0.381 = 2.10).

*Fix:* say which cell and which k the target column is read at (it appears to be the 100k pair
at k=60) and either add that row to §5.3's table or cross-reference it.

**12. Glossary line 67 — the consensus entry gives two incompatible figures for the same effect.** `major`

"…is worth +22 points of `rec@1`… The two differ by 16 points." The +22 is `small_1m` on the
common protocol at k=20 (§5.9); the 16 is the final run on the 30+ protocol at k=60 (and is
itself wrong, per major point 1). The reader meets both in one glossary cell with nothing to
distinguish them.

*Fix:* "…worth +22 points of `rec@1` on the cell where it was measured (§5.9) and +15 on the
final run (§5.13); the gain is always quoted against a named cell."

**13. §3.8–§3.9 — the report's statistical vocabulary and its session numbering are both used before they are introduced.** `major`

§3.8 and §3.9 are the sections on which a sceptical reader's trust rests, and they open with
McNemar, discordance, difference-in-differences, four kinds of SE, and references to "night 7"
and "night 8" — all before §4 names the sessions and with none of the statistics defined.

*Fix:* (a) add three glossary rows (paired/McNemar SE, discordant pair, difference-in-
differences); (b) either move §4's nine-row session table to the front of §3, or give §3.8
and §3.9 a parenthetical date on first mention ("night 7 (10-20)", "night 8 (10-24/25)").

**14. "entry N" is never introduced as a notation.** `major`

First use line 355, ~20 uses thereafter, including three in §3.9's numbered rules where they
are load-bearing.

*Fix:* one sentence in "How to read this document", beside the `retractions.md` table row:
"Withdrawn claims are cited here as **entry N**, meaning row N of `retractions.md`."

**15. The five pre-registrations of the final run are never enumerated.** `major`

§1.4 (lines 234–240) and §5.13 (1412, 1421) refer to "the five", "(1)", and "§8 of the final
run plan" without ever listing them. A reader cannot check the claim "9 of the 26 landed
inside" or understand why registration (1) is reported-not-scored.

*Fix (free, ~8 lines):* a small table at the head of §5.13 — registration, what it predicted,
how many band × metric intervals it unfolds into, and how it was scored. From
`job4_scored.json`: (2) 50+ instrument rec@60 and struct@60, 4 bands each = 8; (3) 30+
protocol rec@1 and struct@1 consensus, 7 bands each = 14; (4) 30+ protocol rec@60 and
struct@60, 2 bands each = 4. Total 26, 9 HIT, 13 MISS HIGH, 4 MISS LOW. That last breakdown
is also worth printing: §5.13 says "16 run with size" but never gives the high/low split.

**16. §5.9 line 1169 — the three-seed pooling result is quoted at "the same oracle budget" without its 3× sampling cost.** `minor`

"three seeds with votes pooled beat one seed by 6.49 points of rec@20 at the *same* oracle
budget". `docs/overnight-2026-10-15.md` line 406 records it as "+6.49 points for 3× compute".
The sentence sits two lines below the consensus result that genuinely "costs nothing", and the
next sentence does carefully note that the temperature-pooling result "survives matching the
sampling cost". The asymmetry invites a reader to think seed-pooling is free.

*Fix:* "…by 6.49 points of rec@20 at the same oracle budget, though at three times the
sampling and training cost — unlike the temperature vote below, which survives matching it."

**17. §5.11a's placement.** `minor`

The section opens "Referenced three times above and never described" (line 1226), which is a
self-diagnosed ordering fault, and the "a" in "5.11a" tells the reader it was bolted on.

*Fix:* move the three-line description of the size-weighted mix into §3.4 (training) or into
§3.6 where it is first used as the protocol-blindness example, and renumber this as §5.11 or
§5.12.

---

## 4. Minor points and line edits

1. **Line 164:** "On the easier **unrestricted** protocol" — §3.6 states "These three names are
   used throughout and nothing else is." The canonical name is "the common protocol". Change it.
2. **Line 200:** "about **ten thousand queries** for the cell it was first measured on, and
   **55,000–122,000** for the final one" — 55,271 is a ×0.5 figure and 121,634 a ×0.75 figure
   (`step_curve_pair_30plus.json`), so the range spans two different cut factors. Quote one
   ("61,000–72,000 for a halving") or say the range covers both.
3. **§10.1, lines 1747–1767:** the hours column sums to **118.53**, not the 118.7 claimed at
   lines 5, 132 and 782. `results/leaderboard.jsonl` sums to 118.73 across 24 rows; the table
   has 19 rows and omits two short `small` re-runs (0.03 h and 0.06 h), and lists
   `small_full_6p` at 25.36 h where the leaderboard records 25.46 h. Either reconcile, or add
   a footnote: "plus 0.09 h in two aborted re-runs of `small`; totals from `leaderboard.jsonl`."
4. **§5.13 line 1327** says the final run was "25.4 h of training" while §10.1 says 25.36 and
   the leaderboard says 25.46. Pick one and use it in both places.
5. **§3.3 line 483:** "0.90–1.37" s/step for the 8.0M model, explained as "a range because the
   rate depends on the shard" — but §3.10's per-shard figures are 1.047 / 1.337 / 1.373. The
   0.90 is a within-run epoch minimum (`final-run-plan.md` line 124), not a shard rate. Either
   change the range to 1.05–1.37 or change the explanation.
6. **§5.9 table line 1154** gives consensus `rec@1` 0.7520 for `small_1m`; §5.1 line 815 gives
   0.7526 for the same checkpoint, protocol, k and temperature. `docs/overnight-2026-10-15.md`
   lines 52 and 71 show 0.7520 was the superseded night-3 analysis-script figure and 0.7526 the
   library figure. Use 0.7526 in both, and the gain becomes +22.24 rather than +22.18.
7. **§1.4 table (line 246) and §5.13 exponent table (line 1425)** both end in an unnamed column
   (`| |`) holding the verdict. Give it a header ("vs registration", "verdict").
8. **§10.2 (line 1774)** is a two-column table with an empty header row. Add headers
   ("artefact", "what it holds").
9. **§3.11 lines 770–772:** "**`format` gates `pytest`**,\nso a formatting miss hides every test
   result behind it." The line break mid-clause after a comma reads as a typo. Rewrap.
10. **Over-long lines** breaking the file's ~79-character wrap: 199–200, 342, 871, 1183, 1446,
    1593. Also line 1593 runs two unrelated rules into one paragraph (see §2b).
11. **§5.4 table (line 934):** the 30–34 row is absent although the dump has it
    (96,406 / 60,662), and the `small_1m` "all" row is "—". Add the 30–34 row and say in one
    clause why `small_1m` has no "all" figure.
12. **§5.6 table (line 993)** header column reads "rec@60, all". Per §3.6, "all" means 30+ only.
    The §5.13 tables have the same issue. Consider "rec@60, 30+ (all)".
13. **§5.3's segment table (line 902)** never says which corpus it is on; the reader learns it
    is the 90,682-molecule shard only from the bullet at line 916. Add "100k shard" to the
    caption.
14. **§5.2 line 836** and **§5.5 line 956** quote |r| thresholds without saying what is being
    correlated (log deficit against log k). One clause would help.
15. **§6 (line 1521)** — twelve one-line death certificates with no pointer to where each was
    measured. Adding a section reference to each row (most already exist in §5) would make the
    table usable rather than merely reassuring.
16. **§9 line 1727:** "to five decimal places — 0.7402 × (1 − 0.13162) = 0.642777 against a
    measured 0.642777" — the inputs are quoted to four decimals, and the relation is
    definitional. Say so (see §2b).
17. **Line 1348 vs 1357:** "structure@60" in one table, "struct@60" in the next. Standardise.
18. **Line 1534, §6:** "60+ heavy atoms is answerable from this corpus" is listed as a dead
    *claim*, but the claim that died was "the 60+ band needs a larger sample" (entry 15). As
    written, the row says the project refused a true statement. Rephrase to "60+ heavy atoms is
    answerable from this corpus with a larger sample".
19. **Line 439 and line 446** both end with near-identical clauses ("which is what makes one
    shared evaluation set possible at all" / "which is what makes an evaluation set clean for
    every model possible at all"), seven lines apart. Cut one.
20. **Line 1769:** `base_1m` is the 25.7M config; the name reads as the smallest. A four-word
    aside ("the project's original, largest config") would stop the double-take.

---

## 5. Factual and consistency concerns

**Internal contradictions**

1. **Line 228 vs line 1485** — "roughly fiftyfold" against "traces to nothing". Major point 3.
2. **Lines 157–162** — conventions mixed within a row; the 16-point gap is cross-convention.
   Major point 1.
3. **Line 1296 vs line 1488** — "preimages barely depend on size — 15% across the range" against
   "Preimages per query *rise* with size (1.63 → 2.87)". Both are correct for their own cell;
   the report never says the direction inverted or why.
4. **Line 192 vs lines 839–845** — 0.144–0.396 attributed to eight cells; it is one cell's band
   range. Major point 4.
5. **Line 1261 vs `budget_filled_rate` 0.462** — "the full-k rate is 1.000 in every band".
   Major point 8.
6. **Line 991 vs line 1017** — §5.6's table is captioned "the same 2,321 queries, 1.2087 passes
   throughout", but the 90,682-molecule row's floor check was measured on **571 queries**
   (`results.md` line 398, `docs/overnight-2026-10-20.md` lines 95 and 373). The table as
   printed asserts a common `n` that the first row does not have.
7. **Line 1270** — the 0.75 / 0.78 / 0.86 triple. Major point 5.
8. **Line 176** — non-monotone "rises". Major point 6.
9. **§3.3 line 483 vs §3.10 line 723** — 0.90 vs 1.047 s/step. Minor point 5.
10. **§5.1 line 815 vs §5.9 line 1154** — 0.7526 vs 0.7520. Minor point 6.
11. **§10.1 hours** — 118.53 vs 118.7. Minor point 3.
12. **§5.3 line 909** says "this is the **only** bend the project measured"; `results.md`
    line 117 says "the **first** bend the project has measured". Not a contradiction, but §5.13
    then measures `c` on a second corpus without a bend, so "only" is a stronger claim than the
    evidence. Prefer "the only bend the project has located".
13. **Cross-document naming:** `docs/methodology.md` §2 — listed at line 20 as the authority on
    conventions — calls the protocols "common" and "large-molecule", while the report declares
    three canonical names and says "nothing else is" used. The report is not wrong, but a reader
    who follows the pointer lands on different vocabulary. Worth a half-sentence in §3.6.

**Numbers I tried to trace and could not**

- **"1.46% of distinct atom environments" (line 342).** Not found in any night log, in
  `results.md`, in `methodology.md`, or in `results/`. The companion figures in the same
  paragraph (943,177 / 950,967 / 99.2% / 98.6%) all trace cleanly to
  `docs/overnight-2026-10-16.md` lines 594–611. This one does not, and the sentence around it
  is also the least parseable in §2. Please either source it or cut it.
- **"`c` per band | 1.092 / 1.083 / 0.770 / 0.381" (line 1430).** Not in the report, not in
  `results.md`, not in `step_curve_pair_30plus.json`. Major point 11.
- **"501 tests" (line 764).** `README.md` line 1098 agrees, so this is consistent within the
  repo, but I could not execute `pytest` in this environment (no `click`), so it is unverified
  rather than wrong. The same applies to `scripts/check_md.py`, which I could not run for the
  same reason — though I did verify by hand that every internal `](#...)` anchor in the report
  resolves to a real heading, and that every bare `§n` resolves to a real section (the single
  `§2.8` is correctly attributed to `results.md`).

**Numbers I did trace, and which reproduce exactly** (recorded so the author knows what has
been checked and need not be re-verified): 118.73 h from `leaderboard.jsonl`; the §5.13 band
table (0.7788/0.9756/0.9731/0.003/2.0 and the other three rows) from `miss_anatomy_full_6p.json`;
the §5.13 Poisson table and all four "drawing none" shares from `budget_curve_full_6p.json`;
all six registration-of-record rows and their SEs from `job4_scored.json`; the "9 of 26" count
and the 13-high/4-low split; the §5.13 cliff prices (1 / 9 / 669 … 654 / 6,640 / 1,444,900);
the §5.4 final-run crossover column; `b` = 0.299–0.385 and `c ÷ b` = 2.25–2.90; 0.9582 for
registration (1); 0.8591 for the pooled consensus rec@1; §1.3's 0.79 Tanimoto and 29% near-miss
share (0.7923, 0.2906); 0.9986 vs 0.6890; the twelvefold preimage rise and 96.9% → 52.0%; 0.729
Poisson at 50+; 80.1% three-seed unanimity; +6.49; 0.6258 twice; 2.558% and 16,465; f′ = +22.09,
g′ = +22.28, g′/f′ = 1.322; `fingerprint_id` 465725d9dece; and the §9 item 6 identity
(0.7402 × 0.86838 = 0.642774).

**One judgement call worth stating.** §9 item 1 ("~50 h, one run") is the only place the report
proposes work, and it is honestly priced: 176,436 steps at the measured 1.047 s/step is 51.3 h.
No complaint — just confirming the arithmetic, since the rest of the report is careful about
cost estimates having been wrong three times (line 730).

---

## 6. Suggested cheap additions

All of these are **free** — they re-read dumps already in `results/` — except where noted.

1. **Both conventions in the headline table (free).** Fixing major point 1 is also the single
   best addition available: a four-cell table showing consensus and generation order in *both*
   conventions makes §3.7's four-point gap concrete in the place a reader will remember it,
   instead of being an abstract warning 400 lines later. All four numbers exist
   (0.8591 / 0.9582 / 0.7066 molecule budget; 0.6963 / 0.9496 raw slots).
2. **The registration inventory table (free).** Major point 15. Eight lines from
   `job4_scored.json`, and it closes the only place where §1.4 and §5.13 are not
   self-contained. Include the HIT / MISS HIGH / MISS LOW counts (9 / 13 / 4), which the report
   currently gives only as "9 of 26" and "16 run with size".
3. **A `preimages per hit` column in §5.13's Poisson table (free).** §1.3 already quotes "the
   successful ones draw 3.5 each" (line 224), but the table it points at has no such column.
   `budget_curve_full_6p.json` has `preimages_per_hit` for every band: 1.66 / 1.83 / 2.29 /
   3.54. Adding it makes §5.12's and §5.13's tables the same shape, which is most of what a
   reader needs to see the mechanism change.
4. **A budget-fill row for the final run in the molecule budget (free).** `comparison_k60_full_6p.json`
   gives `budget_filled_rate` 0.462, `unique_valid_per_query` 28.67 and `duplicate_rate` 0.905
   for the final run. One row repairs major points 8 and 9 at once, and it is a genuinely
   interesting number: the project's strongest model is the first that cannot fill a 60-molecule
   budget, which is "better models explore less" (§3.5) carried to its conclusion.
5. **Generation-order struct@1 beside consensus (free).** `comparison_k60_full_6p.json` has
   `structure_accuracy_at_k` 0.6558 against `structure_accuracy_at_k_consensus` 0.8040 on the
   `fp_unseen` slice. §5.9 shows the consensus gain only on recovery; showing it on structure
   accuracy too would satisfy §3.9's own rule 3, which §5.9 currently does not follow.
6. **The 30–34 row in §5.4's crossover table (free).** It is in the dump (96,406 / 60,662) and
   its absence makes the table look like it starts at 35–39 for a reason.
7. **A corpus funnel, three or four rows (free).** The report never states how large ChEMBL 35
   is before standardisation, so §8's "2.558% … about 63,000 molecules" and §3.1's shard sizes
   float free of each other. Raw compounds → surviving standardisation → the four shards would
   take four lines and answer a question every reader will have at §3.1.
8. **One validity-by-band number for 50–64 (free).** §5.10 line 1183 currently sends the reader
   to night 6 for the claim that 50–64 is "the corpus's worst-validity band". The number is in
   the night-6 dumps; quoting it keeps the document self-contained.
9. **A `b` comparison table across the two cells (free).** §5.2 gives `b` per band for
   `small_1m`; `budget_curve_full_6p.json` gives it for the final run (0.369 / 0.385 / 0.320 /
   0.299). §5.13 asserts "the *band structure* of `b` flattened with scale" in prose (line 1443)
   and the four-by-two table would show it in one glance — it is one of the report's better
   findings and currently the hardest to see.

I have nothing to propose that needs compute. Everything the report would be strengthened by is
already on disk, which is itself a compliment to how the runs were instrumented.

---

## 7. Verdict

**Major revision.**

The report is close to publishable and in places exemplary — the methods section, the
retraction ledger's integration into the argument, and §5.13's handling of its own registration
failures are better than most of what gets published on work of this scale. But it carries three
blocker-class defects in its summary, which is the part of an 1,800-line document that most
readers will actually read: the headline table mixes the two recovery conventions inside a single
row and derives a 16-point ranking claim across them, in a document whose §3.7 exists to forbid
precisely that and whose §7.2 counts five prior instances; the "~50×" figure that §5.13
explicitly retracts as tracing to nothing is still asserted as fact in §1.3; and "Tanimoto", on
which the central negative result about near-misses turns, is never defined anywhere. Around
those sit a handful of late-draft factual slips — a Tanimoto triple that does not match its own
dump, a `b` range attributed to the wrong population, an `n` of 41 behind the most-quoted cliff
number, a "full-k rate is 1.000" that is false in the adopted convention, and a table captioned
with an `n` its first row does not have. None of this requires new compute, and most of it
requires only re-reading JSON the project already saved; but the corrections change printed
numbers and retract one summary claim, which is more than a minor revision. Fix the three
blockers, work through the comprehensibility log, and I would expect to accept the next version
without further rounds.
