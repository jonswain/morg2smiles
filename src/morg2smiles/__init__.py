"""Morg2SMILES: generative recovery of SMILES strings from Morgan fingerprints.

The task is to invert something normally treated as one-way. Folding and hash
collisions make the mapping genuinely many-to-one, so this is a generative
model, used with a budget of k guesses and an exact oracle:

    >>> from morg2smiles import FPConfig, Morg2Smiles, compute
    >>> cfg = FPConfig()                        # morgan r=2, binary, 2048 bits
    >>> fp = compute("CC(=O)Oc1ccccc1C(=O)O", cfg)
    >>> model = Morg2Smiles.load("checkpoints/best.pt")
    >>> model.generate(fp, k=20)                # verified matches first

The headline metric is recovery@k on fingerprints absent from training; see
:mod:`morg2smiles.metrics` for why that qualifier is the whole point.
"""

from .fingerprints import FPConfig, compute, compute_dense, tanimoto
from .generate import Morg2Smiles
from .metrics import evaluate, recovery_at_k
from .model import ModelConfig, Morg2SmilesModel
from .oracle import OracleResult, check
from .tokenizer import SmilesTokenizer

__version__ = "0.1.0"

__all__ = [
    "FPConfig",
    "ModelConfig",
    "Morg2Smiles",
    "Morg2SmilesModel",
    "OracleResult",
    "SmilesTokenizer",
    "check",
    "compute",
    "compute_dense",
    "evaluate",
    "recovery_at_k",
    "tanimoto",
    "__version__",
]
