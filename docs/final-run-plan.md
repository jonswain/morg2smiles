# The final run — plan, as of 2026-10-26

Item 4 of [next-steps-2026-10-19.md](next-steps-2026-10-19.md) is the last GPU
job in the project. Items 1, 2 and 3 are closed; item 5 is writing. This
document is the plan for the one run that remains, with every cost re-derived
from the runs on disk rather than carried forward from an earlier estimate.

Three of the last four cost figures in this project were wrong because they
were priced off a cell that differed from the target in shard, fingerprint or
evaluation cadence. So the cost model below is **solved**, not quoted.

---

## 1. Where the four jobs stand

| item | status | where |
|---|---|---|
| 1. f′ at constant passes | **done**, night 7 | f′ = **+22.09** pts rec@60 per corpus doubling (SE 0.89, n = 2,321). Convex branch falsified by 12 SE; `results.md` §2.9 convexity retracted (entry 27). |
| 2. Step saturation, third point | **done**, night 8 | 52,500 steps, rec@60 **0.8789**. Registered 0.88–0.95 → **miss, low by 0.11 pts**. Saturation is real on the *slope*: deficit exponent c falls **0.9113 → 0.7008**. |
| 3. The 64-heavy-atom cap | **decided**, night 7b | Keep 64. The premise was false (2.558% of ChEMBL is above it), and the binding constraint is `max_tokens: 128` — 73.0% of what the atom cap discards exceeds the decoder context anyway. Yield of raising it: 0.87%. |
| 4. The final run | **this document** | 6 passes, 88,218 steps, full shard. |
| 5. The write-up | 5a, 5c, 5e done; 5b, 5d open | `results.md`, `methodology.md`, `retractions.md` exist. README restructure and the guardrail rules remain. |

### The decision rule for item 4 is void, and the budget stands anyway

Item 2 was built to pick this budget: *saturation absent by 52,500 steps → 6
passes; present → 3 passes.* Saturation appeared, which by the letter of the
rule means 3 passes. **The rule does not apply**, for the reason night 8 gives:
on a fixed corpus `steps × batch = corpus × passes`, so item 2's bend was
measured between the **30th and the 74th pass** over the same 90,682 molecules.
This run does 3 → 6 passes over 1,881,996 and never sees a molecule a seventh
time. The bend is 24 passes out of regime.

The in-regime evidence is the 1M-shard pair, and it shows no bend:

| corpus | passes | rec@60 | per doubling |
|---|---|---|---|
| 900,917 | 1.21 → 3.00 | 0.5205 → 0.8427 | **+24.57** |
| 90,682 | 12.01 → 29.81 | 0.4752 → 0.7708 | +22.54 |
| 90,682 | 29.81 → 74.05 | 0.7708 → 0.8789 | +8.23 |

The slope is stable near +23 while repetition is low and collapses only in the
segment that crosses into the dozens of passes. **6 passes.** This is item 2
answering a different question than the one it was commissioned for, which is
worth recording as such rather than as a budget derived on schedule.

---

## 2. The run

8.0M parameters, `data/shards/full`, batch 128, cosine to completion, T=0.6 at
evaluation.

| quantity | value |
|---|---|
| training molecules | 1,881,996 |
| steps per pass | 1,881,996 / 128 = **14,703** |
| passes | 6.00 |
| **max_steps** | **88,218** |
| in-training eval cadence | 8,000 steps (12 evaluations) |
| max_hours | 31.0 — a runaway guard, not a schedule |

### Why cadence 8,000

Cadence buys two things that trade against each other, and `train.py:443` is
why: the stop check — including the wall-clock brake — is evaluated at
`eval_every_steps` boundaries, so **the cadence is also the brake's
resolution.**

| cadence | evals | eval cost | brake resolution |
|---|---|---|---|
| 4,000 | 23 | 1.18 h | 1.17 h |
| **8,000** | **12** | **0.62 h** | **2.33 h** |
| 14,703 (per epoch) | 7 | 0.36 h | 4.28 h |

8,000 is the middle. The registered numbers are read off `band_analysis.py`
against the finished checkpoint, never off the in-training trace — night 8
confirmed the trace and the held-out protocol disagree in *direction* on the
step exponent, and the protocol is the authority — so the trace is worth 0.62 h
and no more.

### max_hours is a guard, not a budget

