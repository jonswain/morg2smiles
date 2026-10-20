# Retractions

Every claim this project published and later withdrew, what killed it, and what
it cost. The list is long on purpose: the pattern in it is the most transferable
thing here, and three of the entries below were found only because the number
had been written down before the run that broke it.

The ledger is chronological within each theme, and each entry names the
document where the claim and its correction live.

---

## The corpus axis, which went wrong four times

| # | the claim | what killed it |
|---|---|---|
| 1 | **"10× data is worth +30.4 points of rec@20"** — night 1's headline | The comparison was 100k at 8,508 steps against 1M at 21,117. Night 2's controls found **+24.9 points from compute alone** on a fixed 90,682 molecules, so the attribution was wrong regardless of how the remainder divides. |
| 2 | **`rec@20` 0.993 at PubChem scale** (night 1), and the **0.949** that replaced it (night 2) | The first was compute wearing data's label; the second rested on a two-point fit that a third point broke. Both withdrawn, with no defensible corpus-direction scaling law left behind. |
| 3 | **"1.39× per decade of data"** | Registered a prediction of rec@20 0.705 for `small_1m_matched` before it ran. Measured **0.6299** — 7.5 points low, outside the band. Returns in the corpus direction are not log-linear at fixed steps, because corpus size cannot be isolated at fixed steps at all. |
| 4 | **"These models were under-trained, not corpus-limited"**, at 17:1 steps-to-corpus (block 1, weekend) | A third corpus point made the axis convex: 17:1 holds on the segment block 1 happened to measure, and past 900k molecules it is **2.1:1**. The claim was read off the flat part of a convex curve, without knowing the curve was convex. |
| 5 | **"The second corpus segment is 8.4× steeper"** (stage 9, same weekend) | True of the observable and badly overstated as a statement about data. At constant steps a corpus doubling is a passes halving, so the observable is a small difference of two large numbers; decomposed, f′ rises only **1.4×** while the net rises 8.4×. Most of the convexity was a near-cancellation amplifying a mild one. |

## The size cliff, and what fixes it

| # | the claim | what killed it |
|---|---|---|
| 6 | **"The novel-scaffold penalty halves with 10× data"** | The correction inverts the ranking: the **lowest** penalty of the three strong runs belongs to `small_100k_long`, which has the least data. On an identical 90,682 molecules the penalty fell 12.7 → 4.2 points with nothing changed but training length. |
| 7 | **"Extra data bought confidence, not diversity"** | With five runs instead of two, distinct molecules per query falls monotonically as recovery rises, whatever bought the recovery. A property of model quality, not of data. |
| 8 | **"Capacity fixed the size defect"**, and later **"the budget-curve exponent is a property of capacity"** | Neither comparison varied capacity. The first was an attribution error corrected on the front page; the second compared two checkpoints of the *same* architecture, and the exponent turned out to be training length — four parts length to one part corpus. |
| 9 | **"The decoder needs a size token"** (item 2b, night 5) | Retired before it was built. At k=60 the truncation is 5.1 atoms rather than 10.7, 89.8% of 50+ queries get a right-sized proposal, and the closest proposal is within 0.2 atoms of the target in every band. The defect was a property of a 100k-parameter checkpoint at a 20-slot budget, not of the problem. |
| 10 | **"Successive samples are independent draws"** | The factorisation predicted rec@100 ≈ 0.66 at 35+; the measured deficit is a power law in k with a size-dependent exponent, and the decoder keeps re-proposing from the same shrinking neighbourhood. Arithmetic that happened to fit at k=20. |
| 11 | **"Validity is what holds large molecules back"** | Cooling to T=0.3 at 50+ raises validity by 6.6 and 2.8 points and recovery nets **zero**: the invalid strings it removes are replaced by valid wrong answers. |

## Nulls that were not nulls

| # | the claim | what killed it |
|---|---|---|
| 12 | **"Count fingerprints make no difference"** (p = 0.32, common protocol) | The common protocol is 63% molecules under 30 heavy atoms. Re-scored on the large protocol, counts are **4.18 points worse** over 2,321 queries. The null was hiding a loss. |
| 13 | **"Capacity buys nothing at 50+ heavy atoms"** (127 queries) | On a dedicated 893-query protocol the gain is **+3.70 points** (+4.48 in the molecule-budget convention), with structure accuracy moving more than recovery. |
| 14 | **"Capacity's cut is uniform across size"** | The cut declines from **25.4% at 30–34 to 3.9% at 50+**. The uniform-cut reading survived four cells and died on the fifth. |
| 15 | **"The 60+ band needs a larger sample"** | It needs a larger *corpus*, and there is none: `prepare.py` caps heavy atoms at 64 and every shard used the default, so the largest clean pool is 308 molecules against a fourfold power requirement. Closed as unanswerable rather than open. |

**Two nulls in this project have been called on roughly 130 queries and both
were overturned by enlarging the sample.** A discordant-pair count in single
digits is not evidence of absence, however good the p-value looks.

## Measurement infrastructure that was quietly wrong

