# Round 1 review — `docs/report.md`

Reviewer brief: proofread end to end as a first-time reader with no prior
knowledge of the project. Priority is comprehensibility. Read the whole
document before writing. Claims spot-checked against `docs/results.md`,
`docs/retractions.md`, `docs/methodology.md`, `docs/final-run-plan.md`,
the night logs, `configs/small_full_6p.yaml` and the JSON dumps under
`results/overnight9/`.

---

## 1. Assessment

This is an unusually good report, and most of what is good about it is
structural rather than stylistic. The decision to lead with a glossary, to put
one domain statement at the top ("3 to 64 heavy atoms, everywhere"), to state
in §3.6 that the three protocols are *not* comparable before any number is
quoted, and to carry a measurement convention on every figure, means a
newcomer is given the apparatus before the results. §3 (Methods) is the
strongest part: the oracle, the two metrics, the `fp_unseen` slice with its
exactly-zero baseline, the error-bar section, and the pre-registration rules
are each motivated by a specific failure rather than asserted. §7 is genuinely
transferable and I would recommend it on its own. The report is also honest in
places where it costs it something — §1.4 opens on a failed prediction, §8
leads with "no number here has ever been measured on an untouched test split",
and §5.6 is frank that four claims died on one identity. The numbers I traced
to `results/overnight9/*.json` matched to four decimal places far more often
than not: the §5.13 band table, the budget-price table, the stage-6 exponents,
the 9-of-20 registration score and the 18.9% "none" share are all exactly
reproducible from the dumps.

What most needs work is a specific, recurring thing: **the report's §1 and
§5.1–§5.12 were largely written before the final run, and §5.13 was bolted on
at the end without going back to retire the statements it falsifies.** Four
claims elsewhere in the document are now contradicted by the report's own last
section, and two of them are stated as universals in Findings (see blockers
1–4). The most serious is the near-miss claim: §1.3 and §5.1 tell the reader
"even the misses are near misses" off a mean best Tanimoto of 0.976, while
§5.12 has a bullet headed **"Not near-misses"** quoting 0.69/0.64/0.57, and the
saved dump for the final run gives 0.792 among misses. A careful reader hits
that contradiction and starts doubting everything. The second recurring problem
is that the headline `rec@1` of 69.6% is in generation order while the
project's own adopted ranking is consensus, which gives 0.8591 on the same
queries — a 16-point difference the report never mentions, in a document that
elsewhere advertises consensus ranking as free and worth +22 points.

Would a newcomer come away understanding what was done and what was found?
Yes, substantially — on the shape of the result (a size cliff that is
combinatorial rather than informational; two power laws priced against each
other; a methodology whose failures were all cross-run comparisons). But they
would come away with three or four specific wrong beliefs, and they would have
to stop and re-read perhaps twenty passages. Several of those are fixable by
defining notation that is currently used and never introduced — `f` and `g`
(the primes are derivatives of functions the report never writes down), "the
additive law", "the size defect", and the distinction between the report's
three interchangeable names for the same 893-query instrument. Nothing here
requires new compute; almost everything requires either a sentence of
definition or a cross-check against `results/overnight9/`.

---

## 2. Comprehensibility log

Ordered by line number. "†" marks the ones I think cost the most.

**Front matter and glossary**

- **L27** † — "Every number here carries the convention it was measured in,
  because two of them differ by about four points and conflating them has
  voided two pre-registrations." *"Two of them"* has no antecedent: the
  sentence introduced "the convention", singular. I had to reach §3.7 to learn
  that there are exactly two conventions. Fix: "…because the two conventions in
  use differ by about four points".
- **L62** — "**deficit** | `1 − rec@k`". The glossary writes the deficit against
  `rec@k`; §1.3 and §5.2 write it as `1 − rec(k)`. Two notations for one
  quantity, in the two places a reader meets it.
- **L67** — "**consensus ranking** | … worth +22 points of `rec@1`." The
  glossary presents consensus as adopted, which made me read every later
  `rec@1` as a consensus number. It is not: the §5.13 headline `rec@1` is in
  generation order. See major point 2.
- **L76** — "`steps × batch = corpus × passes` is an **identity**, so the steps
  axis *is* the passes axis — which is why 'what is data worth at fixed
  compute' is not a well-posed question". This is the conceptual pivot of the
  whole corpus story and it arrives compressed into a glossary cell. I had to
  re-read it three times and then re-read §5.6 to believe it.
- **L83–88** † — the four-exponent table is the first place `f′` and `g′`
  appear, and the primes are never explained. `results.md` §2.9 has the missing
  definition — `value = f(log distinct molecules) + g(log passes)`, so `f′` and
  `g′` are its derivatives — and the report never states it. Without it, "the
  additive law" (L224, L1283, L1487) and "additive separability" (L917, L961)
  are unparseable. **This is the single cheapest high-value fix in the
  document.** Add one display line in the glossary or at the head of §5.6.
- **L90** — "`b` and `c` are exponents in a power law; `f′` and `g′` are quoted
  in points of recovery per doubling, because that is how the corpus question
  was asked." I could not work out from this *why* the same phenomenon is
  measured in two incommensurable units, and the mixture makes §5.13's
  exponent table hard to read as one object.

**§1 Summary**

- **L142–144** † — "Among the failures the closest proposal averages 0.976
  Tanimoto similarity, so even the misses are near misses." I could not
  determine which model or protocol this belongs to; placed where it is, it
  reads as the final run's. It also directly contradicts §5.12's bullet headed
  "**Not near-misses**" (L1125). See blocker 1.
- **L148** — "Read per band, the same model goes **97.6% at 30–34, 90.3% at
  40–49 and 79.5% at 50–64.**" 35–39 is silently dropped from a four-band
  table. A reader cannot tell whether it was omitted for brevity or because it
  is awkward (it is 96.0%, i.e. not awkward). Quote all four.
- **L160–161** — "The fit is excellent — correlation |r| ≥ 0.991 — across nine
  separately trained cells, with `b` between 0.144 and 0.396". Three facts from
  three different places fused into one clause: |r| ≥ 0.991 is the eight-cell
  figure, the ninth cell is |r| ≥ 0.985 (§5.13, and `budget_curve_full_6p.json`
  confirms 0.9852 at 30–34), and 0.144–0.396 is the eight-cell range while the
  ninth measures 0.299–0.385. As written it is a composite no single
  measurement supports.
- **L167–169** — "The crossover is around **ten thousand queries**". §5.4's own
  table spans 4,100–20,900, and the final run's saved break-even numbers are
  55,000–122,000. "Around ten thousand" is not a reading of either. See major
  point 7.
- **L186** — "in the final run **18.9% of 50–64 queries draw no preimage at
  all** while the successful ones draw several each". I had to go to §5.12 to
  learn what a "preimage draw" is and to §5.13 to find the 18.9%; and §5.12's
  comparable figure for an earlier cell is 52.0%, so the two numbers sit in the
  reader's head unreconciled until L1174 finally pairs them.
- **L195** † — section heading "**1.4 The final run's headline result is a
  failed prediction**". The headline *result* is the project's best number; it
  is the *prediction* that failed. I read the heading as "the final run did not
  work". Suggest "1.4 The final run beat its own registration, and the misses
  have a direction".
- **L199** † — "five predictions were written into its config file as numeric
  intervals, and the code that would score them was written while it trained.
  Of **20 scored predictions, 9 landed inside their intervals.**" Five becomes
  twenty with no explanation. From `configs/small_full_6p.yaml` and
  `final-run-plan.md` §4: there are five *registrations*, of which (1) is
  reported-not-scored and (5) is registered as questions rather than intervals,
  so three carry intervals, which unfold into 20 band × metric entries in
  `job4_scored.json`. One sentence would fix this.
- **L205–210** † — the four-row table is headed "predicted | measured" with no
  statement of metric convention or ranking, and its "50–64, first-guess
  recovery … **0.5984**" is irreconcilable with §5.13's band table, which gives
  50–64 `rec@1` = **0.3150**. The 0.5984 is consensus order on the 127-query
  slice (confirmed in `band_k1_full_6p.json`); the 0.3150 is generation order,
  raw slots. Nothing in §1.4 says so, and a reader who reaches §5.13 will think
  one of the two is a typo. Same problem for the 40–49 row (0.7842 vs 0.5447).