A run stopped by `max_hours` has an unfinished cosine schedule and **the
pre-registration does not apply to it** (block 1's voided-trace lesson). So
`max_hours: 31.0` sits above the worst plausible completion, and the driver
refuses to start without a **33 h** window rather than starting and hoping.

`max_hours` now measures the right clock — `train.py:404` uses `time.time()`,
so retractions entry 19 is fixed and the brake is true wall clock.

---

## 3. The cost model, solved from the two full-shard cells

Both 8.0M cells trained on `data/shards/full`, from `results/leaderboard.jsonl`:

| run | steps | cadence | evals | total s | all-in s/step |
|---|---|---|---|---|---|
| `small_full` | 8,508 | 1,500 | 6 | 10,203 | 1.1993 |
| `small_full_1p2` | 17,772 | 8,886 | 2 | 18,966 | 1.0672 |

Two equations, two unknowns — per-step cost `a` and per-eval cost `e`. Taking
`small_full_1p2`'s measured final-eval time of 180.3 s:

```
18,966 = a × 17,772 + 180.3 × 2     →  a = 1.047 s/step
10,203 = a ×  8,508 + e × 6         →  e = 216 s
```

**The model is independently confirmed.** The solved per-eval cost of ~216 s
matches the `elapsed_seconds` the leaderboard records for each run's own final
500-molecule k=20 evaluation: 180.3 s for `small_full_1p2`, **224.6 s** for
`small_100k_52k`. The eval cost is a measured quantity, not a fitted residual,
and the two routes agree.

### No thermal drift to budget for

The obvious risk is that 1.047 s/step comes from a 2-epoch run while this one
is 6. Per-epoch rates across night 8's 75-epoch run say otherwise:

| epoch | 1 | 3 | 10 | 25 | 50 | 60 | 71 | 72 |
|---|---|---|---|---|---|---|---|---|
| s/step | 0.904 | 1.055 | 1.133 | 1.209 | 1.048 | 1.039 | 1.023 | 1.018 |

The rate ramps from a warm-up low, bulges to ~1.19 through the middle, and
**settles back to 1.02–1.07 in the late epochs** — the fastest sustained part
of the run is its end. The spikes at epochs 30/35/40/46/51/57/63/68/74 line up
exactly with the 4,000-step eval boundaries and are the eval cost, not
throttling. A long run on this machine does not degrade, so no drift penalty is
warranted. The unexplained mid-run bulge is what the upper bound below covers.

### The price

| component | basis | hours |
|---|---|---|
| training, 88,218 steps @ 1.047 s/step | solved above | **25.66** |
| 12 in-training evals @ ~185 s | measured | 0.62 |
| **training stage** | | **26.3** |
| score large protocol, 30+, k=60, 2,400 queries | night 8 stage 2, 80 min | 1.34 |
| score 50+ protocol, k=60, 1,000 queries | night 7b stage 1, 18 min | 0.30 |
| band tables ×2 metrics ×2 protocols, anatomy, curves | measured, seconds each | 0.11 |
| **scoring stage** | | **1.75** |
| **end to end** | | **28.0** |

**Upper bound.** If the whole run held the mid-run bulge rate — night 8's all-in
1.179 s/step, which is the slowest sustained figure any 8.0M cell has produced —
training is 28.9 h and the job is **30.6 h**.

> ### Is ~30 hours still the estimate?
>
> **Yes as a number to schedule against, no as the centre.** The honest figure
> is **28 h end to end, with a plausible range of 27.5–31 h.** Training alone is
> **26.3 h**, which is close to the 27 h already written into the plan — that
> figure used 1.10 s/step as a "cadence-matched middle" and the solved rate is
> 1.047, so it was slightly conservative and roughly right.
>
> Where 30 h comes from is worth naming, because two different 30-ish numbers
> are in circulation. The plan's original **32.8 h** was priced off `small_1m`'s
> 1.337 s/step — the **1M** shard, not the full one — and is wrong in the way
> night 8 and item 2's launch note both warn about. The **27.0 h** that replaced
> it is right for training and omits scoring. Adding the two scoring protocols
> is what takes it to 28, and the rate uncertainty is what takes the ceiling to
> 31.
>
> Plan the window at **33 h** so the `max_hours` guard never fires on a healthy
> run.

---

## 4. The pre-registration

Three rules from night 5, plus night 7's and night 8's amendments:
register the **interval** not a point; report **per band**; read every size
claim on **structure accuracy** too; and — night 8, entry 26 — **the intervals
must tile the line**, or the verdict is a judgement made after seeing the
number.

### 4a. The headline is not the measurement, and must not be scored as one

Under f′ = +22.09 and g′ = +23.55, the 3-pass full-shard cell lands at
rec@60 ≈ **1.06** whole-protocol. At 6 passes it is further above. **The
all-slice rec@60 saturates before the run finishes**, and a ceiling is where
this project has twice mistaken a null for a result. Report it; do not register
it as the result.

### 4b. The 50+ bands — built, and the registration of record

From [job4_registration.py](../scripts/job4_registration.py) against the three
cells of the 50+ instrument (`small_1m_matched`, `small_full_1p2`, `small_1m`),
in deficit form, on the 893-query draw at k=60. Already on disk as
`results/overnight8/job4_registration_6p_{recovery,structure}.json`:

| band | n | rec@60 | struct@60 |
|---|---|---|---|
| 50–54 | 433 | **0.7325 – 0.7997** | **0.6482 – 0.7222** |
| 55–59 | 257 | **0.5804 – 0.6696** | **0.4979 – 0.5884** |
| 60–64 | 203 | **0.3841 – 0.4785** | **0.2682 – 0.3542** |
| all 50+ | 893 | **0.6310 – 0.6912** | **0.5403 – 0.6025** |

Two things set those widths and both are lessons. **43% of the passes
extrapolation is beyond the measured range** — g′ is read over 1.31 doublings
and the target is 2.31 — so the upper bound holds the exponent constant and the
lower bound decays it by night 8's measured factor of 0.769. And the
extrapolation bounds *alone* span 2.5 points at 60–64 while the binomial SE on
203 queries is 3.5, so each interval is widened by one SE per side. A
registration narrower than the noise on its own instrument is night 7c's
thin-sample error in a new place.

**The protocol is unchanged by this run, which is what makes these intervals
valid.** The 50+ pool is 1,068 molecules drawn from `data/shards/1m` valid minus
the union of every present run's training set. `data/shards/full` is already in
that union via `small_full` and `small_full_1p2`, so adding a fourth run on the
same shard moves neither the draw nor the `fp_unseen` flags, and the three
existing cells stay the right comparisons.

### 4c. The 30+ registration at 6 passes — built 2026-10-26

Night 7c computed the whole-protocol and 40–49 registrations (**0.92** and
**0.83**) for **3 passes**, so both were for the wrong run once the budget
changed. The 50+ table was rebuilt on night 8; the 30+ one was not. It is now.

Zero GPU — the obstacle was plumbing. `band_analysis.py --dumps` reads every
dump in one directory and no directory held all three instrument cells on the
30+ protocol: `small_full_1p2` is in night 7's `outcomes_full_1p2`, `small_1m`
in night 5's `outcomes_large_k60`, and `small_1m_matched` in night 6's
`outcomes_exponent_2x2` under the name `s1m_8k_t06`. All three sit on the
identical protocol — `eval_n` 2400, 2,321 fp_unseen, T=0.6, k=60,
`max_oversample` 12 — and `band_analysis.py` confirms it by matching the
reference list across dumps. Collected under canonical names, read at k=60
`generation` and k=1 `consensus`, both metrics, the same convention the 50+
instrument was built in. Artifacts in `results/overnight9/`.

**The result changes the plan's emphasis: the 30+ protocol is almost entirely
ceiling at this budget.**

| band | n | rec@60 registered | informative? |
|---|---|---|---|
| 30–34 | 1189 | 0.9841 – 0.9930 | no — ceiling |
| 35–39 | 625 | 0.9754 – 0.9900 | no — ceiling |
| **40–49** | **380** | **0.9140 – 0.9522** | **yes** |
| 35+ | 1132 | 0.9368 – 0.9599 | marginal |
| all | 2321 | 0.9634 – 0.9767 | no — §4a |

Seven of those intervals are narrower than or comparable to the 1.6-point
whole-protocol threshold, which is the tell: a registration the instrument
cannot resolve is not a test. The plan's earlier wording — "the 35+ and 40–49
bands, where the ceiling has not yet bitten" — was half wrong. Only **40–49**
carries information on this protocol, and 50+ belongs to the 893-query
instrument rather than this one's n=127.

**rec@1 in consensus order is the informative instrument**, and it is where the
reportable content now sits. Every band clear of the ceiling, intervals 3–7
points wide:

| band | n | rec@1 | struct@1 |
|---|---|---|---|
| 30–34 | 1189 | 0.9073 – 0.9354 | 0.8808 – 0.9129 |
| 35–39 | 625 | 0.8467 – 0.8916 | 0.8026 – 0.8532 |
| **40–49** | **380** | **0.6705 – 0.7445** | **0.6210 – 0.6971** |
| 35+ | 1132 | 0.7538 – 0.8021 | 0.7025 – 0.7537 |
| all | 2321 | 0.8405 – 0.8732 | 0.8025 – 0.8384 |

Consensus order is the project's adopted ranking (`results.md` §2.7, worth +22
points of rec@1 at no extra oracle call), and on this protocol `small_1m` sits
at 0.6493 there against 0.4072 in generation order.

