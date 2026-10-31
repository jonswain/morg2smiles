# Author response to round 2

Reviewer verdict: **major revision**, 3 `blocker`, 12 `major`, 2 `minor`, plus
20 line edits and a comprehensibility log. A second reviewer, no knowledge of
round 1, `docs/reviews/` off limits.

**Two of the three blockers are defects I introduced while fixing round 1.**
That is the finding of this round and it is worth stating before the table.

- **I committed the convention collision while documenting it.** Round 1's
  blocker 2 was that the headline `rec@1` was in the unranked generation order.
  My fix put consensus and generation side by side in one table — and paired a
  **molecule-budget** `rec@1` (0.8591) with a **raw-slot** `rec@60` (0.9496),
  then subtracted 85.9 − 69.6 across conventions to get "16 points". The honest
  figure, within one convention, is **70.7 → 85.9, a gain of +15.3**. This is
  the error §3.7 exists to prevent and §7.2 had just been updated to say had
  been caught five times. **It is now six, and the sixth was committed in the
  commit that recorded the fifth.**
- **I retracted a number in one section and left it asserted in another.**
  §5.13 explains at length why no "fiftyfold" ratio is defensible and says the
  figure "traces to nothing". §1.3 went on saying the cliff was "pushed back
  roughly fiftyfold". A reader meets the claim in the summary and the retraction
  1,250 lines later.

Round 1's reviewer had suggested, as cheap addition 6, making convention and
ranking **columns of every table** rather than prose in the captions. I recorded
that as "done for every table I touched" and then built a new table without
them. The structural fix was proposed, acknowledged, and not applied; the error
it was designed to prevent occurred immediately. That is now the headline of
`round-2` in the register, and the convention is a column in the §1.3 table.

I verified all three blockers and all twelve majors against the dumps.
**I rejected one in part, with a reason; everything else is accepted.**

## Blockers

| # | point | status | what changed |
|---|---|---|---|
| 1 | §1.3's headline table mixes conventions within a row; "16 points" is a cross-convention subtraction | **accepted** | Verified: molecule budget gives generation 0.7066 and consensus 0.8591 on the same dump, a gain of **+15.25**. The table now has an explicit **convention column**, three rows (budget/consensus, budget/generation, raw-slot/generation), and states the gain within one convention. The glossary's propagated "16 points" is fixed too. |
| 2 | "Tanimoto" is never defined, yet carries §5.12's central negative result | **accepted** | Glossary row added under "The task", defining it 0–1 and saying explicitly that it is never the correctness criterion — the oracle is — which also sets up §2.3's "smooth, flattering and lagging". |
| 3 | the retracted "fiftyfold" survives in §1.3 | **accepted** | Replaced with the measured statement (`rec@60` at 50–64, 0.2251 → 0.7402). I also grepped for other surviving ratios of two extrapolations; there are none. |

## Major

