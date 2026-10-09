"""The fingerprint-conditioned autoregressive decoder.

**How the fingerprint enters the model** is the decision that matters most.

The obvious choice -- a 2048-to-d_model dense projection -- is a poor fit. It
asks one weight matrix to encode a sparse, unordered set, gives the decoder a
single summary vector to attend to, and spends 98% of its compute on zeros (a
drug-like molecule sets only ~50 of 2048 bits).

Instead the fingerprint is treated as **a set of set bits**. Each set bit
becomes a token, embedded by its identifier plus its count, with *no positional
encoding* because a fingerprint has no order. A transformer encoder over that
short sequence produces a cross-attention memory the decoder queries bit by
bit, so generating an atom can attend to the specific environments implying it.
The same code path serves binary and count fingerprints (binary is count
clamped to 1) and folded and unfolded ones (unfolded identifiers are hashed
into the embedding table by the dataset).

**Why the decoder is hand-written** rather than ``nn.TransformerDecoder``:
evaluation generates k candidates per query, so the iteration loop lives or
dies on generation throughput. ``nn.TransformerDecoder`` has no incremental
decoding, which makes each step re-attend over the whole prefix -- quadratic
work per sequence and, measured on an M2, roughly 2 s per query. The layers
here keep a per-layer key/value cache (:class:`LayerCache`), including the
cross-attention projections of the fixed memory, which makes each step attend
over one new token instead.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from pathlib import Path

import torch
import torch.nn.functional as F
from torch import Tensor, nn

from .data.dataset import MAX_COUNT
from .fingerprints import FPConfig
from .tokenizer import SmilesTokenizer

__all__ = ["ModelConfig", "Morg2SmilesModel", "build_model", "select_device", "LayerCache"]


def select_device(preference: str = "auto") -> torch.device:
    """Pick a compute device.

    Order is MPS, then CUDA, then CPU -- this project is developed on an Apple
    machine, but nothing here is MPS-specific, so a CUDA box runs the same code
    and configs unchanged.
    """
    if preference != "auto":
        return torch.device(preference)
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


@dataclass(frozen=True)
class ModelConfig:
    """Architecture hyperparameters.

    Defaults are sized for an M2: ~25M parameters, large enough that failing to
    learn is informative, small enough to train on the 100k shard overnight.
    """

    d_model: int = 384
    n_heads: int = 8
    d_ff: int = 1536
    n_encoder_layers: int = 6
    n_decoder_layers: int = 6
    dropout: float = 0.1
    max_tokens: int = 128
    #: Token vocabulary size; set from the tokenizer by :func:`build_model`.
    vocab_size: int = 0
    #: Fingerprint identifier space; set from :attr:`FPConfig.vocab_size`.
    fp_vocab_size: int = 2048

    def __post_init__(self) -> None:
        if self.d_model % self.n_heads:
            raise ValueError(f"d_model {self.d_model} not divisible by n_heads {self.n_heads}")

    @property
    def head_dim(self) -> int:
        return self.d_model // self.n_heads

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> ModelConfig:
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in d.items() if k in known})


class LayerCache:
    """Per-layer key/value cache for incremental decoding.

    The self-attention buffers are **preallocated to the full sequence length
    and written in place**. The obvious implementation grows them with
    ``torch.cat`` each step, which reallocates and copies the whole prefix every
    token, for every layer -- quadratic memory traffic that measured
    catastrophically and erratically on MPS (sampling cost varied by 25x with
    batch size, non-monotonically, as the allocator thrashed). Writing into a
    fixed buffer and slicing a view costs nothing per step.

    The cross-attention projections of the memory are constant across steps, so
    they are computed once per sequence rather than once per token.
    """

    def __init__(
        self,
        batch: int,
        n_heads: int,
        head_dim: int,
        max_len: int,
        device: torch.device,
        dtype: torch.dtype,
    ):
        shape = (batch, n_heads, max_len, head_dim)
        self.self_k = torch.zeros(shape, device=device, dtype=dtype)
        self.self_v = torch.zeros(shape, device=device, dtype=dtype)
        self.length = 0
        self.cross_k: Tensor | None = None
        self.cross_v: Tensor | None = None

    def append(self, k: Tensor, v: Tensor) -> tuple[Tensor, Tensor]:
        """Write this step's keys and values, and return views of the prefix."""
        new = k.size(2)
        if self.length + new > self.self_k.size(2):
            raise ValueError(
                f"cache overflow: {self.length + new} positions exceeds "
                f"capacity {self.self_k.size(2)}"
            )
        self.self_k[:, :, self.length : self.length + new] = k
        self.self_v[:, :, self.length : self.length + new] = v
        self.length += new
        return self.self_k[:, :, : self.length], self.self_v[:, :, : self.length]

    def reorder(self, index: Tensor) -> None:
        """Permute (and expand) the cache to follow beam selection.

        ``index`` maps each new beam to the old beam it continues, so this also
        handles the first step's one-to-width expansion.
        """
        self.self_k = self.self_k.index_select(0, index)
        self.self_v = self.self_v.index_select(0, index)
        if self.cross_k is not None:
            self.cross_k = self.cross_k.index_select(0, index)
            self.cross_v = self.cross_v.index_select(0, index)


