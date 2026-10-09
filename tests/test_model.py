"""Tests for the model and generation.

The load-bearing test here is
:func:`test_incremental_decoding_matches_full_prefix`. Generation uses a
per-layer key/value cache for speed, and a subtle cache bug -- a stale entry, a
missed beam reorder, an off-by-one in the position offset -- would not crash.
It would just make sampled molecules slightly wrong, which looks exactly like a
model that has not learned. Numerical equivalence with the uncached path is the
only cheap way to tell those apart.
"""

from __future__ import annotations

import pytest
import torch

from morg2smiles.data.dataset import FingerprintDataset, collate
from morg2smiles.fingerprints import FPConfig, compute
from morg2smiles.generate import Morg2Smiles, beam_search, sample
from morg2smiles.model import ModelConfig, Morg2SmilesModel, build_model
from morg2smiles.tokenizer import SmilesTokenizer

MOLECULES = [
    "CC(=O)Oc1ccccc1C(=O)O",
    "CC(C)Cc1ccc(C(C)C(=O)O)cc1",
    "CN1C=NC2=C1C(=O)N(C)C(=O)N2C",
    "CCO",
    "c1ccccc1",
    "O=S(=O)(N)c1ccccc1",
]

def _padded_tokens(tokenizer: SmilesTokenizer, length: int) -> torch.Tensor:
    """A fixed-width token batch over MOLECULES, padded to `length`."""
    rows = []
    for smiles in MOLECULES:
        ids = tokenizer.encode(smiles)[:length]
        ids += [tokenizer.pad_id] * (length - len(ids))
        rows.append(torch.tensor(ids))
    return torch.stack(rows)


TINY = ModelConfig(
    d_model=64, n_heads=4, d_ff=128, n_encoder_layers=2, n_decoder_layers=2, max_tokens=48
)


@pytest.fixture
def tokenizer():
    return SmilesTokenizer.build(MOLECULES)


@pytest.fixture
def model(tokenizer):
    torch.manual_seed(0)
    return build_model(TINY, FPConfig(), tokenizer).eval()


@pytest.fixture
def fps():
    return [compute(s, FPConfig()) for s in MOLECULES]


# -- construction --------------------------------------------------------------
def test_build_model_fills_derived_config(tokenizer):
    model = build_model(TINY, FPConfig(n_bits=1024), tokenizer)
    assert model.cfg.vocab_size == len(tokenizer)
    assert model.cfg.fp_vocab_size == 1024


def test_mismatched_vocab_size_rejected(tokenizer):
    with pytest.raises(ValueError, match="vocab_size"):
        Morg2SmilesModel(ModelConfig(vocab_size=999), FPConfig(), tokenizer)


def test_mismatched_fp_vocab_rejected(tokenizer):
    cfg = ModelConfig(vocab_size=len(tokenizer), fp_vocab_size=99)
    with pytest.raises(ValueError, match="fp_vocab_size"):
        Morg2SmilesModel(cfg, FPConfig(), tokenizer)


def test_d_model_must_divide_heads():
    with pytest.raises(ValueError, match="divisible"):
        ModelConfig(d_model=100, n_heads=8)


def test_output_weight_is_tied(model):
    assert model.output.weight is model.token_embedding.weight


# -- forward pass --------------------------------------------------------------
def test_forward_shapes_and_finiteness(model, tokenizer):
    ds = FingerprintDataset(MOLECULES, FPConfig(), tokenizer, max_tokens=TINY.max_tokens)
    batch = collate([ds[i] for i in range(len(MOLECULES))], tokenizer.pad_id)
    logits = model(
        batch["fp_indices"], batch["fp_counts"], batch["fp_mask"], batch["tokens"]
    )
    assert logits.shape == (len(MOLECULES), batch["tokens"].size(1) - 1, len(tokenizer))
    assert torch.isfinite(logits).all()


def test_backward_produces_finite_gradients(model, tokenizer):
    ds = FingerprintDataset(MOLECULES, FPConfig(), tokenizer, max_tokens=TINY.max_tokens)
    batch = collate([ds[i] for i in range(len(MOLECULES))], tokenizer.pad_id)
    logits = model(batch["fp_indices"], batch["fp_counts"], batch["fp_mask"], batch["tokens"])
    loss = torch.nn.functional.cross_entropy(
        logits.reshape(-1, logits.size(-1)),
        batch["tokens"][:, 1:].reshape(-1),
        ignore_index=tokenizer.pad_id,
    )
    loss.backward()
    grads = [p.grad for p in model.parameters() if p.grad is not None]
    assert grads
    assert all(torch.isfinite(g).all() for g in grads)


