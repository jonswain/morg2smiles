"""Atom-level SMILES tokenizer.

Character-level tokenization splits multi-character atoms (``Cl`` into ``C`` +
``l``, bracket atoms into their innards), which forces the decoder to spend
capacity relearning SMILES lexing. The regex below is the standard atom-level
pattern: one token per atom, ring closure, bond or branch symbol.

Tokenization must be lossless -- ``"".join(tokenize(s)) == s`` for every SMILES
the model is trained on -- otherwise the target the model learns is not the
string the oracle will check. :meth:`SmilesTokenizer.tokenize` enforces this.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

__all__ = ["SmilesTokenizer", "SMILES_TOKEN_PATTERN", "TokenizationError"]

#: One token per atom / bond / branch / ring-closure symbol.
#: Order matters: two-character atoms must precede their one-character prefixes,
#: and ``%NN`` ring closures must precede bare digits.
SMILES_TOKEN_PATTERN = (
    r"(\[[^\]]+\]"  # bracket atom, e.g. [nH], [C@@H], [Na+]
    r"|Br|Cl"  # two-letter organic-subset atoms
    r"|B|C|N|O|S|P|F|I"  # one-letter organic-subset atoms
    r"|b|c|n|o|s|p"  # aromatic atoms
    r"|%\d{2}"  # two-digit ring closure
    r"|\d"  # one-digit ring closure
    r"|\(|\)"  # branches
    r"|\.|=|#|\$|:|~|-|\+|\\|/|@|\*)"  # bonds and modifiers
)

_TOKEN_RE = re.compile(SMILES_TOKEN_PATTERN)

PAD, BOS, EOS, UNK = "<pad>", "<bos>", "<eos>", "<unk>"
SPECIAL_TOKENS = (PAD, BOS, EOS, UNK)


class TokenizationError(ValueError):
    """Raised when a SMILES string cannot be tokenized losslessly."""


class SmilesTokenizer:
    """Maps SMILES strings to and from integer sequences.

    The vocabulary is built from the training corpus and saved beside the
    checkpoint, so a loaded model always decodes with the ids it was trained on.
    """

    def __init__(self, tokens: Iterable[str]):
        vocab = list(SPECIAL_TOKENS)
        vocab += [t for t in tokens if t not in SPECIAL_TOKENS]
        if len(set(vocab)) != len(vocab):
            dupes = [t for t, n in Counter(vocab).items() if n > 1]
            raise ValueError(f"duplicate tokens in vocabulary: {dupes}")
        self.itos: list[str] = vocab
        self.stoi: dict[str, int] = {t: i for i, t in enumerate(vocab)}

    # -- ids for the special tokens -------------------------------------------
    @property
    def pad_id(self) -> int:
        return self.stoi[PAD]

    @property
    def bos_id(self) -> int:
        return self.stoi[BOS]

    @property
    def eos_id(self) -> int:
        return self.stoi[EOS]

    @property
    def unk_id(self) -> int:
        return self.stoi[UNK]

    def __len__(self) -> int:
        return len(self.itos)

    # -- tokenization ----------------------------------------------------------
    @staticmethod
    def tokenize(smiles: str) -> list[str]:
        """Split a SMILES string into atom-level tokens.

        Raises:
            TokenizationError: If the tokens do not rejoin to the input, which
                means the pattern failed to cover some character.
        """
        tokens = _TOKEN_RE.findall(smiles)
        if "".join(tokens) != smiles:
            raise TokenizationError(
                f"lossy tokenization of {smiles!r}: rejoined as {''.join(tokens)!r}"
            )
        return tokens

    def encode(self, smiles: str, *, add_special: bool = True) -> list[int]:
        """Encode a SMILES string to token ids, with ``<bos>``/``<eos>`` by default."""
        ids = [self.stoi.get(t, self.unk_id) for t in self.tokenize(smiles)]
        if add_special:
            ids = [self.bos_id, *ids, self.eos_id]
        return ids

    def decode(self, ids: Iterable[int]) -> str:
        """Decode token ids back to a SMILES string.

        Stops at the first ``<eos>`` and drops all special tokens, so raw model
        output can be passed in directly.
        """
        out: list[str] = []
        specials = {self.pad_id, self.bos_id, self.unk_id}
        for i in ids:
            i = int(i)
            if i == self.eos_id:
                break
            if i in specials:
                continue
            out.append(self.itos[i])
        return "".join(out)

    # -- construction and persistence -------------------------------------------
    @classmethod
    def build(cls, corpus: Iterable[str], *, min_count: int = 1) -> SmilesTokenizer:
        """Build a vocabulary from a corpus of SMILES strings.

        Args:
            corpus: The training SMILES.
            min_count: Drop tokens rarer than this; they decode as ``<unk>``,
                which cannot produce a valid molecule, so the default keeps
                everything.
        """
        counts = Counter()
        for smiles in corpus:
            counts.update(cls.tokenize(smiles))
        tokens = sorted(t for t, n in counts.items() if n >= min_count)
        return cls(tokens)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"tokens": self.itos}, indent=2))

    @classmethod
    def load(cls, path: str | Path) -> SmilesTokenizer:
        tokens = json.loads(Path(path).read_text())["tokens"]
        if tokens[: len(SPECIAL_TOKENS)] != list(SPECIAL_TOKENS):
            raise ValueError(f"vocabulary at {path} does not start with the special tokens")
        return cls(tokens[len(SPECIAL_TOKENS) :])

    def to_dict(self) -> dict:
        return {"tokens": self.itos}

    @classmethod
    def from_dict(cls, d: dict) -> SmilesTokenizer:
        return cls(d["tokens"][len(SPECIAL_TOKENS) :])