The fifth registration — **do the exponents transport?** — stays a question
rather than an interval: `b` per band against the 0.144–0.396 range of
`results.md` §2.1, and `c` against the 0.701–0.911 that item 2 measured. Read
off `budget_curve.py` and `step_curve.py` in stage 5.

### 4d. Score rec@60 with the right tool

`compare_checkpoints.py` computes `ks = [n for n in (1, 5, 20, 100) if n <=
eval_k]`, so an `--eval-k 60` run reports rec@1/5/20 **under a 60-slot budget
and never prints rec@60**. Every rec@60 in this project comes from
`band_analysis.py`, and the two tools do not share a convention. Retractions
entry 20 has been caught four times on exactly this. The registered numbers
above are `band_analysis.py` numbers; score them with it.

---

## 5. Execution

### Before the run — done, and in one commit

Night 8 lost three hours because `small_100k_52k` had a config but no entry in
`compare_checkpoints.py`'s `RUNS` registry, so scoring could not resolve
`--only small_100k_52k` and failed two seconds after a 17-hour training run.
**A new checkpoint needs its `RUNS` entry in the same commit as its config.**

All four artifacts exist and are committed:

1. `configs/small_full_6p.yaml` — the config, carrying all five
   pre-registrations in its header as every other registered run does.
2. The `("small_full_6p", …, "data/shards/full")` line in `RUNS`, with the note
   that the shard is already listed so the protocol is unchanged.