| # | the fault | what it cost |
|---|---|---|
| 16 | **Deduplication by string** | Inverting aspirin reported "18 of 20 exact matches" that were 18 spellings of one molecule. One slot now buys a distinct *molecule*. |
| 17 | **`oversample=2.0`, calibrated on the 100k model** | Better models explore less, so a constant oversample handed the **stronger** model fewer effective candidates: 12.6 distinct molecules of a 20 budget against the weak model's 21.3. Every cross-run gap was understated, and the headline was pessimistic. |
| 18 | **The 10k-shard ambiguity table** | Two conclusions drawn from 11,669 molecules — that the fingerprint essentially always determines the molecule, and that counts carry no extra information — are both wrong on the corpus the models are trained on. Ambiguity is **30×** higher on the 1M shard and counts cut it **5.6×**. |
| 19 | **`max_hours` measured the wrong clock** | Built on `perf_counter`, which is right for per-step rates and wrong for a wall-clock brake, so the cap measured the wrong quantity from the moment it was written. |
| 20 | **A void step-exponent pre-registration** | The prediction was computed in one recovery convention and the run scored in another; only one of two scripts caught it. |
| 21 | **Unseeded evaluation** | Two evaluations of the same checkpoint differed by 2.2 points, about 1.4 standard errors at n ≈ 1000. |
| 28 | **"Nothing above 64 heavy atoms exists in ChEMBL 35 as standardised here"** — the premise item 3 of the closing plan rested on | Circular: the standardisation *is* the cap. Measured on the raw chemreps file, **2.558% of ChEMBL 35 is above 64 heavy atoms**, about 63,000 molecules tailing to 508. The decision it supported (keep the cap) survived re-derivation, but on a different and better reason — `max_tokens: 128` binds first, and 73.0% of the molecules the atom cap discards exceed the decoder's context anyway, leaving a yield of 0.87%. A conclusion reached from a false premise is not a conclusion. |

## Registrations that were mis-specified rather than wrong

| # | the fault | what it cost |
|---|---|---|
| 22 | **Three branches separated by less than the noise** (stage 12, weekend) | The registration fired FALSIFIED HIGH on a difference-in-differences of **+1.01 points [−0.90, +2.91]** — indistinguishable from zero. Two of the three branches were inside the paired SE before the run started. |
| 23 | **A prediction computed for one model and registered on another** (stage 12, night 5) | The two accounts' constants came from the 100k arm while the run specified `small_1m`, so the registration was void before the GPU started. The run was still informative; the registration was not. |
| 24 | **A metric chosen on its error bar alone** (the 30–39 band) | It did not clear, because three fifths of it is molecules that do not respond. An error bar is a necessary condition for choosing a metric, not a sufficient one. |
| 25 | **A result quoted at a temperature the project no longer uses** | The size mix's exchange rate was 2.3 small molecules per large one at T=1.0 and **1.28** at the adopted T=0.6, with the whole-protocol penalty falling from −1.13 points to −0.28. The only case where a stale setting made a result look *worse* than it is. |
| 26 | **Registered intervals that did not tile the line** (item 1, night 7) | The registration assigned 0.76–0.82, 0.86–0.92, an "uninformative" 0.82–0.86 and a third branch below 0.72 — leaving **0.72–0.76 unassigned**, which is where the result landed (0.7553). The verdict was clear anyway, but it required a judgement made after seeing the number, which is the thing a registration exists to prevent. "Flat if below 0.82" would have cost nothing. |

## The claim this ledger's method killed on schedule

| # | the claim | what killed it |
|---|---|---|
| 27 | **"f′ rises 1.4× along the corpus axis"** — the last live piece of the convexity story | Measured directly at constant passes: **+22.09** points per doubling on the 900.9k → 1.88M segment, against the +35.03 the decomposition inferred for it. The inference overstated it by 13 points, 60% of the measured value. Registered as an interval beforehand, and the convex branch missed by twelve standard errors. The near-cancellation half of §2.9 survives; the convexity half does not. |

---

## The pattern

Twenty-eight entries, five causes:

1. **Cross-run comparison.** Every claim that broke in the first two nights was
   a comparison *between* runs; every claim that survived was measured *within*
   one. Later nights broke the same way whenever two things moved at once.
2. **A constant calibrated on one run, applied across runs.** Entries 17 and 20
   are this, and so is 25. The constant is usually invisible in the result it
   distorts.

   Entry 20's specific form — a prediction computed in one recovery convention
   and scored in another — has now been caught four times, and night 7 found
   the structural reason it recurs. `compare_checkpoints.py` computes
   `ks = [n for n in (1, 5, 20, 100) if n <= eval_k]`, so an `--eval-k 60` run
   reports rec@1/5/20 *under a 60-slot budget* and **never prints rec@60**.
   Every rec@60 in this project therefore comes from a second tool, and the two
   tools do not share a convention. Scoring night 7's registration against the
   wrong one of them inflated f′ by 4 points and would have read as a cleaner
   CONFIRMED than the truth.
3. **A metric averaged over a population that does not respond.** Entries 12,
   13 and 24. The common protocol is 63% small molecules and cannot describe
   anything acting on part of the size distribution.
4. **Point-estimate registrations of noisy quantities.** Entries 22 and 23.
   Register the interval. Entry 26 is the refinement: adjacent intervals have
   to tile the line, or scoring still needs a judgement made after the fact.
5. **A premise that restates the design.** Entry 28 — "nothing above 64 heavy
   atoms exists in ChEMBL as standardised here" — was true only because the
   standardisation imposed the cap, and it was load-bearing for a decision
   about whether to change the cap. The tell is a premise about the data whose
   evidence is a config default. Check it against the raw file; it took one
   120,000-row sample to find that 2.6% of ChEMBL lives above the line.

And one thing that worked, repeatedly: **writing the number down before the run
that produced it.** Entries 3, 10 and 13 were caught *because* a prediction was
on record and failed. A two-point slope reported as a law was about to go out
with a PubChem extrapolation attached; the registration is what turned a repeat
of the previous night's mistake into a result.

Entry 27 is the clearest case: f′ was written down as an inference, labelled in
`results.md` as *the most load-bearing unverified number in this project*, and
given a run designed to kill it. It died. A number carrying that label and no
scheduled test is the thing to look for in any project that keeps a ledger like
this one.
