# Round 3 — adjudication of `docs/report.md`

Round-1 reviewer returning. I wrote the 16 numbered points of round 1 (4
`blocker`, 10 `major`, 3 `minor`) plus 28 line edits, 17 consistency items and
~70 comprehensibility entries. I have now read, for the first time,
`docs/reviews/round-2-review.md` (3 `blocker`, 12 `major`, 2 `minor`, 20 line
edits and a four-part comprehensibility log), both author responses, the
register, and the current 1,858-line report.

Everything below was checked against the dumps rather than against the
responses. Where I say "verified", I recomputed or re-read the JSON.

---

## 1. Adjudication table

Verdicts: **resolved** / **rejection justified** / **still stands**.
Rows I spot-checked beyond the register's `fixed` claim are marked ✓-checked.

### Round 1

| id | sev | verdict | note |
|---|---|---|---|
| R1-01 | blocker | **resolved** ✓-checked | §5.1 now keeps 0.976 but labels it "over *all* queries… dominated by the exact hits, which score 1.0, and it says nothing about the failures", and points to §5.12. §1.3 gives 0.79 and the 29% above 0.9. This is better than my suggested fix: it leaves the wrong statistic visible and explains why it is wrong. |
| R1-02 | blocker | **resolved** ✓-checked | Ranking is now named on every `rec@1` I could find, and the glossary makes it a standing rule. Verified 0.7066 (`comparison_k60_full_6p.json`, `fp_unseen`) and 0.8591 (`band_k1_full_6p.json`). One residual, see new point 6. |
| R1-03 | blocker | **resolved** ✓-checked | §5.13's six-band Poisson table reproduces `budget_curve_full_6p.json` exactly (1.63/1.77/2.10/2.87/1.81; 0.9823/0.9664/0.9184/0.8110/0.9582; 0.8036/0.8291/0.8775/0.9435/0.8364; 1.8/3.4/8.2/18.9/4.2%). The claim is now the stronger, correct one: concentration switches on with size. The same sentence was corrected in `overnight-2026-10-30.md`. |
| R1-04 | blocker | **resolved** ✓-checked | §5.5 is scoped to "the four cells available when this was measured", and the ninth-cell break is stated with `A` = 0.70 and 0.3150/0.5984. I recomputed `A` at 50+ from the final run's exponent and `rec@60`: 0.696. |
| R1-05 | major | **resolved** | Now "+22.09 − 23.55 = **−1.46** … while the measured net on that segment was **+1.37**. Both sit inside the project's own 1.6-point threshold". Exactly right, and sharper than the original. |
| R1-06 | major | **resolved** | §5.8's first table is captioned "Read on `rec@60`, 30+ protocol, 2,321 queries, bootstrap CIs"; the second "`rec@20` on the common protocol, 1,956 queries". Both match `overnight-2026-10-17.md` L930/L961. |
| R1-07 | major | **resolved** ✓-checked | §5.4's final-run column reproduces `step_curve_pair_30plus.json`'s `break_even` exactly (96,406/60,662 … 100,226/61,210), and the text now says the crossover is a property of the model. One residual, new point 10. |
| R1-08 | major | **resolved** | §5.11a is substantive, not a stub: the trade at both temperatures, the exposure-already-spent dose, and the slope-not-a-law result with the band-level predictions failing. |
| R1-09 | major | **resolved at source** ✓-checked | `retractions.md` entry 26 now reads "(item 1, night 7; and again, item 2, night 8)" and spells out both incidents, ending "cite it by night". §7.4 and §3.9 rule 4 do. This is the better of the two fixes I offered. |
| R1-10 | major | **resolved** | §5.13 now quotes no ratio, gives the two comparison points (93,923 and 1.0 × 10⁷), explains why the quotient is unstable, and says the defensible statement is 0.2251 → 0.7402. |
| R1-11 | major | **resolved, and it produced a real result** ✓-checked | All six sub-band rows and every SE in §5.13 reproduce `job4_scored.json`; the verdict split is exactly 9 HIT / 13 MISS HIGH / 4 MISS LOW over 26 rows; `b50_subbands_{recovery,structure}.json` confirm `"budget": "molecules"`, `"order": "generation"`, `k=60`, matching the caption. The monotone +0.40 / +8.53 / +20.13 and +2.14 / +6.53 / +22.71 gradient is now the best evidence in the section, and the disclosure box is the right way to publish it. Ledger entry 29 exists and is well written. **But §1.4's restatement of the same fact is wrong — see new point 1.** |
| R1-12 | major | **resolved, improved** | §9 item 6 now says the relation is "by construction", which is what round 2 asked for, and keeps the slot visible. |
| R1-13 | major | **resolved** | The glossary writes the law as a display line, names `f` and `g`, says `f′`/`g′` are their slopes and `g′/f′` the exchange rate, and names additivity as the assumption §5.13 breaks. This was the cheapest high-value fix available and it landed. |
| R1-14 | minor | **resolved** ✓-checked | §4's column is "session" with a note; §10.1 reconciles to the ledger's 118.73 h over 24 rows with the two aborted `small` re-runs (0.09 h) footnoted. The 19 listed rows sum to 118.63; +0.09 = 118.72 ≈ 118.73. Consistent. |
| R1-15 | minor | **resolved** ✓-checked | `c ÷ b` row added: target 2.54–3.39, measured 2.25–2.90, all-slice 2.75. Matches the `break_even` ratios in `step_curve_pair_30plus.json`. |
| R1-16 | minor | **resolved** | Carried across *and* improved: "Extra guesses now help large molecules roughly twice as much as they did — the same flattening that made the size extrapolations too steep." |
| R1-C | consistency | **still stands, in part** | Most of the 17 are genuinely fixed (the `\|r\|`/cells/range composite, eight-vs-nine cells, the 98.6% inference, the invented sixth cause, Phase 1 hours, the date range, "two of them", the §2.1 self-reference, the shard table). Five are not: (a) §5.6's table is still captioned "the same 2,321 queries" with a first row whose floor check is then said to be "on 571 queries" — round 2 flagged this independently as its consistency item 6 and no register row exists for it; (b) "Four successive claims died on it (**entries 1–5**)" — five entries for four claims; (c) §5.8's "+3.70 points [+2.13, +5.26]" still names no convention, in a report whose own rule is that every number does (`results.md` §2.5: raw slots, +4.48 in the molecule budget); (d) "the cut declines from 25.4% at 30–34 to 3.9% at 50+" is still unsourced inside the report; (e) §5.12's "0.953 with no stereocentres to 0.355 with five or more" still sits unexplained in a document whose §3.1 strips stereochemistry. |
| R1-N | naming | **still stands, barely** | The sweep worked — §3.6 now declares three names and notes the aliases, and 12 lines use "the 30+ protocol". Two survivors: L1018 "Large / protocol, k=60, T=0.6" (line-wrapped, which is why a grep missed it) and L1151–1152 "the dedicated 893-query instrument". §3.6 promises "nothing else is", so these two should go. |
| R1-A7 | addition | **rejection justified** | The stated reason — `plot_size_cliff.py` predates the final run, so the figure would show an eight-cell world inside a section the final run rewrote — is correct and I accept it. I would now close the row rather than defer it again: the report is 1,858 lines with no figure at all, and the honest options are a regenerated figure or a decision not to have one. Either is fine; a third deferral is not. |
| R1-A8 | addition | **still stands** | §5.10 still hands the reader off: "the corpus's worst-validity band (measured in [night 6]; **this report carries no validity-by-band table**)". The section's central claim is a validity/diversity cancellation, so one band-level number belongs in it. Free: `"valid"` is a per-candidate field in the `results/overnight9/outcomes_*` dumps. |

