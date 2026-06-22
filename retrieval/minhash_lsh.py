
# retrieval/minhash_lsh.py
"""
Minimal MinHash + LSH utilities for token or graph shingles.

This module is deliberately dependency–free so it can be used in the
recall stage (M0–M1) and pickled as part of the index object.

The design is standard:
- MinHasher: generates a fixed‑length minhash signature for a multiset
  of shingles (strings).
- LSH: buckets signatures into bands and supports approximate
  near‑neighbor queries.
"""
from __future__ import annotations

import hashlib
from typing import Iterable, List, Set, Dict, Tuple

_MASK_64 = (1 << 64) - 1


def _hash_bytes(x: bytes, seed: int) -> int:
    """64‑bit hash via blake2b with a per‑permutation seed."""
    h = hashlib.blake2b(digest_size=8, person=seed.to_bytes(8, "little"))
    h.update(x)
    return int.from_bytes(h.digest(), "little")


def _hash_str(s: str, seed: int) -> int:
    return _hash_bytes(s.encode("utf-8"), seed)


def shingles(tokens: List[str], k: int = 5) -> Set[str]:
    """Form k‑gram shingles from a token sequence.

    Returns a set of joined tokens, e.g. "tok0|tok1|tok2".
    If the sequence is shorter than k, returns the empty set.
    """
    if k <= 0:
        raise ValueError("k must be positive")
    if len(tokens) < k:
        return set()
    return {"|".join(tokens[i : i + k]) for i in range(len(tokens) - k + 1)}


class MinHasher:
    """Simple minhash implementation with deterministic permutation seeds."""

    def __init__(self, num_perm: int = 128, seed: int = 2025) -> None:
        if num_perm <= 0:
            raise ValueError("num_perm must be positive")
        self.num_perm = int(num_perm)
        self.seed = int(seed)
        # Deterministic set of seeds for the permutations.
        # Use a simple LCG‑style progression on 64‑bit space.
        self._perm_seeds = [
            (self.seed * 0x9E3779B97F4A7C15 + i * 0xBF58476D1CE4E5B9) & _MASK_64
            for i in range(self.num_perm)
        ]

    def signature(self, shingle_set: Iterable[str]) -> List[int]:
        """Compute a minhash signature for a set (or iterable) of shingles."""
        # Materialise once since we scan multiple times.
        shingles_list = list(shingle_set)
        if not shingles_list:
            # Empty set → all max values so distance is well‑defined.
            return [ _MASK_64 ] * self.num_perm

        sig: List[int] = []
        for perm_seed in self._perm_seeds:
            m = _MASK_64
            for sh in shingles_list:
                hv = _hash_str(sh, perm_seed)
                if hv < m:
                    m = hv
            sig.append(m)
        return sig


class LSH:
    """Banding‑based LSH for fixed‑length minhash signatures.

    Each band stores a dict: band_hash -> set(doc_id).
    """

    def __init__(self, bands: int = 32) -> None:
        if bands <= 0:
            raise ValueError("bands must be positive")
        self.bands = int(bands)
        self.rows: int | None = None
        self.tables: List[Dict[int, Set[str]]] | None = None

    def _ensure(self, sig_len: int) -> None:
        if self.rows is None:
            if sig_len % self.bands != 0:
                raise ValueError(
                    f"signature length {sig_len} must be divisible by bands={self.bands}"
                )
            self.rows = sig_len // self.bands
            self.tables = [dict() for _ in range(self.bands)]
        elif self.rows * self.bands != sig_len:
            raise ValueError(
                f"signature length {sig_len} inconsistent with existing bands/rows "
                f"({self.bands} * {self.rows})"
            )

    @staticmethod
    def _band_hash(vals: Tuple[int, ...]) -> int:
        """Combine a small tuple of 64‑bit ints into a single 64‑bit hash.

        Use FNV‑1a over 64‑bit words for determinism.
        """
        x = 0xCBF29CE484222325  # FNV offset basis
        for v in vals:
            x ^= v & _MASK_64
            x = (x * 0x100000001B3) & _MASK_64  # FNV prime
        return x

    def insert(self, doc_id: str, signature: List[int]) -> None:
        self._ensure(len(signature))
        assert self.tables is not None and self.rows is not None
        for b in range(self.bands):
            start = b * self.rows
            end = start + self.rows
            hv = self._band_hash(tuple(signature[start:end]))
            bucket = self.tables[b].setdefault(hv, set())
            bucket.add(doc_id)

    def query(self, signature: List[int]) -> Set[str]:
        self._ensure(len(signature))
        assert self.tables is not None and self.rows is not None
        result: Set[str] = set()
        for b in range(self.bands):
            start = b * self.rows
            end = start + self.rows
            hv = self._band_hash(tuple(signature[start:end]))
            bucket = self.tables[b].get(hv)
            if bucket:
                result |= bucket
        return result


def save_index(path: str, obj) -> None:
    """Helper to pickle an index object."""
    import pickle

    with open(path, "wb") as f:
        pickle.dump(obj, f)


def load_index(path: str):
    """Helper to unpickle an index object."""
    import pickle

    with open(path, "rb") as f:
        return pickle.load(f)