def test_padded_fingerprint_bits_do_not_change_the_output(model, tokenizer):
    """Padding must be masked out, not silently attended to."""
    ds = FingerprintDataset(MOLECULES, FPConfig(), tokenizer, max_tokens=TINY.max_tokens)
    items = [ds[0], ds[3]]  # very different numbers of set bits
    batch = collate(items, tokenizer.pad_id)

    memory, pad_mask = model.encode_fp(
        batch["fp_indices"], batch["fp_counts"], batch["fp_mask"]
    )
    tokens = batch["tokens"][:, :4]
    with torch.no_grad():
        before = model.decode_step(tokens, memory, pad_mask)

    # Corrupt the padded positions only; a correctly masked model ignores them.
    corrupted = batch["fp_indices"].clone()
    corrupted[~batch["fp_mask"]] = 7
    memory2, pad_mask2 = model.encode_fp(corrupted, batch["fp_counts"], batch["fp_mask"])
    with torch.no_grad():
        after = model.decode_step(tokens, memory2, pad_mask2)

    assert torch.allclose(before, after, atol=1e-5)


def test_empty_fingerprint_does_not_produce_nan(model):
    """An all-masked attention row would otherwise yield NaN and poison the batch."""
    indices = torch.zeros(1, 4, dtype=torch.long)
    counts = torch.zeros(1, 4, dtype=torch.long)
    mask = torch.zeros(1, 4, dtype=torch.bool)
    memory, pad_mask = model.encode_fp(indices, counts, mask)
    assert torch.isfinite(memory).all()


# -- the cache -----------------------------------------------------------------
def test_incremental_decoding_matches_full_prefix(model, tokenizer, fps):
    """Cached step-by-step decoding must equal uncached whole-prefix decoding.

    This is what certifies the generation fast path. A cache bug here would
    silently degrade sampled molecules rather than fail.
    """
    from morg2smiles.generate import _batch_inputs

    indices, counts, mask = _batch_inputs(fps, FPConfig(), torch.device("cpu"))
    memory, pad_mask = model.encode_fp(indices, counts, mask)
    tokens = _padded_tokens(tokenizer, 10)

    with torch.no_grad():
        full = model.decode_step(tokens, memory, pad_mask)
        caches = model.new_caches(tokens.size(0), device=torch.device("cpu"))
        steps = [
            model.decode_step(tokens[:, p : p + 1], memory, pad_mask, caches=caches, offset=p)
            for p in range(tokens.size(1))
        ]
        incremental = torch.cat(steps, dim=1)

    assert torch.allclose(full, incremental, atol=1e-4)


def test_position_offset_is_respected(model, tokenizer, fps):
    """Decoding at an offset must differ from decoding at position zero."""
    from morg2smiles.generate import _batch_inputs

    indices, counts, mask = _batch_inputs(fps[:1], FPConfig(), torch.device("cpu"))
    memory, pad_mask = model.encode_fp(indices, counts, mask)
    token = torch.tensor([[tokenizer.stoi["C"]]])
    with torch.no_grad():
        at_zero = model.decode_step(token, memory, pad_mask, caches=model.new_caches(1, device=torch.device("cpu")), offset=0)
        at_five = model.decode_step(token, memory, pad_mask, caches=model.new_caches(1, device=torch.device("cpu")), offset=5)
    assert not torch.allclose(at_zero, at_five)


def test_decoding_past_max_tokens_raises(model, tokenizer, fps):
    from morg2smiles.generate import _batch_inputs

    indices, counts, mask = _batch_inputs(fps[:1], FPConfig(), torch.device("cpu"))
    memory, pad_mask = model.encode_fp(indices, counts, mask)
    token = torch.tensor([[tokenizer.bos_id]])
    with pytest.raises(ValueError, match="max_tokens"):
        model.decode_step(token, memory, pad_mask, offset=TINY.max_tokens)


# -- sampling ------------------------------------------------------------------
def test_sample_returns_k_per_query(model, fps):
    out = sample(model, fps, k=5, max_tokens=24, device=torch.device("cpu"))
    assert len(out) == len(fps)
    assert all(len(c) == 5 for c in out)
    assert all(isinstance(s, str) for c in out for s in c)