### Round 2

| id | sev | verdict | note |
|---|---|---|---|
| R2-01 | blocker | **resolved** ✓-checked | The convention is now a column, three rows, and the gain is read within one convention. I verified every cell: molecule budget 0.7066 / 0.8591 at `rec@1` and 0.9582 at `rec@60`; raw slots 0.6963 / 0.9496. The ranking gain is 0.8591 − 0.7066 = **15.25 points**, printed as +15.3. The glossary's propagated "16 points" is gone. The second reviewer was right and the fix is correct. Two small residuals follow as new points 4 and 6. |
| R2-02 | blocker | **resolved** | The glossary row is well judged — it defines the scale *and* says Tanimoto is never the correctness criterion, which sets up §2.3 and §5.12 both. |
| R2-03 | blocker | **resolved** ✓-checked | §1.3 now ends "The final run moved `rec@60` at 50–64 from 0.2251 to 0.7402 and left the cliff's shape intact." I grepped for other surviving ratios of two extrapolations and found none. |
| R2-04 | major | **resolved** | Both halves: §1.3 reads "across the size bands of the cell it was first fitted on"; §5.5 reads "**read at 35+ heavy atoms**". |
| R2-05 | major | **resolved** ✓-checked | All four bands given (0.75 / 0.80 / 0.78 / 0.86), matching `miss_anatomy_full_6p.json` (0.7494 / 0.7976 / 0.7782 / 0.8550), with "not monotone in between" said plainly. |
| R2-06 | major | **resolved** | "17% at 30–34 against **58% at 50–64**, with the two middle bands at 24% and 22%, so it rises overall but not monotonically". |
| R2-07 | major | **STILL STANDS (half)** | Fixed in §1.3 (L226–230: cell, protocol, both `n`, and the band correctly relabelled 50–69). **Not fixed in §5.12**, which is the line round 2 cited: L1284 still reads "Recovery falls from 0.981 below 15 heavy atoms to **0.366 at 50–64**", with no `n`, no cell and no protocol. Worse, the half-fix has created a new internal inconsistency: the same number is 50–69 in §1.3 and 50–64 in §5.12, 1,050 lines apart. Fix: copy §1.3's clause into §5.12's opening sentence. |
| R2-08 | major | **resolved, and well** ✓-checked | The bullet now gives both conventions, each labelled, with 46%, 28.7 and the 90% duplicate rate (verified: `budget_filled_rate` 0.4623, `unique_valid_per_query` 28.674, `duplicate_rate` 0.9047), and draws the better conclusion — "not short of slots; it is short of *distinct ideas*". This is the best single fix of the round. |
| R2-09 | major | **STILL STANDS (half)** | §1.3 is fixed exactly as asked (the k=20 cells named, 28.7 given for the final run). But §5.12 L1313 still asserts it generally: "At every size the decoder fills **its twenty slots** with molecules roughly 0.65 Tanimoto from the target". That is the same k=20-era figure presented as a property of the decoder, in the section that owns the mechanism. Fix: "fills its twenty slots (in the k=20 cells this was measured on; 28.7 distinct valid molecules at k=60 in the final run)". |
| R2-10 | major | **resolved for §5.13; STILL STANDS for §1.4** ✓-checked | §5.13's registration tables now say "Molecule budget, generation order, k=60" and carry the explicit note that they are not comparable with the raw-slot before/after table. Verified against `b50_subbands_*.json`. But §1.4's table — which reproduces three of those rows alongside two from registration (3) — has columns `band / metric / predicted / measured / vs registration` and **still no convention**, which is precisely the half round 2 named ("§1.4's table has no convention column at all"). It is all molecule budget, so one word in the caption closes it. |
| R2-11 | major | **STILL STANDS — now mis-sourced** | The row now reads "the 100k capacity × steps 2×2 of §5.8, read at k=60". That source is wrong on two counts. The targets are `results/overnight6/step_curve_100k.json`, whose `pair` block gives k=60 values of **1.0916 / 1.0831 / 0.7698 / 0.3809** — an exact match — and that is the **100k shard's step pair** (8,508 → 21,117), the pair §5.3 refers to as "the 100k pair". §5.8's 2×2 is a *capacity* × steps design on the **1M** shard (its 8.0M row is 0.5205 → 0.8427, which §5.6's table shows is 900,917 molecules). So the citation points at the wrong shard and the wrong design, and since the 2.11× conclusion rests entirely on this column, a reader who follows the pointer to §5.8 cannot reconcile it. Fix: "the 100k shard's 8,508 → 21,117 step pair of §5.3, read at k=60 (`results/overnight6/step_curve_100k.json`)" — and add the clause round 2 actually asked for, that §5.3's own table is the **1M** pair read at **k=20**, which is why its numbers (1.294 / 1.240 / 0.893 / 0.366) differ. Verified: `step_curve_1m.json` k20 reproduces §5.3's table exactly. |
| R2-12 | major | **resolved** | "+22 points … on the cell where it was measured (§5.9) and **+15.3** on the final run (§5.13)", with the standing rule attached. |
| R2-13 | major | **resolved (part a); rejection JUSTIFIED IN PART (part b)** | Part a is well done: the four-row Statistics block defines discordant pair, paired/McNemar SE, between-seed sd and difference-in-differences, and it is placed where §1 can use it. On part b, see §1a below — I accept the refusal to move §4 and do not accept the refusal to date the first mention. |
| R2-14 | major | **resolved** | "Cited throughout as **entry N**, meaning row N of that table", in the authority table where the reader meets `retractions.md`. |
| R2-15 | major | **resolved** ✓-checked | The inventory table at the head of §5.13 is the single most useful addition of this round: each registration, its interval count, and how it was scored, summing 1 + 8 + 14 + 4 with "**26 scorable intervals: 9 HIT, 13 MISS HIGH, 4 MISS LOW**". All of it reproduces `job4_scored.json`. §1.4's "five registrations … the remaining three unfold into 26" now agrees. |
| R2-16 | minor | **resolved** | "though at three times the training and sampling cost, unlike the temperature vote below". |
| R2-17 | minor | **rejection justified** | The substance was accepted (the self-diagnosing opening is gone, and §5.11a now opens by saying what the intervention *is*). On the renumber: I checked the cost claim and it is credible — `§5.12`/`§5.13` and their anchors occur on 27 lines of `report.md` and `README.md` and ~167 times across `docs/`, and two of those anchors are the report's most-linked. Declining a cosmetic renumber at that risk is the right call, and the "a" suffix costs a reader nothing now that the section no longer announces itself as bolted on. One residual worth four words: §3.6 uses the mix as its worked example 650 lines before §5.11a describes it, and §5.11a back-references §3.6 but §3.6 does not forward-reference §5.11a. Add "(described in §5.11a)". |
| R2-L | line edits | **resolved, in part** ✓-checked | I spot-checked eight: L3 (118.73/24 rows/0.09 h footnote) ✓; L4 (25.46 h in both §5.13 and §10.1) ✓; L6 (0.7526 in §5.1 and §5.9, gain now +22.24) ✓; L7 ("vs registration" and "verdict" headers added) ✓; L8 (§10.2 headers) ✓; L11 (30–34 row added to §5.4, with a clause explaining the `small_1m` gaps) ✓; L15 (section reference on every §6 row) ✓; L18 (60+ row rephrased) ✓; L20 (`base_1m` labelled "the project's original and largest config") ✓. **Not done:** L10's over-long lines — L216–217 of §1.3 is ~97 characters, and §7.4 still runs "Nothing flagged it, because every interval that *was* computed scored cleanly. And register the **slope, not the level**…" into one over-long paragraph, which is the exact run-together L10 and §2b both flagged. And see new point 10 for a place §5.4 reintroduces the mixed cut-factor range that L2 fixed in §1.3. |
| R2-X | factual | **resolved** | The unsourceable 1.46% is gone from `report.md` and `README.md`. The replacement sentence is circular, though — new point 8. |
| R2-A | addition | **STILL STANDS, and it is no longer only an addition** | §1.3 now says "the successful ones draw **3.5 each**" and points at §5.13. §5.13's Poisson table has no per-hit column, and the only "per hit" column in the document is §5.12's, which gives **2.72** at 50+ for a different cell. So a reader who checks §1.3's 3.5 finds 2.72 and concludes one is wrong. `budget_curve_full_6p.json` has `preimages_per_hit` 1.66 / 1.83 / 2.29 / 3.54 for the four bands; adding the column is free and now repairs a checkability gap rather than merely strengthening a table. |
| *(no row)* | — | **STILL STANDS** | **Round 2's comprehensibility log has no register row at all.** See new point 3. |

### 1a. The two declined points, judged

**R2-13b — moving §4 ahead of §3, or dating every "night N".** The reviewer
offered two fixes and the author declined both as one. I would split them.

*Declining the move is justified.* §4 is a programme narrative and it reads as
one; it depends on vocabulary §3 establishes (protocol, convention, `fp_unseen`,
the 1.6-point threshold), so putting it first would make §4 the section that
forward-references everything instead of §3. The author's instinct that "§4 sits
where a reader expects the programme narrative" is right.

*Declining the dating does not hold up.* The stated reason is that "the sessions
are numbered in date order so 'night 7' before §4 costs a reader little", and
that is reasoning from the author's knowledge, not the reader's: at L541, where
"night 8's best was step 52,000 of 52,500" appears, a first-time reader does not
yet know that there are nine sessions, that they are numbered in date order, or
that §4 tabulates them. There are nine such references before §4. But the
reviewer's own fix — dating *every* mention — is heavier than the problem, and I
would not ask for it. **One forward pointer at the first occurrence closes it**:
at L541, "night 8 (10-24/25; the sessions are tabulated in §4)". That is one
clause, zero restructuring risk, and it converts eight later bare references
from dangling to resolvable. I record R2-13b as **rejection justified in part**:
the move is correctly refused, the dating still stands at this reduced cost.

**R2-17 — renumbering §5.11a.** **Rejection justified**, as above. The cost
claim is verifiable and the benefit is cosmetic. I would not raise it again.

---

## 2. Are the revisions substantive, and is the convention error fixed?

**Substantive, with one systematic exception.** Of the 33 numbered points across
the two rounds I judge 24 fully resolved, 7 resolved in part or still standing,
and 2 correctly rejected. The resolutions are not wording changes: §5.13 gained
a registration inventory and six scored intervals that did not exist before,
§5.12's budget bullet gained the molecule-budget fill rate and a better
conclusion than either reviewer proposed, the glossary gained the scaling law it
had been assuming, and `retractions.md` gained two entries (26 broadened, 29
new). Three of the fixes improved on the suggestion rather than implementing it —
R1-01 (leaving the wrong statistic visible and explaining it), R1-09 (fixing the
ledger rather than routing around it) and R1-12 (naming the identity as
definitional). That is the signature of someone verifying rather than complying.

The exception is round 2's comprehensibility log, which was its own "most
important section" and which the register does not track at all. See new
point 3.

**The convention error.** I take this seriously because the author's own account
is that they committed it in the commit that documented it as having happened
five times. It is genuinely fixed where round 2 found it:

- §1.3's table carries `convention` as a column, not caption prose, with three
  rows; the ranking gain is computed within one convention and is 15.25 points,
  printed as +15.3. Verified against `comparison_k60_full_6p.json` and
  `band_k1_full_6p.json`.
- §5.13's registration tables are labelled "Molecule budget", the before/after
  table "raw-slot convention throughout", and the inventory adds an explicit
  note that the two are in different conventions by design and are not
  comparable. Verified against `b50_subbands_*.json`.
- §5.12's budget bullet now names both conventions in the same bullet and keeps
  them apart.

**I looked for further instances and found no sixth subtraction.** Specifically,
I checked the one place a cross-convention ratio could hide unnoticed: `g′ / f′`
= 1.322 at 50+. `score_stage6.py` reads `g′` from `miss_anatomy_50plus_*`
(raw slots) and hard-codes `F_PRIME_50 = 16.86`; I traced 16.86 to the 893-query
table whose endpoints are 0.0459 → 0.2251, and confirmed from
`results/overnight7b/miss_anatomy_50plus_full_1p2.json` that 0.22508 is the
raw-slot figure. Both legs are raw slots, so the ratio is within one convention.
Good.

Two weaker relatives survive, neither a subtraction:

- §5.8's "+3.70 points [+2.13, +5.26]" names no convention (R1-C(c)).
- §1.4's table names no convention (R2-10, half).

And one *new* numeric slip sits inside the sentence whose job is to warn about
the convention gap — §1.3 says the two conventions differ "by about a point at
`rec@1` and **four-tenths** at `rec@60`", when the table's own cells give 1.03
and **0.86** points. See new point 4. It is not the same error, but it is in the
same sentence, which is worth one more pass with a calculator.

---

## 3. Cold read of §1 and §5.13

**§1 now stands alone, and that is the headline of this round.** Reading it as
if for the first time: §1.1 motivates the task in three paragraphs; §1.2 gives
the oracle, `recovery@k` and the two things that make the numbers trustworthy;
§1.3 opens with a three-row table whose every cell is labelled by ranking and
convention, and then walks through the two power laws, the crossover, the cliff
and concentration with every number attached to a named cell and a sample size.
The glossary carries the eleven things §1 assumes, including — now — Tanimoto,
the scaling law, and four statistical terms. I can follow the argument end to
end without leaving the document, which was not true in round 1 and, judging by
round 2's log, not fully true after round 1 either.

Three things in §1 I would still change, all small. The near-miss paragraph
(L188–195) is the one place §1.3 asks the reader to hold two opposed ideas —
"the failures are *near*-failures but not near enough" — and it does it in four
sentences with five numbers; it is correct and it is the densest thing in §1.
L216–217 is an over-long line that breaks mid-clause. And §1.4's miss count is
wrong (new point 1), which matters more than its size because §1.4 is the
section whose whole subject is counting misses honestly.

**§5.13 is now the strongest section in the report.** The order is right:
before/after, then the warning that the pooled figure is not about large
molecules, then per band, then the two independent reads of 50–64 reconciled
within one convention, then the registration inventory, then the scored misses
with their gradient, then the disclosure box, then the exponents, then the
cliff's price, then the Poisson table, then the collision floor. A reader who
starts at §5.13 and has the glossary can follow all of it. The disclosure box is
the best paragraph in the document: it states that six intervals the plan called
"the registration of record" went unscored, says why ("the default arguments of
the tool that scores it are part of the registration"), gives the six rows, and
notes that they turned out to be the sharpest evidence in the section. Very few
reports would print that.

What §5.13 still needs: the `c` per-band source corrected (new point 2), a
per-hit column so §1.3's 3.5 can be checked (R2-A), and §1.4 brought into line
with it on the miss count.

---

## 4. New points

**1. §1.4 L285–287 miscounts the misses, and contradicts §5.13.** `major`
§1.4: "Of the **eleven** misses outside the 50–64 instrument, **ten** run with
size in exactly this way. The one exception is the pooled 35+ `rec@1`."
§5.13 L1433 has it right: "Of the **17** misses, **16** run with size … the
single exception is the pooled 35+ `rec@1`." From `job4_scored.json`:
registration (2) — the 50+ instrument — is 8 intervals, all MISS HIGH, so the
misses outside it are 17 − 8 = **nine**, of which **eight** run with size. I
enumerated them: (3) `rec@1` 40–49 +3.97, 50+ +15.83, 35+ +0.53; (3) `struct@1`
30–34 −1.37, 40–49 +2.13, 50+ +9.93, 30–39 −1.00; (4) 35+ `rec@60` −0.39, 35+
`struct@60` −0.48. Eight run with size, one exception. The round-1 revision had
this right as "16 of 17"; the round-2 revision restated it for §1.4 and broke
it. *Fix:* "Of the nine misses outside the 50–64 instrument, eight run with size
in exactly this way" — or simply use §5.13's "17 misses, 16 run with size" in
both places so the two sections cannot drift again.

**2. §5.13's `c` per-band targets are now sourced, but to the wrong cell.**
`major` (R2-11, re-raised)
Detail and fix in the table above. The targets are the 100k shard's *step* pair
at k=60 (`results/overnight6/step_curve_100k.json`), not "the 100k capacity ×
steps 2×2 of §5.8", whose 2×2 is on the 1M shard. Because the 2.11× conclusion
rests on this column, a wrong pointer is worse than none: a reader who checks
§5.8 finds numbers that cannot produce 1.092 / 1.083 / 0.770 / 0.381.

**3. Round 2's comprehensibility log is untracked and largely unaddressed.**
`major`
Round 2 called §2 "the most important section" and the brief both reviewers were
given made comprehensibility the priority. Its §2a listed ~27 terms used before
definition or never defined; three were promoted to numbered points (Tanimoto,
"entry N", the five registrations) and fixed. I checked the rest and **17 are
untouched**: `top_p` (in a section heading), "teacher-forced", "OPSIN round-trip
accuracy", "MPS", `RUNS`, "rungs", "prefix-to-prefix", "the closed 2×2",
"truncation" (as a quantity, in §6), `beats original`, "the remaining 10.5%",
`max_steps`, `--exclude`, `FPConfig`, "exposure", `generate_outcomes`, and "arm".
§2b's unparseable sentences are also still there: "`caffeinate -dimsu -w <pid>`
holds the machine awake rather than merely measuring the loss correctly", "Both
mechanisms registered for one stage were eliminated…", "it was originally
written here as a universal", "a reader would never have seen them", and "A
registration is not scored because it was written down" (which still wants
"merely"). None of this appears in `open-points.md`, so by the register's own
standard — "the check that nothing raised in one round is quietly lost" — it has
been lost.
*Fix:* add one register row per cluster (§2a terms, §2b passages, §2c hand-offs,
§2d unparseable sentences) with a status, then work the glossary additions. Most
are four-word parentheticals; `top_p` is a section heading, so that one is
conspicuous.

**4. §1.3 L176 — "four-tenths at `rec@60`" is 0.86 points.** `minor`
From the table's own cells: 0.9582 − 0.9496 = 0.86, and 0.7066 − 0.6963 = 1.03.
"About a point" is right; "four-tenths" is not. *Fix:* "about a point at `rec@1`
and nine-tenths at `rec@60`".

**5. §1.3 and §5.12 disagree on the band label for 0.366.** `minor`
L227 says "36.6% at 50–69" (correct, per `overnight-2026-10-14.md` L122); L1284
says "0.366 at 50–64". Consequence of R2-07 being fixed in one place only.

**6. §1.3's consensus `rec@60` of 95.8% is asserted rather than measured.**
`minor`
Both the consensus and generation-order molecule-budget rows read 95.8%, on the
stated reasoning that "Ranking cannot move `rec@60` here, because the budget is
the whole candidate list". 0.9582 is `band_k60_full_6p.json`, whose `order` is
`generation`. The reasoning holds for the 54% of queries whose candidate list is
shorter than 60, but `budget_filled_rate` is 0.4623 — 46% of queries do reach
the 60-slot cap, and §3.5 records `mean_candidates_per_query` of 423.6, so for
those queries ranking could in principle change which 60 are scored. *Fix:*
either measure it (free — `band_analysis.py` at k=60 with consensus order over
the existing dump, exactly as `band_k1_full_6p.json` was produced), or soften to
"identical for the 54% of queries with fewer than 60 distinct candidates; the
rest unmeasured".

**7. §3.7's "about four points at `k=60`" names no cell, and §1.3 now shows
0.86.** `minor`
The four-point figure is the report's standing rule of thumb and the reader's
first encounter with the convention gap; §1.3's table then shows the final run's
gap is under a point, and §5.13 repeats "about four points at k=60". Nothing
reconciles them. *Fix:* name the cell the four points came from
(`methodology.md` §1 gives `variance_s1` at 35+, k=20: 0.1885 vs 0.1634) and add
that the magnitude is cell-dependent while the hazard is not — which is in fact
the stronger version of the rule.

**8. §2.1's replacement for the deleted 1.46% is circular.** `minor`
"Folding to 2,048 bits does collide distinct atom environments, but rarely
enough to matter at this scale: the measured consequence is that 950,967
molecules produce 943,177 distinct fingerprints." Those two totals are the first
sentence of the same paragraph, so the sentence offers as evidence the thing it
just stated. *Fix:* cut the second clause, or give the collision statistic that
round 2 could not find and the author could not source — in which case say it is
not measured.

**9. §1.4's table has no convention column.** `minor` (R2-10, half)
As above. All six rows are molecule budget; one word in the caption.

**10. §5.4's summary sentence reintroduces the mixed cut-factor range that
R2-L2 fixed in §1.3.** `minor`
§1.3 now says "about 60,000 … both for a halving" ✓. §5.4 says "It moved up
roughly sixfold between these two cells, from ~10,000 queries to
~55,000–120,000" — 55,271 is a ×0.5 figure and 121,634 a ×0.75 figure, which is
exactly R2-L2's complaint. *Fix:* "from ~10,000 to ~60,000 for a halving" and
let the table carry both cut factors.

**11. Two protocol aliases survived the sweep.** `minor` (R1-N)
L1018 "Large / protocol" and L1151–1152 "the dedicated 893-query instrument",
against §3.6's "These three names are used throughout and nothing else is."

---

## 5. Verdict

**Minor revision.**

The report has changed category. Round 1's four blockers were statements in the
Summary that the project's own final run had falsified and nobody had retired;
round 2's three were defects the first revision introduced, two of them in the
Summary as well. All seven are gone, and I verified each against the dumps
rather than against the responses. What replaced them is better than what I
asked for in three cases, and the single most valuable change in either round —
scoring the six "registration of record" intervals that the scoring tool's
default arguments had silently dropped — was a real result that came out of the
review process and is now published with a disclosure box and a ledger entry. §1
and §5.13 both stand alone now, which was the brief. The convention error is
fixed where it was found, the convention is a table column rather than caption
prose, and I could not find a sixth instance of the subtraction.

What remains is eight register rows that still stand plus eleven new points, and
every one of them is a one-line, one-caption or one-column fix requiring no
compute: a miscount in §1.4 that §5.13 already states correctly, a citation in
§5.13 pointing at the wrong shard, a glossary pass over the seventeen terms
round 2 listed and the register never recorded, and seven small labelling and
arithmetic slips. Three of those I have tagged `major`, which is why this is not
an accept — the §1.4 miscount and the §5.13 mis-citation both sit on central
claims, and an untracked comprehensibility log is the one place this otherwise
exemplary review process has leaked. But none of them threatens a finding, and
the pattern across both rounds is that this author verifies before responding
and fixes at the source. I would expect to accept the next version.

One observation to close on, since the reviews are in the repository and
therefore part of the record. The register's own note — "Round 2 found more
`major` points than round 1, not fewer… The count going up is the measurement
working" — is the right reading, and this round continues it: three of my eleven
new points are defects the round-2 revision introduced (the miss count, the
mis-citation, "four-tenths"), in exactly the pattern round 2 identified in round
1's revision. That is not a criticism of the process; it is the process telling
you that the thing to add before the next revision is not another reviewer but a
numeric proofread of every figure that changed, against the dump it came from.
`check_md.py` already guards the references. Nothing yet guards the arithmetic.
