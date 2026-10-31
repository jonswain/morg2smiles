# Reviews

Three rounds of blind peer review of [report.md](../report.md), run after the
experiments were complete. The report was written by someone with total
familiarity with the project, which is the one reader whose judgement of
"is this understandable?" is worthless. So it was given to reviewers with no
prior knowledge of it.

Each reviewer saw the repository for the first time, was asked to prioritise
comprehensibility for a first-time reader, could check any claim against the
dumps in `results/`, and could not modify anything. Rounds 1 and 2 are
independent cold reads; round 3 is the original reviewer returning to judge
whether its points were genuinely addressed.

| round | review | author response |
|---|---|---|
| 1 | [round-1-review.md](round-1-review.md) | [round-1-response.md](round-1-response.md) |
| 2 | [round-2-review.md](round-2-review.md) | [round-2-response.md](round-2-response.md) |
| 3 | [round-3-review.md](round-3-review.md) | [round-3-response.md](round-3-response.md) |

[open-points.md](open-points.md) is the running register: every numbered point
from every round, its severity, and whether it was fixed, rejected with a
reason, or is still open. It is the check that nothing raised in one round is
quietly lost in the next.

## Why these are in the repo

The same reason `retractions.md` and nine night logs including the wrong turns
are. The report's quality is otherwise an assertion; with the reviews beside it,
it is auditable. Round 1 found four blocking errors, three of them statements in
the Summary that the project's own final run had falsified and nobody had gone
back to retire — and one genuine scientific gap, six pre-registered intervals
that were never scored because the scoring tool's default arguments did not
contain them. That gap is now [retractions.md](../retractions.md) entry 29.

## What three rounds actually showed

Blockers went 4 → 3 → 0 and the verdict went major → major → minor revision, but
the interesting number is not the trend. **Two of round 2's three blockers were
defects the round-1 revision introduced**, and round 3 reported that three of
its eleven new points were defects round 2's revision introduced. Each pass
removed more errors than it added, but it did add them — including, once, the
project's signature convention error, committed in the same commit that
documented it as having happened five times.

Round 3 drew the right conclusion: `check_md.py` guarded the document's
references and nothing guarded its arithmetic. So the exercise ends with
`tests/test_report_figures.py`, which recomputes every load-bearing figure from
the dumps and fails if the prose disagrees. It caught a rounding error on its
first run. That guard, not the three reviews, is what makes the next edit safe.
