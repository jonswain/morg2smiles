"""Decoding defaults, in one small module both the CLI and the model can import.

A value used in a ``click`` option decorator has to exist at import time, and
:mod:`morg2smiles.cli` otherwise keeps its heavier imports inside its command
bodies; giving the constant its own module keeps that arrangement and gives it
one obvious home rather than two copies.
"""

from __future__ import annotations

DEFAULT_TEMPERATURE = 0.6
"""Softmax temperature for user-facing generation.

Measured, not guessed. On the common protocol of 1,956 fingerprint-unseen
molecules, sampling ``small_1m`` at 0.6 rather than 1.0 is worth +1.99 points of
recovery@20 (0.8962 -> 0.9162, McNemar p = 1.3e-05), and it wins at every
matched candidate budget, so the gain is the decoder rather than the 18% extra
strings a colder decoder draws while trying to fill its budget. Essentially all
of it is on large molecules: +7.5 points at 35 or more heavy atoms against +0.75
below. 0.6 and 0.7 are not distinguishable from each other (p = 0.056) and
colder than 0.5 is worse, so this sits on a plateau rather than a peak.

Deliberately *not* the default in
:func:`morg2smiles.evaluation.generate_outcomes` or
:func:`morg2smiles.generate.sample`, which stay at 1.0 so that every number this
project has published keeps its meaning and re-scoring an old checkpoint
reproduces it exactly. See docs/overnight-2026-10-15.md, stages 6 to 10.
"""


TEMPERATURE_POOL = (0.6, 0.7, 1.0)
"""Temperatures to pool when one sampling pass is not the budget.

Also measured. Drawing candidates at these three temperatures from *one* model
and ranking the union by how many spellings it received gives recovery@20
0.9279 on the common protocol -- the best this project has recorded, +1.18
points over sampling at 0.6 alone (McNemar p = 6.6e-05), and ahead of pooling
three *differently trained* checkpoints (0.9039). It costs three forward passes
per query; capping each arm so the three together draw what 0.6 alone draws
still gives 0.9238 (+0.77, p = 0.006), so what buys the gain is mixing
temperatures rather than drawing more.

The reason it works: a model's samples at one temperature exhaust their
diversity quickly -- night 4 found extra candidates at a fixed temperature buy
nothing past about 80 -- while a cold arm and a hot arm make *different*
mistakes. Not the default for :meth:`morg2smiles.generate.Morg2Smiles.generate`,
because a default that silently triples the work is the caller's decision to
make: pass ``temperature=TEMPERATURE_POOL`` to take it.
"""