| # | point | status | what changed |
|---|---|---|---|
| 4 | `b` 0.144–0.396 attributed to "eight cells"; it is one cell's band range. And §5.5's invariant is measured at 35+ only | **accepted, both** | Verified against §5.2's table and `overnight-2026-10-17.md` L1056. §1.3 now says "across the size bands of the cell it was first fitted on"; §5.5 now says "read at 35+ heavy atoms". |
| 5 | §5.12's final-run Tanimoto triple skips a band, and its monotonicity is an artefact of that | **accepted** | Verified 0.7494 / 0.7976 / 0.7782 / 0.8550. All four bands now given, with "not monotone in between" said plainly. |
| 6 | "near-miss share rises with size" is not monotone | **accepted** | 17.2 / 24.0 / 21.6 / 57.7. Rewritten to "much higher at the top than the bottom … rises overall but not monotonically". |
| 7 | the most-quoted cliff numbers rest on n=54 and n=41 with no n, cell or protocol | **accepted** | Both now name the cell, the protocol and both sample sizes, and say to read them as shape rather than estimate. The reviewer also caught that the 0.366 band is labelled **50–69** in its source, not 50–64; corrected. |
| 8 | "the full-k rate is 1.000 in every band" is true in raw slots and misleading in the adopted convention | **accepted** | Verified `budget_filled_rate` = **0.4623**, 28.7 distinct valid molecules per query, 90% duplicate rate. The bullet now gives both and draws the better conclusion: the model is not short of slots, it is short of *distinct ideas* — the concentration result from the supply side. |
| 9 | "about twenty slots" is a k=20-era figure presented as general | **accepted** | Now names the k=20 cells it characterises and gives the final run's 28.7 beside it. |
| 10 | the registration tables name no convention, and sit next to a table declared raw-slot | **accepted** | Both now say "molecule budget", and the new registration inventory states that the registration tables and the before/after table are in different conventions by design. |
| 11 | the `c` per-band targets are unsourced and inconsistent with §5.3 | **accepted** | They trace to `final-run-plan.md` §8 — "the 2×2's k=60 column". The row now names that cell and k inline, so the 2.11× conclusion can be checked. |
| 12 | the glossary gives +22 and 16 points for the same effect | **accepted** | Now "+22 on the cell where it was measured (§5.9) and +15.3 on the final run (§5.13); always quoted against a named cell". |
| 13 | §3.8/§3.9 use four statistical terms and the night numbering before either is introduced | **accepted in part** | Added a four-row **Statistics** block to the glossary: discordant pair, paired/McNemar SE, between-seed sd, difference-in-differences. **Declined** the second half — moving §4's session table ahead of §3, or dating every "night N" mention. §4 sits where a reader expects the programme narrative, and the sessions are numbered in date order so "night 7" before §4 costs a reader little. Noted as a judgement, not a disagreement about the facts. |
| 14 | "entry N" is never introduced | **accepted** | One clause in the authority table: "Cited throughout as **entry N**, meaning row N of that table." |
| 15 | the five pre-registrations are never enumerated, so "9 of 26" cannot be checked | **accepted** | New table at the head of §5.13: each registration, what it predicted, how many band × metric intervals it unfolds into, how it was scored. 1 + 8 + 14 + 4 = 26, with the verdict split **9 HIT / 13 MISS HIGH / 4 MISS LOW** now printed. |
| 16 | §5.9's seed-pooling gain omits its 3× cost, beside a result that genuinely costs nothing | **accepted** | Cost stated, and contrasted with the temperature vote that survives cost-matching. |
| 17 | §5.11a's placement and its self-diagnosing opening | **accepted in part** | The opening no longer admits to being out of order; the section now begins with what the intervention *is*. **Declined the renumber**: promoting it to §5.12 would shift §5.12 and §5.13, changing two heavily-cited anchors and about forty cross-references across five files, to fix something the reviewer rated `minor`. The cost/benefit is wrong and the risk of a silently broken reference is real. |

## Line edits

All twenty accepted and applied, including: the cut-factor mismatch in the
crossover range (55,271 is a ×0.5 figure and 121,634 a ×0.75 — now quoted as
"about 60,000, both for a halving"); `small_full_6p` at 25.36 vs 25.46 h
(the leaderboard says 25.46, now used in both places); §10.1's total reconciled
to the ledger's 118.73 h with the two aborted `small` re-runs footnoted;
0.7520 → 0.7526 for `small_1m`'s consensus `rec@1`, which also makes the gain
+22.24; the "0.90–1.37 s/step" explanation corrected (0.90 is a within-run epoch
minimum, not a shard rate); headers added to three unnamed table columns; the
30–34 row added to §5.4; "all" clarified as 30+ in §5.6; the 100k shard named on
§5.3's segment table; `structure@60` standardised to `struct@60`; the 60+ dead
claim rephrased so it no longer reads as refusing a true statement; a duplicated
clause in §3.1 cut; `base_1m` labelled as the largest config; and a section
reference added to all eleven rows of §6 so the dead-claims table is usable.

## One number removed rather than fixed

The reviewer could not trace "**1.46% of distinct atom environments**" (§2.1).
Neither could I: it appears in `README.md` and `report.md` and in **no dump, log
or results file**. It is a descriptive claim about folding loss that nothing on
disk supports, so it is gone from both documents, replaced by the figure that
*is* measured — 950,967 molecules producing 943,177 distinct fingerprints.

The reviewer also flagged the `c` targets (traced, see major 11) and the test
count (correct; `click` was unavailable in the reviewer's environment, so it
could not run pytest).

## Cheap additions

Nine suggested, all free. Done: the two-convention headline table (blocker 1),
the registration inventory (major 15), the molecule-budget budget-fill row
(major 8), the `b`-by-band comparison across cells (already added in round 1 as
the band-structure caveat). Still open: the `preimages_per_hit` column
(1.66 / 1.83 / 2.29 / 3.54), which would strengthen §5.13's concentration table.
Carried into the register as `open` alongside round 1's two deferrals.

## What this round cost and bought

No GPU. Two self-inflicted defects caught — one of them the project's signature
error, committed in the act of documenting it — and roughly fifty sourcing,
convention and definition fixes. The lesson I take is the one round 1's
reviewer offered and I did not implement: **conventions belong in table columns,
not in captions or in the author's memory.**