class SelfAttention(nn.Module):
    """Causal multi-head self-attention with an optional incremental cache."""

    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.n_heads = cfg.n_heads
        self.head_dim = cfg.head_dim
        self.dropout = cfg.dropout
        self.qkv = nn.Linear(cfg.d_model, 3 * cfg.d_model)
        self.out = nn.Linear(cfg.d_model, cfg.d_model)

    def _split(self, x: Tensor) -> Tensor:
        b, t, _ = x.shape
        return x.view(b, t, self.n_heads, self.head_dim).transpose(1, 2)

    def forward(self, x: Tensor, cache: LayerCache | None = None) -> Tensor:
        b, t, d = x.shape
        q, k, v = self.qkv(x).chunk(3, dim=-1)
        q, k, v = self._split(q), self._split(k), self._split(v)

        if cache is not None:
            k, v = cache.append(k, v)

        # With a cache and a single new token, every cached position is in the
        # past, so no mask is needed. Without one, the usual causal mask applies.
        is_causal = t > 1
        attended = F.scaled_dot_product_attention(
            q, k, v, dropout_p=self.dropout if self.training else 0.0, is_causal=is_causal
        )
        return self.out(attended.transpose(1, 2).reshape(b, t, d))


class CrossAttention(nn.Module):
    """Multi-head attention over the fingerprint memory.

    The memory is fixed for a sequence, so its key and value projections are
    cached on first use -- a real saving when decoding 128 steps.
    """

    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.n_heads = cfg.n_heads
        self.head_dim = cfg.head_dim
        self.dropout = cfg.dropout
        self.q = nn.Linear(cfg.d_model, cfg.d_model)
        self.kv = nn.Linear(cfg.d_model, 2 * cfg.d_model)
        self.out = nn.Linear(cfg.d_model, cfg.d_model)

    def _split(self, x: Tensor) -> Tensor:
        b, t, _ = x.shape
        return x.view(b, t, self.n_heads, self.head_dim).transpose(1, 2)

    def forward(
        self,
        x: Tensor,
        memory: Tensor,
        memory_pad_mask: Tensor | None,
        cache: LayerCache | None = None,
    ) -> Tensor:
        b, t, d = x.shape
        if cache is not None and cache.cross_k is not None:
            k, v = cache.cross_k, cache.cross_v
        else:
            k, v = self.kv(memory).chunk(2, dim=-1)
            k, v = self._split(k), self._split(v)
            if cache is not None:
                cache.cross_k, cache.cross_v = k, v

        attn_mask = None
        if memory_pad_mask is not None:
            # scaled_dot_product_attention takes True as "attend here", the
            # opposite of the key_padding_mask convention.
            attn_mask = (~memory_pad_mask)[:, None, None, :]

        attended = F.scaled_dot_product_attention(
            self._split(self.q(x)),
            k,
            v,
            attn_mask=attn_mask,
            dropout_p=self.dropout if self.training else 0.0,
        )
        return self.out(attended.transpose(1, 2).reshape(b, t, d))


class DecoderLayer(nn.Module):
    """Pre-norm decoder layer: self-attention, cross-attention, feed-forward."""

    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.norm1 = nn.LayerNorm(cfg.d_model)
        self.self_attn = SelfAttention(cfg)
        self.norm2 = nn.LayerNorm(cfg.d_model)
        self.cross_attn = CrossAttention(cfg)
        self.norm3 = nn.LayerNorm(cfg.d_model)
        self.ff = nn.Sequential(
            nn.Linear(cfg.d_model, cfg.d_ff),
            nn.GELU(),
            nn.Dropout(cfg.dropout),
            nn.Linear(cfg.d_ff, cfg.d_model),
        )
        self.dropout = nn.Dropout(cfg.dropout)

    def forward(
        self,
        x: Tensor,
        memory: Tensor,
        memory_pad_mask: Tensor | None,
        cache: LayerCache | None = None,
    ) -> Tensor:
        x = x + self.dropout(self.self_attn(self.norm1(x), cache))
        x = x + self.dropout(self.cross_attn(self.norm2(x), memory, memory_pad_mask, cache))
        return x + self.dropout(self.ff(self.norm3(x)))


