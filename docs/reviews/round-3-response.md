# Author response to round 3

Round 1's reviewer, returning with round 2's full review in hand to adjudicate
both rounds. Verdict: **minor revision** — the first round not to return "major".

Its adjudication: **24 of 33 numbered points resolved** (16 of 16 from round 1,
14 of 17 from round 2), **both declined points judged justified**, **8 rows
still standing**, and **3 new majors plus 8 minors**.

Everything it raised is accepted and fixed. There is nothing in this round I
pushed back on.

## The pattern it named

> "Three of my eleven new points are defects the round-2 revision *introduced*,
> the same pattern round 2 found in round 1's revision. What the process needs
> next is not another reviewer but a numeric proofread of every changed figure
> against its dump — `check_md.py` guards the references; nothing guards the
> arithmetic."

That is the correct diagnosis and it is the most useful sentence in three rounds
of review. Every round found arithmetic defects, and every round's *fix* for
them introduced more. Reviewers do not scale; a guard does.

So the substantive output of this round is not the edits — it is
**`tests/test_report_figures.py`**, 22 tests that recompute every load-bearing
figure in the report from the JSON dumps and assert the document states it. It
pins both conventions wherever a figure has two, asserts the retracted numbers
(`fiftyfold`, `1.46%`, `9 of 20`, "even the misses are near misses") do not
reappear, and fails if a dump moves without the prose moving with it.

**It caught a defect in its first run.** The 50–64 mean Tanimoto among misses is
**0.8550**, exactly on the two-decimal rounding boundary: round 2's reviewer
wrote 0.86, I wrote 0.86, and Python renders 0.85. The report now quotes three
decimals — 0.749 / 0.798 / 0.778 / 0.855 — and says why.

## New points

| # | point | status | what changed |
|---|---|---|---|
| 1 | §1.4 says "eleven misses outside the 50–64 instrument, ten run with size"; `job4_scored.json` gives **nine and eight** | **accepted** | Verified: 17 misses total, 8 inside registration (2), 9 outside, of which 8 run with size. Round 1's revision had this right and my round-2 rewrite for §1.4 broke it. Now nine and eight, with the arithmetic shown, and pinned by a test. |
| 2 | the `c` per-band targets are now sourced to the **wrong cell** | **accepted** | Verified: 1.092 / 1.083 / 0.770 / 0.381 is the `k60` column of `results/overnight6/step_curve_100k.json`'s pair — the 100k shard's **step pair**, which is §5.3's — not §5.8's 1M capacity 2×2. Its all-slice 0.911 is §5.3's segment-1 `c` of 0.9113, which confirms it. The reviewer is right that a wrong pointer is worse than none when the 2.11× conclusion rests on the column. Corrected and cross-referenced to §5.3. |
| 3 | round 2's comprehensibility log was never tracked and is largely unaddressed | **accepted** | True, and the register's own standard says that means it was lost. Of the ~27 terms, 3 had been promoted to blockers and fixed; the rest were not. Now defined: `top_p`, "arm", "rung", "prefix-to-prefix", "truncation" (glossary); "teacher-forced", MPS, `RUNS`, OPSIN, "the closed 2×2", "beats original", "the remaining 10.5%" (inline at use). A register row now exists. |

Minors, all applied: "four-tenths at `rec@60`" was **0.86** points (fixed, and
the gap now quoted against a named cell in §3.7, since it depends on how often
the model fills its budget); §1.3 and §5.12 disagreed on 50–69 versus 50–64 for
the same number (the source bins it 50–69, now said in both); the consensus
`rec@60` of 95.8% was **asserted, not measured** — now measured at **0.9586**
against generation's 0.9582, so ranking moves it by +0.04 points rather than the
zero I claimed, because 46% of queries fill the cap; §2.1's replacement for the
deleted 1.46% was circular (now gives the 1.4% non-unique share and says
explicitly that the folding/degeneracy split is not measured here); §5.4 had
reintroduced the mixed cut-factor range (now compares halving with halving); two
protocol aliases survived in a sentence that was describing the aliases.

## The two declined points, re-examined

The reviewer judged both rejections justified and verified my cost claim on
R2-17 independently — §5.12/§5.13 and their anchors occur ~167 times across
`docs/`. On R2-13b it split the difference and was right to: declining to move
§4 ahead of §3 is justified (§4 depends on §3's vocabulary), but declining to
help the reader with "night N" was reasoning from my knowledge rather than
theirs. Its own fix is lighter than round 2's — one forward pointer at the first
occurrence instead of dating every mention — and that is what I have done.

## Still open, deliberately

**R1-A8, a validity-by-band table.** Three rounds have now asked for it. §5.10's
cancellation argument turns on validity and the report has band-level figures
for nothing else. It is a few minutes of CPU over the existing dumps, not free,
and it is the one outstanding item. Recorded as `open` rather than quietly
dropped — which is the register's whole purpose.

## Also in this round

The table of contents the author was asked for, with internal links to all 54
headings — **generated from the headings** and asserted by a test to match them
exactly, anchor by anchor, using the same slug function `check_md.py` validates
links with. A hand-maintained contents list in a 1,900-line document that four
rounds of revision moved sections around in would be wrong within a week.
