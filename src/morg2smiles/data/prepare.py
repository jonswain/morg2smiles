"""Build standardised, split ChEMBL shards.

Shards store **only canonical SMILES**, never fingerprints. Fingerprints are
cheap to recompute (tens of thousands per second) and tying a shard to one
:class:`~morg2smiles.fingerprints.FPConfig` would mean re-downloading and
re-standardising every time a fingerprint setting changes. The per-config
``fp_unseen`` mask is derived and cached separately, by
:mod:`morg2smiles.data.dataset`.

Standardisation choices that matter for this task:

* **Stereochemistry is stripped.** The default Morgan fingerprint is
  stereo-blind, so a target carrying stereo information asks the model to
  predict something its input cannot determine. Keeping it would put a
  permanent, invisible ceiling on recovery.
* **Salts and solvents are stripped** to the largest fragment, and charges
  neutralised where possible, so the corpus is one molecule per record.
* **Anything the tokenizer cannot round-trip is dropped** here rather than at
  training time, so a lossy example can never silently become the target.

Subsets are nested: the raw records are shuffled once under a fixed seed and
consumed in order, so the 10k shard is a subset of the 100k shard. An
improvement measured on the small shard therefore carries over meaningfully.
"""

from __future__ import annotations

import gzip
import json
import random
import shutil
import urllib.request
from collections import Counter
from dataclasses import dataclass
from multiprocessing import Pool
from pathlib import Path

import click
from rdkit import Chem, RDLogger
from rdkit.Chem.MolStandardize import rdMolStandardize
from rdkit.Chem.Scaffolds import MurckoScaffold
from tqdm import tqdm

from ..tokenizer import SmilesTokenizer, TokenizationError

RDLogger.DisableLog("rdApp.*")

__all__ = ["StandardizeConfig", "standardize", "prepare", "SUBSETS", "shard_dir"]

CHEMBL_RELEASE = 35
CHEMBL_URL = (
    "https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/"
    "chembl_{release}/chembl_{release}_chemreps.txt.gz"
)

#: Named subset sizes. ``None`` means "every molecule that survives standardisation".
SUBSETS: dict[str, int | None] = {"10k": 10_000, "100k": 100_000, "1m": 1_000_000, "full": None}

#: Organic chemistry as the model will see it. Exotic elements are rare enough
#: in ChEMBL that they only add vocabulary the decoder cannot learn to place.
ALLOWED_ELEMENTS = frozenset({"H", "B", "C", "N", "O", "F", "Si", "P", "S", "Cl", "Br", "I"})


@dataclass(frozen=True)
class StandardizeConfig:
    """Corpus filtering and normalisation settings."""

    max_heavy_atoms: int = 64
    min_heavy_atoms: int = 3
    max_tokens: int = 128
    allowed_elements: frozenset[str] = ALLOWED_ELEMENTS
    strip_stereo: bool = True

    def to_dict(self) -> dict:
        d = {
            "max_heavy_atoms": self.max_heavy_atoms,
            "min_heavy_atoms": self.min_heavy_atoms,
            "max_tokens": self.max_tokens,
            "allowed_elements": sorted(self.allowed_elements),
            "strip_stereo": self.strip_stereo,
        }
        return d


# Standardizer components are expensive to build and safe to reuse within a
# process. One set per worker process.
_LARGEST_FRAGMENT: rdMolStandardize.LargestFragmentChooser | None = None
_UNCHARGER: rdMolStandardize.Uncharger | None = None


def _components():
    global _LARGEST_FRAGMENT, _UNCHARGER
    if _LARGEST_FRAGMENT is None:
        _LARGEST_FRAGMENT = rdMolStandardize.LargestFragmentChooser()
        _UNCHARGER = rdMolStandardize.Uncharger()
    return _LARGEST_FRAGMENT, _UNCHARGER