3. `scripts/overnight9.sh` — the driver.
4. `results/overnight9/` — the 30+ and rec@1 registrations of §4c.

Launch is one command, and it takes its own deadline:

```
scripts/overnight9.sh                      # 33 h from now
scripts/overnight9.sh "2026-11-02 18:00"   # or pin it
```

Standing constraint from 2026-10-17: run `ruff format --check`, `ruff check`
and `pytest -q` **over the whole tree** before committing, because `format`
gates `pytest` in CI and a per-file check is how CI stayed red for two days
with the test step never executing.

### The driver

Night 8's shape, which worked: training is the only stage given the clock, every
later stage guards tightly and skips rather than overruns, and the script
re-runs idempotently to collect whatever the clock cut. Scoring is 1.75 h
against a checkpoint on disk and can happen any time afterwards.

| stage | what | guard |
|---|---|---|
| 1 | train 88,218 steps | needs 33 h; skipped if `best.pt` exists |
| 2 | score large protocol, 30+, k=60, T=0.6, 2,400 queries | needs 2 h |
| 3 | score 50+ protocol, k=60, T=0.6, 1,000 queries | needs 1 h |
| 4 | band tables, both metrics, both protocols | needs 0.5 h |
| 5 | miss anatomy, budget curve, step curve with the new point | needs 0.5 h |

Stage 2's invocation must be night 6's `score()` exactly — `--eval-n 2400
--min-heavy-atoms 30 --eval-k 60 -T 0.6 --top-p 1.0 --max-oversample 12` — and
stage 3's night 7b's — `--eval-n 1000 --min-heavy-atoms 50 --eval-k 60 -T 0.6
--top-p 1.0 --max-oversample 10`. Prefix-to-prefix comparability with the
existing cells is the whole value of both.

### One wrinkle in what gets scored

`best.pt` is saved on best in-training recovery, and with 500 molecules the
metric carries about ±2 points of noise, so it is not guaranteed to be the final
step — night 8's best was step 52,000 of 52,500. `RUNS` points at `best.pt`, and
every cell of both instruments was scored the same way, so this is consistent
rather than a defect. Worth noting in the write-up, not worth changing here.

---

## 6. Schedule

| | | GPU | mine |
|---|---|---|---|
| ~~before launch~~ | ~~30+ registration; config, `RUNS`, driver~~ | — | **done** |
| launch → +26.3 h | training | 26.3 h | — |
| +26.3 → +28 h | both protocols, band tables, curves | 1.75 h | — |
| after | read the registration out; items 5b, 5d | — | ~3 h |

**One window of 33 h**, inside which the job is expected to take 28. After it,
the project is done by the definition in
[next-steps-2026-10-19.md](next-steps-2026-10-19.md#definition-of-done), and
everything left is an extension taken up deliberately.

## 7. What this run can and cannot settle

It is the deliverable, not a discriminating experiment, and the registration is
where the content is. Three things to hold onto when the number lands:

- **A hit inside the 50+ intervals confirms very little.** They are wide on
  purpose — one binomial SE per side on top of an extrapolation whose upper and
  lower bounds differ only in whether g′ decays. Confirmation means the passes
  axis behaved; it does not discriminate between the two decay accounts.
- **A miss low at 60–64 is the interesting outcome.** It would mean the passes
  exponent decays faster at 1–6 passes than night 8 measured at 30–74, which
  would be new and would be the first evidence that the size cliff tightens
  under the one lever still paying.
- **The headline will saturate and that is not a result.** §4a. Report rec@60
  all-slice as a ceiling reading, and put the weight on rec@1, 40–49, 50+ and
  structure accuracy.
