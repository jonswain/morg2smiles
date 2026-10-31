# Inverting Morgan fingerprints: the complete report

**Morg2SMILES — generative recovery of SMILES strings from Morgan (ECFP)
fingerprints. 2026-10-09 to 2026-10-31, one Apple M2, nine overnight sessions,
roughly 118 hours of GPU time.**

---

## How to read this document

This is the project's one self-contained account: what was asked, how it was
measured, what was found, what was withdrawn, and what is left. It is written
for a reader who has not read the night logs, and it supersedes nothing — the
three reference documents it draws on remain the authorities on their own
subjects:

| document | authority on |
|---|---|
| [results.md](results.md) | each measured law, with its domain, error bar and producing script |
| [methodology.md](methodology.md) | the conventions, and the ones that have cost this project claims |
| [retractions.md](retractions.md) | all 28 withdrawn claims and the five causes behind them |
| `overnight-*.md` | the primary record, including the wrong turns, in order |

Where this report and a night log disagree, the night log is the contemporaneous
record and this document is the corrected reading. Every number here carries the
convention it was measured in, because two of them differ by about four points
and conflating them has voided two pre-registrations ([§3.7](#37-two-recovery-conventions-and-why-it-matters)).

**One domain statement governs the whole document.** Everything here was
measured on ChEMBL 35 molecules of **3 to 64 heavy atoms** with stereochemistry
stripped, a twelve-element whitelist and a 128-token decoder context. "50+"
means 50–64 everywhere, and "30+" means 30–64. Nothing in this project speaks to
molecules larger than 64 heavy atoms, and the cap is a real exclusion rather
than an artefact of the corpus — see [§8](#8-limitations).

**Section references.** `§n` always means a section of *this* report. References
to a section of another document always name that document.

### Glossary

Everything the summary and the findings assume. Each term is defined properly
where it is first used in the methods; this table is so that §1 can be read
cold.

**The task**

| term | meaning |
|---|---|
| **SMILES** | a molecule written as a text string. The thing the model generates. |
| **Morgan fingerprint** (ECFP) | a fixed-length bit vector summarising which circular atom environments a molecule contains. The thing the model is given. Normally treated as one-way. |
| **heavy atom** | any atom that is not hydrogen. The project's measure of molecular size; a typical drug is 20–40. |
| **preimage** | a molecule whose fingerprint equals the query's. Usually the original molecule, occasionally a different one that collides with it. |
| **oracle** | exact fingerprint equality, recomputed locally with RDKit. Free, local, and decides correctness with no proxy and no human judgement. |

**Measuring**

| term | meaning |
|---|---|
| **k** | the **budget**: how many distinct candidate molecules the model is allowed to propose per query. The oracle checks all k. |
| **recovery@k**, `rec@k` | the primary metric: the fraction of queries for which at least one of k candidates has the query's fingerprint. `rec@1` is the first-guess rate; `rec@60` allows sixty guesses. |
| **structure_accuracy@k** | the stricter metric: is one of the candidates the query's *own* molecule, rather than a different molecule with the same fingerprint? |
| **deficit** | `1 − rec@k`, the shortfall. The laws here are fitted in deficit because it has no ceiling, while recovery is bounded by 1 and flattens near it. |
| **fp_unseen** | the memorisation-proof slice: queries whose fingerprint appears in **no** model's training data. A retrieval baseline scores exactly 0.0000 on it. Every headline number is on this slice. |
| **band** | a size bucket of queries, e.g. 30–34 heavy atoms. Results are reported per band because the whole-protocol average hides everything. |
| **protocol** | one fixed evaluation instrument — a query set, a k, and sampling settings. Three were used, and their numbers are **not** comparable with each other ([§3.6](#36-the-protocols)). |
| **saturated** | a measurement so close to its ceiling of 1.0 that it can no longer distinguish anything. Several of this project's later whole-protocol numbers are saturated by design. |
| **consensus ranking** | ordering candidates by how many of the model's samples spell the same molecule. Costs nothing and is worth +22 points of `rec@1`. |
| **temperature**, `T` | how randomly the decoder samples. `T=0.6` was adopted throughout. |

**Training**

| term | meaning |
|---|---|
| **shard** | a prepared subset of the corpus with its own train/validation/test split. Four were built — 10k, 100k, 1M and `full` (1,881,996 training molecules). The first three are **nested**, which matters a great deal ([§3.1](#31-data)). |
| **step** | one optimiser update on one batch of 128 molecules. |
| **pass** (epoch) | one traversal of the training corpus. On a fixed corpus `steps × batch = corpus × passes` is an **identity**, so the steps axis *is* the passes axis — which is why "what is data worth at fixed compute" is not a well-posed question ([§5.6](#56-the-corpus-axis-f--2209-points-per-doubling-flat)). |
| **capacity** | model size. 8.0M parameters was the workhorse; 15.1M was tested; 25.7M was infeasible on this hardware. |
| **cell** | one (corpus, steps, capacity, temperature) combination that was trained and scored — the unit a law is fitted across. |

**The four exponents.** Each says how fast the deficit falls when one thing
doubles. Larger means the spending works harder.

| symbol | what doubles | measured |
|---|---|---|
| **b** | the inference budget `k` | 0.144–0.396 |
| **c** | training steps (= passes, on a fixed corpus) | 0.37–1.29, and it is a *local slope* that bends |
| **f′** | distinct training molecules | +22.09 points of `rec@60` per doubling |
| **g′** | passes over a fixed corpus | +22.28 to +26.30 points per doubling |

`b` and `c` are exponents in a power law; `f′` and `g′` are quoted in points of
recovery per doubling, because that is how the corpus question was asked. A
quantity **transports** when it holds in a cell it was not fitted on — the main
thing this project tested, and the main thing that failed.

---

## 1. Summary

### 1.1 The question

A Morgan fingerprint is a bit vector that records which small atomic
neighbourhoods a molecule contains. It is the standard way to describe a
molecule to a computer, and it is normally treated as one-way: the molecule
cannot be read back out. This project asked **how much of the molecule a
learned model can put back**, and what governs how well.

The answer matters because the information is mostly still there. On the
million-molecule corpus, 98.6% of molecules are the only molecule with their
fingerprint — so the obstacle is the model, not the descriptor
([§2.1](#21-the-problem)).

The tool is a **fingerprint-conditioned encoder–decoder transformer**: it reads
the fingerprint's set bits as an unordered set and writes the molecule out as a
SMILES string, one token at a time. It was trained on ChEMBL on a single laptop
over nine overnight sessions and 118.7 hours of recorded run time.

### 1.2 How it is scored

Correctness is decided by an **oracle**: recompute a proposed molecule's
fingerprint and compare it bit-for-bit against the query. This is free, local,
and admits no judgement. Because checking is free, the natural task is "propose
**k** candidates and keep whatever the oracle accepts", and the primary metric
is **recovery@k** — the fraction of queries for which at least one of k
candidates has the right fingerprint. `rec@1` is the first-guess rate; `rec@60`
allows sixty guesses.

Two things make the numbers trustworthy rather than merely large. Every
headline is measured on **fingerprints that appear in no model's training
data**, where a nearest-neighbour retrieval baseline scores **exactly 0.0000**
by construction — so any score above zero is reconstruction and not lookup. And
results are reported **per size band**, because molecular size dominates
everything here and whole-corpus averages conceal it.

### 1.3 What was found

**At drug-like size the molecule can be put back almost completely.** The final
model — 8.0M parameters, all 1.88M training molecules, six passes over them —
recovers **69.6% of molecules on the first guess and 95.0% within sixty**, on
2,321 held-out fingerprints of **30–64 heavy atoms**. On the easier unrestricted
protocol an earlier model reaches **91.6% within twenty guesses**, with over
three in four on the first ([§5.1](#51-headline)). Among the failures the
closest proposal averages 0.976 Tanimoto similarity, so even the misses are
near misses.

One caution about that headline, because it reads better than it is: the
30–64 set is **dominated by its smallest band** — 1,189 of its 2,321 queries are
30–34 heavy atoms — so 95.0% is not "95% of large molecules". Read per band, the
same model goes **97.6% at 30–34, 90.3% at 40–49 and 79.5% at 50–64.**

**Performance is governed by two power laws and a cliff.**

*Spending at inference.* Doubling the budget `k` always cuts the shortfall by a
constant factor. Writing the shortfall as a **deficit**, `1 − rec(k)`, it falls
as

> `1 − rec(k) = A · k^−b`

where `k` is the number of guesses allowed, `b` is the exponent being measured
(bigger means extra guesses help more), and `A` is the fitted deficit
extrapolated back to a single guess. The fit is excellent — correlation
|r| ≥ 0.991 — across nine separately trained cells, with `b` between 0.144 and
0.396 ([§5.2](#52-the-budget-deficit-is-a-power-law-in-k)).

*Spending at training.* The deficit falls as a power law in **training steps**
too, and about **3.1× faster** per doubling. These are the two different things
one can buy, and they are priced differently: budget is paid on every query
forever, training once. The crossover is around **ten thousand queries** — below
it, buy guesses; above it, train longer
([§5.4](#54-where-the-two-kinds-of-spend-cross-over)). A *third* axis, the
number of distinct training molecules, is measured separately as `f′` and is
worth +22.09 points of `rec@60` per doubling
([§5.6](#56-the-corpus-axis-f--2209-points-per-doubling-flat)).

*The cliff.* Recovery collapses with molecular size — 98.1% below 15 heavy
atoms, 36.6% at 50–64 for the model that was current when it was characterised.
**The cause is combinatorial, not informational**, which is the single most
useful finding here. It is *not* that large fingerprints are ambiguous: of 206
misses, two were cases of a different molecule sharing the fingerprint. It is
that the decoder proposes a cloud of roughly twenty plausible molecules at any
size, and recovery asks whether that cloud happens to contain an exact
**preimage** — a molecule whose fingerprint matches — which becomes
exponentially less likely as molecules grow.

The sharper version is **concentration**. The number of preimages the model
draws barely changes with size, but their *distribution across queries* changes
enormously: in the final run **18.9% of 50–64 queries draw no preimage at all**
while the successful ones draw several each. The population splits into
fingerprints the model can reach and fingerprints it cannot. Extra budget
therefore spends most of itself re-finding molecules on queries that were
already solved, which is why nothing tried here dissolves the cliff — the final
run pushed it back roughly fiftyfold and left its shape intact
([§5.12](#512-the-size-cliff-what-it-is-and-what-it-is-not),
[§5.13](#513-the-final-run-full-chembl-at-six-passes)).

### 1.4 The final run's headline result is a failed prediction

Before the last run was launched, five predictions were written into its config
file as numeric intervals, and the code that would score them was written while
it trained. Of **20 scored predictions, 9 landed inside their intervals.**

The failures are informative because they are **not random — they have a
direction.** Where the task is hard the model beat its prediction; where the
task was already near its ceiling it fell slightly short:

| | predicted | measured | |
|---|---|---|---|
| 50–64, first-guess recovery | 0.3283–0.4401 | **0.5984** | 15.8 points **better** |
| 50–64, recovery within 60 | 0.6310–0.6912 | **0.7615** | 7.0 points **better** |
| 40–49, first-guess recovery | 0.6705–0.7445 | **0.7842** | 4.0 points **better** |
| 30–34, first-guess exact structure | 0.8808–0.9129 | **0.8671** | 1.4 points **worse** |

Those predictions came from the scaling laws above, which were fitted on short
runs where the size cliff is at its most severe. Projected onto a run five times
longer, **they over-predicted how severe the cliff would remain.** Both
directions of error are the same mistake seen from two sides, and the practical
consequence is that every size extrapolation in this report should be read as an
*upper bound* on the cliff's severity.

Two quantities that had looked like constants also broke the first time they
were tested on a second corpus. The exchange rate between the two training axes,
`g′ / f′`, had been 1.52–1.68 and measured **1.322**; and the step exponent's
size structure reproduced in the easy bands but not the hard ones. Together
these say that extra passes and extra molecules **partly substitute for each
other rather than simply adding up** — the first direct counter-evidence to this
report's own additive scaling law
([§5.6](#56-the-corpus-axis-f--2209-points-per-doubling-flat)–[§5.7](#57-the-passes-axis-and-why-neither-axis-closes-the-cliff)).
It rests on a single pair of runs with no error bar, which is exactly why
measuring that error bar is item 2 of [§9](#9-next-steps).

### 1.5 What survived, and what the method cost

Several findings held up throughout and are cheap to reuse. **Consensus
ranking** — ordering candidates by how often the model spells the same molecule
— is worth **+22 points of first-guess recovery and costs nothing**
([§5.9](#59-consensus-ranking-is-free-and-worth-22-points-of-rec1)). Sampling
at temperature 0.6 is worth +1.99 points, essentially all of it on molecules
above 35 heavy atoms ([§5.10](#510-decoding-t06-top_p-10-everywhere)). Model
capacity cuts a constant *fraction* of the deficit rather than changing the
curve's shape ([§5.8](#58-capacity-cuts-a-constant-fraction-of-the-deficit)).
And the ratio `b ÷ rec@60` has now held across nine cells, meaning every
intervention tried here **slides the model along one curve rather than bending
it** ([§5.5](#55-nothing-changes-the-shape-of-the-budget-curve)). Twelve
directions were tested and are dead ([§6](#6-what-is-dead)).

**The method is part of the result.** Twenty-eight claims were published in this
project and later withdrawn, traceable to five recurring causes, all logged in
[retractions.md](retractions.md). The dominant pattern is stark: **every claim
that broke was a comparison *between* training runs; every claim that survived
was measured *within* one** ([§7.1](#71-cross-run-comparison)). Three of the
nine sessions existed only to correct the previous session's headline. The five
causes and the five pre-registration rules they produced are in
[§3.9](#39-pre-registration-as-practised-here) and [§7](#7-methodological-findings)
— including the uncomfortable one, that **writing the guard did not stop the
overclaim** ([§7.6](#76-and-one-thing-that-worked-repeatedly)).

What this report does **not** establish is in [§8](#8-limitations) — most
importantly that no number here has ever been measured on an untouched test
split. What it leaves open is in [§9](#9-next-steps). The leading question is
simply **where the training axis stops**: the final run's checkpoint selector
chose its very last checkpoint, so six passes over all of ChEMBL had not
exhausted it, and the only slowdown ever located sits in a regime
[§5.13](#513-the-final-run-full-chembl-at-six-passes) shows does not carry over.

---

## 2. Background

### 2.1 The problem

A Morgan (extended-connectivity) fingerprint is computed by enumerating each
atom's circular environment out to a fixed radius, hashing each environment to
an integer, and folding those integers into a fixed-width bit vector. It is the
standard molecular descriptor in cheminformatics, and it is normally treated as
one-way: the hash is not invertible, the fold discards collisions, and the
molecule is considered gone.

This project tests how true that is. The question is not whether the mapping is
*information-theoretically* invertible — it very nearly is, as §2.1's own
measurement shows below — but whether a learned model can actually perform the
inversion, and what governs how well.

The information available is more than one would guess. On the 1M-molecule
shard, 943,177 distinct fingerprints describe 950,967 distinct molecules, so
**98.6% of molecules are the only molecule in the corpus with their
fingerprint**. Folding 2,048 bits loses 1.46% of distinct atom environments and
affects half of all molecules, but rarely enough to make two molecules collide.
The representation is close to a lossless molecular identifier at this corpus
size, and the interesting question is therefore about the model rather than
about the descriptor.

That framing was itself a finding rather than an assumption, and an early
version of it was wrong. The first ambiguity measurement used an
11,669-molecule shard and reported 99.97% uniqueness and a maximum of two
molecules per fingerprint, which licensed the conclusion that degeneracy is
negligible and counts add nothing. On the corpus the models actually train on,
ambiguity is **30× higher** — 1.40% of molecules share a fingerprint overall,
and 6.13% at 50–59 heavy atoms — and counts cut it 5.6-fold. Both early
conclusions were withdrawn (entry 18).

### 2.2 Why the task suits autonomous iteration

Two properties, and they are what made a nine-session agentic programme
possible at all:

- **Correctness is decidable, locally and for free.** RDKit recomputes any
  candidate's fingerprint and compares it bit-for-bit against the query. There
  is no proxy metric and no human judgement in the loop. A candidate either has
  the right fingerprint or it does not.
- **Many guesses are allowed.** Because verification is free to anyone holding
  the query fingerprint, the natural formulation is "generate k candidates, keep
  what the oracle accepts". The primary metric, `recovery@k`, is defined on
  exactly that.

The combination means an iteration loop can make hundreds of decisions against
a number that means something. It also means the project's failures were
measurement failures rather than wishful ones — which is the subject of
[§7](#7-methodological-findings).

### 2.3 Prior art, including this project's own predecessor

The motivating example is [NISPO](https://github.com/oxpig/nispo), which
reached 98.1% OPSIN round-trip accuracy on 103M PubChem compounds via an
autonomous coding loop against an oracle. NISPO and the comparable
[openclatura](https://github.com/lamalab-org/openclatura) are **rule-based
packages, not neural models**; what this project borrows is the
loop-plus-oracle methodology, not the approach.

The direct predecessor is
[`jonswain/morg-to-smiles`](https://github.com/jonswain/morg-to-smiles), the
same author's earlier attempt, written without AI assistance and archived after
three hours and ten minutes. It chose the right problem and the same dataset,
and failed for three reasons worth stating because all three are about
measurement rather than architecture:

1. **No oracle.** It selected checkpoints on validation loss and reported mean
   Tanimoto similarity. Neither answers "did we get the molecule back". This
   project's own first run shows why that is fatal: at epoch 2, mean Tanimoto
   was 0.385 while `recovery@20` was **0.018**; by epoch 12, Tanimoto 0.861 and
   recovery 0.575. Tanimoto is smooth, flattering and lagging.
2. **One candidate, by greedy argmax**, for a task whose natural form is
   generate-k-and-filter — a self-imposed `recovery@1`, the hardest version of
   the metric.
3. **The fingerprint reached the decoder only as a GRU's initial hidden state**,
   squeezed through a stochastic 128-dimensional latent. A VAE compresses; a
   conditional decoder needs the condition to stay addressable. The input here
   is not something to compress, it is the entire specification of the answer.

A fourth, quieter problem: no standardisation, so every stereocentre in a target
string was noise the stereo-blind fingerprint could not determine.

The honest moral is symmetric. The predecessor reported a number that could not
support its conclusion; this project then did the same thing, in bold, on its
own front page, on night 1 — attributing a 30-point gap to data when the two
runs differed in compute as well (entry 1). The agentic loop's real contribution
was not a cleverer model. It was building the oracle, the two metric slices and
the memorisation baseline *before* training anything, so that every subsequent
number meant something.

---

## 3. Methods

### 3.1 Data

ChEMBL 35, downloaded as `chembl_35_chemreps.txt.gz` and standardised in one
pass: largest-fragment salt stripping, uncharging, stereochemistry removal
(`strip_stereo: true`), a twelve-element whitelist, a 128-token SMILES cap and a
**64 heavy-atom cap** (`prepare.py`, `max_heavy_atoms: int = 64`). Molecules are
deduplicated before splitting, and the split-disjointness invariants are under
test.

Four shards were built, and their relationship is load-bearing:

| shard | train | valid | test |
|---|---|---|---|
| 10k | 11,669 total | — | — |
| 100k | 90,682 | — | — |
| 1m | 900,917 | 45,528 clean | untouched |
| full | 1,881,996 | 104,555 | 104,555 |

**The 10k, 100k and 1M shards are nested** — drawn in order from one fixed
shuffle, each splitting within itself — so a molecule held out of the 100k shard
is usually *inside* the 1M shard's training set, measured at 4,540 of 5,037, or
90%. Evaluating a 1M-trained model on the 100k shard's validation split measures
memorisation. The full shard was built with `--exclude` so the 1M and 100k
shards' valid and test molecules stay out of its training set, which is what
makes an evaluation set clean for every model possible at all.

**The test splits have never been touched.** Every number in this project,
anywhere, is validation.

### 3.2 Fingerprints

Morgan radius 2, 2,048 bits, folded, binary, as the default
(`fingerprint_id` `465725d9dece`). Count fingerprints were ablated
([§5.11](#511-count-fingerprints-carry-information-that-does-not-reach-recovery));
radius, bit width and unfolded variants were not.

Every artefact — shard mask, checkpoint, leaderboard row — carries the
`fingerprint_id` hash of the `FPConfig` that produced it, and loading a
mismatched one is a hard error. A silent fingerprint mismatch between training
and evaluation would make every number meaningless rather than merely wrong.
This was the project's first guard and the only one that never failed.

### 3.3 Architecture

A fingerprint is a **set**, so it is encoded as one. Each set bit becomes a
token (`bit_embedding[index] + count_embedding[count]`) with no positional
encoding; a transformer encoder over that short sequence — about 50 tokens, not
2,048 — produces the cross-attention memory for a causal SMILES decoder. The
decoder can then attend to the specific atom environments implying each atom it
emits.

This is permutation-invariant by construction, spends no compute on the 98% of
bits that are zero, and serves binary, count, folded and unfolded fingerprints
through one code path.

Two sizes were used throughout:

| | d_model | heads | layers | params | s/step on this M2 |
|---|---|---|---|---|---|
| **8.0M** (the workhorse) | 256 | 8 | 4 + 4 | 7,951,945–7,963,767 | 0.90–1.37 |
| 15.1M | 320 | 8 | 5 + 5 | 15,123,953 | 1.91–2.66 |
| ~~25.7M~~ | 384 | — | 6 + 6 | ~25.7M | **6.58** — infeasible |

Parameter counts differ by 0.15% between otherwise identical 8.0M configs
because vocabulary size depends on the shard (73 tokens for 100k, 119 for the
full corpus). Three orders of magnitude below any measured effect; noted rather
than corrected.

### 3.4 Training

Batch 128, AdamW, learning rate 5×10⁻⁴ (4.5×10⁻⁴ for the 15.1M config, which is
a confound noted wherever capacity is compared), 300 warmup steps, **cosine
decay to zero over `min(total_steps, max_steps)`**.

Training uses **SMILES randomisation**: a fresh random traversal of each
molecule every epoch. The fingerprint is always computed from the canonical
molecule, so the input is unchanged while the target varies — which stops the
decoder collapsing onto one string and supplies the sampling diversity
`recovery@k` rewards. It is also, almost certainly, why 30 epochs over 90,682
molecules showed **no overfitting at all**: every epoch is a fresh target
string.

Checkpoints are selected on **oracle-based in-training recovery**, not on
validation loss, with teacher-forced validation loss kept only as a diagnostic
and a tie-break. The tie-break fixes a real bug: early in a run every
evaluation recovers nothing, and without one the first evaluation wins and
`best.pt` holds the *worst* model in the run.

Because `best.pt` is selected on a 500-molecule in-training metric carrying
about ±2 points of noise, it is not guaranteed to be the final step — night 8's
best was step 52,000 of 52,500. Every cell of every instrument was scored the
same way, so this is consistent rather than a defect, and it is noted here
because it is the kind of thing that looks like one.

### 3.5 The oracle and the metrics

The oracle is exact fingerprint equality, recomputed locally with RDKit.

**`recovery@k`** — the primary metric — is the fraction of queries for which at
least one of k candidates has the query's fingerprint. Two definitional points
carry several points of headline each:

- **One slot buys one distinct molecule.** Two spellings of one molecule are
  **one** guess. An early version deduplicated by string and reported "18 of 20
  exact matches" for aspirin that were 18 spellings of one molecule (entry 16).
- **An unparseable string is not a guess at all.** RDKit rejects it locally and
  for free, so no caller spending oracle queries would spend one on it.
  Deduplication must *mark* same-molecule candidates rather than drop them, or
  validity's denominator silently changes — dropping removes mostly *valid*
  candidates, which made validity read 0.714 against a true 0.785.

**`structure_accuracy@k`** asks the stricter question: is one of the candidates
the query's *own* molecule? The two metrics part company above 35 heavy atoms,
where one recovery in eight is a different molecule sharing the fingerprint, and
**both must be quoted for any size claim** — rule 3 of §3.9.

**`fp_unseen`** is the memorisation-proof slice: queries whose fingerprint
appears nowhere in the **union** of every model's training fingerprints
(1,989,502 of them). The nearest-neighbour retrieval baseline scores **exactly
0.0000** on this slice by construction, so any score above zero is
reconstruction rather than retrieval. Every headline number in this project is
on `fp_unseen`.

**Ranking.** Candidates are ordered by **consensus** — how many of the model's
samples spell the same molecule — which costs nothing, since the spellings are
already drawn ([§5.9](#59-consensus-ranking-is-free-and-worth-22-points-of-rec1)).
Reports carry generation order beside it so numbers measured before the change
keep their meaning.

**Filling the budget.** `generate_outcomes` draws `k × oversample` strings and
tops up k at a time until the query has k distinct scored candidates or hits
`max_oversample × k`. The original constant `oversample=2.0` was calibrated on
the 100k model and silently stopped filling the budget as models improved:

| model | duplicate rate | distinct valid / query at k=20 |
|---|---|---|
| `small_100k` | 0.247 | 21.3 |
| `small_1m` | **0.569** | **12.6** |

**Better models explore less**, so a constant oversample hands the *stronger*
model fewer effective candidates — understating every cross-run gap, in the
direction the project wanted (entry 17). A capped draw and an uncapped one are
different protocols, so the cap is named wherever a number is quoted.

### 3.6 The protocols

Three evaluation instruments, and their numbers are **not comparable to each
other**:

| | common protocol | large-molecule protocol | the 50+ instrument |
|---|---|---|---|
| molecules | 2,000 random held-out | 2,400 drawn from 30+ heavy atoms | 1,000 drawn from 50+ |
| `fp_unseen` | 1,956 | 2,321 | 893 |
| k | 20 | 60 | 60 |
| `max_oversample` | 10 | 12 | 10 |
| invocation | `--eval-n 2000 --eval-k 20` | `--eval-n 2400 --min-heavy-atoms 30 --eval-k 60 --max-oversample 12` | `--eval-n 1000 --min-heavy-atoms 50 --eval-k 60 --max-oversample 10` |

**Each protocol is blind in its own direction.** The common protocol is 63%
molecules under 30 heavy atoms, so it cannot describe an intervention acting on
part of the size distribution: it reported the size-weighted training mix as a
flat −1.13 points, which is the average of +4.60 above 35 atoms and −3.11 below
24, and it hid a 4.18-point loss from count fingerprints behind p = 0.32. The
large protocol has the power where the common one has none, and its "all" column
means *all molecules in that protocol* — 30+ heavy atoms — not all molecules. Its
own 50+ band is only 127 queries, which is the sample size that produced two of
this project's overturned nulls, hence the third instrument.

The clearest demonstration that the common protocol cannot see a redistribution:
up-weighting large molecules sixfold and down-weighting them threefold produced
**the same whole-protocol recovery to four decimal places** (0.6258 both), while
doing opposite things in every band.

`compare_checkpoints.py` exists for the nesting problem of §3.1 alone: it builds
one evaluation set held out of *every* model's training data, computes
`fp_unseen` against the union, and scores every checkpoint on identical
molecules with an identical seed, budget and k. **Nothing in the per-run
leaderboard numbers is wrong; they simply each answer a different question.**

### 3.7 Two recovery conventions, and why it matters

The same checkpoint, the same queries, the same k, two numbers:

| convention | one of the k slots is | tool |
|---|---|---|
| **molecule budget** | one distinct valid molecule | `compare_checkpoints.py`, `band_analysis.py` |
| **raw slots** | one proposal, duplicates and invalid strings included | `miss_anatomy.py` |

They differ by about **four points at k=60**. Both are correct and they answer
different questions. Conflating them has cost this project two pre-registrations
and nearly a third.

The reason it recurs is structural, and worth stating plainly because it is the
single most expensive piece of plumbing here.
`compare_checkpoints.py` computes its k-list as
`ks = [n for n in (1, 5, 20, 100) if n <= eval_k]`, so **a run invoked with
`--eval-k 60` reports rec@1, rec@5 and rec@20 under a 60-slot budget and never
prints rec@60 at all.** Every rec@60 figure in this project therefore comes from
a second tool, and the two tools do not share a convention.

**The rule: read columns against each other, never across tools.** A comparison
is prefix-to-prefix or it is nothing. On night 7 the mixed pair would have
inflated f′ by 4 points and read as a cleaner CONFIRMED than the truth.

### 3.8 Error bars

Three runs identical but for `train.seed` scored `rec@20` of 0.6053, 0.6084 and
0.5941, so single-run `rec@20` carries an **sd of about 0.75 points**. Since
every run is scored on the *same* molecules, the right error bar for comparing
two of them is McNemar's paired SE on the discordant pairs — about **0.8 points**
at 13% discordance.

**Gaps below about 1.6 points between two training runs are not evidence of
anything.** Three differences whose true value is exactly zero came out at
−0.31, +1.12 and +1.43 points, the last being 1.7 paired SE.

Three refinements, each earned:

- **The threshold is whole-protocol and does not survive slicing.** The same
  three seeds read inside bands give a between-seed sd of 0.23 points below 29
  heavy atoms and **2.99 at 30–34**, where two runs differing only in seed are
  5.63 points apart at p = 0.022. The cliff's *shoulder* is where a training
  experiment is hardest to measure.
- **Comparisons sharing candidates cancel almost everything.** Two rankings or
  two temperatures over one checkpoint disagree on ~1% of queries rather than
  13%, giving SEs of 0.2–0.5 points, so sub-point effects are real there. The
  1.6-point rule nearly killed a genuine +0.77-point result at p = 0.001.
- **A discordant-pair count in single digits is not evidence of absence,
  however good the p-value looks.** Two nulls here were called on roughly 130
  queries and **both were overturned** by enlarging the sample (entries 12, 13).

**An error bar belongs to a comparison, not to a project, and the slice is part
of the comparison.** Every gap is tested against its own discordance
(`paired_tests.py`).

Evaluation is seeded. Unseeded, two evaluations of the same checkpoint differed
by 2.2 points (entry 21).

### 3.9 Pre-registration, as practised here

Five rules, each earned by being broken:

1. **Register the interval, not the point.** A registration whose branches are
   separated by less than the quantity's paired SE is decided before the GPU
   starts. One fired FALSIFIED HIGH on a difference-in-differences of +1.01
   points [−0.90, +2.91] — indistinguishable from zero (entry 22).
2. **Register the band *and* the predicted location of the effect.** A metric
   chosen on its error bar alone — the 30–39 band, picked because it was the
   largest — failed to clear, because three fifths of it is molecules the
   intervention does not affect (entry 24).
3. **Read every size claim on `structure_accuracy` as well as `recovery`.** The
   two part company above 35 atoms. **The gap has no fixed sign:** both working
   interventions were *understated* by recovery, while night 7's scaling slopes
   are *overstated* by it — by a fifth whole-band and 43% at 60–64. The reason
   biases any cell near the floor: among hits at 50+, the fraction that are a
   different molecule with the same fingerprint is **58.5%** for a model at
   rec@60 0.0459, 27.9% at 0.2251 and 20.9% at 0.3908. A weak model's few hits
   land on the ambiguous fingerprints — the easy ones to satisfy and the ones
   where satisfying them proves least — so **a slope measured from a floor cell
   flatters itself on recovery**, which is exactly where constant-passes designs
   put their small cells.
4. **The registered intervals must tile the line.** Night 8 registered rec@60 in
   0.88–0.95 with "below 0.85" as saturation, leaving **0.85–0.88 unnamed**. The
   measurement came in at **0.8789** — 0.11 points under the floor, a sixth of
   the 1.6-point threshold — so the reading had to be constructed after the fact
   (entry 26). "Uninformative" is a legitimate branch provided it is named in
   advance.
5. **Register the slope, not the level, whenever the metric is bounded.**
   Recovery is bounded by 1, so a threshold on the level conflates *the curve
   bent* with *the curve ran out of room*. Night 8's level test cleared 0.85
   comfortably while the deficit exponent fell 0.911 → 0.701 across one doubling
   of steps — the bend the test existed to find. A saturation question is a
   question about a derivative, and belongs in the deficit form, which has no
   ceiling.

   Its companion: **a registered quantity has to be measured in the regime the
   decision applies to.** Night 8's bend sits between the 30th and 74th pass
   over a fixed corpus; the budget it was commissioned to pick was for a run at
   3–6 passes, so it could not speak to it at all.

A registration also has to say what each branch would *mean*. Both mechanisms
registered for one stage were eliminated, and the useful output was the null —
which only reads as useful because the branches carried mechanisms rather than
directions.

### 3.10 Hardware, cost, and the operational guards

One Apple M2 (MPS), torch 2.13.0, device selection `mps → cuda → cpu`; nothing
is MPS-specific and configs are portable. Measured costs on this machine:

| quantity | value | source |
|---|---|---|
| 8.0M training, full shard | **1.047 s/step** (solved) | `small_full`, `small_full_1p2` |
| 8.0M training, 1M shard | 1.337 s/step | `small_1m` |
| 8.0M training, 100k shard | 1.373 s/step | `small_100k_long` |
| 15.1M training | 1.91 s/step | `medium_1m_full` |
| generation | 0.016 s/slot/query | `small_1m_matched` |
| one 2,400-query k=60 scoring arm | ~0.64–1.34 h | measured |

**Three of the last four cost figures in this project were wrong because they
were priced off a cell differing from the target in shard, fingerprint or
evaluation cadence.** The final run's cost model was therefore *solved* from two
same-shard cells rather than quoted — two equations in per-step and per-eval
cost — and independently confirmed against the measured final-eval times
(~216 s solved, 180.3 s and 224.6 s measured).

Unattended runs fail differently from supervised ones, because nobody notices
for hours. The guards that resulted:

- **`max_hours`, on the right clock.** The original was built on
  `perf_counter`, which does not advance while a macOS process is suspended, so
  an 8.5 h cap recorded 6.90 h across 10.78 h of real time and never fired
  (entry 19). It now uses `time.time()`, and `caffeinate -dimsu -w <pid>` holds
  the machine awake rather than merely measuring the loss correctly.
- **`max_hours` is a runaway guard, not a budget.** A run stopped by it has an
  unfinished cosine schedule and **is not the run its config pre-registered**,
  so drivers refuse to start without a window above the worst plausible
  completion rather than starting and hoping.
- **Deadline-aware, fail-soft, idempotent drivers.** Training is the only stage
  given the clock; every later stage guards tightly, skips rather than
  overruns, and re-runs idempotently to collect whatever the clock cut. An
  unanalysed checkpoint is worth much less than an analysed one.
- **This machine runs one job.** Three stalls of ~1,000 s each were traced to a
  benchmark of the author's own running against the live job.
- **A new checkpoint needs its `RUNS` entry in the same commit as its config.**
  Night 8 lost three hours because scoring could not resolve `--only
  small_100k_52k`, failing two seconds after a 17-hour training run.

A cap that is never exercised in testing is an assertion, not a guard.

### 3.11 Reproducing CI

```bash
pytest -q                               # 478 tests; the 5 needing a shard self-skip
ruff check src tests scripts
ruff format --check src tests scripts
```

CI runs exactly these on Python 3.11 and 3.12 and **`format` gates `pytest`**,
so a formatting miss hides every test result behind it. Run them on the whole
tree, not on the files you touched: checking per-file is how CI stayed red from
2026-10-17 to 2026-10-19 with the test step never executing.

---

## 4. The experimental programme

Nine sessions. The column that matters is the last one.

| # | date | GPU | what it was for | what it actually produced |
|---|---|---|---|---|
| — | 10-08 | 4.2 h | Phase 1: can a conditional decoder reconstruct unseen molecules at all? | `rec@20` 0.5367 on `fp_unseen` against a baseline of exactly 0.0000. Gate passed by the whole margin. |
| 1 | 10-09 | 15 h | Where is the ceiling — data, compute or capacity? | "10× data is worth +30.4 points" — **wrong**, the runs differed in compute too. Also: three measurement fixes made first, and two guards that did not hold. |
| 2 | 10-10 | 16 h | The missing control | **+24.9 points from compute alone** on a fixed corpus, so night 1's attribution was wrong regardless. Corpus size cannot be isolated at fixed steps *at all*: `steps × batch = corpus × passes` is an identity. |
| 3 | 10-14 | 6 h | The remaining 10.5%, and count fingerprints | **2 of 206 misses are fingerprint collisions** — a capability ceiling, not an information one. **Consensus ranking is worth +22 points of rec@1.** Counts: no gain. |
| 4 | 10-15 | 12 h | The error bar this project never had | **sd 0.75 points, paired SE 0.8, so the threshold is 1.6.** Three seeds agree on 80% of the evaluation set while proposing almost disjoint molecules. **T=0.6 is worth +1.99 points**, all of it above 35 heavy atoms. |
| 5 | 10-16 | 15 h | The size cliff, factorised | The cliff is **combinatorial**: at every size the decoder proposes ~20 molecules at ~0.65 Tanimoto, and recovery is whether that cloud contains an exact preimage. The budget deficit is a **power law in k**, measured to k=60. Ensembling is dead. Counts are 4.18 points *worse* on the right protocol. |
| 6 | 10-17/19 | 35 h | Capacity, and what moves the budget exponent | **It was training length, not capacity** — night 5's headline named a variable that never moved. Capacity cuts a **constant fraction** of the deficit, independent of training length, declining from 25.4% at 30–34 to 3.9% at 50+. The step law is **3.1× steeper** than the budget law. |
| 7 | 10-20 | 6 h | f′ at constant passes | **f′ = +22.09 points per corpus doubling**, measured with nothing subtracted. The convex branch is **falsified by 12 SE**. Both scaling axes decay in the direction the cliff does. |
| 8 | 10-24/25 | 19 h | Step saturation, the third point | **Saturation is real, on the slope**: the deficit exponent falls 0.911 → 0.701. The registered *level* test could not detect it, and the bend sits 24 passes out of the regime it was commissioned to inform. |
| 9 | 10-30/31 | 28 h | The final run | **Full ChEMBL, 6 passes: rec@1 0.6963 and rec@60 0.9496 on the 30+ protocol, 0.3180 and 0.7402 at 50+.** The registration missed *high* on every hard band and *low* on the saturated ones — the size extrapolation was too steep. `g′ / f′` is **not** corpus-invariant, the first counter-evidence to the additive law. [§5.13](#513-the-final-run-full-chembl-at-six-passes) |

Two patterns in that table are the project's real output. **Every claim that
broke in the first two nights was a comparison *between* runs; every claim that
survived was measured *within* one.** And three of the nine sessions existed
only to correct the previous one's headline — nights 2, 6 and 7 are each a
retraction with a measurement attached.

---

## 5. Findings

### 5.1 Headline

One protocol: 2,000 held-out molecules (1,956 fingerprint-unseen) in no model's
training set, `fp_unseen` against the union of 1,989,502 training fingerprints,
fixed seed, molecule budget.

| model | rec@1 | rec@20 | struct@20 | validity |
|---|---|---|---|---|
| 8M, ChEMBL 1M, 21,117 steps, T=1.0 | 0.7526 | **0.8962** | 0.8860 | 0.921 |
| the same at the adopted T=0.6 | 0.7730 | **0.9162** | — | — |
| three-temperature vote, still 20 oracle calls | — | **0.9279** | — | — |
| retrieval baseline | 0.0000 | 0.0000 | 0.0000 | 1.000 |

**Over 91% of held-out Morgan fingerprints can be inverted exactly within 20
guesses by an 8M-parameter model trained overnight on a laptop, and more than
three in four on the first guess.** Mean best Tanimoto is 0.976, so even the
failures are near misses.

The baseline is zero **by construction** on `fp_unseen`, so the primary metric
cannot be gamed by memorisation.

### 5.2 The budget deficit is a power law in k

`1 − rec(k) = A·k^−b`, fitted over a twelvefold range of k, **|r| ≥ 0.991 in
every size band**. `small_1m` at T=0.6 on the large protocol:

| band | b |
|---|---|
| 30–34 | 0.396 |
| 35–39 | 0.387 |
| 40–49 | 0.263 |
| 50+ | 0.144 |
| all | 0.317 |

Inverting the fits prices the brute-force route, and it is a measurement rather
than a guess up to k=60:

| band | k for rec 0.90 | k for 0.95 |
|---|---|---|
| 30–34 | 41 | 238 |
| 35–39 | 128 | 768 |
| 40–49 | 3,080 | 42,917 |
| 50+ | 1.0 × 10⁷ | 1.2 × 10⁹ |

**Brute force is a real route below 40 heavy atoms and arithmetic above 50.**

The exponent falls with molecule size, which is the sharp version of the cliff:
big molecules do not merely start lower on the curve, each doubling of budget
buys them proportionally less as well. **The cliff steepens with spending rather
than eroding.**

The method transports. Refitting on k ≤ 20 only and predicting k=60 lands within
half a point in the two bands with real n; and fitted on the 100k arm's k ≤ 20
rungs it predicted 0.232 for a cell it had never seen, which measured **0.2491**
inside a registered 0.21–0.26. Against that, an independence model — each draw
an independent trial at the model's own first-slot rate — predicted 0.9986 at
35+ against a measured 0.6890, **wrong by 31 points**, and was wrong by a wide
margin four times (entry 10). The decoder re-proposes from a neighbourhood that
barely moves as the budget grows.

One caveat the numbers themselves demand: a power law with no visible floor and
a population with unreachable members are in tension, since the second implies
an asymptote below 1 and the first denies one. k ≤ 60 cannot separate them. The
fit is excellent over the measured range, it is a **lower bound** on cost, and
[§5.12](#512-the-size-cliff-what-it-is-and-what-it-is-not)'s concentration
result is the reason to expect the real curve to bend worse rather than better.

### 5.3 The step deficit is also a power law, and it is 3.1× steeper

Same queries, same k, two checkpoints differing only in step count:

| band | b (budget) | c (steps) | c / b |
|---|---|---|---|
| 30–34 | 0.396 | 1.294 | 3.27 |
| 35–39 | 0.387 | 1.240 | 3.20 |
| 40–49 | 0.263 | 0.893 | 3.39 |
| 50+ | 0.144 | 0.366 | 2.54 |
| all | 0.317 | 1.062 | 3.35 |

The 100k pair gives 2.86–3.13 for the same bands. **A doubling of training steps
cuts the deficit about 3.1 times as far as a doubling of inference budget,
across two corpora and every band** — and the ratio is flat in size even though
both exponents fall threefold across it.

**The step law is the weaker of the two, and it bends.** The budget deficit is
straight in log-log to |r| ≥ 0.991; the step deficit is not. Night 8 added a
third point at 52,500 steps and the local slope *falls*:

| segment | steps | passes | rec@60 | per doubling | c |
|---|---|---|---|---|---|
| 1 | 8,508 → 21,117 | 12.01 → 29.81 | 0.4752 → 0.7708 | +22.54 | **0.9113** |
| 2 | 21,117 → 52,500 | 29.81 → 74.05 | 0.7708 → 0.8789 | **+8.23** | **0.7008** |

Two near-identical doublings, and the second cuts the deficit a fifth less
efficiently. The deficit form has no ceiling, so this is not recovery running out
of room: **the step law weakens with range, and this is the only bend the
project measured.** Structure accuracy agrees (structure@60 0.8656 against
rec@60 0.8789 — the usual few points below, not a different shape).

Two things it does **not** license:

- **It does not transfer out of its repetition regime.** On a fixed corpus the
  steps axis *is* the passes axis, so segment 2 is the 30th to the 74th look at
  the same 90,682 molecules. The in-regime comparison — 900,917 molecules at
  1.21 → 3.00 passes — gives **+24.57** points per doubling with no bend at all.
- **The in-training traces say the opposite and are wrong here.** They have the
  exponent *climbing* with range (0.703 → 0.843). Those traces are own-shard,
  500 molecules, at differing cadences. **Where a trace and the held-out
  protocol disagree, the protocol is the measurement.**

### 5.4 Where the two kinds of spend cross over

Budget is charged on every query forever, training once. Cutting the deficit by a
factor f needs `f^(−1/b)` times the budget or `f^(−1/c)` times the steps, so
there is a query count above which the longer run is cheaper:

| band | queries for a ×0.75 cut | for a ×0.5 cut |
|---|---|---|
| 35–39 | 20,900 | 13,300 |
| 40–49 | 16,900 | 8,000 |
| 50+ | 16,600 | 4,100 |
| 35+ | 17,900 | 9,000 |

**Below roughly ten thousand queries, buy budget; above it, train longer.** This
project's own protocols are 2,000 and 2,400 queries — an order of magnitude
below the crossover — so "brute force is affordable" is true *for a benchmark*
and is the wrong advice for anyone inverting fingerprints at scale.

### 5.5 Nothing changes the shape of the budget curve

Eight cells, four interventions (corpus, steps, capacity, temperature), spanning
0.249 to 0.870 in recovery and 2.9-fold in the exponent: **`b ÷ rec@60` stays
between 0.320 and 0.380** with no monotone trend. In the `k ≤ 20` refit
convention the same cells read 0.290–0.427; the two conventions are not
interchangeable and the conclusion is the same in both.

**Interventions slide a model along one curve rather than bending it.** This
retired three successive claims that something was a second dial — the training
mix, then capacity, then training length — each of which moved the exponent by
almost exactly the amount its recovery level accounts for.

The one place the instinct was right, under a different label: `A` is the deficit
the law extrapolates back to k=1, and above 50 heavy atoms it sits at **1.01,
1.00, 1.00, 1.02** across four cells. **No model in this project, at any corpus
or training length, ever finds a 50-atom molecule on its first proposal.** There
the exponent really is the only quantity anything can move, because the other is
against its ceiling.

### 5.6 The corpus axis: f′ = +22.09 points per doubling, flat

This took nine nights and four retractions, and the reason is one identity:
`steps × batch = corpus × passes`. **At a fixed step budget, corpus size and
repetition rate are perfectly anti-correlated**, so "what data is worth at fixed
compute" is not a well-posed quantity. Four successive claims died on it
(entries 1–5).

The design that works holds **passes** fixed instead, which necessarily varies
compute — and then the comparison is f′ with nothing to subtract. Large
protocol, k=60, T=0.6, the same 2,321 queries, 1.2087 passes throughout:

| molecules | steps | rec@60, all | 35+ | 50–64 |
|---|---|---|---|---|
| 90,682 | 856 | 0.0000 | 0.0000 | 0.0000 |
| 900,917 | 8,508 | 0.5205 | 0.3613 | 0.0630 |
| 1,881,996 | 17,772 | **0.7553** | 0.6378 | 0.2598 |

**f′ = +22.09 points of rec@60 per doubling of distinct molecules** (1.0628
doublings, +23.48 points, binomial SE 0.89), a 46.1% cut of the deficit per
doubling. It replicates at +20.96 in the molecule-budget convention and +16.79
on the common protocol at k=20 — the last lower because that protocol is 63%
small molecules, which gain least.

**The pre-registered convex branch is falsified by twelve standard errors.** The
decomposition that inferred +35.03 for this segment overstated it by 13 points,
60% of its measured value (entry 27). What survives from that decomposition is
the *near-cancellation*: at constant steps a corpus doubling is a passes
halving, so +22.09 against −23.55 nets +1.37, and **the corpus axis at constant
steps is a terrible instrument** — a small difference of two large numbers. The
"8.4× convexity" three nights rested on was that cancellation, not a property of
the corpus.

The 90.7k floor check came in at **0.0000 at every k, in every band, on 571
queries**, as registered — consistent with additive separability and weak
evidence for it, since a number pushed to a floor it was predicted to be below
agrees without evidence.

**f′ is itself size-dependent, and falls off in the same direction the cliff
does.** On the dedicated 893-query instrument:

| band | n | 900,917 | 1,881,996 | per doubling | SE |
|---|---|---|---|---|---|
| 50–54 | 433 | 0.0647 | 0.2910 | **+21.30** | 2.18 |
| 55–59 | 257 | 0.0428 | 0.1946 | **+14.28** | 2.47 |
| 60–64 | 203 | 0.0099 | 0.1232 | **+10.66** | 2.31 |
| all 50+ | 893 | 0.0459 | 0.2251 | **+16.86** | 1.40 |

Each step down is about 3 SE. At 60–64 a corpus doubling pays less than half the
whole-protocol rate. Notably, the 127-query estimate (+18.52) **survived** the
re-measure at +16.86, 1.2 SE away — the first time in this project a number read
on roughly 130 queries held.

### 5.7 The passes axis, and why neither axis closes the cliff

With `small_1m` on the same instrument, both slopes are available per band:

| band | n | f′ / corpus doubling | g′ / passes doubling | g′ / f′ |
|---|---|---|---|---|
| 50–54 | 433 | +21.30 | +32.40 | 1.52 |
| 55–59 | 257 | +14.28 | +24.03 | 1.68 |
| 60–64 | 203 | +10.66 | +16.15 | 1.52 |
| all 50+ | 893 | +16.86 | +26.30 | 1.56 |

**Neither scaling lever reaches the far end of the size cliff**: both pay about
half as much at 60–64 as at 50–54. That is the strongest form of the capability
ceiling finding — the ceiling is not something more data or more passes removes,
within the range this hardware can reach.

The ratio sits at 1.52–1.68 while both slopes halve, which looks like a
size-invariant exchange rate near 1.55. Each slope's SE is about 2.2 points, so
the ratio's is about 0.2 and that spread is inside it: **consistent with
size-invariant, not measured to be.** Testing it needed a second passes point
at 50+ on another corpus, which did not exist when this was written.

**The final run created that point, and the exchange rate did not transport**
— `g′ = +22.28` and `g′ / f′ = 1.322` on the full shard, against the +26.30 and
1.56 above. See [§5.13](#513-the-final-run-full-chembl-at-six-passes), which is
where this section's assumption of additive separability meets its first
counter-evidence.

**On structure accuracy both slopes are about a fifth smaller**, and the gap
widens with size — the opposite direction from the two cases that prompted the
read-both rule:

| band | f′ rec → struct | g′ rec → struct |
|---|---|---|
| 50–54 | +21.30 → **+17.60** | +32.40 → **+28.17** |
| 55–59 | +14.28 → **+12.45** | +24.03 → **+19.88** |
| 60–64 | +10.66 → **+6.03** | +16.15 → **+12.02** |
| all 50+ | +16.86 → **+13.49** | +26.30 → **+22.11** |

At 60–64, +10.66 points of recovery per corpus doubling is +6.03 points of
getting the right molecule. The cause is rule 3's mechanism: collisions among
hits scale with weakness, not only with size.

**g′ should not be extrapolated below one pass.** The same corpus at 0.58 and
1.21 passes gives g′ = +10.62 per doubling, half the +23.55 measured at ≥1.21
passes. A model that sees each molecule less than once is not in the same
regime.

And at these budgets, **passes still beat molecules**: `small_1m` at 21,117
steps on 900,917 molecules scores 0.8427 while `small_full_1p2` at 17,772 steps
on 1,881,996 scores 0.7553 — the smaller corpus ahead by 8.7 points. The
additive law accounts for it exactly (+31 points of passes against −22 of
corpus). "Prefer more molecules to more passes" holds only at fixed steps, which
is not a budget anyone has.

### 5.8 Capacity cuts a constant fraction of the deficit

15.1M against 8.0M parameters, same shard, at two step counts — the closed 2×2:

| | deficit ratio, 15.1M / 8.0M | 95% CI |
|---|---|---|
| at 8,508 steps | 0.808 | [0.778, 0.837] |
| at 21,117 steps | 0.825 | [0.766, 0.888] |

**The cut does not depend on training length** — every band-level difference
straddles zero across a 2.48-fold change in steps — so the 21,117-step figure
was not a lower bound.

The most useful thing in the comparison is that the *same* comparison is worth
+1.33 or +7.11 points:

| steps | 8.0M rec@20 | 15.1M rec@20 | gain | deficit ratio |
|---|---|---|---|---|
| 8,508 | 0.6825 | 0.7536 | **+7.11 pts** | 0.776 |
| 21,117 | 0.9131 | 0.9264 | **+1.33 pts** | 0.847 |

A 5.3-fold difference in the headline from a multiplicative cut that barely
moves. **"Capacity is worth N points" is not a property of capacity; it is a
property of how long the baseline trained.**

**It is not uniform across size.** The cut declines from 25.4% at 30–34 to 3.9%
at 50+. An intermediate claim that it reaches *zero* above 50 atoms rested on
127 queries and ten discordant pairs and was withdrawn: on the dedicated
893-query instrument the gain is **+3.70 points [+2.13, +5.26], p = 9×10⁻⁶**
(entry 13). Capacity helps at every size; the *fraction* falls about sixfold.

Capacity buys **ordering, not reach**: the larger model proposes *fewer* distinct
molecules per query (13.6 against 14.7) while proposing more valid ones, and
wins anyway. It is also the only intervention here that does anything at k=1
(+5.63 points of rec@1).

Caveats: the two architectures train at lr 4.5×10⁻⁴ and 5×10⁻⁴, so each
comparison carries a 10% learning-rate difference alongside the 1.9× in
parameters; and scaling is linear in wall clock to 15M parameters and
superlinear beyond (25.7M costs 6.58 s/step — 7.3× the time for 3.2× the
parameters), so **capacity is the wrong lever on this hardware.**

### 5.9 Consensus ranking is free and worth 22 points of rec@1

Rank candidates by how many of the model's samples spell the same molecule. No
extra oracle call, no extra sampling — the count falls out of samples already
drawn.

| ordering | rec@1 | rec@5 |
|---|---|---|
| generation order (baseline) | 0.5302 | 0.7996 |
| log P(sampled string) | 0.5153 | 0.8298 |
| log P per token | 0.5327 | 0.8364 |
| log P(canonical form) | 0.6580 | 0.8701 |
| **sampling frequency (consensus)** | **0.7520** | 0.8666 |

**+22 points of rec@1**, and +11 to +26 on every other checkpoint measured. The
model's confidence is encoded in **repetition**, not in the per-string
probability of the spelling it happened to emit — scoring the sampled string is
*worse* than generation order, because randomised-SMILES training spreads a
molecule's mass across its spellings. Canonicalising before scoring recovers
+12.8 of that.

The gain is largest in the middle of the quality range: the one model that barely
gains (+1.9) is the pre-competent one, which has no confidence to express.
`rec@20` is nearly insensitive, as it should be.

Two second-order results from the same mechanism. **Agreement between models is
a better signal than agreement within one** — three seeds with votes pooled beat
one seed by 6.49 points of rec@20 at the *same* oracle budget. And **three
samplings of one model at different temperatures, pooled, reach rec@20 0.9279**,
the best figure in the project, from no additional training, and it survives
matching the sampling cost (+0.77 points, p = 0.006).

### 5.10 Decoding: T=0.6, top_p 1.0, everywhere

Cooling from T=1.0 to T=0.6 is worth **+1.99 points** of rec@20 (p = 1.3×10⁻⁵),
and essentially all of it is large molecules: **+7.5 points at 35+ heavy atoms
against +0.75 below.** The gain rises monotonically across six size bands, from
under half a point below 24 atoms to nearly ten above 50.

Pushing further buys nothing. Tested where it was most likely to fail — 893
queries at 50–64 heavy atoms, the worst-validity band in the corpus — T=0.3
moves recovery by **−0.34 to +1.34 points** depending on model and budget, every
interval straddling zero.

**The mechanism is a cancellation worth stating on its own:** cooling raises
validity by 6.6 and 2.8 points for the two models and *lowers* distinct
molecules per query by 3.3 and 6.1. **Validity is not the binding constraint on
large molecules** — the invalid strings cooling removes are replaced by valid
wrong answers, not by right ones.

A size-conditional temperature is dead, and the reason generalises. A
fingerprint's set-bit count predicts heavy atoms at r = 0.83, so routing is
deployable; it is worth **+0.10 ± 0.25 points** over a flat 0.6. The cause is
that cooling never *hurt* small molecules, it just did not help them. **An
intervention that only helps subgroup X is worth conditioning on X only if it
hurts not-X** — and the missing measurement was the cost side, which is flat.

### 5.11 Count fingerprints carry information that does not reach recovery

Counts retain substructure multiplicity, so they carry strictly more information
than bits. On the 1M shard they cut fingerprint ambiguity **5.6×** — 1.40% to
0.25% overall, 6.13% to 1.11% at 50–59 heavy atoms, largest collision group
39 → 5 — and the reduction factor is flat in size, so counts take a 50-atom
molecule back to roughly a 20-atom molecule's ambiguity under binary bits.

**Recovery does not follow.** On the large protocol `count_fp_100k` is **4.18
points worse** than its binary twin over 2,321 queries, −6.81 at 30–34, −1.41 at
35+, and it costs validity too (0.566 against 0.673).

What counts deliver is precision in what recovery *means*: a quarter fewer
recoveries are a different molecule with the same fingerprint (13.3% → 9.6% at
35+), and failed proposals land closer (0.651 → 0.681, between-seed sd 0.0018).

**The hypothesis was wrong, and its reasoning was sound in every step.**
Ambiguity was never what makes the cliff: 1.63% of molecules at 35–39 share a
fingerprint against 75% of queries failing there. This question was closed
twice — once at p = 0.32 on a protocol that could not see it, which was hiding a
*loss* rather than the gain re-opening was meant to find (entry 12), and once
properly.

### 5.12 The size cliff: what it is, and what it is not

Recovery falls from 0.981 below 15 heavy atoms to 0.366 at 50–64, and from 0.953
with no stereocentres to 0.355 with five or more. It is a **cliff, not a slope**:
above 40 heavy atoms the 100k models are almost never right, and above 50 no
seed ever differs from another.

Four dead explanations, each measured:

- **Not the budget.** The full-k rate is 1.000 in every band — the model never
  runs out of slots. "It runs out of guesses" is the intuitive story and it is
  false.
- **Not ranking.** The mean rank of a hit drifts only 4.4 → 8.4 across the range.
- **Not near-misses.** Best Tanimoto on a miss is 0.69 at 35–39, 0.64 at 40–49,
  0.57 above 50 — nowhere near as fast a decline as recovery's 0.28 → 0.10 →
  0.02.
- **Not ambiguity.** Of 206 misses, **2** are fingerprint collisions.

What is left is **combinatorial**. At every size the decoder proposes about
twenty molecules roughly 0.65 Tanimoto from the target, and recovery asks
whether that cloud contains an exact preimage — exponentially less likely the
bigger the molecule. Two predictions of that account held: both interventions
that work above 35 atoms work by putting more right-sized molecules in the
budget (1.93 per query at 35+, 2.56 with both) while the chance a right-sized
candidate is the preimage stays between 10.2% and 11.2% — a constant conversion
rate, which is why two interventions that each multiply the count **compose**.
And the same tightening buys less as molecules grow: 2.2–2.8 recovery points per
point of Tanimoto at 40–49, 0.4–0.9 above 50.

**The sharper mechanism is concentration, not cloud width.** Counting exact
preimages per query on the strongest model at k=60:

| band | n | rec | preimages/query | none | per hit |
|---|---|---|---|---|---|
| 30–34 | 1,189 | 0.9285 | 1.532 | 7.1% | 1.65 |
| 35–39 | 625 | 0.8912 | 1.459 | 10.9% | 1.64 |
| 40–49 | 380 | 0.7579 | 1.395 | 24.2% | 1.84 |
| 50+ | 127 | 0.4803 | 1.307 | **52.0%** | **2.72** |

**The number of preimages the model draws barely depends on size — 15% across
the range. Their distribution across queries depends on it enormously.** Above
50 atoms 52% of queries draw none at all while the successful ones draw 2.72
each; Poisson would give 0.729 against a measured 0.480. The population splits
into fingerprints the conditional can reach and fingerprints it cannot, and the
split sharpens with size. **Extra budget spends most of itself re-finding
molecules it has already found on queries it was always going to solve.**

That one mechanism also explains why more models is not a route. Of one seed's
misses above 50 atoms, **1.6%** are recovered by either of two other seeds;
96.9% of the band is missed by all three against 95.3% from chance alone. Three
*differently trained* models do no better (14.2% luck at 35+ against 13.5%), and
at equal spend one model given twenty candidates beats three given six each.
**The reachable set is not just small, it is the same small set for every
seed** — a differently initialised or differently fed copy proposes the same
neighbourhood.

Three seeds also agree on **80.1%** of the evaluation set (against 28% if they
failed independently), with median heavy atoms rising monotonically from 24 for
the unanimously solved to 34 for the unanimously missed. **The ceiling is in the
molecules.**

Training longer widens the reachable set rather than merely hitting it harder —
preimages per query rise twelvefold and the share drawing none falls 96.9% →
52.0% — but even in the best cell a third of the recovery the draw count would
support is still lost to concentration. **The cliff is being pushed back, not
dissolved.**

### 5.13 The final run: full ChEMBL at six passes

The last experiment: 8.0M parameters, all 1,881,996 training molecules, batch
128, **88,218 steps = 6.00 passes**, cosine to zero, 25.4 h of training and
27.9 h end to end. It stopped on the registered step budget, not the clock.
Scored by [`scripts/score_job4.py`](../scripts/score_job4.py) and
[`scripts/score_stage6.py`](../scripts/score_stage6.py), both written before the
run finished. Full account in
[overnight-2026-10-30.md](overnight-2026-10-30.md).

**The oracle selected the final checkpoint.** In the eight previous sessions the
selector usually preferred an earlier one; here it took step 88,218. The step
axis was still paying when the budget ended the run, and this report does not
measure where it stops.

Against the same protocol, same shard, same queries at 1.2087 passes — the only
clean before/after this programme has on the full corpus (raw-slot convention
throughout, §3.7):

| | 30+ protocol (2,321) | 50+ instrument (893) |
|---|---|---|
| rec@1 | 0.2783 → **0.6963** | 0.0258 → **0.3180** |
| rec@20 | 0.6829 → **0.9302** | 0.1501 → **0.6685** |
| rec@60 | 0.7553 → **0.9496** | 0.2251 → **0.7402** |
| structure@60 | 0.7376 → **0.9375** | 0.1624 → **0.6428** |
| collision rate among hits | 0.023 → 0.013 | 0.279 → **0.132** |
| mean fp hit rank | 7.0 → 2.5 | 16.3 → **6.6** |

**The pooled 30+ figure is not a figure about large molecules.** Half its
queries (1,189 of 2,321) are 30–34 heavy atoms, the easiest band it contains, so
the whole-protocol 0.9496 is dominated by them. Per band, same run, same
convention:

| band | n | rec@1 | rec@60 | struct@60 | collisions among hits | mean hit rank |
|---|---|---|---|---|---|---|
| 30–34 | 1,189 | 0.7788 | **0.9756** | 0.9731 | 0.003 | 2.0 |
| 35–39 | 625 | 0.7088 | 0.9600 | 0.9520 | 0.008 | 2.3 |
| 40–49 | 380 | 0.5447 | 0.9026 | 0.8842 | 0.020 | 3.6 |
| 50–64 | 127 | 0.3150 | **0.7953** | 0.6929 | 0.129 | 6.9 |

The two independent reads of 50–64 agree. Compared **within one convention**, as
§3.7 requires: in the molecule budget, 0.8110 on the 127 queries inside the 30+
protocol against 0.7615 on the dedicated 893-query instrument — 4.95 points
apart against a combined SE of 3.76, so **1.3 SE**. In raw slots the same pair
reads 0.7953 against 0.7402, 1.4 SE. The two protocols are blind in opposite
directions (§3.6) and they do not disagree.

#### The registration missed, with a direction

9 of 20 scored entries landed inside their intervals. **Every miss on a hard
band is high; every miss on a saturated or pooled band is low.** The largest:
50+ consensus rec@1 registered 0.3283–0.4401 and measured **0.5984** (+15.8 pts,
3.6 SE); the 50+ instrument's rec@60 registered 0.6310–0.6912 and measured
**0.7615** (+7.0 pts, 4.9 SE); structure@60 there +7.8 pts. Against that,
30–34 struct@1 came in 1.37 points *under* its floor and the pooled 30–39 one
point under.

So **the size extrapolation was too steep.** The laws of §5.2–§5.7 were fitted
where the cliff is severe and projected onto a run five times longer than any
that fitted them; the cliff flattened faster than they predicted. Both
directions of miss are the same error in the same model.

Registration (1), the all-slice rec@60, was declared a ceiling reading in
advance and is reported rather than scored: 0.9582 against a registered
0.9634–0.9767, an interval narrower than the metric's own 1.6-point threshold
(§3.8). It resolves nothing, which is what §3.9's fifth rule predicted and why
the weight was placed on rec@1, the hard bands and structure accuracy before the
number existed.

#### What the exponents say

Registered in §8 of [the final run plan](final-run-plan.md) before the numbers
existed, as questions against specific targets rather than intervals, because
this project has never measured the error bar on an exponent from a single pair:

| quantity | target | measured | |
|---|---|---|---|
| `b` (budget law) | 0.144–0.396 | 0.299–0.385, **every band** | holds |
| `b ÷ rec@60` | 0.320–0.380 | 5 of 6 inside; 35–39 at 0.401 | essentially holds |
| `c` at k=60 | 0.7008–0.9113 | **0.986** | miss high, as registered to expect |
| `c` per band | 1.092 / 1.083 / 0.770 / 0.381 | 1.058 / 1.080 / **0.970** / **0.802** | easy bands only |
| `g′` at 50+ | +26.30 | **+22.28** | 4.02 lower on the larger corpus |
| `g′ / f′` at 50+ | 1.52–1.68 | **1.322** | miss low |

Four consequences, and the last is the expensive one.

**The budget law transports to a ninth cell** — `b` inside its range in every
band, |r| ≥ 0.985. It is the most robust quantity in the project.

**`c` is confirmed a local slope, not a law.** The plan recorded in advance that the
honest expectation for that row was a miss. It missed high. A slope read at
30–74 passes on 100k molecules does not hold at 1.2–6 passes on 1.9M.

**`c`'s size dependence is corpus-dependent, not a property of decoding.** The
registered reading of a match was that the exponent's size structure belongs to
the problem; instead the two easy bands reproduce the 100k exponents to within
3% while 40–49 comes in 1.26× and 50+ **2.11×** higher. It transports where the
task is easy and not where it is hard — the same flattening the registration
misses showed, measured independently.

**The exchange rate between the two axes is not corpus-invariant.** `g′` at 50+
fell from +26.30 on the 1M shard to +22.28 on the full shard; against the 1M
shard's `f′` of +16.86 the ratio is 1.322 where 1.52–1.68 was registered. The plan
named what a miss would mean in advance: **passes and molecules substitute
rather than purely add.** This is the first direct counter-evidence to the
additive law of §5.6–§5.7, and it is one pair, on one corpus, with no error bar.
What survives is `b ÷ rec@60`: interventions still slide the model along one
curve rather than bending it (§5.5). What does not survive is the claim that a
doubling costs the same on either axis regardless of corpus.

#### The cliff, pushed back fifty-fold and unchanged in shape

| band | k for 0.9 | k for 0.95 | k for 0.99 |
|---|---|---|---|
| 30–34 | **1** | 9 | 669 |
| 35–39 | 5 | 30 | 1,929 |
| 40–49 | 50 | 437 | 66,912 |
| 50+ | 654 | 6,640 | 1,444,900 |

Extrapolations and lower bounds, every one. 30–34 reaching 0.9 in a single slot
is new. 50+ needing 654 is the cliff surviving everything: ~50× cheaper than a
fortnight earlier, still three orders of magnitude from the easy bands.

And §5.12's mechanism holds exactly. Preimages per query *rise* with size
(1.63 → 2.87 from 30–34 to 50+) while **18.9% of 50+ queries draw none at all**,
and the Poisson comparison shows proposals concentrated on fewer queries than
chance in every band. Six passes made the cliff much smaller without changing
what it is: concentration, not scarcity.

One thing the run did settle that no earlier session could. The collision rate
at 50+ — recoveries made by a *different* molecule with the same fingerprint,
the irreducible part of the task — **halved, 0.279 → 0.132**. Earlier models
were too weak at 50+ to distinguish the irreducible floor from their own
failure. At six passes the floor is visible, and 13.2% of 50+ recoveries are not
a modelling problem at all.

---

## 6. What is dead

Claims tested and refused, so they are not re-opened by accident:

| claim | how it died |
|---|---|
| the size defect needs a size token on the encoder | no size defect left to fix at k=60: truncation 5.1 atoms, 89.8% of 50+ queries get a right-sized proposal, closest within 0.2 atoms in every band |
| the 50+ capacity gain is a decode artefact of T=0.6 | cooling to T=0.3 moves it by +1.01 points [−0.90, +2.91] |
| validity is the binding constraint on large molecules | cooling raises validity and recovery nets zero |
| successive samples are independent draws | the deficit is a power law in k with a size-dependent exponent; independence predicted 0.9986 at 35+ against a measured 0.6890 |
| splitting a fixed budget across models beats spending it on the best one | measured and dead, at both k=20 and k=60 |
| ensembling independently-seeded models is a route | 1.6% luck above 50 atoms; the reachable set is the same for every seed |
| counts fix the size cliff | −4.18 points at 30+; ambiguity was never what made the cliff |
| recovery level and budget slope are separate dials | `b ÷ rec@60` is invariant across eight cells |
| the exponent is a property of capacity | it is training length; the comparison that said otherwise varied no capacity |
| a size-conditional decode temperature | +0.10 ± 0.25 points; cooling never hurt small molecules |
| there is latent generative capability to read out of this model | perturbing the fingerprint degrades the inverse rather than steering it; `beats original` ≤ 0.010 in every condition |
| 60+ heavy atoms is answerable from this corpus | nothing above 64 exists in it; the largest clean pool is 308 molecules against a fourfold power requirement |

---

## 7. Methodological findings

This is the most transferable part of the project, and it is the reason the
retractions ledger is kept long on purpose. **Twenty-eight claims were published
here and withdrawn.** Five causes account for all of them.

### 7.1 Cross-run comparison

Every claim that broke in the first two nights was a comparison *between* runs;
every claim that survived was measured *within* one. Later nights broke the same
way whenever two things moved at once. The canonical case is night 1's headline —
"10× data is worth +30.4 points" — where the two runs differed in compute as
well, and the control recovered **+24.9 of those points from compute alone**.

The structural fix is `compare_checkpoints.py`: one evaluation set held out of
every model's training data, one seed, one budget, one k.

### 7.2 A constant calibrated on one run, applied across runs

`oversample=2.0` was calibrated on the 100k model and handed the *stronger*
model fewer effective candidates as models improved, understating every cross-run
gap. A result was quoted at a temperature the project no longer used, making an
intervention look twice as expensive as it is. And three of the last four cost
figures were priced off a cell differing from the target in shard, fingerprint or
cadence.

**The constant is usually invisible in the result it distorts.** Its worst form
here is the convention collision of §3.7, which has now been caught **five
times** and has a structural cause in a tool's k-list. The fifth was in a draft
of this report, comparing the final run's two reads of the 50–64 band across the
two conventions; it was caught by proof-reading, which is the weakest of the
five catches and the reason §3.7 ends with a rule rather than a guard.

### 7.3 A metric averaged over a population that does not respond

The common protocol is 63% molecules under 30 heavy atoms and cannot describe
anything acting on part of the size distribution. It reported a redistribution
as a flat −1.13 points, hid a 4.18-point loss behind p = 0.32, and gave the same
whole-protocol number to two interventions moving in opposite directions.

**Report per band, always.** And an error bar is a *necessary* condition for
choosing a metric, not a sufficient one — the band chosen purely on power failed
because three fifths of it does not respond.

### 7.4 Point-estimate registrations of noisy quantities

Register the interval. Then make the intervals **tile the line**, or scoring
still needs a judgement made after the fact — night 8's result landed in a
0.85–0.88 gap nobody had named. And register the **slope, not the level**,
whenever the metric is bounded, or the test cannot distinguish *the curve bent*
from *the curve ran out of room*.

### 7.5 A premise that restates the design

"Nothing above 64 heavy atoms exists in ChEMBL as standardised here" was true
only because the standardisation *imposed* the cap, and it was load-bearing for a
decision about whether to change the cap (entry 28). **The tell is a premise
about the data whose evidence is a config default.** Checking it against the raw
file took one 120,000-row sample and found that 2.6% of ChEMBL lives above the
line. The decision survived re-derivation on a better reason; a conclusion
reached from a false premise is not a conclusion.

### 7.6 And one thing that worked, repeatedly

**Writing the number down before the run that produced it.** Three retractions
were caught *because* a prediction was on record and failed. A two-point slope
reported as a law was about to go out with a PubChem extrapolation attached; the
registration is what turned a repeat of the previous night's mistake into a
result.

Entry 27 is the clearest case. f′ was written down as an inference, labelled in
`results.md` as *the most load-bearing unverified number in this project*, and
given a run designed to kill it. **It died.** A number carrying that label and
no scheduled test is the thing to look for in any project that keeps a ledger
like this one.

The corollary is less comfortable and belongs here too: **writing the guard did
not stop the overclaim.** The 50+ capacity null was registered *with* an explicit
warning that a thin sample might produce exactly this error, and the overclaim
still went into the commit message and the README before the powered test ran.

---

## 8. Limitations

In the order a sceptical reader would ask.

- **Domain.** ChEMBL 35 only, 3–64 heavy atoms, stereochemistry stripped, twelve
  elements, 128 tokens. "50+" always means 50–64. The atom cap discards **2.558%
  of ChEMBL 35** — about 63,000 molecules, tailing to 508 heavy atoms — so it is
  a real exclusion, measured on the raw file rather than assumed. But
  **`max_tokens: 128` binds first**: 73.0% of what the atom cap discards exceeds
  the decoder's context anyway, so raising the cap alone would add 16,465
  molecules (0.87% of the corpus), selected by SMILES compactness rather than by
  chemistry. Widening the domain means a longer context and a retrain, not
  editing one default.
- **Scale.** 8M parameters, ≤1.88M molecules, one laptop GPU. The corpus slope
  of +22.09 points per doubling was measured over 90.7k–1.88M and is **not** a
  licence to extrapolate to PubChem's 10⁸. Both earlier attempts to do so are
  withdrawn.
- **The far end of the size cliff rests on thin samples.** 50–64 is 127 queries
  on the 30+ protocol and 893 on the dedicated one; 127 is the sample size that
  produced two overturned nulls. The 60+ question is closed as **unanswerable**
  from this corpus rather than answered.
- **Two recovery conventions** differ by about 4 points at k=60, and comparisons
  across tools are invalid. Every number here names its convention.
- **Nested shards.** The 10k, 100k and 1M shards are prefixes of one shuffle, so
  per-run leaderboard numbers are not comparable to each other. Only
  `compare_checkpoints.py` output is.
- **The test split has never been touched.** Everything reported anywhere in this
  project is validation, so **no number here has survived a truly untouched
  set.** This is the largest single caveat on the headline, and it is deliberate:
  an iteration loop making hundreds of choices against a number would have
  consumed the test split's meaning by night 2.
- **One architecture, one fingerprint.** Morgan r=2, 2,048 folded binary bits,
  one encoder–decoder shape. Counts were ablated; radius, bit width and
  architecture were not.
- **The step law's exponent is a local slope**, not a law — it bends, and nothing
  here measures where it stops.
- **Learning rate moves with capacity.** The 8.0M and 15.1M configs train at
  5×10⁻⁴ and 4.5×10⁻⁴, so every capacity comparison is capacity-plus-schedule.
- **One machine, one seed per cell, mostly.** Only the 8,508-step 100k cell has
  three seeds. The 0.75-point sd is measured at that one point, on a model whose
  rec@20 is 0.60, and whether it shrinks at longer budgets is unmeasured.

---

## 9. Next steps

Ordered by what they would decide, not by cost. Each is written as this project
writes them: the question, the instrument, and the number it would be read
against — because an experiment whose reading is chosen afterwards is §7.4.

**1. Where does the step axis stop? (~50 h, one run)** The oracle took the final
checkpoint of the final run, so 6.00 passes had not exhausted the full corpus.
Night 8 found a bend, but at 30–74 passes on 100k molecules, and §5.13 showed
`c` does not transport between those regimes. The bend on the full corpus has
never been located. A 12-pass run — 176,436 steps, roughly 50 h on this hardware
— would put a third point on the full-shard passes axis and is the only way to
find it. Register the **slope** between 6 and 12 passes against the measured
+22.28 per doubling at 50+, not a level, per §3.9's fifth rule. This is the
single most informative run left and it needs no new code.

**2. Put an error bar on an exponent (~6 h, two short runs).** Every exponent in
§5.13 is from one pair, and the plan registered targets rather than
intervals precisely because the noise floor has never been measured. Two
same-config runs at different seeds, scored by the same matched pair, would give
the first `sd` on `c` — and would say whether `g′ / f′` dropping from ~1.56 to
1.322 is a corpus effect or a one-pair artefact. **Until this exists, the
counter-evidence against the additive law in §5.13 should not be promoted to a
finding.** Cheapest item here and it gates the most interesting one.

**3. Attack concentration directly, not with budget (~8 h).** §5.12 and §5.13
agree the cliff is concentration: 18.9% of 50+ queries draw no preimage at all
while preimages per query *rise* with size. Every intervention tried so far buys
more draws from the same distribution, which §5.5 shows slides along one curve.
Untested: decoding that is diverse by construction rather than by temperature —
diverse beam search, or sampling without replacement over the set-encoder
attention. Register against the **"none" column** (0.189 at 50+), not against
recovery, since the mechanism is the claim. Note that two nearby ideas are
already dead (§6): size-conditional decode temperature, and ensembling
independently seeded models.

**4. Break the collisions, or accept them (~10 h).** 13.2% of 50+ recoveries are
a different molecule with the same fingerprint — an irreducible fraction of the
task as posed, now measurable for the first time (§5.13). Richer fingerprints
(counts, chirality, radius 3, 4,096 bits) would shrink it. §5.11 found count
information *does not reach recovery* at small scale, but that was measured on a
model far from this one's strength, and §5.13 is a standing warning about
transporting small-scale readings. Register against the collision rate at 50+
(0.132), with recovery as the secondary read.

**5. The untested cell: capacity on the full corpus (~60 h, needs more memory).**
§5.8 says capacity cuts a constant fraction of the deficit, measured at 100k and
1M. 25.7M parameters was infeasible on this hardware (§3.3), so the
large-model × large-corpus cell is empty, and it is exactly the cell where §5.13
suggests the small-scale laws are least trustworthy. Needs different hardware
before it is worth planning.

**6. Close the recovery/structure gap at 50+.** Recovery 0.7402 against structure
0.6428 is a 9.7-point gap, far wider than the 1–2 points elsewhere. Some is
collisions (item 4); the remainder is the model proposing the right fingerprint
by a wrong molecule in a way the easy bands do not show. Not yet a hypothesis,
which is why it is last — but it is the clearest unexplained number in the
report.

**What not to do.** §6 lists twelve measured-and-dead directions. The
pre-registration rules in §3.9 and the five recurring causes in §7 exist so they
are not repeated; the newest of them is §5.13's own, that a registered command
which has never been executed is a registration of intent rather than procedure.

---

## 10. Appendices

### 10.1 Run inventory

Every training run on disk, from `results/leaderboard.jsonl`. Per-run numbers are
**not** comparable across rows (§3.1, §3.6); the comparable tables are
`compare_checkpoints.py` output.

| run | params | shard | steps | hours | what it was for |
|---|---|---|---|---|---|
| `tiny` | 1.2M | 10k | — | 0.17 | smoke test |
| `small` | 7.95M | 100k | 8,508 | 3.75 | Phase 1, the go/no-go gate |
| `small_1m` | 7.96M | 1m | 21,117 | 7.93 | the headline model |
| `medium_1m` | 15.1M | 1m | 2,500 | 1.98 | capacity, truncated by `max_hours` |
| `small_100k_long` | 7.95M | 100k | 21,117 | 8.15 | night 1's missing control |
| `small_full` | 7.96M | full | 8,508 | 2.83 | third fixed-compute corpus point |
| `small_1m_matched` | 7.96M | 1m | 8,508 | 3.08 | the predicted third point |
| `small_100k_3ep` | 7.95M | 100k | 2,127 | 1.14 | constant-epochs, degenerate |
| `count_fp_100k` | 7.95M | 100k | 8,508 | 2.99 | count fingerprints |
| `variance_s1/2/3` | 7.95M | 100k | 8,508 | 8.98 | **the error bar** |
| `size_mix_s1/s2` | 7.95M | 100k | 8,508 | 5.79 | size-weighted mix, ×3 at 30+ |
| `size_mix_t35` | 7.95M | 100k | 8,508 | 2.88 | the second dose, ×6 at 35+ |
| `size_mix_rev` | 7.95M | 100k | 8,508 | 2.86 | the reverse-direction control |
| `medium_1m_full` | 15.1M | 1m | 21,117 | 11.54 | the capacity arm |
| `medium_1m_8k` | 15.1M | 1m | 8,508 | 6.24 | the fourth 2×2 cell |
| `small_100k_1p2` | 7.95M | 100k | 856 | 0.39 | the floor check |
| `small_full_1p2` | 7.96M | full | 17,772 | 5.27 | **f′ at constant passes** |
| `small_100k_52k` | 7.95M | 100k | 52,500 | 17.20 | step saturation |
| `small_full_6p` | 7.96M | full | 88,218 | 25.36 | **the final run** |

`base_1m` (25.7M parameters) is kept in the repo as a record of what was tried:
6.58 s/step, 20.5–25.7 h for two epochs, not an overnight run on this hardware.

### 10.2 Where the artefacts are

| | |
|---|---|
| `configs/*.yaml` | one per run; **the pre-registrations live in their headers**, written before the run |
| `results/leaderboard.jsonl` | every run, with git commit, platform, torch version and `fingerprint_id` |
| `results/overnight*/` | per-night dumps, comparisons, band tables and curves |
| `checkpoints/*/record.json` | `stopped_because`, total seconds, history |
| `docs/overnight-*.md` | the primary record, in order |
| `scripts/` | the analysis tools; each night's driver is `overnight*.sh` |

### 10.3 The tools, and what each is the authority on

| script | authority on |
|---|---|
| `compare_checkpoints.py` | the common and large protocols; the only cross-run comparisons |
| `band_analysis.py` | **every rec@60 in the molecule-budget convention**, per band |
| `miss_anatomy.py` | rec@k in raw slots; the cloud, truncation and preimage counts |
| `budget_curve.py` | the budget power law `b`, and the inverted prices |
| `step_curve.py` | the step exponent `c` |
| `paired_tests.py` | McNemar, per comparison, from its own discordance |
| `arm_table.py` | multi-seed arms with between-seed sds |
| `job4_registration.py` | the final run's registered intervals |
| `score_job4.py` | scoring those intervals, with a convention guard |
| `score_stage6.py` | scoring the final run's exponents from the matched pair |
