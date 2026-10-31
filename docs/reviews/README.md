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