def standardize(smiles: str, cfg: StandardizeConfig) -> tuple[str | None, str]:
    """Standardise one SMILES string.

    Returns:
        ``(canonical_smiles, "ok")`` on success, or ``(None, reason)`` where
        ``reason`` is a short tag describing why the molecule was dropped. The
        tags are tallied into the prepare report so a surprising drop rate is
        visible rather than silent.
    """
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None, "unparseable"

        largest_fragment, uncharger = _components()
        mol = largest_fragment.choose(mol)
        if mol is None:
            return None, "no_fragment"
        mol = rdMolStandardize.Normalize(mol)
        mol = uncharger.uncharge(mol)
        if cfg.strip_stereo:
            Chem.RemoveStereochemistry(mol)

        n_heavy = mol.GetNumHeavyAtoms()
        if n_heavy < cfg.min_heavy_atoms:
            return None, "too_small"
        if n_heavy > cfg.max_heavy_atoms:
            return None, "too_large"

        for atom in mol.GetAtoms():
            if atom.GetSymbol() not in cfg.allowed_elements:
                return None, "disallowed_element"

        Chem.SanitizeMol(mol)
        canonical = Chem.MolToSmiles(mol)
        if not canonical:
            return None, "empty"

        # The target string must be exactly what the tokenizer can reproduce,
        # and short enough for the decoder's context.
        try:
            n_tokens = len(SmilesTokenizer.tokenize(canonical))
        except TokenizationError:
            return None, "untokenizable"
        if n_tokens > cfg.max_tokens:
            return None, "too_many_tokens"

        # A canonical SMILES that does not itself re-parse would poison the
        # oracle. Vanishingly rare, but cheap to exclude.
        if Chem.MolFromSmiles(canonical) is None:
            return None, "unstable_canonical"

        return canonical, "ok"
    except Exception:
        return None, "exception"


_WORKER_CFG: StandardizeConfig | None = None


def _init_worker(cfg: StandardizeConfig) -> None:
    global _WORKER_CFG
    _WORKER_CFG = cfg


def _standardize_chunk(smiles_list: list[str]) -> list[tuple[str | None, str]]:
    assert _WORKER_CFG is not None
    return [standardize(s, _WORKER_CFG) for s in smiles_list]


def download_chembl(data_dir: Path, release: int = CHEMBL_RELEASE) -> Path:
    """Download the ChEMBL chemreps file, or reuse the cached copy."""
    data_dir.mkdir(parents=True, exist_ok=True)
    dest = data_dir / f"chembl_{release}_chemreps.txt.gz"
    if dest.exists() and dest.stat().st_size > 0:
        click.echo(f"using cached {dest.name} ({dest.stat().st_size / 1e6:.0f} MB)")
        return dest

    url = CHEMBL_URL.format(release=release)
    click.echo(f"downloading {url}")
    tmp = dest.with_suffix(".partial")
    with urllib.request.urlopen(url) as response, open(tmp, "wb") as out:
        total = int(response.headers.get("Content-Length", 0))
        with tqdm(total=total or None, unit="B", unit_scale=True) as bar:
            while chunk := response.read(1 << 20):
                out.write(chunk)
                bar.update(len(chunk))
    tmp.rename(dest)
    return dest


def read_raw_smiles(path: Path) -> list[str]:
    """Read the ``canonical_smiles`` column out of a chemreps TSV."""
    opener = gzip.open if path.suffix == ".gz" else open
    smiles = []
    with opener(path, "rt") as handle:
        header = handle.readline().rstrip("\n").split("\t")
        try:
            col = header.index("canonical_smiles")
        except ValueError as exc:
            raise ValueError(f"no canonical_smiles column in {path}; found {header}") from exc
        for line in tqdm(handle, desc="reading", unit=" rows"):
            parts = line.rstrip("\n").split("\t")
            if len(parts) > col and parts[col]:
                smiles.append(parts[col])
    return smiles


def shard_dir(data_dir: Path, subset: str) -> Path:
    return Path(data_dir) / "shards" / subset


def _murcko_scaffold(smiles: str) -> str:
    try:
        return MurckoScaffold.MurckoScaffoldSmiles(smiles=smiles, includeChirality=False)
    except Exception:
        return ""