- **L211** — the table's fourth column is unlabelled, and its entries mix
  directions ("15.8 points **better**" is measured from the interval's ceiling;
  "1.4 points **worse**" from its floor). Correct, but I had to reverse-engineer
  the rule from `job4_scored.json`.
- **L219–226** — "Two quantities that had looked like constants also broke the
  first time they were tested on a second corpus. The exchange rate between the
  two training axes, `g′ / f′`, had been 1.52–1.68 and measured **1.322**; and
  the step exponent's size structure reproduced in the easy bands but not the
  hard ones." The second clause is not a quantity and not a constant, so
  "two quantities" does not describe what follows. I re-read this three times.
- **L224** — "the first direct counter-evidence to this report's own **additive
  scaling law**". The additive scaling law has not been stated anywhere in the
  report at this point, and is never stated. Blocking for §1.4's conclusion.

**§2–§3 Background and Methods**

- **L278** — "as §2.1's own measurement shows below". §2.1 referring to itself
  by number, inside §2.1. Say "as the next paragraph shows".
- **L284** — "943,177 distinct fingerprints describe 950,967 distinct
  molecules, so **98.6% of molecules are the only molecule in the corpus with
  their fingerprint**". The ratio of those two numbers is 99.2%, not 98.6%;
  98.6% is a different statistic (molecules in singleton classes, confirmed via
  `next-steps-2026-10-13.md`'s 98.687%). A reader who divides gets a different
  answer. Add "— which, counted per molecule rather than per fingerprint, is
  98.6%".
- **L296** — "ambiguity is **30× higher**". 30× what? The reader has just been
  given 99.97% and 1.40%; the factor is 1.40/0.05 from the three-corpus table
  in `results.md` §3, which the report does not reproduce.
- **L378** — shard table, 10k row: "11,669 total | — | —". "Total" in a column
  headed "train", with em-dashes for valid and test. I could not tell whether
  the 10k shard has no splits or whether they were not recorded.
- **L378** — "45,528 clean". "Clean" is not defined here and not in the
  glossary.
- **L396** — "(`fingerprint_id` `465725d9dece`)" — a bare hash with no
  statement of what it is for until L399.
- **L422** — the architecture table's last column is "s/step on this M2", and
  the 8.0M row reads "0.90–1.37", while §3.10's cost table gives "1.047
  s/step (solved)" and "1.337 s/step" and "1.373 s/step". Three overlapping
  presentations of the same quantity, 25 lines apart.
- **L451–455** — "`best.pt` is selected on a 500-molecule in-training metric
  carrying about ±2 points of noise, it is not guaranteed to be the final step
  — night 8's best was step 52,000 of 52,500." Fine, but §5.13 then says "The
  oracle selected the final checkpoint … here it took step 88,218", and a
  reader needs to hold both to see why that is notable. A forward reference
  would help.
- **L512–518** † — the protocol table's columns are headed "common protocol |
  large-molecule protocol | the 50+ instrument", and the report thereafter calls
  the second one "the large protocol" (L758, L892, L1097), "the 30+ protocol"
  (L1198, L1228) and "this protocol" (L904), and the third one "the 50+
  instrument" (L1198), "the dedicated 893-query instrument" (L1221), "a
  dedicated 893-query protocol" (L1018) and "the dedicated one" (L1439). Five
  names for three objects. Pick one name per instrument and use it everywhere;
  this cost me more re-reading than any other single thing in the document.
- **L520–528** † — "**Each protocol is blind in its own direction.** The common
  protocol is 63% molecules under 30 heavy atoms, so it cannot describe an
  intervention acting on part of the size distribution: it reported the
  size-weighted training mix as a flat −1.13 points, which is the average of
  +4.60 above 35 atoms and −3.11 below 24, and it hid a 4.18-point loss from
  count fingerprints behind p = 0.32." The "size-weighted training mix" is
  invoked here as an established experiment and is never described anywhere in
  the report. It has no Findings subsection, yet four of its runs
  (`size_mix_s1/s2`, `size_mix_t35`, `size_mix_rev`) appear in the §10.1
  inventory and `results.md` §2.8 gives it a full section. See major point 8.
- **L556–559** — "`ks = [n for n in (1, 5, 20, 100) if n <= eval_k]`, so **a run
  invoked with `--eval-k 60` reports rec@1, rec@5 and rec@20 under a 60-slot
  budget and never prints rec@60 at all.**" This is the clearest explanation in
  the repository of why the convention problem recurs, and it is excellent —
  but a reader who does not know that `eval_k` is the budget and the list is
  the *reporting* points will not see the trap. One clause: "the list is the
  points it reports at, not the budget it draws under".
- **L564** — "On night 7 the mixed pair would have inflated f′ by 4 points and
  read as a cleaner CONFIRMED than the truth." "CONFIRMED" in caps appears here
  for the first time, as a registration verdict vocabulary the reader has not
  been given. §3.9 later uses "FALSIFIED HIGH" (L606) and §5.13 "MISS HIGH"
  implicitly. Introduce the verdict labels once.
- **L613–622** † — rule 3 is one 9-line sentence with three clauses, two
  parentheticals and four numbers: "**The gap has no fixed sign:** both working
  interventions were *understated* by recovery, while night 7's scaling slopes
  are *overstated* by it — by a fifth whole-band and 43% at 60–64. The reason
  biases any cell near the floor: among hits at 50+, the fraction that are a
  different molecule with the same fingerprint is **58.5%** for a model at
  rec@60 0.0459, 27.9% at 0.2251 and 20.9% at 0.3908." I understood it only
  after reading `results.md` §2.9a. "The reason biases any cell near the floor"
  is not a grammatical sentence I could resolve — a reason does not bias a cell.
  Break into three sentences.
- **L624–628** — rule 4 cites "(entry 26)" for a night-8 registration whose gap
  was 0.85–0.88 and whose result was 0.8789. `retractions.md` entry 26 is
  labelled "(item 1, night 7)" with gap 0.72–0.76 and result 0.7553. Following
  the citation lands the reader on a different incident. See major point 9.
- **L666** — "(~216 s solved, 180.3 s and 224.6 s measured)". A solved estimate
  sitting *between* two measurements is good news, but the sentence says
  "independently confirmed" without saying against what tolerance.
- **L690** — "A cap that is never exercised in testing is an assertion, not a
  guard." Excellent line, but it arrives as an orphan paragraph with no
  referent in the bullets above it.

**§4 The programme**

- **L711–712** † — "Nine sessions. The column that matters is the last one." The
  table has ten rows (a "—" Phase 1 row plus 1–9), and its "GPU" column sums to
  156.2 h, against the 118.7 h of L115 and the "roughly 118 hours of GPU time"
  of L5. The 118.7 figure is the sum of *training* hours (the §10.1 inventory
  sums to 118.53); the §4 column is session wall-clock. Nothing says so, and a
  reader who adds the column up concludes the headline is wrong by a third.
  Relabel the column "session" and footnote the 118.7.
- **L713** — the Phase 1 row is dated 10-08, but the document's own date range
  (L4) is "2026-10-09 to 2026-10-31".
- **L716** — "**2 of 206 misses are fingerprint collisions** — a capability
  ceiling, not an information one." I could not determine what protocol or
  model the 206 belongs to (it is `small_1m` at k=20 on the 1,956-query common
  protocol, per `overnight-2026-10-14.md` L91), nor, on first reading, what it
  means for a *miss* to be a collision. It means: of the queries never
  inverted, only two have a fingerprint shared by another corpus molecule — so
  ambiguity is not what blocks them. Spell that out; it is a load-bearing
  finding reduced to seven words.

**§5 Findings**

- **L757** — "fitted over a twelvefold range of k". Twelvefold is 5→60;
  `results.md` makes the domain explicit ("5 ≤ k ≤ 60"). The report does not,
  and since §5.2 also quotes `rec@1`, a reader may think the fit starts at k=1.
- **L776** — "50+ | 1.0 × 10⁷ | 1.2 × 10⁹". Nine orders of magnitude of
  extrapolation from a fit whose domain stops at 60, in a table whose caption
  says "it is a measurement rather than a guess up to k=60". The caveat is at
  L795–799, four paragraphs later. Move it adjacent.
- **L789–791** — "an independence model … predicted 0.9986 at 35+ against a
  measured 0.6890, **wrong by 31 points**, and was wrong by a wide margin four
  times (entry 10)." `retractions.md` entry 10 gives different numbers ("rec@100
  ≈ 0.66 at 35+"). Both may be true of different k, but the reader who follows
  the citation finds no 0.9986.
- **L824–825** — the segment table's "per doubling" column gives +22.54 and
  +8.23 while the adjacent `c` column gives 0.9113 and 0.7008, and the prose
  says "the second cuts the deficit **a fifth less** efficiently". The fifth is
  the ratio of the `c` values (0.701/0.911 = 0.77); the "per doubling" column
  falls by nearly two thirds. Both numbers are in the same table row and they
  tell opposite-magnitude stories. One clause distinguishing "points per
  doubling" from "fraction of deficit per doubling" would settle it.
- **L847** † — "Cutting the deficit by a factor f needs `f^(−1/b)` times the
  budget". `f` here is a cut factor; `f′` thirty lines later is the corpus
  exponent. Two unrelated meanings for one letter. Rename the cut factor (`ρ`,
  or just "a cut to 75%").
- **L850–855** — column headers "queries for a ×0.75 cut | for a ×0.5 cut".
  The ×0.5 column is *smaller* than the ×0.75 column throughout, which is
  correct and counter-intuitive, and nothing says why. One sentence: "a deeper
  cut favours training sooner, so the break-even query count falls".
- **L865** — "**`b ÷ rec@60` stays between 0.320 and 0.380**". Why that ratio
  is the right invariant to test is never explained. A reader needs: "if an
  intervention only moved the model along one curve, `b` would rise in
  proportion to recovery, so their ratio is the test".
- **L877–879** † — "above 50 heavy atoms it sits at **1.01, 1.00, 1.00, 1.02**
  across four cells. **No model in this project, at any corpus or training
  length, ever finds a 50-atom molecule on its first proposal.**" The second
  sentence is false of the ninth cell. See blocker 2.
- **L896** — the f′ table's first row is "90,682 | 856 | 0.0000 | 0.0000 |
  0.0000" under a caption saying "the same 2,321 queries", and L915 then says
  the floor check was "on 571 queries". Two query counts for one row, 19 lines
  apart, with no reconciliation. (`overnight-2026-10-20.md` L95 explains it: the
  floor-check cell was drawn with a cap of 4 rather than 12, so its
  `fp_unseen` count differs. The report should say this or drop the 571.)
- **L900** — "(1.0628 doublings, +23.48 points, binomial SE 0.89)". Doublings
  of what, on which segment? It is 900.9k → 1.88M, which the reader must infer
  from the table.
- **L910** † — "at constant steps a corpus doubling is a passes halving, so
  **+22.09 against −23.55 nets +1.37**". 22.09 − 23.55 = −1.46, not +1.37. See
  major point 5.
- **L917–918** — "consistent with additive separability and weak evidence for
  it, since a number pushed to a floor it was predicted to be below agrees
  without evidence." I understood this only on the third pass. Suggest: "the
  prediction was 'at the floor', and a measurement at the floor cannot
  distinguish that prediction from any other prediction below the floor."
- **L951–955** — "The ratio sits at 1.52–1.68 while both slopes halve, which
  looks like a size-invariant exchange rate near 1.55. Each slope's SE is about
  2.2 points, so the ratio's is about 0.2 and that spread is inside it". The
  propagation from 2.2 points of slope SE to 0.2 of ratio SE is not shown and
  I could not reproduce it confidently. One parenthetical would do it.
- **L983–988** — "**passes still beat molecules**: `small_1m` at 21,117 steps on
  900,917 molecules scores 0.8427 while `small_full_1p2` at 17,772 steps on
  1,881,996 scores 0.7553". 0.8427 appears here for the first and only time in
  the report and is not in any table. A reader cannot check it against
  anything.
- **L994–1009** † — §5.8 presents two tables of deficit ratios for the *same
  two cells*: 0.808/0.825 in the first, 0.776/0.847 in the second. Neither
  table names its metric, its k or its protocol. From
  `overnight-2026-10-17.md` L930 the first pair is rec@60 on the 2,321-query
  large protocol and the second is rec@20 on the common protocol. As printed
  the reader concludes one of them is a typo. See major point 6.
- **L1018** — "the gain is **+3.70 points [+2.13, +5.26], p = 9×10⁻⁶**" with no
  convention named, in a report whose own §3.7 rule says every number names its
  convention. `results.md` §2.5 names it: raw slots (+4.48 in molecule budget).
- **L1023–1024** — "It is also the only intervention here that does anything at
  k=1 (+5.63 points of rec@1)." `results.md` restricts this to 30–49 heavy
  atoms; the report drops the restriction, and §5.9's +22 points of `rec@1`
  from consensus ranking is a flat contradiction of "the only intervention that
  does anything at k=1" unless "intervention" silently excludes ranking.
- **L1038–1044** — the ranking table gives no model, protocol, k or n. It is the
  single most reusable result in the report (§1.5 leads on it) and it is the
  least anchored table in the document.
- **L1046** — "+11 to +26 on every other checkpoint measured" — how many
  checkpoints?
- **L1060–1062** — "three seeds with votes pooled beat one seed by 6.49 points
  of rec@20 at the *same* oracle budget. And **three samplings of one model at
  different temperatures, pooled, reach rec@20 0.9279**". These are the project's
  best numbers and they sit in §5.9 as asides, while §6 says "splitting a fixed
  budget across models beats spending it on the best one" is *dead*. I spent a
  while deciding whether those two statements conflict. (They do not — the
  pooled-vote result keeps the oracle budget fixed while splitting the
  *sampling* — but the report should say so.)
- **L1071–1073** — "Tested where it was most likely to fail — 893 queries at
  50–64 heavy atoms, the worst-validity band in the corpus". "Worst-validity
  band" is asserted without a number anywhere in the report.
- **L1084** — "A fingerprint's set-bit count predicts heavy atoms at r = 0.83,
  so routing is deployable". The inference from a correlation to
  "deployable" is a jump; say what threshold deployability needed.
- **L1108–1110** — "This question was closed twice — once at p = 0.32 on a
  protocol that could not see it, which was hiding a *loss* rather than the gain
  re-opening was meant to find (entry 12), and once properly." The clause
  "rather than the gain re-opening was meant to find" needs a comma or a
  rewrite; I parsed it wrongly twice.
- **L1114** — "Recovery falls from 0.981 below 15 heavy atoms to 0.366 at
  50–64" — no model named, no protocol, no k. §1.3 at least says "for the model
  that was current when it was characterised", which is itself vague. Given
  §5.13 reports 0.7953 at 50–64, the unattributed 0.366 reads as a
  contradiction until the reader works out it is a different, earlier model.
- **L1117** — "above 50 no seed ever differs from another". I could not
  determine whether this means the seeds score identically or that they all
  fail on the same queries.
- **L1121–1122** — "**Not the budget.** The full-k rate is 1.000 in every band".
  "Full-k rate" is used once and never defined. (It is `budget_filled_rate` in
  the dumps: the fraction of queries for which all k slots were filled.)
- **L1125–1127** † — "**Not near-misses.** Best Tanimoto on a miss is 0.69 at
  35–39, 0.64 at 40–49, 0.57 above 50 — nowhere near as fast a decline as
  recovery's 0.28 → 0.10 → 0.02." Head-on contradiction with L142/L750. Also
  "0.28 → 0.10 → 0.02" is an unattributed recovery triple that matches no table
  in the report.
- **L1136** — "the chance a right-sized candidate is the preimage stays between
  10.2% and 11.2%". "Right-sized" is used three times before it is explained
  (it means within some heavy-atom tolerance of the target; §6's "closest within
  0.2 atoms in every band" hints at it). Define it.
- **L1144–1149** — the concentration table's columns are "rec | preimages/query
  | none | per hit". "none" as a column header is opaque; "per hit" needs
  "preimages per solved query".
- **L1153–1154** — "Poisson would give 0.729 against a measured 0.480." Which
  Poisson, with what rate? (It is 1 − e^−1.307 using the preimages/query
  column; it took me a minute to reconstruct and it is worth one clause.)
- **L1159–1161** — "Of one seed's misses above 50 atoms, **1.6%** are recovered
  by either of two other seeds; 96.9% of the band is missed by all three against
  95.3% from chance alone." Then L1174 reuses 96.9% for an entirely different
  quantity: "the share drawing none falls 96.9% → 52.0%". Same number, two
  meanings, fifteen lines apart. I assumed a typo.
- **L1168** — "Three seeds also agree on **80.1%** of the evaluation set".
  "Agree" is not defined — all three succeed or all three fail, presumably.
- **L1196** — "(raw-slot convention throughout, §3.7)" governs the before/after
  table, but 48 lines later L1243 quotes "0.9582 against a registered
  0.9634–0.9767" for the same all-slice rec@60 the table gives as 0.9496. Two
  all-protocol rec@60 figures inside one subsection, differing by 0.9 points,
  with the convention difference only implicit. I checked the dumps:
  0.9496 is `miss_anatomy_full_6p.json` (raw slots), 0.9582 is
  `band_k60_full_6p.json` (molecule budget). Say so at L1243.
- **L1219–1224** — "The two independent reads of 50–64 agree. Compared **within
  one convention**, as §3.7 requires: in the molecule budget, 0.8110 … against
  0.7615 … — 4.95 points apart against a combined SE of 3.76, so **1.3 SE**. In
  raw slots the same pair reads 0.7953 against 0.7402, 1.4 SE." Four numbers in
  two conventions across two protocols in three sentences. It is correct (I
  verified all four against the dumps) and it is the densest passage in the
  report. Consider a four-cell table.
- **L1229** — "**Every miss on a hard band is high; every miss on a saturated or
  pooled band is low.**" `job4_scored.json` contains a counterexample: 35+
  `rec@1` consensus is a MISS **HIGH** by 0.53 points, and 35+ is a pooled band.
  See major point 11.
- **L1232** — "structure@60 there +7.8 pts". "There" = the 50+ instrument, two
  clauses back. Name it.
- **L1234** — "and the pooled 30–39 one point under". 30–39 is not a band in
  §5.13's own band table (which has 30–34 and 35–39), so the reader has nowhere
  to look it up.
- **L1254–1261** — the exponent table's fourth column is unlabelled and its
  entries are verdicts in prose ("holds", "essentially holds", "miss high, as
  registered to expect", "easy bands only", "4.02 lower on the larger corpus",
  "miss low"). Head it "verdict".
- **L1258** — "`c` at k=60 | 0.7008–0.9113 | **0.986**". `stage6_scored.json`
  also contains `c_all_50plus` = 0.682, which the report never mentions; so the
  single "0.986" is the 30+ figure only. Say which slice.
- **L1270** — "A slope read at 30–74 passes on 100k molecules does not hold at
  1.2–6 passes on 1.9M." Good sentence — but the "1.2–6 passes" pairing with
  "2.3115 doublings" in the dump is where the 0.986 comes from, and the report
  never states the doublings, so the reader cannot check it.
- **L1296** — "50+ | 654 | 6,640 | 1,444,900" under a heading claiming the cliff
  was "pushed back fifty-fold". The fiftyfold is 10⁷/654 ≈ 15,000-fold at
  rec 0.9, or… I could not locate the comparison that yields fifty. L1299
  says "~50× cheaper than a fortnight earlier" — against what number? §5.2's
  50+ row gives 1.0 × 10⁷ for 0.90, which is 15,000×, not 50×. See major
  point 10.
- **L1304** † — "the Poisson comparison shows proposals concentrated on fewer
  queries than chance **in every band**". False in five of six bands per
  `budget_curve_full_6p.json`. See blocker 3.
- **L1312–1313** — "At six passes the floor is visible, and 13.2% of 50+
  recoveries are not a modelling problem at all." "Not a modelling problem" is
  a strong reading of "a different molecule has the same fingerprint" and
  deserves a clause of justification — the task as posed scores these as
  successes, so calling them a floor requires saying which metric the floor
  belongs to.

**§6–§10**

- **L1323** — "the size defect needs a size token on the encoder | no size
  defect left to fix at k=60: **truncation 5.1 atoms**, 89.8% of 50+ queries get
  a right-sized proposal". "The size defect" and "truncation 5.1 atoms" are both
  undefined in the report. (`retractions.md` entry 9 explains: the model's
  proposals were on average 10.7 heavy atoms short of the target at k=20, 5.1
  at k=60.) As printed, the row is unreadable.
- **L1324** — "cooling to T=0.3 moves it by +1.01 points [−0.90, +2.91]". The
  identical interval appears at L607 as a *difference-in-differences* that fired
  FALSIFIED HIGH (entry 22). Same numbers, two described quantities. If it is
  one measurement serving both roles, say so.
- **L1326** — "independence predicted 0.9986 at 35+ against a measured 0.6890".
  See L789 above.
- **L1330** — "`b ÷ rec@60` is invariant across **eight** cells", while §1.5
  (L240) says it "has now held across **nine** cells". Both appear in the same
  document.
- **L1333** — "`beats original` ≤ 0.010 in every condition". `beats original` is
  a column name from `overnight-2026-10-14.md` and is undefined in the report.
- **L1334** — "the largest clean pool is 308 molecules against a fourfold power
  requirement". "A fourfold power requirement" — four times what?
- **L1367–1369** — "The fifth was in a draft of this report … it was caught by
  proof-reading, which is the weakest of the five catches and the reason §3.7
  ends with a rule rather than a guard." Admirably candid, and it is also the
  reason I would urge a convention/ranking audit pass (see major point 2).
- **L1396** — "Checking it against the raw file took one 120,000-row sample and
  found that 2.6% of ChEMBL lives above the line", against §8's "**2.558% of
  ChEMBL 35**". Fine as rounding, but §8's three-decimal precision from a
  120,000-row sample is more precision than the sample supports.
- **L1429–1432** — "**`max_tokens: 128` binds first**: 73.0% of what the atom cap
  discards exceeds the decoder's context anyway, so raising the cap alone would
  add 16,465 molecules (0.87% of the corpus)". Three denominators in two lines:
  2.558% is of raw ChEMBL 35, 73.0% is of the discarded set, 0.87% is of the
  training corpus. I had to compute all three to check consistency (they are
  consistent).
- **L1461** — "**One machine, one seed per cell, mostly.** Only the 8,508-step
  100k cell has three seeds." Good — but §5.1's "three-temperature vote" and
  §5.9's "three seeds with votes pooled" made me think there were more
  multi-seed cells than there are.
- **L1517–1522** † — item 6: "Recovery 0.7402 against structure 0.6428 is a
  9.7-point gap … Some is collisions (item 4); the remainder is the model
  proposing the right fingerprint by a wrong molecule". The "remainder" is
  described in the same words as the collisions, and arithmetically there is no
  remainder: 0.7402 × (1 − 0.1316) = 0.6428 exactly. See major point 12.
- **L1527** — "the newest of them is §5.13's own, that a registered command
  which has never been executed is a registration of intent rather than
  procedure." §5.13 contains nothing about this, and §7's five causes do not
  include it. A reader sent to §5.13 finds nothing.
- **L1541** — inventory row "`tiny` | 1.2M | 10k | — | 0.17". The steps column is
  "—" for the only row where it is, with no footnote.
- **L1542** — "`small` … 3.75 | Phase 1, the go/no-go gate", against §4's Phase
  1 row of "4.2 h". Two durations for one event.
- **L1561** — "`base_1m` (25.7M parameters) is kept in the repo as a record of
  what was tried". `base_1m` appears nowhere else in the report; §3.3 calls the
  same thing "~~25.7M~~".

---

## 3. Major points

**1. §1.3 (L142–144) and §5.1 (L750) tell the reader the misses are near
misses; §5.12 (L1125) says they are not, and the dumps side with §5.12.**
*Problem.* "Among the failures the closest proposal averages 0.976 Tanimoto
similarity, so even the misses are near misses" / "Mean best Tanimoto is 0.976,
so even the failures are near misses". The 0.976 traces to
`overnight-2026-10-14.md` L214, where it is the "Tanimoto to original" column of
the *unperturbed control* of the latent-generativity probe — a mean over **all**
queries, which at ~90% recovery is dominated by exact hits scoring 1.0. The
same inference appears at `overnight-2026-10-09.md` L242 ("mean best Tanimoto
rose 0.885 → 0.974, so even the failures are near misses now"), which is the
same error. The actual mean best Tanimoto **among misses** is on disk:
`miss_anatomy_full_6p.json` gives 0.792 for the final run's 30+ protocol
(0.749 at 30–34, 0.855 at 50+), and §5.12 quotes 0.69/0.64/0.57 for an earlier
cell. So the report asserts and then denies the same thing, and the version in
§1.3 and §5.1 is the unsupported one.
*Fix.* Delete the 0.976 sentence from §1.3 and §5.1. Replace with the figure
that is actually among-misses, which is free to read off the dumps: "the closest
proposal to a missed target averages 0.79 Tanimoto, and 29% of misses are above
0.9 — close, but §5.12 shows the decline is far slower than recovery's, which
is why near-misses are not the explanation of the cliff." That also removes the
contradiction with §5.12 instead of papering over it.
*Severity:* `blocker`

**2. The headline `rec@1` is in generation order, while the project's adopted
ranking is consensus — a 16-point difference the report never discloses.**
*Location.* §1.3 L137–141, §5.13 L1194–1205 and the band table L1212–1217.
*Problem.* §1.3's "recovers **69.6% of molecules on the first guess**" is
`miss_anatomy_full_6p.json`'s generation-order figure. On the same 2,321
queries, `band_k1_full_6p.json` gives consensus `rec@1` = **0.8591** (and per
band 0.9083 / 0.8640 / 0.7842 / 0.5984). `final-run-plan.md` §4c states
flatly: "Consensus order is the project's adopted ranking … worth +22 points of
rec@1 at no extra oracle call". Meanwhile the report's own §1.5 and §5.9 sell
consensus ranking as free and worth +22 points. So the report's headline
first-guess number is in the ranking the project does *not* use, understating
its own result by 16 points, and §1.4's table then quotes the consensus 0.5984
for 50–64 while §5.13's band table quotes the generation-order 0.3150 — with no
label on either. A first-time reader cannot reconcile the two and has no way to
know which is "the" result.
*Fix.* Name the ranking on every `rec@1` in the document, exactly as the report
already names the budget convention. In §1.3, lead with the consensus number
(0.859 whole-protocol, 0.598 at 50–64) since that is the adopted configuration,
and give the generation-order number beside it as the unranked baseline. Add
a ranking column to §5.13's band table. In §1.4's table, head the rows "50–64,
first-guess recovery (consensus)".
*Severity:* `blocker`

**3. §5.13 (L1304) asserts the Poisson concentration result "in every band";
the saved dump contradicts it in five of six bands.**
*Problem.* "the Poisson comparison shows proposals concentrated on fewer queries
than chance in every band." From `budget_curve_full_6p.json`, measured recovery
against the Poisson expectation implied by preimages/query is:
30–34 0.982 vs 0.804, 35–39 0.966 vs 0.829, 40–49 0.918 vs 0.878, 35+ 0.933 vs
0.865, all 0.958 vs 0.836, 50+ **0.811 vs 0.944**. Measured recovery *exceeds*
Poisson everywhere except 50+ — i.e. preimages are spread *more evenly* than
chance in the easy bands, and concentration is a large-molecule phenomenon
only. Since concentration is the report's central mechanism (§1.3, §5.12,
§5.13, §9 item 3), overstating its reach undermines the one explanation the
report says is "the single most useful finding here".
*Fix.* Replace with the truth, which is a stronger result: "the Poisson
comparison separates the bands — below 50 atoms the model's preimages are
spread *more* evenly across queries than chance (0.958 measured against 0.836
Poisson whole-protocol), while at 50+ it inverts, 0.811 against 0.944.
Concentration is not a property of decoding in general; it switches on with
size." Free — the numbers are in the dump.
*Severity:* `blocker`

**4. §5.5 (L877–879) states a universal that §5.13 falsifies.**
*Problem.* "**No model in this project, at any corpus or training length, ever
finds a 50-atom molecule on its first proposal.**" §5.13's own band table gives
50–64 `rec@1` = 0.3150 in generation order and 0.5984 in consensus, and
`budget_curve_full_6p.json`'s 50+ exponent implies A = 0.696, not the ~1.00 the
sentence rests on. The claim was true of the first eight cells and the ninth
broke it.
*Fix.* Scope it and then note the break: "`A` sat at 1.01, 1.00, 1.00, 1.02
across the four cells available when this was measured — no model then could
find a 50-atom molecule on its first proposal. §5.13 is where that stopped
being true: the final run's 50+ `A` is 0.70, and its first-guess recovery at
50–64 is 0.315." That turns a falsified universal into one of the report's
better before/after contrasts.
*Severity:* `blocker`

**5. §5.6 (L910): the near-cancellation arithmetic does not add up.**
*Problem.* "at constant steps a corpus doubling is a passes halving, so **+22.09
against −23.55 nets +1.37**". 22.09 − 23.55 = −1.46. The same sentence appears
in `results.md` §2.9, so the error is inherited, not introduced. What the
underlying data say (`results.md` §2.9's own table) is that the *measured* net
on the 90.7k → 900.9k segment was +1.37 points per doubling while the predicted
net from the two slopes is −1.46 — which is actually a sharper version of the
point being made: the observable is ±1.5 points, i.e. inside the project's own
1.6-point threshold, formed as the difference of two ~23-point quantities.
*Fix.* "+22.09 against −23.55 predicts −1.46 per doubling; the measured net was
+1.37. Both are inside the 1.6-point threshold, which is the whole problem: the
constant-steps corpus axis is a sub-threshold difference of two 23-point
numbers."
*Severity:* `major`

**6. §5.8 (L994–1009): two tables of deficit ratios for the same two cells,
neither labelled with metric, k or protocol.**
*Problem.* The first table gives 0.808 and 0.825; the second gives 0.776 and
0.847. From `overnight-2026-10-17.md` L930 and L961, the first pair is `rec@60`
on the 2,321-query large protocol with bootstrap CIs; the second is `rec@20` on
the common protocol. Nothing in §5.8 says this, and the section's whole claim
is that the ratio is *constant*, which the two unlabelled pairs appear to
contradict.
*Fix.* Add the metric and protocol to both captions, and say explicitly that
the two pairs are the same finding read on two instruments. While there, note
that the 50+ row of the underlying 2×2 is 0.983/0.914 — a ratio essentially at
1.0 — which is the real reason "the cut declines to 3.9% at 50+" and would
anchor that number (currently traceable only to `overnight-2026-10-17.md`
L1142).
*Severity:* `major`

**7. §1.3 (L167–169) and §5.4: the stated crossover is contradicted by the
final run's own saved break-even numbers, which the report never reads.**
*Problem.* "**Below roughly ten thousand queries, buy budget; above it, train
longer.**" §5.4's table spans 4,100–20,900, computed from `small_1m` at
1.337 s/step. `results/overnight9/step_curve_pair_30plus.json` already contains
`break_even` for the ninth cell: **55,271–121,634** queries across the bands
(all-slice 61,210 for a ×0.5 cut, 100,226 for ×0.75). The final run moved the
crossover up by roughly an order of magnitude, and the report's practical
advice — the one sentence a practitioner would act on — is a fortnight stale.
*Fix.* Add the ninth-cell row to §5.4's table (free, already on disk) and
restate: "on the final model the crossover is 55,000–120,000 queries, up roughly
sixfold, because training got cheaper per point faster than budget did. The
advice holds in direction and the threshold moves with the model, so quote it
against a named cell."
*Severity:* `major`

**8. The size-weighted training mix is cited four times as an established
result and never described.**
*Location.* §3.6 L522–533, §5.5 L872, §10.1 L1551–1553.
*Problem.* §3.6 uses it as the worked example of protocol blindness ("a flat
−1.13 points, which is the average of +4.60 above 35 atoms and −3.11 below 24",
and "up-weighting large molecules sixfold and down-weighting them threefold
produced the same whole-protocol recovery to four decimal places"), §5.5 lists
it as one of the three retired "second dial" claims, and §10.1 lists four runs
for it. But §5 has no subsection for it, so a reader never learns what the
intervention was, whether it worked, or what became of it. `results.md` §2.8
devotes a full section with a clear verdict ("cooled, the mix is close to
free", −0.28 points whole-protocol, +5.29 above 35 atoms, and an exposure
response that replicates as a rate but fails every band-level prediction).
That is a substantive finding, and the report is the project's one
self-contained account.
*Fix.* Add a short §5.x (ten lines would do) summarising it from `results.md`
§2.8, or — if it is deliberately cut — say so in §6 or §8 so the reader is not
left with four dangling references and four unexplained runs in the inventory.
*Severity:* `major`

**9. §3.9 rule 4 (L624–628) cites entry 26 for an incident entry 26 does not
describe.**
*Problem.* The report: "Night 8 registered rec@60 in 0.88–0.95 with 'below 0.85'
as saturation, leaving **0.85–0.88 unnamed**. The measurement came in at
**0.8789** … (entry 26)." `retractions.md` entry 26 reads "(item 1, night 7)"
and describes gaps of 0.72–0.76 with a result of 0.7553. `overnight-2026-10-24.md`
L14/L36 confirms night 8 had its own, separate tiling failure, and
`configs/small_full_6p.yaml` and `final-run-plan.md` §4 both also call the
night-8 case "entry 26". So the repository has two tiling failures and one
ledger entry, and the report's citation sends the reader to the wrong one. §7.4
(L1386) repeats it.
*Fix.* The cleanest fix is in `retractions.md` (split into two entries, or
broaden entry 26 to cover both nights). Failing that, the report should cite by
night rather than by entry here: "night 8's registration left 0.85–0.88 unnamed
and the result landed in it; night 7 had made the same mistake at 0.72–0.76
(entry 26)". Note this also bears on the "twenty-eight claims" count in §1.5
and §7.
*Severity:* `major`

**10. §5.13 (L1289, L1299): the "fiftyfold" cannot be reconstructed.**
*Problem.* The heading claims "pushed back fifty-fold" and the text says 50+
"needing 654 is the cliff surviving everything: ~50× cheaper than a fortnight
earlier". §5.2's comparable figure is 1.0 × 10⁷ for rec 0.90 at 50+, which is
15,000× not 50×. The fiftyfold is presumably against a different pairing
(perhaps k for 0.95: 1.2 × 10⁹ → 6,640, which is 180,000×; or against an
intermediate cell not in the report). §1.3 repeats "pushed it back roughly
fiftyfold". I could not trace it to any source.
*Fix.* State the two numbers the ratio is taken between, in one clause. If the
honest ratio is three or four orders of magnitude, say that instead — it is a
better result.
*Severity:* `major`

**11. §5.13 (L1229): the directional rule has a counterexample in its own
scoring file.**
*Problem.* "**Every miss on a hard band is high; every miss on a saturated or
pooled band is low.**" `job4_scored.json` records "(3) 30+ protocol, rec@1
consensus", band **35+** (pooled, n = 1132), as **MISS HIGH** by 0.53 points.
So one of the four pooled-band misses goes the other way. The rule is nearly
right and the report states it as exceptionless.
*Fix.* "Of the eleven misses, ten run with size: high on the hard bands, low on
the pooled and saturated ones. The single exception is 35+ `rec@1`, which
missed high by half a point — inside the noise." Also worth noting in the same
place that six registered intervals (the 50–54 / 55–59 / 60–64 rec@60 and
struct@60 rows that `final-run-plan.md` §4b calls "the registration **of
record** for large molecules") were never measured, because the final run's
50+ band table was computed with only the pooled `50+` grouping. The report
says "9 of 20 scored" without saying that 20 is not the number registered.
*Severity:* `major`

**12. §9 item 6 (L1517–1522): the "clearest unexplained number in the report"
is fully explained by the line above it.**
*Problem.* "Recovery 0.7402 against structure 0.6428 is a 9.7-point gap … Some
is collisions (item 4); the remainder is the model proposing the right
fingerprint by a wrong molecule in a way the easy bands do not show." The
"remainder" is defined in exactly the words that define a collision, so the
sentence says the remainder is the thing it was just distinguished from. And
arithmetically there is no remainder: 0.7402 × (1 − 0.13162) = 0.64277, against
a measured structure@60 of 0.642777. The gap is 100% collisions, to five
decimal places, and the report's own §5.13 L1308–1313 already says so.
*Fix.* Either drop item 6 and fold its content into item 4, or recast it
honestly: "Recovery 0.7402 against structure 0.6428 is exactly the collision
rate (0.7402 × 0.868 = 0.6428), so there is no residual to explain — the gap
*is* item 4, and the open question is whether a richer fingerprint shrinks it."
That is a cleaner close than "not yet a hypothesis".
*Severity:* `major`

**13. "The additive law" is the subject of §1.4's most important conclusion and
is never stated in the report.**
*Location.* L224, L917, L961, L1283–1287, L1487.
*Problem.* §1.4 tells the reader that `g′ / f′` failing to transport is "the
first direct counter-evidence to this report's own additive scaling law", and
§9 item 2 says the counter-evidence "should not be promoted to a finding" until
an error bar exists. Both depend on the reader knowing what the additive law
claims. The report never writes it down. `results.md` §2.9 does: `value =
f(log distinct molecules) + g(log passes)`.
*Fix.* One display line in the glossary (next to the f′/g′ rows) and one at the
head of §5.6: "the law fitted here is additively separable — `rec@60 ≈ f(log₂
distinct molecules) + g(log₂ passes)` — so `f′` and `g′` are its two slopes and
`g′/f′` is the exchange rate between them. Additivity is what §5.13 breaks."
*Severity:* `major`

**14. §4's hours and the document's headline hours disagree by a third, with no
reconciliation.**
*Location.* L5, L115, L711–722, L1539–1559.
*Problem.* The title block says "roughly 118 hours of GPU time", §1.1 says
"118.7 hours of recorded run time", and §4's table has a column headed "GPU"
whose ten entries sum to 156.2 h. The §10.1 inventory sums to 118.53 h, so
118.7 is training time and the §4 column is session wall-clock.
*Fix.* Rename the §4 column "session" and footnote it: "session length
including scoring and analysis; the 118.7 h of L115 is training time only, per
§10.1." Also reconcile the Phase 1 duration (4.2 h in §4, 3.75 h in §10.1) and
the date range (L4 starts 10-09; §4's first row is 10-08).
*Severity:* `minor`

**15. §5.3's "3.1× steeper" headline is not re-checked against the ninth
cell, which gives 2.75.**
*Location.* L801–816, and §5.13's exponent table L1254–1261.
*Problem.* §5.3's claim is "**across two corpora and every band**", and §5.13
goes to some trouble to report what did and did not transport — but omits
`c / b`. `step_curve_pair_30plus.json` already has it: 2.90 / 2.72 / 2.82 /
2.25 per band, 2.75 all-slice, against §5.3's 3.1 and the 100k arm's 2.86–3.13.
Given that §5.13's whole point is which quantities transport, this is a gap in
its own audit, and it is free to fill.
*Fix.* Add a `c ÷ b` row to the §5.13 exponent table with target 2.54–3.39 and
measured 2.25–2.90, verdict "holds at the low edge". It strengthens §5.3 by
testing it rather than restating it.
*Severity:* `minor`

**16. §5.13's "the budget law transports" omits the one caveat `results.md`
attaches to it.**
*Location.* L1265–1266.
*Problem.* "**The budget law transports to a ninth cell** — `b` inside its range
in every band, |r| ≥ 0.985. It is the most robust quantity in the project."
`results.md` §2.1 adds: "Note the direction of the change, though: the final
run's `b` at 50+ is **0.299** against the 0.144 above, so the *band structure*
of `b` flattened with scale even as its range held — the same flattening that
made night 9's size extrapolations too steep." That caveat matters, because the
flattening of `b` is the same phenomenon §5.13 spends two subsections
establishing, and it is independent evidence for it.
*Fix.* Carry the sentence across. It costs two lines and converts a
transport-confirmed into a transport-confirmed-plus-mechanism.
*Severity:* `minor`

---

## 4. Minor points and line edits

1. **L5** — "roughly 118 hours of GPU time" on an Apple M2 with MPS. "GPU time"
   is loose for a unified-memory laptop; §3.10 is more careful. Suggest "118
   hours of training".
2. **L21** — "all 28 withdrawn claims and the five causes behind them". §7's
   five causes and §3.9's five rules are different lists, and §1.5 (L251–253)
   blurs them ("The five causes and the five pre-registration rules they
   produced"). The rules were produced by a subset. Reword.
3. **L34** — "see [§8](#8-limitations)" — the anchor style `#8-limitations`
   assumes a particular Markdown renderer's slugging; several anchors in the
   document (e.g. `#56-the-corpus-axis-f--2209-points-per-doubling-flat`) look
   fragile. Worth one pass with the renderer that will host this.
4. **L60** — "`rec@1` is the first-guess rate; `rec@60` allows sixty guesses."
   Repeated verbatim at L124–125. Cut one.
5. **L74** — "**shard** | … Four were built — 10k, 100k, 1M and `full`". The
   report then uses `1m` (lowercase, L378), "1M" (L74), "1M-molecule shard"
   (L283) and "the 1M shard" (L1092). Pick one.
6. **L116–125** — §1.2's explanation of the oracle and `recovery@k` repeats §1.1
   and the glossary almost word for word. §1 would be a page shorter and no less
   clear with one of the three.
7. **L205** — table header `| | predicted | measured | |` has two unnamed
   columns. Same at L1254 and L994. Head them "band / metric" and "verdict".
8. **L424** — `| ~~25.7M~~ | 384 | — | 6 + 6 | ~25.7M | **6.58** — infeasible |`
   — strikethrough plus an em-dash in the heads column plus a tilde in the
   params column. Three notations for "not really used" in one row.
9. **L433** — "learning rate 5×10⁻⁴ (4.5×10⁻⁴ for the 15.1M config…)" uses
   superscript minus; §5.8 L1026 writes "lr 4.5×10⁻⁴ and 5×10⁻⁴" in the reverse
   order, and §8 L1458 writes "5×10⁻⁴ and 4.5×10⁻⁴". Fix the order so the
   8.0M/15.1M pairing reads the same way each time.
10. **L472** — "which made validity read 0.714 against a true 0.785". "True" is
    doing a lot of work; suggest "against 0.785 on the correct denominator".
11. **L500** — the table's `small_1m` row bolds both cells ("**0.569**",
    "**12.6**"); the `small_100k` row bolds neither. The bolding convention
    across the document is inconsistent generally — some tables bold the
    headline cell, some bold both sides of a comparison, some bold nothing.
12. **L518** — the "invocation" row is a very wide cell of CLI flags that will
    wrap badly. Consider moving the three invocations to a fenced block below
    the table.
13. **L571** — "**Gaps below about 1.6 points between two training runs are not
    evidence of anything.**" Then L588: "The 1.6-point rule nearly killed a
    genuine +0.77-point result at p = 0.001." The bolded universal and its
    exception are 17 lines apart; the bold should be qualified in place
    ("…between two *independently trained* runs on the whole protocol").
14. **L695** — "`pytest -q # 478 tests; the 5 needing a shard self-skip`". I
    could not verify 478 (pytest is not installed in this environment; the tree
    has 306 `def test_` across 21 files, so 478 implies parameterisation).
    Either drop the count or say "478 collected, from 306 test functions".
15. **L709** — "Nine sessions. The column that matters is the last one." The
    table has ten rows. "Nine overnight sessions plus the Phase 1 gate."
16. **L742** — the §5.1 table's first row is "8M, ChEMBL 1M, 21,117 steps,
    T=1.0" while the adopted setting is T=0.6 on the row below, and the
    bolded headline figure (0.8962) is the T=1.0 one. Bold the 0.9162.
17. **L766** / **L811** — "all" as a band label, when §3.6 has already warned
    that "all" means "all molecules in that protocol". Use "all (30+)".
18. **L902** — "It replicates at +20.96 in the molecule-budget convention and
    +16.79 on the common protocol at k=20". Three conventions in one sentence
    with the headline figure (+22.09) in a fourth position. Consider a
    three-row table.
19. **L1046** — "**+22 points of rec@1**" rounds 0.7520 − 0.5302 = 22.18.
    Elsewhere the report gives two decimals (+1.99, +4.18, +22.09). Be
    consistent.
20. **L1114** — "and from 0.953 with no stereocentres to 0.355 with five or
    more" — stereochemistry is stripped (§3.1), so "stereocentres" needs one
    clause of explanation (they are counted on the pre-stripping molecule as a
    complexity proxy, presumably).
21. **L1149** — "| 50+ | 127 | 0.4803 | 1.307 | **52.0%** | **2.72** |" — the
    bolding marks the two extreme cells, but the row's point is the contrast
    with the 30–34 row, which is unbolded.
22. **L1182** — "**88,218 steps = 6.00 passes**". 88,218 × 128 / 1,881,996 =
    5.999. Fine, but say "6.00 passes (88,218 × 128 / 1,881,996)" once, since
    the identity is the report's recurring tool.
23. **L1293** — "| 30–34 | **1** | 9 | 669 |". The underlying value is 1.31
    (`budget_curve_full_6p.json`), rounded down to 1. Rounding a budget *down*
    overstates the result; round up, or print 1.3.
24. **L1334** — "nothing above 64 exists in it" sits beside §7.5 and §8, which
    establish that this is true only because the cap imposed it. The §6 row
    restates the retracted premise. Reword to "nothing above 64 survives this
    project's standardisation, and widening it needs a longer context (§8)".
25. **L1471** — "**1. Where does the step axis stop? (~50 h, one run)**" — the
    §9 preamble says items are "Ordered by what they would decide, not by
    cost", but every heading leads with cost. Minor, but it undercuts the
    preamble.
26. **L1535–1537** — §10.1's caption says per-run numbers are "**not**
    comparable across rows", and the table then has an "hours" column that
    readers will certainly sum (and should — it is where 118.7 comes from). Add
    "the hours column is additive; nothing else in the table is."
27. **L1575–1588** — §10.3 lists ten scripts; `scripts/` holds 60 files
    including `band_analysis.py`, `miss_anatomy.py` etc. plus 20 `overnight*.sh`
    drivers and a dozen analysis scripts the report cites by name in passing
    (`exposure_response.py`, `fingerprint_ambiguity.py`, `seed_union.py`,
    `size_bias.py`, `cap_cost.py`, `bitflip_probe.py`). Either say the list is
    the authorities only (it does, in the heading — but "the tools" reads as
    exhaustive) or add the rest.
28. Cross-document: `docs/methodology.md` §2 is headed "There are **two**
    protocols, and their numbers are not comparable", while the report's §3.6
    describes three. Since the report names methodology.md as the authority on
    conventions (L20), the stale count should be fixed there or noted here.

---

## 5. Factual and consistency concerns

**Verified correct** (traced to source, matching to four decimals): the §5.13
band table and all its columns (`miss_anatomy_full_6p.json`); the 50+ instrument
row 0.3180 / 0.6685 / 0.7402 / 0.6428 / 0.132 / 6.6
(`miss_anatomy_50plus_full_6p.json`); the §5.13 brute-force price table and
preimage figures 1.63 → 2.87 and 18.9% (`budget_curve_full_6p.json`); the
molecule-budget 0.8110 vs 0.7615 pair (`band_k60_full_6p.json`,
`b50_full_6p.json`); every entry in the §5.13 exponent table, including
b = 0.299–0.385, 5-of-6 on `b ÷ rec@60` with 35–39 at 0.401, c = 0.986, the
four per-band c values and their 2.11× ratio, g′ = 22.28 and g′/f′ = 1.322
(`stage6_scored.json`); "9 of 20" and every number in §1.4's and §5.13's
registration tables (`job4_scored.json`); the §3.8 seed sd of 0.75 points
(recomputed from 0.6053 / 0.6084 / 0.5941); f′ = +22.09 from 1.0628 doublings
and +23.48 points; the §5.3 segment table's c = 0.9113 and 0.7008 (recomputed
from the deficits); the Poisson 0.729 at 50+ in §5.12 (= 1 − e^−1.307); the
§5.8 "5.3-fold" (7.11/1.33); torch 2.13.0 and the `fingerprint_id` discipline
(`leaderboard.jsonl`); the 2.558%/73.0%/16,465/0.87% chain in §8 (internally
consistent); 3.9% at 50+ (`overnight-2026-10-17.md` L1142); "2 of 206 misses"
(`overnight-2026-10-14.md` L106); 571 queries (`overnight-2026-10-20.md` L95);
98.687% uniqueness (`next-steps-2026-10-13.md` L198).

**Wrong or unsupported** (details in §3):

1. **L1304** "concentrated on fewer queries than chance in every band" — false
   in five of six bands per `budget_curve_full_6p.json`. Blocker 3.
2. **L877–879** "No model … ever finds a 50-atom molecule on its first
   proposal" — falsified by §5.13's own 0.3150 / 0.5984. Blocker 4.
3. **L142, L750** "0.976 … even the misses are near misses" — the 0.976 is a
   mean over all queries, not over misses; the among-misses figure is 0.792
   (final run) or 0.69/0.64/0.57 (§5.12). Blocker 1.
4. **L910** "+22.09 against −23.55 nets +1.37" — arithmetic error; −1.46.
   Major 5.
5. **L1229** "Every miss on a … pooled band is low" — 35+ `rec@1` is a MISS
   HIGH. Major 11.
6. **L1517–1522** "the remainder" of the recovery/structure gap — there is no
   remainder; the gap is 0.7402 × 0.13162 to five decimals. Major 12.
7. **L160–161** "|r| ≥ 0.991 across nine … cells, with `b` between 0.144 and
   0.396" — a composite of the eight-cell |r| and range with the nine-cell
   count; the ninth is |r| ≥ 0.985 and 0.299–0.385.
8. **L167, L850–855** "The crossover is around ten thousand queries" — §5.4's
   own table says 4,100–20,900 and the ninth cell's saved break-even says
   55,000–122,000. Major 7.
9. **L1289, L1299** "fifty-fold" / "~50× cheaper" — I could not reconstruct
   this from any pairing in the report or the dumps. Major 10.
10. **L624–628, L1386** "(entry 26)" — cites a night-7 incident for a night-8
    one. Major 9.
11. **L1330** "eight cells" vs **L240** "nine cells" for the same invariant.
12. **L789** "0.9986 at 35+" vs `retractions.md` entry 10's "rec@100 ≈ 0.66 at
    35+" — the citation does not contain the number.
13. **L199** "five predictions … 20 scored predictions" — 26 intervals were
    registered (`final-run-plan.md` §4b/§4c), 20 were scored, 6 (the 50–54 /
    55–59 / 60–64 sub-bands of registration (2), which the plan calls "the
    registration of record for large molecules") were never measured. The report
    does not disclose the shortfall.
14. **L284** "943,177 distinct fingerprints describe 950,967 distinct
    molecules, so 98.6%" — the two numbers give 99.2%; 98.6% is a different,
    correct statistic from a different source.
15. **L5 / L115 / §4 table** 118 h vs 118.7 h vs a column summing to 156.2 h.
    Major 14.
16. **L1542 vs L713** Phase 1 at 3.75 h vs 4.2 h.
17. **L1527** "§5.13's own [newest cause], that a registered command which has
    never been executed is a registration of intent rather than procedure" —
    §5.13 contains no such statement, and §7 does not list a sixth cause.

**Numbers I tried to trace and could not:**

- The **"fiftyfold"** of L1289/L1299 (see above). Nothing in `results.md`,
  `overnight-2026-10-30.md` or the overnight9 dumps gives it.
- **478 tests** (L695) — pytest is not installed here; the tree has 306 test
  functions, so the count is plausible via parameterisation but unverified.
- **"roughly twenty molecules"** (L180, L1130) as the cloud size, against §3.5's
  measured 12.6 distinct valid molecules per query for `small_1m` at k=20. The
  two are presumably at different oversample caps, but I could not find the
  cell the twenty comes from.
- **"0.28 → 0.10 → 0.02"** (L1127) as recovery across 35–39 / 40–49 / 50+ —
  matches no table in the report and no dump I opened.
- **"the worst-validity band in the corpus"** (L1072) — no validity-by-band
  table exists anywhere in the report.
- **"+1.01 points [−0.90, +2.91]"** serving as both a difference-in-differences
  (L607, entry 22) and a T=0.3 effect on the 50+ capacity gain (L1324). If
  these are one measurement, the report should say which it is.
- **§5.9's ranking table** has no model, protocol, k or n, so its five rows
  cannot be located in any dump.

---

## 6. Suggested cheap additions

All of these are re-analyses of data already on disk, so **free** unless
marked otherwise. I have listed them in the order I would do them.

1. **Score the six registered intervals that were never measured.** *(Free —
   one `band_analysis.py` invocation on an existing dump.)*
   `final-run-plan.md` §4b registers rec@60 and struct@60 for 50–54, 55–59 and
   60–64 and calls them "the registration **of record** for large molecules";
   `job4_scored.json` contains only the pooled `50+` rows, because
   `b50_full_6p.json` was computed with the default band list
   (`DEFAULT_BANDS` in `scripts/band_analysis.py` has no 50–54/55–59/60–64).
   The 94 MB per-query dump is still there
   (`results/overnight9/outcomes_50plus_full_6p/small_full_6p.jsonl`), so
   `band_analysis.py --bands 50-54,55-59,60-64,50+` followed by
   `score_job4.py` would complete the registration score. This would turn
   "9 of 20" into a full reckoning, and it would also test the report's
   directional claim at the one place it matters most — the far end of the
   cliff, where f′ and g′ both halve (§5.7).
2. **Add the ninth cell to §5.4's crossover table.** *(Free — already computed.)*
   `step_curve_pair_30plus.json` holds `break_even` per band for the final
   model (55,271–121,634 queries). Four numbers, and they change the report's
   one actionable recommendation (major point 7).
3. **Give the Poisson comparison its own column in §5.13.** *(Free — in
   `budget_curve_full_6p.json`.)* Printing measured recovery against Poisson
   recovery for all six bands both fixes blocker 3 and makes the concentration
   mechanism visible as a size-switched effect rather than an assertion. Six
   rows, two columns.
4. **Report mean best Tanimoto among misses per band for the final run.**
   *(Free — in `miss_anatomy_full_6p.json`.)* 0.749 / 0.798 / 0.778 / 0.855,
   with `fraction_of_misses_above_0.9_tanimoto` at 0.172 / 0.240 / 0.216 /
   0.577. This is the correct replacement for the 0.976 claim (blocker 1), and
   the fact that the *proportion* of near-miss failures rises with size while
   recovery falls is a genuinely interesting number the report does not have.
5. **Add a `c ÷ b` row to §5.13's exponent table.** *(Free — in
   `step_curve_pair_30plus.json`'s `break_even` block.)* Tests §5.3's "3.1×
   steeper" headline on the ninth cell (it comes out 2.25–2.90). Minor point 15.
6. **Add a convention/ranking column to every band table.** *(Free, editorial.)*
   §7.2 records that the convention collision has been caught five times, the
   fifth in a draft of this report. The structural guard the report says it
   lacks is cheap here: make convention and ranking columns of the tables rather
   than prose in the captions. It would have caught the §1.4-vs-§5.13 mismatch
   in major point 2 before a reader did.
7. **One combined before/after figure for the size cliff.** *(Free —
   `plot_size_cliff.py` already exists and `docs/images/` already holds
   `size-cliff-light.png`, referenced from `README.md` L243 but from nothing in
   the report.)* The report is 1,588 lines of prose and tables with no figure at
   all; the one plot the project already made is exactly the thing §1.3, §5.12
   and §5.13 each describe in words. Dropping it into §5.12 costs nothing.
8. **The only item with real cost: a validity-by-band table.** *(Free if
   validity is in the existing dumps — the per-candidate records carry
   `"valid"`, so it is a pass over
   `results/overnight9/outcomes_*/small_full_6p.jsonl`, a few minutes of CPU, no
   GPU.)* §5.10 asserts 50–64 is "the worst-validity band in the corpus" and
   §5.11 quotes two whole-protocol validity figures, but the report has no
   validity-by-band numbers anywhere, and validity is the mechanism §5.10's
   cancellation argument turns on.

---

## 7. Verdict

**Major revision.**

The report is close to very good, and nothing I found requires new compute or
threatens the project's central results — the size cliff, its combinatorial
rather than informational cause, the budget power law, the step law's bend, the
consensus-ranking result and the methodological ledger all survive scrutiny and
mostly reproduce exactly from the saved dumps. But four statements in the
Summary and Findings are contradicted by the report's own §5.13 or by data
already on disk, and two of them ("even the misses are near misses" against
§5.12's "Not near-misses"; "concentrated on fewer queries than chance in every
band" against a dump that shows the opposite in five bands of six) are
load-bearing for the explanation the report calls its most useful finding. On
top of that, the headline first-guess number is quoted in a ranking the project
does not use and never says so, which is a 16-point understatement in the one
figure a reader will remember. Those are not polish; a careful first-time reader
will find them and will stop trusting the rest. The remedy is a pass that
re-reads §1 and §5.1–§5.12 against §5.13 and retires what the final run broke,
plus three or four definitions the document currently assumes (`f` and `g`, the
additive law, "the size defect", one name per protocol). That is a day's work
with no GPU, and the result would deserve acceptance.
