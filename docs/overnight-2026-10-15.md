# Night 4 — 2026-10-15 into 2026-10-16

Executes the "new, and cheap" section of
[night 3's revised plan](overnight-2026-10-14.md): ship the consensus-ranking
result, then measure the one thing whose absence limits every comparison in
this repository — single-run training variance.

```
stage 0  consensus ranking shipped, dumps re-scored      18:26 -> 18:35
stage 1  decode sweep on small_1m (disjoint tuning set)  18:35 -> __:__
stage 2  variance seed 1, 8,508 steps                    __:__ -> __:__
stage 3  variance seed 2, 8,508 steps                    __:__ -> __:__
stage 4  variance seed 3, 8,508 steps                    __:__ -> __:__
stage 5  score all three on the common protocol          __:__ -> __:__
stage 6  verify the swept decode setting                 __:__ -> __:__
```

---

## Stage 0 — consensus ranking, shipped and generalised

Night 3 found that ordering a query's candidates by how many distinct SMILES
spellings the model gave each molecule lifts `small_1m`'s `rec@1` from 0.5302 to
0.7520. That was one model, measured by an analysis script. Two things were
needed before it could be believed or used: it had to hold for more than one
checkpoint, and it had to live in the library rather than in `scripts/`.

### It holds everywhere

`scripts/rerank_dumps.py` re-reads the candidate dumps from night 3 and
re-scores them under both orderings. Nothing is re-sampled; the candidate sets
are exactly those of the common protocol, and only the order changes.

| run | rec@20 | rec@1 generation | rec@1 consensus | Δ | struct@1 gen | struct@1 con | rec@20 consensus |
|---|---|---|---|---|---|---|---|
| `small_100k_3ep` | 0.0603 | 0.0046 | 0.0235 | +1.89 | 0.0041 | 0.0220 | 0.0608 |
| `medium_1m` | 0.2822 | 0.0527 | 0.1600 | +10.74 | 0.0506 | 0.1564 | 0.2832 |
| `count_fp_100k` | 0.5890 | 0.1687 | 0.3727 | +20.40 | 0.1651 | 0.3661 | 0.5920 |
| `small_100k` | 0.5982 | 0.1800 | 0.3793 | +19.94 | 0.1748 | 0.3681 | 0.5992 |
| `small_1m_matched` | 0.6324 | 0.2091 | 0.4407 | +23.16 | 0.2025 | 0.4310 | 0.6401 |
| `small_full` | 0.7403 | 0.3113 | 0.5700 | +25.87 | 0.3001 | 0.5573 | 0.7444 |
| `small_100k_long` | 0.8446 | 0.4519 | 0.6764 | +22.44 | 0.4284 | 0.6529 | 0.8476 |
| `small_1m` | 0.8947 | 0.5302 | 0.7526 | +22.24 | 0.5087 | 0.7249 | 0.8962 |

**Every competent model gains between +10.7 and +25.9 points of `rec@1`**, and
the one model that barely gains — `small_100k_3ep`, at +1.9 — is the
pre-competent one from night 3, which has no confidence to express. This is a
property of the task, not of a checkpoint: a model samples its best answer by
several routes, and generation order throws that signal away.

The gain does not grow monotonically with model quality, which is worth noting
because it would have been the tidier story. It rises from `medium_1m`'s +10.7
to a plateau around +20 to +26 and then flattens; `small_1m`, the strongest
model, gains slightly *less* than `small_full` and `small_1m_matched`. Consensus
ranking is most valuable in the middle of the quality range, where the model
knows the answer but does not put it first.

### `rec@20` moves too, and legitimately

Consensus ordering also lifts `rec@20` by +0.05 to +0.77 points. That needs
justifying, because `rec@20` was supposed to be insensitive to order.

It is sensitive because the top-up fix from night 3 draws **more than 20**
distinct candidates for most queries — 18.9 on average for `small_1m`, up to the
cap. Ranking therefore decides *which* 20 go to the oracle. That is legitimate
under this project's own definition of the budget: the k budget is oracle
queries, and spelling counts are free — they are already in the samples and need
no forward pass. A real system would spend its 20 oracle calls on its 20
most-confident candidates, which is exactly what consensus ordering does. It
recovers part of night 3's `beyond_budget` bucket (18 queries where a correct
candidate was drawn but ranked outside the window).

### What shipped

- `QueryOutcome.spelling_counts()` and `QueryOutcome.scored_by_consensus()`.
- `recovery_at_k` and `structure_accuracy_at_k` take an `order` argument.
- Every report now carries `recovery_at_k_consensus` and
  `structure_accuracy_at_k_consensus` **beside** the generation-order fields,
  which keep their meaning, so numbers measured before this change stay
  comparable with numbers measured after. `primary_metric` is untouched.
- `Morg2Smiles.generate` sorts by `(fp_match, votes, tanimoto)`. `fp_match`
  stays on top — an exact hit is the answer, and the oracle is free to a caller
  who holds the query fingerprint — with consensus as the tiebreak inside each
  group where the oracle cannot discriminate.
- Nine tests, including that the two orderings agree once k covers the budget,
  that ties do not reshuffle generation order, and that the headline metric is
  unchanged.

---

## Stage 1 — decode sweep

_pending_

## Stages 2–4 — training variance

_pending_

## Stage 5 — the variance result

_pending_

## Stage 6 — verifying the swept decode setting

_pending_