def _scaffold_split(
    molecules: list[str], valid_frac: float, test_frac: float, seed: int
) -> dict[str, list[str]]:
    """Group molecules by Bemis-Murcko scaffold, then assign whole groups.

    A secondary, harder probe: the random split tells you how the model does on
    chemistry it has seen the shape of, this one on chemistry it has not.
    """
    groups: dict[str, list[str]] = {}
    for smiles in molecules:
        groups.setdefault(_murcko_scaffold(smiles), []).append(smiles)

    # Largest groups into train first, so the small splits stay close to their
    # target size rather than being dominated by one huge scaffold family.
    ordered = sorted(groups.values(), key=len, reverse=True)
    rng = random.Random(seed)
    rng.shuffle(ordered)

    n = len(molecules)
    targets = {"test": int(n * test_frac), "valid": int(n * valid_frac)}
    splits: dict[str, list[str]] = {"train": [], "valid": [], "test": []}
    for group in ordered:
        for name in ("test", "valid"):
            if len(splits[name]) < targets[name]:
                splits[name].extend(group)
                break
        else:
            splits["train"].extend(group)
    return splits


def prepare(
    subset: str = "10k",
    *,
    data_dir: Path = Path("data"),
    release: int = CHEMBL_RELEASE,
    source: Path | None = None,
    cfg: StandardizeConfig = StandardizeConfig(),
    seed: int = 0,
    valid_frac: float = 0.05,
    test_frac: float = 0.05,
    processes: int | None = None,
    overwrite: bool = False,
    exclude: tuple[Path, ...] = (),
) -> Path:
    """Download, standardise, deduplicate and split ChEMBL into a shard set.

    Args:
        subset: One of :data:`SUBSETS`.
        data_dir: Root for downloads and shards.
        release: ChEMBL release number. Pinned by default so benchmarks are
            reproducible.
        source: Use this local chemreps file instead of downloading.
        cfg: Standardisation and filtering settings.
        seed: Controls both the shuffle of raw records and the split. Fixed
            seeds keep subsets nested and splits stable across runs.
        valid_frac: Validation fraction. The iteration loop optimises against
            this split; the test split is left alone.
        test_frac: Test fraction, for occasional, deliberate measurement.
        processes: Worker processes for standardisation. Defaults to all cores.
        overwrite: Rebuild shards that already exist.
        exclude: SMILES files whose molecules must not enter *any* split of
            this shard. Shards are nested by construction, so a larger shard
            normally swallows a smaller one's held-out molecules -- 90% of the
            100k shard's validation split sits inside the 1M shard's training
            set. That makes two models trained on different shards impossible
            to compare honestly on either one's own split. Passing the smaller
            shards' valid and test files here keeps one evaluation set clean
            across every model. The removed molecules are written to
            ``excluded.smi`` for the record.

    Returns:
        The shard directory.
    """
    if subset not in SUBSETS:
        raise ValueError(f"unknown subset {subset!r}; expected one of {sorted(SUBSETS)}")

    out_dir = shard_dir(data_dir, subset)
    if out_dir.exists() and not overwrite:
        if (out_dir / "meta.json").exists():
            click.echo(f"{out_dir} already prepared; pass --overwrite to rebuild")
            return out_dir
        shutil.rmtree(out_dir)

    raw_path = Path(source) if source else download_chembl(Path(data_dir) / "raw", release)
    raw = read_raw_smiles(raw_path)
    click.echo(f"{len(raw):,} raw records")

    # One fixed shuffle, consumed in order, makes the subsets nested.
    random.Random(seed).shuffle(raw)

    target = SUBSETS[subset]
    reasons: Counter[str] = Counter()
    seen: set[str] = set()
    molecules: list[str] = []

    chunk_size = 2000
    chunks = [raw[i : i + chunk_size] for i in range(0, len(raw), chunk_size)]
    desc = f"standardising -> {subset}"
    with Pool(processes, initializer=_init_worker, initargs=(cfg,)) as pool:
        with tqdm(total=target or len(raw), desc=desc, unit=" mol") as bar:
            for results in pool.imap(_standardize_chunk, chunks):
                for canonical, reason in results:
                    reasons[reason] += 1
                    if canonical is None:
                        continue
                    if canonical in seen:
                        reasons["duplicate"] += 1
                        continue
                    seen.add(canonical)
                    molecules.append(canonical)
                    if target:
                        bar.update(1)
                if not target:
                    bar.update(len(results))
                if target and len(molecules) >= target:
                    break
            pool.terminate()

    if target and len(molecules) < target:
        click.echo(f"warning: only {len(molecules):,} molecules available, wanted {target:,}")
    click.echo(f"{len(molecules):,} unique standardised molecules")

    excluded: list[str] = []
    if exclude:
        blocked: set[str] = set()
        for path in exclude:
            text = Path(path).read_text().split("\n")
            blocked.update(line.strip() for line in text if line.strip())
        click.echo(f"excluding {len(blocked):,} molecules named by --exclude")
        kept = [m for m in molecules if m not in blocked]
        excluded = [m for m in molecules if m in blocked]
        click.echo(f"{len(excluded):,} of them were present; {len(kept):,} molecules remain")
        molecules = kept

    # Random split. Deduplication happened above, so no canonical SMILES can
    # appear in two splits.
    rng = random.Random(seed + 1)
    shuffled = molecules.copy()
    rng.shuffle(shuffled)
    n_test = int(len(shuffled) * test_frac)
    n_valid = int(len(shuffled) * valid_frac)
    splits = {
        "test": shuffled[:n_test],
        "valid": shuffled[n_test : n_test + n_valid],
        "train": shuffled[n_test + n_valid :],
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    for name, members in splits.items():
        (out_dir / f"{name}.smi").write_text("\n".join(members) + "\n")

    if excluded:
        (out_dir / "excluded.smi").write_text("\n".join(excluded) + "\n")

    scaffold_splits = _scaffold_split(molecules, valid_frac, test_frac, seed + 2)
    scaffold_dir = out_dir / "scaffold"
    scaffold_dir.mkdir(exist_ok=True)
    for name, members in scaffold_splits.items():
        (scaffold_dir / f"{name}.smi").write_text("\n".join(members) + "\n")

    meta = {
        "subset": subset,
        "chembl_release": release if source is None else f"local:{Path(source).name}",
        "seed": seed,
        "standardize": cfg.to_dict(),
        "n_molecules": len(molecules),
        "n_excluded": len(excluded),
        "exclude_files": [str(path) for path in exclude],
        "splits": {name: len(members) for name, members in splits.items()},
        "scaffold_splits": {name: len(m) for name, m in scaffold_splits.items()},
        "drop_reasons": dict(reasons.most_common()),
        "records_consumed": sum(reasons.values()),
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    click.echo(f"wrote {out_dir}")
    for name, members in splits.items():
        click.echo(f"  {name:<6} {len(members):>9,}")
    kept = reasons["ok"]
    consumed = sum(reasons.values())
    if consumed:
        click.echo(f"  standardisation kept {kept / consumed:.1%} of {consumed:,} records consumed")
    return out_dir


@click.command()
@click.option("--subset", default="10k", type=click.Choice(sorted(SUBSETS)), show_default=True)
@click.option("--data-dir", default="data", type=click.Path(path_type=Path), show_default=True)
@click.option("--release", default=CHEMBL_RELEASE, show_default=True, help="ChEMBL release number.")
@click.option("--source", type=click.Path(exists=True, path_type=Path), help="Local chemreps file.")
@click.option("--seed", default=0, show_default=True)
@click.option("--max-heavy-atoms", default=64, show_default=True)
@click.option("--max-tokens", default=128, show_default=True)
@click.option("--processes", default=None, type=int, help="Defaults to all cores.")
@click.option("--overwrite", is_flag=True)
@click.option(
    "--exclude",
    multiple=True,
    type=click.Path(exists=True, path_type=Path),
    help="SMILES file whose molecules must not enter this shard. Repeatable.",
)
def main(
    subset,
    data_dir,
    release,
    source,
    seed,
    max_heavy_atoms,
    max_tokens,
    processes,
    overwrite,
    exclude,
):
    """Prepare ChEMBL shards for training and evaluation."""
    prepare(
        subset,
        data_dir=data_dir,
        release=release,
        source=source,
        cfg=StandardizeConfig(max_heavy_atoms=max_heavy_atoms, max_tokens=max_tokens),
        seed=seed,
        processes=processes,
        overwrite=overwrite,
        exclude=tuple(exclude),
    )


if __name__ == "__main__":
    main()