def test_sample_on_empty_input(model):
    assert sample(model, [], k=5, device=torch.device("cpu")) == []


def test_sampling_is_diverse_but_greedy_is_not(model, fps):
    """Low temperature should collapse to near-identical strings, high should not."""
    cold = sample(model, fps[:1], k=8, temperature=0.01, max_tokens=24, device=torch.device("cpu"))[0]
    hot = sample(model, fps[:1], k=8, temperature=2.0, max_tokens=24, device=torch.device("cpu"))[0]
    assert len(set(cold)) <= len(set(hot))


def test_top_p_and_top_k_filtering_run(model, fps):
    out = sample(
        model, fps[:2], k=4, top_p=0.9, top_k=5, max_tokens=24, device=torch.device("cpu")
    )
    assert len(out) == 2


def test_sample_respects_max_tokens(model, fps, tokenizer):
    """No candidate may exceed the context the model was built for."""
    out = sample(model, fps, k=4, max_tokens=12, device=torch.device("cpu"))
    for candidates in out:
        for smiles in candidates:
            assert len(SmilesTokenizer.tokenize(smiles)) <= 12


def test_beam_search_returns_strings(model, fps):
    out = beam_search(model, fps[0], k=5, max_tokens=24, device=torch.device("cpu"))
    assert 0 < len(out) <= 5
    assert all(isinstance(s, str) for s in out)


def test_beam_search_wider_than_k(model, fps):
    out = beam_search(model, fps[0], k=3, beam_width=8, max_tokens=24, device=torch.device("cpu"))
    assert len(out) <= 3


# -- persistence and the public API --------------------------------------------
def test_save_load_round_trip_preserves_outputs(model, tokenizer, fps, tmp_path):
    path = tmp_path / "model.pt"
    model.save(path, epoch=3, note="test")
    loaded, ckpt = Morg2SmilesModel.load(path)

    assert ckpt["epoch"] == 3
    assert loaded.cfg == model.cfg
    assert loaded.fp_cfg == model.fp_cfg
    assert loaded.tokenizer.itos == tokenizer.itos

    from morg2smiles.generate import _batch_inputs

    indices, counts, mask = _batch_inputs(fps, FPConfig(), torch.device("cpu"))
    tokens = _padded_tokens(tokenizer, 8)
    with torch.no_grad():
        a = model(indices, counts, mask, tokens)
        b = loaded(indices, counts, mask, tokens)
    assert torch.allclose(a, b, atol=1e-6)


def test_checkpoint_carries_the_fingerprint_config(model, tmp_path):
    """So a model can never be evaluated under settings it was not trained for."""
    path = tmp_path / "model.pt"
    model.save(path)
    loaded, _ = Morg2SmilesModel.load(path)
    assert loaded.fp_cfg.fingerprint_id == model.fp_cfg.fingerprint_id


def test_public_api_generate(model, tmp_path, fps):
    path = tmp_path / "model.pt"
    model.save(path)
    wrapper = Morg2Smiles.load(path, device="cpu")
    out = wrapper.generate(fps[0], k=4, max_tokens=24)
    assert len(out) <= 4
    assert wrapper.fp_config == FPConfig()


def test_public_api_accepts_dense_fingerprints(model, tmp_path):
    from morg2smiles.fingerprints import compute_dense

    path = tmp_path / "model.pt"
    model.save(path)
    wrapper = Morg2Smiles.load(path, device="cpu")
    dense = compute_dense(MOLECULES[0], FPConfig())
    assert len(wrapper.generate(dense, k=3, max_tokens=24)) <= 3


def test_public_api_rejects_wrong_width(model, tmp_path):
    import numpy as np

    path = tmp_path / "model.pt"
    model.save(path)
    wrapper = Morg2Smiles.load(path, device="cpu")
    with pytest.raises(ValueError, match="bits"):
        wrapper.generate(np.zeros(512), k=2)


def test_public_api_rejects_unknown_strategy(model, tmp_path, fps):
    path = tmp_path / "model.pt"
    model.save(path)
    wrapper = Morg2Smiles.load(path, device="cpu")
    with pytest.raises(ValueError, match="unknown strategy"):
        wrapper.generate(fps[0], k=2, strategy="nonsense")