class FPSetEncoder(nn.Module):
    """Encodes a fingerprint as a sequence of its set bits."""

    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.bit_embedding = nn.Embedding(cfg.fp_vocab_size, cfg.d_model)
        # Index 0 is unused (counts start at 1) but kept so clamping is simple.
        self.count_embedding = nn.Embedding(MAX_COUNT + 1, cfg.d_model)
        self.dropout = nn.Dropout(cfg.dropout)
        layer = nn.TransformerEncoderLayer(
            d_model=cfg.d_model,
            nhead=cfg.n_heads,
            dim_feedforward=cfg.d_ff,
            dropout=cfg.dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(
            layer, cfg.n_encoder_layers, enable_nested_tensor=False
        )
        self.norm = nn.LayerNorm(cfg.d_model)

    def forward(
        self, fp_indices: Tensor, fp_counts: Tensor, fp_mask: Tensor
    ) -> tuple[Tensor, Tensor]:
        """
        Args:
            fp_indices: ``(batch, n_bits)`` embedding indices, zero-padded.
            fp_counts: ``(batch, n_bits)`` counts, clamped to :data:`MAX_COUNT`.
            fp_mask: ``(batch, n_bits)`` True at real bits.

        Returns:
            ``(memory, memory_pad_mask)``, the latter True at padding.
        """
        x = self.bit_embedding(fp_indices) + self.count_embedding(fp_counts.clamp(0, MAX_COUNT))
        x = self.dropout(x)

        # A row with no unmasked positions makes attention softmax over an
        # all-(-inf) row, giving NaN that silently poisons the batch. Every real
        # molecule sets at least one bit, so this only fires on degenerate
        # input -- but such a NaN is very hard to trace back.
        safe_mask = fp_mask.clone()
        empty = ~safe_mask.any(dim=1)
        if empty.any():
            safe_mask[empty, 0] = True

        memory = self.encoder(x, src_key_padding_mask=~safe_mask)
        return self.norm(memory), ~safe_mask


class Morg2SmilesModel(nn.Module):
    """Fingerprint set encoder plus a causal SMILES decoder.

    Carries its own :class:`ModelConfig`, :class:`FPConfig` and tokenizer, so a
    checkpoint is self-describing and cannot be used with the wrong fingerprint
    settings or vocabulary.
    """

    def __init__(self, cfg: ModelConfig, fp_cfg: FPConfig, tokenizer: SmilesTokenizer):
        super().__init__()
        if cfg.vocab_size != len(tokenizer):
            raise ValueError(
                f"model config vocab_size={cfg.vocab_size} != tokenizer size {len(tokenizer)}"
            )
        if cfg.fp_vocab_size != fp_cfg.vocab_size:
            raise ValueError(
                f"model config fp_vocab_size={cfg.fp_vocab_size} != "
                f"fingerprint config vocab_size {fp_cfg.vocab_size}"
            )
        self.cfg = cfg
        self.fp_cfg = fp_cfg
        self.tokenizer = tokenizer

        self.fp_encoder = FPSetEncoder(cfg)
        self.token_embedding = nn.Embedding(
            cfg.vocab_size, cfg.d_model, padding_idx=tokenizer.pad_id
        )
        self.position_embedding = nn.Embedding(cfg.max_tokens, cfg.d_model)
        self.dropout = nn.Dropout(cfg.dropout)
        self.layers = nn.ModuleList(DecoderLayer(cfg) for _ in range(cfg.n_decoder_layers))
        self.norm = nn.LayerNorm(cfg.d_model)
        self.output = nn.Linear(cfg.d_model, cfg.vocab_size)
        # Weight tying: input and output token spaces are identical, and sharing
        # them frees parameters better spent on depth.
        self.output.weight = self.token_embedding.weight

        self.apply(self._init_weights)

    @staticmethod
    def _init_weights(module: nn.Module) -> None:
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, std=0.02)

    @property
    def n_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters())

    def encode_fp(self, fp_indices: Tensor, fp_counts: Tensor, fp_mask: Tensor):
        """Run the set encoder. Separated out so sampling can reuse the memory."""
        return self.fp_encoder(fp_indices, fp_counts, fp_mask)

    def new_caches(
        self, batch: int, *, max_len: int | None = None, device: torch.device | None = None
    ) -> list[LayerCache]:
        """Fresh per-layer caches for one incremental decoding run.

        Args:
            batch: Number of sequences decoded in parallel.
            max_len: Capacity to preallocate. Defaults to the model's
                ``max_tokens``.
            device: Where to allocate. Defaults to the model's device.
        """
        device = device or next(self.parameters()).device
        dtype = next(self.parameters()).dtype
        return [
            LayerCache(
                batch,
                self.cfg.n_heads,
                self.cfg.head_dim,
                max_len or self.cfg.max_tokens,
                device,
                dtype,
            )
            for _ in self.layers
        ]

    def decode_step(
        self,
        tokens: Tensor,
        memory: Tensor,
        memory_pad_mask: Tensor | None,
        *,
        caches: list[LayerCache] | None = None,
        offset: int = 0,
    ) -> Tensor:
        """Score next-token logits.

        Args:
            tokens: ``(batch, seq)`` token ids. With ``caches``, pass only the
                new token(s); without, pass the whole prefix.
            memory: Encoder output.
            memory_pad_mask: True at padded memory positions.
            caches: Per-layer caches from :meth:`new_caches`, updated in place.
            offset: Absolute position of ``tokens[:, 0]``, so position
                embeddings stay correct during incremental decoding.

        Returns:
            ``(batch, seq, vocab)`` logits.
        """
        seq = tokens.size(1)
        if offset + seq > self.cfg.max_tokens:
            raise ValueError(f"position {offset + seq} exceeds max_tokens {self.cfg.max_tokens}")

        positions = torch.arange(offset, offset + seq, device=tokens.device)
        x = self.dropout(self.token_embedding(tokens) + self.position_embedding(positions))

        for i, layer in enumerate(self.layers):
            x = layer(x, memory, memory_pad_mask, caches[i] if caches is not None else None)
        return self.output(self.norm(x))

    def forward(
        self, fp_indices: Tensor, fp_counts: Tensor, fp_mask: Tensor, tokens: Tensor
    ) -> Tensor:
        """Teacher-forced forward pass.

        Args:
            tokens: Full target sequence including ``<bos>`` and ``<eos>``.

        Returns:
            ``(batch, seq - 1, vocab)`` logits, aligned so position ``i``
            predicts ``tokens[:, i + 1]``.
        """
        memory, memory_pad_mask = self.encode_fp(fp_indices, fp_counts, fp_mask)
        return self.decode_step(tokens[:, :-1], memory, memory_pad_mask)

    # -- persistence -----------------------------------------------------------
    def save(self, path: str | Path, **extra) -> None:
        """Write a self-describing checkpoint."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "model_config": self.cfg.to_dict(),
                "fp_config": self.fp_cfg.to_dict(),
                "tokenizer": self.tokenizer.to_dict(),
                "state_dict": self.state_dict(),
                **extra,
            },
            path,
        )

    @classmethod
    def load(
        cls, path: str | Path, *, device: torch.device | str = "cpu", strict: bool = True
    ) -> tuple[Morg2SmilesModel, dict]:
        """Load a checkpoint written by :meth:`save`.

        Returns:
            ``(model, checkpoint)``; the checkpoint retains extras saved
            alongside, such as the validation report.
        """
        ckpt = torch.load(Path(path), map_location=device, weights_only=False)
        model = cls(
            ModelConfig.from_dict(ckpt["model_config"]),
            FPConfig.from_dict(ckpt["fp_config"]),
            SmilesTokenizer.from_dict(ckpt["tokenizer"]),
        )
        model.load_state_dict(ckpt["state_dict"], strict=strict)
        model.to(device)
        model.eval()
        return model, ckpt


def build_model(
    model_cfg: ModelConfig, fp_cfg: FPConfig, tokenizer: SmilesTokenizer
) -> Morg2SmilesModel:
    """Build a model, filling in the config fields that derive from its inputs."""
    model_cfg = replace(model_cfg, vocab_size=len(tokenizer), fp_vocab_size=fp_cfg.vocab_size)
    return Morg2SmilesModel(model_cfg, fp_cfg, tokenizer)
